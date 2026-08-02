import unittest
from datetime import date

from jobs_agent.schedule import should_run


class ScheduleTests(unittest.TestCase):
    def test_manual_runs_always_execute(self):
        self.assertTrue(should_run("workflow_dispatch", "", date(2026, 8, 2)))

    def test_summer_selects_06_utc_even_if_workflow_execution_is_delayed(self):
        self.assertTrue(should_run("schedule", "0 6 * * *", date(2026, 8, 2)))
        self.assertFalse(should_run("schedule", "0 7 * * *", date(2026, 8, 2)))

    def test_winter_selects_07_utc(self):
        self.assertFalse(should_run("schedule", "0 6 * * *", date(2026, 12, 2)))
        self.assertTrue(should_run("schedule", "0 7 * * *", date(2026, 12, 2)))


if __name__ == "__main__":
    unittest.main()
