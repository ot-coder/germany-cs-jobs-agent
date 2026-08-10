import unittest

from jobs_agent.sources import (
    _parse_ba_search_html,
    fetch_all,
    is_leipzig_area,
    normalize_arbeitnow,
    normalize_ba,
)


class SourceTests(unittest.TestCase):
    def test_leipzig_area_accepts_city_and_surrounding_towns_only(self):
        for location in (
            "Leipzig, Sachsen, Deutschland",
            "Markkleeberg, Sachsen, Deutschland",
            "Schkeuditz, Sachsen, Deutschland",
            "Taucha, Sachsen, Deutschland",
            "Delitzsch, Sachsen, Deutschland",
            "Borna, Sachsen, Deutschland",
        ):
            with self.subTest(location=location):
                self.assertTrue(is_leipzig_area(location))
        for location in (
            "Stuttgart, Baden-Württemberg, Deutschland",
            "Berlin, Berlin, Deutschland",
            "Dresden, Sachsen, Deutschland",
            "Germany",
            "Remote",
        ):
            with self.subTest(location=location):
                self.assertFalse(is_leipzig_area(location))

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
        self.assertEqual(job.category, "cs")
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

    def test_normalizes_current_bundesagentur_ssr_job(self):
        raw = {
            "stellenangebotsTitel": "Werkstudent Softwareentwicklung (m/w/d)",
            "firma": "Example GmbH",
            "referenznummer": "10000-SSR-S",
            "stellenlokationen": [{"adresse": {
                "ort": "Berlin", "region": "BERLIN", "land": "DEUTSCHLAND"
            }}],
            "hauptberuf": "Softwareentwickler/in",
            "datumErsteVeroeffentlichung": "2026-08-04",
        }
        job = normalize_ba(raw)
        self.assertEqual(job.company, "Example GmbH")
        self.assertEqual(job.location, "Berlin, Berlin, Deutschland")
        self.assertIn("10000-SSR-S", job.url)
        self.assertGreaterEqual(job.score, 70)

    def test_normalizes_general_minijob_into_part_time_category(self):
        raw = {
            "stellenangebotsTitel": "Minijob Lagerhelfer (m/w/d)",
            "firma": "Warehouse GmbH",
            "referenznummer": "GENERAL-1",
            "stellenlokationen": [{"adresse": {
                "ort": "Hamburg", "region": "HAMBURG", "land": "DEUTSCHLAND"
            }}],
            "hauptberuf": "Helfer/in - Lagerwirtschaft",
        }
        job = normalize_ba(raw)
        self.assertEqual(job.role_type, "minijob")
        self.assertEqual(job.category, "part-time")
        self.assertGreaterEqual(job.score, 55)

    def test_parses_bundesagentur_ssr_search_state(self):
        html = '''<html><script id="ng-state" type="application/json">{
          "suchergebnis": {"ergebnisliste": [{"referenznummer": "SSR-1"}]}
        }</script></html>'''
        self.assertEqual(
            _parse_ba_search_html(html),
            {"stellenangebote": [{"referenznummer": "SSR-1"}]},
        )

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

    def test_fetch_all_keeps_general_part_time_jobs_only_in_leipzig_area(self):
        def fake_fetch(url):
            if "arbeitnow" in url:
                return {"data": [
                    {
                        "title": "Minijob Lagerhelfer",
                        "company_name": "Leipzig Warehouse",
                        "location": "Leipzig, Sachsen, Deutschland",
                        "url": "https://example.test/leipzig",
                        "description": "Flexible minijob shifts",
                    },
                    {
                        "title": "Minijob Lagerhelfer",
                        "company_name": "Stuttgart Warehouse",
                        "location": "Stuttgart, Baden-Württemberg, Deutschland",
                        "url": "https://example.test/stuttgart",
                        "description": "Flexible minijob shifts",
                    },
                    {
                        "title": "Aushilfe Restaurant",
                        "company_name": "Nearby Restaurant",
                        "location": "Markkleeberg, Sachsen, Deutschland",
                        "url": "https://example.test/markkleeberg",
                        "description": "Teilzeit",
                    },
                ]}
            if "remotive" in url:
                return {"jobs": []}
            return {"stellenangebote": []}

        jobs = fetch_all(fetch_json=fake_fetch, min_score=55)
        self.assertEqual(
            {job.location for job in jobs},
            {
                "Leipzig, Sachsen, Deutschland",
                "Markkleeberg, Sachsen, Deutschland",
            },
        )

    def test_fetch_all_searches_and_keeps_general_part_time_jobs(self):
        requested = []

        def fake_fetch(url):
            requested.append(url)
            if "arbeitnow" in url:
                return {"data": []}
            if "remotive" in url:
                return {"jobs": []}
            if "minijob" in url:
                return {"stellenangebote": [{
                    "stellenangebotsTitel": "Minijob Lagerhelfer",
                    "firma": "Warehouse GmbH",
                    "referenznummer": "MINI-1",
                    "stellenlokationen": [{"adresse": {
                        "ort": "Leipzig", "land": "DEUTSCHLAND"
                    }}],
                    "hauptberuf": "Helfer/in - Lagerwirtschaft",
                }]}
            return {"stellenangebote": []}

        jobs = fetch_all(fetch_json=fake_fetch, min_score=55)
        self.assertEqual([job.category for job in jobs], ["part-time"])
        self.assertTrue(any("minijob" in url for url in requested))
        self.assertTrue(any("aushilfe+lager" in url for url in requested))
        self.assertTrue(any("aushilfe+gastronomie" in url for url in requested))
        general_terms = ("minijob", "teilzeit", "studentenjob", "aushilfe+")
        general_urls = [url for url in requested if any(term in url for term in general_terms)]
        self.assertTrue(general_urls)
        self.assertTrue(all("wo=Leipzig" in url and "umkreis=35" in url for url in general_urls))
        self.assertTrue(any("werkstudent+informatik" in url and "wo=Deutschland" in url for url in requested))

    def test_fetch_all_continues_when_bundesagentur_is_unavailable(self):
        def fake_fetch(url):
            if "arbeitnow" in url:
                return {"data": [{
                    "title": "Werkstudent Python Developer",
                    "company_name": "Acme",
                    "location": "Berlin",
                    "url": "https://example.test/job",
                    "description": "Computer science student Python",
                }]}
            if "remotive" in url:
                return {"jobs": []}
            raise OSError("404 Not Found")

        jobs = fetch_all(fetch_json=fake_fetch, min_score=60)
        self.assertEqual([job.title for job in jobs], ["Werkstudent Python Developer"])

    def test_fetch_all_fails_if_every_internet_source_is_unavailable(self):
        def failing_fetch(url):
            raise OSError("503 Unavailable")

        with self.assertRaisesRegex(RuntimeError, "All job sources failed"):
            fetch_all(fetch_json=failing_fetch)


if __name__ == "__main__":
    unittest.main()
