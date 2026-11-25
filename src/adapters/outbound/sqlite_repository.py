"""Adaptador secundario SQLite; ninguna evaluación SLA se realiza en SQL."""

import sqlite3
from datetime import datetime, timedelta
from typing import List

from src.domain.models import Incident, SeverityLevel
from src.domain.sla_calculator import SLA_POLICY_TABLE


class SQLiteIncidentRepository:
    """Una conexión por instancia; usar como gestor de contexto."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._persistent = db_path != ":memory:"
        self.conn = sqlite3.connect(db_path, timeout=15)
        self.conn.row_factory = sqlite3.Row
        try:
            self._init_schema()
        except BaseException:
            self.conn.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        with self.conn:
            # Serializar la migración inicial ante accesos simultáneos.
            self.conn.execute("BEGIN IMMEDIATE")
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS sla_policies (
                    severity TEXT PRIMARY KEY,
                    max_resolution_minutes INTEGER NOT NULL,
                    operates_24x7 INTEGER NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    component TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    recommended_team TEXT,
                    duplicate_group_key TEXT
                )
            """)
            columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(incidents)")}
            if "recommended_team" not in columns:
                self.conn.execute("ALTER TABLE incidents ADD COLUMN recommended_team TEXT")
            if "duplicate_group_key" not in columns:
                self.conn.execute("ALTER TABLE incidents ADD COLUMN duplicate_group_key TEXT")
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_incidents_component_status
                ON incidents(component, status)
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_incidents_dup_key
                ON incidents(duplicate_group_key, status)
            """)
            self.conn.executemany("""
                INSERT INTO sla_policies (severity, max_resolution_minutes, operates_24x7)
                VALUES (?, ?, ?)
                ON CONFLICT(severity) DO UPDATE SET
                    max_resolution_minutes=excluded.max_resolution_minutes,
                    operates_24x7=excluded.operates_24x7
                WHERE max_resolution_minutes != excluded.max_resolution_minutes
                   OR operates_24x7 != excluded.operates_24x7
            """, [(rule.severity, rule.max_resolution_minutes, int(rule.operates_24x7))
                  for rule in SLA_POLICY_TABLE.values()])

    @staticmethod
    def _to_incident(row: sqlite3.Row) -> Incident:
        return Incident(
            incident_id=row["incident_id"], title=row["title"],
            component=row["component"], severity=row["severity"], status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
            recommended_team=row["recommended_team"],
            duplicate_group_key=row["duplicate_group_key"],
        )

    def supports_persistent_writes(self) -> bool:
        return self._persistent

    def save_incident(self, incident: Incident, duplicate_group_key: str | None = None) -> bool:
        key = incident.duplicate_group_key if duplicate_group_key is None else duplicate_group_key
        with self.conn:
            cursor = self.conn.execute("""
                INSERT INTO incidents (incident_id, title, component, severity, status,
                                       created_at, resolved_at, recommended_team, duplicate_group_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(incident_id) DO NOTHING
            """, (incident.incident_id, incident.title, incident.component, incident.severity,
                  incident.status, incident.created_at.isoformat(),
                  incident.resolved_at.isoformat() if incident.resolved_at else None,
                  incident.recommended_team, key))
        return cursor.rowcount == 1

    def get_incident(self, incident_id: str) -> Incident | None:
        row = self.conn.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)).fetchone()
        return self._to_incident(row) if row else None

    def find_open_duplicates(self, duplicate_group_key: str, incident_id: str = "") -> list[str]:
        if not duplicate_group_key:
            return []
        rows = self.conn.execute("""
            SELECT incident_id FROM incidents WHERE duplicate_group_key = ?
            AND status IN ('OPEN', 'IN_PROGRESS', 'ESCALATION_REQUIRED')
            AND incident_id <> ? ORDER BY incident_id
        """, (duplicate_group_key, incident_id))
        return [row["incident_id"] for row in rows]

    def list_active_incidents(self, component_filter: str | None = None) -> list[Incident]:
        sql = """
            SELECT i.* FROM incidents AS i
            INNER JOIN sla_policies AS p ON p.severity = i.severity
            WHERE i.status IN ('OPEN', 'IN_PROGRESS')
        """
        params = ()
        if component_filter is not None:
            sql += " AND i.component = ?"
            params = (component_filter,)
        sql += " ORDER BY i.incident_id"
        return [self._to_incident(row) for row in self.conn.execute(sql, params)]

    def check_health(self) -> bool:
        try:
            return self.conn.execute("SELECT 1").fetchone()[0] == 1
        except sqlite3.Error:
            return False

    def seed_synthetic_incidents(self, total_records: int = 10000) -> None:
        """Puebla la base de datos con registros sintéticos para pruebas de rendimiento."""
        components = [
            "payments-gateway",
            "auth-identity",
            "database-cluster",
            "reporting-api",
            "frontend-ui",
        ]
        severities: List[SeverityLevel] = ["P0", "P1", "P2", "P3"]
        statuses = ["RESOLVED", "RESOLVED", "RESOLVED", "OPEN", "IN_PROGRESS"]
        base_time = datetime(2026, 11, 1, 8, 0, 0)

        rows = []
        for idx in range(1, total_records + 1):
            sev = severities[idx % len(severities)]
            status = statuses[(idx * 3 + idx // 5) % len(statuses)]
            comp = components[idx % len(components)]
            created = base_time + timedelta(minutes=((idx - 1) % 10000 + 1) * 2)
            resolved = (created + timedelta(minutes=45)).isoformat() if status == "RESOLVED" else None
            rows.append(
                (
                    f"INC-{idx:05d}",
                    f"Reporte sintético #{idx} en {comp}",
                    comp,
                    sev,
                    status,
                    created.isoformat(),
                    resolved,
                )
            )

        cursor = self.conn.cursor()
        cursor.executemany(
            """
            INSERT OR REPLACE INTO incidents
            (incident_id, title, component, severity, status, created_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

