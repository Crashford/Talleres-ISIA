"""Adaptador secundario PostgreSQL; sin ORM y sin cálculo SLA en SQL."""

from datetime import datetime

from src.domain.models import Incident
from src.domain.sla_calculator import SLA_POLICY_TABLE


class PostgresIncidentRepository:
    """Conexión diferida; usar como gestor de contexto."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn = None

    def __enter__(self) -> "PostgresIncidentRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close()
        return False

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
        self._conn = None

    def _connect(self):
        from psycopg import connect
        from psycopg.rows import dict_row

        conn = connect(self._dsn, row_factory=dict_row)
        self._conn = conn
        try:
            self._init_schema()
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            finally:
                conn.close()
                self._conn = None
            raise
        return conn

    def _connection(self):
        if self._conn is None or self._conn.closed:
            return self._connect()
        return self._conn

    def _init_schema(self) -> None:
        conn = self._conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sla_policies (
                severity TEXT PRIMARY KEY,
                max_resolution_minutes INTEGER NOT NULL,
                operates_24x7 INTEGER NOT NULL
            )
        """)
        conn.execute("""
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
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_incidents_component_status
            ON incidents(component, status)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_incidents_dup_key
            ON incidents(duplicate_group_key, status)
        """)
        for rule in SLA_POLICY_TABLE.values():
            conn.execute(
                """
                INSERT INTO sla_policies (severity, max_resolution_minutes, operates_24x7)
                VALUES (%s, %s, %s)
                ON CONFLICT (severity) DO UPDATE SET
                    max_resolution_minutes = EXCLUDED.max_resolution_minutes,
                    operates_24x7 = EXCLUDED.operates_24x7
                WHERE sla_policies.max_resolution_minutes != EXCLUDED.max_resolution_minutes
                   OR sla_policies.operates_24x7 != EXCLUDED.operates_24x7
                """,
                (rule.severity, rule.max_resolution_minutes, int(rule.operates_24x7)),
            )

    @staticmethod
    def _to_incident(row) -> Incident:
        return Incident(
            incident_id=row["incident_id"],
            title=row["title"],
            component=row["component"],
            severity=row["severity"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
            recommended_team=row["recommended_team"],
            duplicate_group_key=row["duplicate_group_key"],
        )

    def supports_persistent_writes(self) -> bool:
        return True

    def save_incident(self, incident: Incident, duplicate_group_key: str | None = None) -> bool:
        key = incident.duplicate_group_key if duplicate_group_key is None else duplicate_group_key
        conn = self._connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO incidents (incident_id, title, component, severity, status,
                                       created_at, resolved_at, recommended_team, duplicate_group_key)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (incident_id) DO NOTHING
                """,
                (
                    incident.incident_id,
                    incident.title,
                    incident.component,
                    incident.severity,
                    incident.status,
                    incident.created_at.isoformat(),
                    incident.resolved_at.isoformat() if incident.resolved_at else None,
                    incident.recommended_team,
                    key,
                ),
            )
            inserted = cursor.rowcount == 1
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return inserted

    def get_incident(self, incident_id: str) -> Incident | None:
        row = self._connection().execute(
            "SELECT * FROM incidents WHERE incident_id = %s", (incident_id,)
        ).fetchone()
        return self._to_incident(row) if row else None

    def find_open_duplicates(self, duplicate_group_key: str, incident_id: str = "") -> list[str]:
        if not duplicate_group_key:
            return []
        rows = self._connection().execute(
            """
            SELECT incident_id FROM incidents
            WHERE duplicate_group_key = %s
            AND status IN ('OPEN', 'IN_PROGRESS', 'ESCALATION_REQUIRED')
            AND incident_id <> %s ORDER BY incident_id
            """,
            (duplicate_group_key, incident_id),
        ).fetchall()
        return [row["incident_id"] for row in rows]

    def list_active_incidents(self, component_filter: str | None = None) -> list[Incident]:
        sql = """
            SELECT i.* FROM incidents AS i
            INNER JOIN sla_policies AS p ON p.severity = i.severity
            WHERE i.status IN ('OPEN', 'IN_PROGRESS')
        """
        params: tuple
        if component_filter is None:
            params = ()
        else:
            sql += " AND i.component = %s"
            params = (component_filter,)
        sql += " ORDER BY i.incident_id"
        rows = self._connection().execute(sql, params).fetchall()
        return [self._to_incident(row) for row in rows]

    @staticmethod
    def _first_row_value(row) -> object:
        if hasattr(row, "values"):
            return next(iter(row.values()), None)
        return row[0]

    def check_health(self) -> bool:
        try:
            row = self._connection().execute("SELECT 1").fetchone()
            if row is None:
                return False
            return self._first_row_value(row) == 1
        except Exception:
            return False
