import tempfile
import unittest
from pathlib import Path

from jobs_agent.core import Job
from jobs_agent.store import JobStore


class StoreTests(unittest.TestCase):
    def test_upsert_reports_only_new_jobs_and_preserves_saved_state(self):
        with tempfile.TemporaryDirectory() as directory:
            store = JobStore(Path(directory) / "jobs.db")
            job = Job(id="abc", title="Junior Developer", company="Acme", location="Berlin", url="https://x", description="Python", source="test", role_type="entry-level", category="cs", score=75, reasons=["Entry-level role"])
            self.assertEqual(store.upsert([job]), 1)
            store.set_status("abc", "saved")
            updated = Job(id="abc", title="Junior Developer", company="Acme", location="Berlin", url="https://x", description="Python backend", source="test", role_type="entry-level", category="part-time", score=80, reasons=["Entry-level role"])
            self.assertEqual(store.upsert([updated]), 0)
            rows = store.list_jobs()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "saved")
            self.assertEqual(rows[0]["score"], 80)
            self.assertEqual(rows[0]["category"], "part-time")


if __name__ == "__main__":
    unittest.main()
