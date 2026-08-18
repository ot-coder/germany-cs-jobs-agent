import json
import tempfile
import unittest
from pathlib import Path

from jobs_agent.core import Job
from jobs_agent.publish import notify_tier, publish_jobs, telegram_message


class PublishTests(unittest.TestCase):
    def make_job(self, job_id: str, title: str, score: int = 90, role_family: str = "CORE_TECH") -> Job:
        return Job(
            id=job_id, title=title, company="Acme", location="Berlin, Deutschland",
            url=f"https://example.test/{job_id}", description="Python",
            source="fixture", role_family=role_family, score=score,
            reasons=["Credible Core Tech entry point", "Clear entry-level/student framing"],
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
            self.assertIn("role_family", html)

    def test_jobs_omitted_by_telegram_cap_do_not_reappear_as_new_next_run(self):
        # Day 1: 20 new jobs discovered, only 5 fit the Telegram cap. All 20
        # must still be written to docs/jobs.json as "known". Day 2: fetching
        # the identical 20 jobs again must report zero new jobs, because they
        # are already present in the previously-published dataset.
        with tempfile.TemporaryDirectory() as directory:
            docs = Path(directory) / "docs"
            docs.mkdir()
            jobs = [self.make_job(f"job{i}", f"Role {i}", score=95 - i) for i in range(20)]

            day1_new = publish_jobs(jobs, docs)
            self.assertEqual(len(day1_new), 20)
            day1_message = telegram_message(day1_new, evaluated=25, duplicates_removed=2, passed_threshold=20, site_url="https://example.test")
            self.assertIn("5 new suitable roles", day1_message)

            day2_new = publish_jobs(jobs, docs)
            self.assertEqual(day2_new, [])
            day2_message = telegram_message(day2_new, evaluated=25, duplicates_removed=2, passed_threshold=20, site_url="https://example.test")
            self.assertEqual(day2_message, "")

    def test_publish_writes_all_new_jobs_even_beyond_telegram_cap(self):
        # publish_jobs() must persist every passing job to docs/jobs.json,
        # not just the subset Telegram will surface — the Telegram cap is a
        # notification concern, not a dashboard/state concern.
        with tempfile.TemporaryDirectory() as directory:
            docs = Path(directory) / "docs"
            docs.mkdir()
            jobs = [self.make_job(f"job{i}", f"Role {i}", score=95 - i) for i in range(20)]
            new_jobs = publish_jobs(jobs, docs)
            self.assertEqual(len(new_jobs), 20)
            exported = json.loads((docs / "jobs.json").read_text())
            self.assertEqual(len(exported), 20)


class NotifyTierTests(unittest.TestCase):
    def test_tier_boundaries(self):
        self.assertEqual(notify_tier(95)[0], "EXCEPTIONAL")
        self.assertEqual(notify_tier(85)[0], "APPLY")
        self.assertEqual(notify_tier(78)[0], "REVIEW")
        self.assertEqual(notify_tier(70)[0], "SILENT")
        self.assertEqual(notify_tier(40)[0], "SILENT")


class TelegramMessageTests(unittest.TestCase):
    def make_job(self, job_id: str, title: str, score: int) -> Job:
        return Job(
            id=job_id, title=title, company="Acme", location="Berlin, Germany",
            url=f"https://example.test/{job_id}", description="Python",
            source="fixture", role_family="CORE_TECH", score=score,
            reasons=["Credible Core Tech entry point", "Clear entry-level/student framing"],
        )

    def test_telegram_message_contains_new_roles_and_live_site(self):
        message = telegram_message(
            [self.make_job("new", "Working Student Backend", 90)],
            evaluated=10, duplicates_removed=1, passed_threshold=1,
            site_url="https://ot-coder.github.io/germany-cs-jobs-agent/",
        )
        self.assertIn("1 new suitable role", message)
        self.assertIn("Working Student Backend", message)
        self.assertIn("Open dashboard", message)
        self.assertIn("EXCEPTIONAL", message)

    def test_telegram_message_is_empty_without_new_jobs(self):
        self.assertEqual(telegram_message([], 0, 0, 0, "https://example.test"), "")

    def test_zero_good_jobs_produces_no_telegram_spam(self):
        # New jobs exist, but none clears the REVIEW threshold (75) -> silent.
        silent_jobs = [self.make_job(f"s{i}", f"Role {i}", score=65 + i) for i in range(3)]
        message = telegram_message(silent_jobs, evaluated=10, duplicates_removed=0, passed_threshold=3, site_url="https://example.test")
        self.assertEqual(message, "")

    def test_caps_at_five_even_with_twenty_new_jobs(self):
        jobs = [self.make_job(f"j{i}", f"Role {i}", score=99 - i) for i in range(20)]
        message = telegram_message(jobs, evaluated=40, duplicates_removed=5, passed_threshold=20, site_url="https://example.test")
        surfaced_titles = [f"Role {i}" for i in range(5)]
        for title in surfaced_titles:
            self.assertIn(title, message)
        for title in [f"Role {i}" for i in range(5, 20)]:
            self.assertNotIn(f"— {title}", message)
        self.assertIn("5 new suitable roles", message)
        self.assertIn("20 new", message)  # summary footer still reports the full count
        self.assertIn("5 surfaced", message)

    def test_does_not_lower_threshold_to_fill_five_slots(self):
        # Only two jobs clear REVIEW (75+); the other three are SILENT and
        # must never appear even though there is spare capacity.
        jobs = [
            self.make_job("a", "Apply Role", 85),
            self.make_job("b", "Review Role", 76),
            self.make_job("c", "Silent Role One", 70),
            self.make_job("d", "Silent Role Two", 68),
            self.make_job("e", "Silent Role Three", 66),
        ]
        message = telegram_message(jobs, evaluated=10, duplicates_removed=0, passed_threshold=5, site_url="https://example.test")
        self.assertIn("Apply Role", message)
        self.assertIn("Review Role", message)
        self.assertNotIn("Silent Role", message)
        self.assertIn("2 new suitable roles", message)

    def test_includes_context_fields_per_job(self):
        message = telegram_message(
            [self.make_job("x", "Junior Data Analyst", 88)],
            evaluated=5, duplicates_removed=0, passed_threshold=1, site_url="https://example.test",
        )
        self.assertIn("Acme", message)
        self.assertIn("Berlin, Germany", message)
        self.assertIn("CORE_TECH", message)
        self.assertIn("Why:", message)
        self.assertIn("https://example.test/x", message)


if __name__ == "__main__":
    unittest.main()
