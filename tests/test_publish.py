import json
import tempfile
import unittest
from pathlib import Path

from jobs_agent.core import Job
from jobs_agent.publish import publish_jobs, telegram_message


class PublishTests(unittest.TestCase):
    def make_job(self, job_id: str, title: str) -> Job:
        return Job(
            id=job_id, title=title, company="Acme", location="Berlin, Deutschland",
            url=f"https://example.test/{job_id}", description="Python",
            source="fixture", role_type="werkstudent", score=90,
            reasons=["Werkstudent role", "Computer-science relevance"],
        )

    def test_publish_writes_static_dashboard_and_reports_only_new_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            docs = Path(directory) / "docs"
            docs.mkdir()
            (docs / "jobs.json").write_text(json.dumps([{"id": "old"}]))

            jobs = [self.make_job("old", "Old role"), self.make_job("new", "New role")]
            new_jobs = publish_jobs(jobs, docs)

            self.assertEqual([job.id for job in new_jobs], ["new"])
            exported = json.loads((docs / "jobs.json").read_text())
            self.assertEqual({job["id"] for job in exported}, {"old", "new"})
            html = (docs / "index.html").read_text()
            self.assertIn("jobs.json", html)
            self.assertIn("localStorage", html)
            self.assertIn("Germany CS Jobs", html)

    def test_telegram_message_contains_new_roles_and_live_site(self):
        message = telegram_message(
            [self.make_job("new", "Working Student Backend")],
            "https://ot-coder.github.io/germany-cs-jobs-agent/",
        )
        self.assertIn("1 new suitable role", message)
        self.assertIn("Working Student Backend", message)
        self.assertIn("Open dashboard", message)

    def test_telegram_message_is_empty_without_new_jobs(self):
        self.assertEqual(telegram_message([], "https://example.test"), "")


if __name__ == "__main__":
    unittest.main()
