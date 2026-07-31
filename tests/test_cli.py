import tempfile
import unittest
from pathlib import Path

from jobs_agent.cli import run_fetch, run_publish
from jobs_agent.core import Job
from jobs_agent.store import JobStore


class CliTests(unittest.TestCase):
    def test_run_fetch_stores_jobs_and_returns_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            store = JobStore(Path(directory) / "jobs.db")
            job = Job(id="x", title="Werkstudent Developer", company="Acme", location="Berlin", url="https://x", description="Python", source="test", role_type="werkstudent", score=90, reasons=["Werkstudent role"])
            new_count, digest = run_fetch(store, fetcher=lambda: [job])
            self.assertEqual(new_count, 1)
            self.assertIn("Werkstudent Developer", digest)
            self.assertEqual(len(store.list_jobs()), 1)

    def test_run_publish_writes_message_for_new_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job = Job(id="x", title="Werkstudent Developer", company="Acme", location="Berlin", url="https://x", description="Python", source="test", role_type="werkstudent", score=90, reasons=["Werkstudent role"])
            count = run_publish(lambda: [job], root / "docs", root / "telegram.txt", "https://example.test/")
            self.assertEqual(count, 1)
            self.assertTrue((root / "docs" / "index.html").exists())
            self.assertIn("Werkstudent Developer", (root / "telegram.txt").read_text())


if __name__ == "__main__":
    unittest.main()
