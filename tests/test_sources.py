import unittest

from jobs_agent.sources import fetch_all, normalize_arbeitnow, normalize_ba


class SourceTests(unittest.TestCase):
    def test_normalizes_arbeitnow_job(self):
        raw = {
            "slug": "working-student-python-acme",
            "title": "Working Student Python Developer",
            "company_name": "Acme",
            "location": "Berlin",
            "url": "https://example.com/job",
            "description": "<p>For enrolled computer science students</p>",
            "remote": False,
            "created_at": 1700000000,
        }
        job = normalize_arbeitnow(raw)
        self.assertEqual(job.role_type, "werkstudent")
        self.assertEqual(job.description, "For enrolled computer science students")
        self.assertEqual(job.source, "arbeitnow")
        self.assertGreaterEqual(job.score, 70)

    def test_normalizes_bundesagentur_job(self):
        raw = {
            "titel": "Werkstudent Informatik (m/w/d)", "arbeitgeber": "PC Shop",
            "refnr": "10001-ABC-S", "arbeitsort": {"ort": "Stralsund", "region": "Mecklenburg-Vorpommern", "land": "Deutschland"},
            "beruf": "Informatiker/in", "aktuelleVeroeffentlichungsdatum": "2026-03-17",
        }
        job = normalize_ba(raw)
        self.assertEqual(job.source, "bundesagentur")
        self.assertEqual(job.location, "Stralsund, Mecklenburg-Vorpommern, Deutschland")
        self.assertIn("10001-ABC-S", job.url)
        self.assertGreaterEqual(job.score, 70)

    def test_fetch_all_keeps_only_suitable_roles_and_deduplicates(self):
        def fake_fetch(url):
            if "arbeitnow" in url:
                return {"data": [
                    {"title": "Werkstudent Software Engineer", "company_name": "Acme", "location": "Berlin", "url": "https://a/1", "description": "Computer science student Python"},
                    {"title": "Senior Software Engineer", "company_name": "Acme", "location": "Berlin", "url": "https://a/2", "description": "Python"},
                ]}
            if "arbeitsagentur" in url:
                return {"stellenangebote": [
                    {"titel": "Werkstudent Informatik", "arbeitgeber": "Gamma", "refnr": "BA-1", "arbeitsort": {"ort": "Hamburg", "land": "Deutschland"}, "beruf": "Informatiker/in"}
                ]}
            return {"jobs": [
                {"title": "Werkstudent Software Engineer", "company_name": "Acme", "candidate_required_location": "Berlin", "url": "https://r/1", "description": "Computer science student Python"},
                {"title": "Junior Data Analyst", "company_name": "Beta", "candidate_required_location": "Germany", "url": "https://r/2", "description": "Entry level data role"},
            ]}

        jobs = fetch_all(fetch_json=fake_fetch, min_score=60)
        self.assertEqual({job.title for job in jobs}, {"Werkstudent Software Engineer", "Werkstudent Informatik", "Junior Data Analyst"})


if __name__ == "__main__":
    unittest.main()
