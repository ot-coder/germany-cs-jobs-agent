import tempfile
import unittest
from pathlib import Path

from jobs_agent.cli import run_fetch, run_publish
from jobs_agent.core import Job
from jobs_agent.sources import FetchResult
from jobs_agent.store import JobStore


class CliTests(unittest.TestCase):
    def make_job(self) -> Job:
        return Job(
            id="x", title="Werkstudent Developer", company="Acme", location="Berlin",
            url="https://x", description="Python", source="test", role_family="CORE_TECH",
            score=90, reasons=["Credible Core Tech entry point"],
        )

    def test_run_fetch_stores_jobs_and_returns_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            store = JobStore(Path(directory) / "jobs.db")
            job = self.make_job()
            fetcher = lambda: FetchResult(jobs=[job], evaluated=1, duplicates_removed=0, passed_threshold=1)
            new_count, digest = run_fetch(store, fetcher=fetcher)
            self.assertEqual(new_count, 1)
            self.assertIn("Werkstudent Developer", digest)
            self.assertEqual(len(store.list_jobs()), 1)

    def test_run_publish_writes_message_for_new_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job = self.make_job()
            fetcher = lambda: FetchResult(jobs=[job], evaluated=1, duplicates_removed=0, passed_threshold=1)
            count = run_publish(fetcher, root / "docs", root / "telegram.txt", "https://example.test/")
            self.assertEqual(count, 1)
            self.assertTrue((root / "docs" / "index.html").exists())
            self.assertIn("Werkstudent Developer", (root / "telegram.txt").read_text())


if __name__ == "__main__":
    unittest.main()
