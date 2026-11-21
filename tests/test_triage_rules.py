"""Pruebas de regresión para la clasificación de IncidentOps."""
import json
import unittest
from collections import defaultdict

from src.triage_rules import SAMPLE_DATA_PATH, classify_incident_report


class TestTriageRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.incidents = json.loads(SAMPLE_DATA_PATH.read_text(encoding="utf-8"))
        cls.results = {
            item["id"]: classify_incident_report(item["id"], item["raw_text"])
            for item in cls.incidents
        }

    def test_expected_severity_and_component(self):
        expected = {
            "INC-1001": ("P0", "payments-gateway", "Backend-Core"),
            "INC-1002": ("P2", "auth-identity", "Security-IAM"),
            "INC-1003": ("P2", "reporting-api", "Backend-Core"),
            "INC-1004": ("P3", "frontend-ui", "Backend-Core"),
            "INC-1005": ("P1", "database-cluster", "Data-DBA"),
            "INC-1006": ("P0", "payments-gateway", "Backend-Core"),
            "INC-1007": ("P0", "security-authorization", "Security-IAM"),
            "INC-1008": ("P2", "reporting-api", "Backend-Core"),
            "INC-1009": ("P2", "reporting-api", "Backend-Core"),
            "INC-1010": ("P3", "infra-certificates", "Platform-SRE"),
        }
        self.assertEqual(len(self.results), 10)
        for incident_id, fields in expected.items():
            result = self.results[incident_id]
            with self.subTest(incident_id=incident_id):
                self.assertEqual((result.severity, result.component, result.recommended_team), fields)

    def test_duplicate_keys(self):
        r = self.results
        self.assertEqual(r["INC-1001"].duplicate_group_key, r["INC-1006"].duplicate_group_key)
        self.assertEqual(r["INC-1003"].duplicate_group_key, r["INC-1008"].duplicate_group_key)
        self.assertNotEqual(r["INC-1003"].duplicate_group_key, r["INC-1009"].duplicate_group_key)
        self.assertTrue(all(x.duplicate_group_key.startswith(x.component + ":") for x in r.values()))

    def test_subjective_urgency_does_not_raise_severity(self):
        base = "La cuenta está bloqueada."
        self.assertEqual(classify_incident_report("A", base).severity, "P2")
        self.assertEqual(classify_incident_report("B", "URGENTE hoy: " + base).severity, "P2")

    def test_key_is_stable_across_case_and_accents(self):
        a = classify_incident_report("A", "ERROR 502 en PAGOS con TARJETA")
        b = classify_incident_report("B", "error 502 en pagos con tarjeta")
        self.assertEqual(a.duplicate_group_key, b.duplicate_group_key)


if __name__ == "__main__":
    unittest.main()
