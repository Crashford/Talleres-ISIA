"""Pruebas de regresión SLA, ventanas y estados de escalamiento."""
import unittest
from datetime import datetime, timezone, timedelta

from src.models import Incident
from src.sla_calculator import evaluate_sla_status, get_sla_rule_for_severity


class TestSLACalculator(unittest.TestCase):
    def evaluate(self, severity, start, end, status="OPEN", resolved_at=None):
        incident = Incident("TEST", "SLA test", "reporting-api", severity, status, start, resolved_at)
        return evaluate_sla_status(incident, end)

    def test_friday_to_monday_business(self):
        self.assertEqual(self.evaluate("P2", datetime(2026, 11, 6, 17), datetime(2026, 11, 9, 9)).elapsed_minutes, 120)

    def test_friday_after_hours_to_monday(self):
        self.assertEqual(self.evaluate("P2", datetime(2026, 11, 6, 18, 30), datetime(2026, 11, 9, 8, 30)).elapsed_minutes, 30)

    def test_weekend_creation(self):
        self.assertEqual(self.evaluate("P3", datetime(2026, 11, 7, 12), datetime(2026, 11, 9, 9)).elapsed_minutes, 60)

    def test_multi_day(self):
        self.assertEqual(self.evaluate("P2", datetime(2026, 11, 9, 16), datetime(2026, 11, 10, 12)).elapsed_minutes, 360)

    def test_multiple_weekends(self):
        self.assertEqual(self.evaluate("P3", datetime(2026, 11, 6, 16), datetime(2026, 11, 16, 10)).elapsed_minutes, 3240)

    def test_24x7_weekend(self):
        self.assertEqual(self.evaluate("P0", datetime(2026, 11, 6, 17), datetime(2026, 11, 9, 9)).elapsed_minutes, 3840)

    def test_p1_24x7_threshold(self):
        r = self.evaluate("P1", datetime(2026, 11, 9, 8), datetime(2026, 11, 9, 11))
        self.assertEqual(r.elapsed_minutes, 180)
        self.assertTrue(r.requires_escalation)
        self.assertFalse(r.is_breached)

    def test_below_threshold(self):
        r = self.evaluate("P2", datetime(2026, 11, 9, 8), datetime(2026, 11, 9, 13, 59))
        self.assertEqual(r.elapsed_minutes, 359)
        self.assertFalse(r.requires_escalation)

    def test_at_sla_exactly_and_after_breach(self):
        start = datetime(2026, 11, 9, 8)
        exact = self.evaluate("P0", start, datetime(2026, 11, 9, 9))
        self.assertFalse(exact.is_breached)
        self.assertTrue(exact.requires_escalation)
        breached = self.evaluate("P0", start, datetime(2026, 11, 9, 9, 1))
        self.assertTrue(breached.is_breached)
        self.assertTrue(breached.requires_escalation)
        self.assertEqual(breached.remaining_minutes, -1)

    def test_resolved_prevents_escalation_keeps_breach(self):
        start = datetime(2026, 11, 9, 8)
        resolved = datetime(2026, 11, 9, 9, 5)
        r = self.evaluate("P0", start, datetime(2026, 11, 11, 10), "RESOLVED", resolved)
        self.assertEqual(r.elapsed_minutes, 65)
        self.assertTrue(r.is_breached)
        self.assertFalse(r.requires_escalation)

    def test_same_day_edges(self):
        self.assertEqual(self.evaluate("P2", datetime(2026, 11, 9, 7), datetime(2026, 11, 9, 8)).elapsed_minutes, 0)
        self.assertEqual(self.evaluate("P2", datetime(2026, 11, 9, 17), datetime(2026, 11, 9, 20)).elapsed_minutes, 60)
        self.assertEqual(self.evaluate("P2", datetime(2026, 11, 9, 18), datetime(2026, 11, 10, 8)).elapsed_minutes, 0)

    def test_subminute_aggregation(self):
        self.assertEqual(self.evaluate("P2", datetime(2026, 11, 9, 17, 59, 30), datetime(2026, 11, 10, 8, 0, 30)).elapsed_minutes, 1)

    def test_invalid_severity(self):
        with self.assertRaises(ValueError):
            get_sla_rule_for_severity("P9")

    def test_invalid_interval(self):
        with self.assertRaises(ValueError):
            self.evaluate("P2", datetime(2026, 11, 10), datetime(2026, 11, 9))

    def test_timezone_consistency(self):
        with self.assertRaises(ValueError):
            self.evaluate("P2", datetime(2026, 11, 9, 8), datetime(2026, 11, 9, 9, tzinfo=timezone.utc))
        zone = timezone(timedelta(hours=-5))
        self.assertEqual(self.evaluate("P2", datetime(2026, 11, 9, 8, tzinfo=zone), datetime(2026, 11, 9, 9, tzinfo=zone)).elapsed_minutes, 60)

    def test_resolved_missing_timestamp(self):
        with self.assertRaises(ValueError):
            self.evaluate("P2", datetime(2026, 11, 9, 8), datetime(2026, 11, 9, 9), "RESOLVED")


if __name__ == "__main__":
    unittest.main()
