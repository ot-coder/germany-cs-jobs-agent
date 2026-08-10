import unittest

from jobs_agent.core import Job, classify_category, classify_role, score_job, stable_job_id


class CoreTests(unittest.TestCase):
    def test_classifies_werkstudent_role(self):
        self.assertEqual(classify_role("Werkstudent Softwareentwicklung"), "werkstudent")

    def test_classifies_entry_level_role(self):
        self.assertEqual(classify_role("Junior Backend Developer"), "entry-level")

    def test_classifies_minijob_and_part_time_roles(self):
        self.assertEqual(classify_role("Minijob Lagerhelfer (m/w/d)"), "minijob")
        self.assertEqual(classify_role("Servicekraft in Teilzeit"), "part-time")
        self.assertEqual(classify_role("Part-time Barista"), "part-time")

    def test_switches_technical_and_general_part_time_categories(self):
        self.assertEqual(classify_category("Werkstudent Softwareentwicklung", "werkstudent"), "cs")
        self.assertEqual(classify_category("Systemadministrator in Teilzeit", "part-time"), "cs")
        self.assertEqual(classify_category("Minijob Lagerhelfer", "minijob"), "part-time")
        self.assertEqual(classify_category("Servicekraft in Teilzeit", "part-time"), "part-time")
        self.assertEqual(classify_category("Junior Sales Manager", "entry-level"), "other")

    def test_rejects_senior_role(self):
        self.assertEqual(classify_role("Senior Software Engineer"), "other")

    def test_does_not_classify_internship_from_description_noise(self):
        self.assertEqual(classify_role("Praktikum E-Commerce", "We also hire working students"), "other")

    def test_non_tech_werkstudent_scores_below_collection_threshold(self):
        job = Job(
            id="2", title="Werkstudent Legal", company="Acme", location="Berlin",
            url="https://example.com/2", description="Use Python, SQL databases and data tools in our legal team. English required. Enrolled student.",
            source="test", role_type="werkstudent"
        )
        score, _ = score_job(job)
        self.assertLess(score, 55)

    def test_scores_relevant_cs_student_role(self):
        job = Job(
            id="1", title="Werkstudent Software Engineer", company="Acme",
            location="Berlin, Germany", url="https://example.com/1",
            description="Python backend role for enrolled computer science students. English.",
            source="test", role_type="werkstudent", category="cs"
        )
        score, reasons = score_job(job)
        self.assertGreaterEqual(score, 70)
        self.assertIn("Werkstudent role", reasons)
        self.assertIn("Computer-science relevance", reasons)

    def test_scores_general_part_time_role_for_collection(self):
        job = Job(
            id="3", title="Minijob Lagerhelfer", company="Acme",
            location="Hamburg, Deutschland", url="https://example.com/3",
            description="Flexible shifts in our warehouse.", source="test",
            role_type="minijob", category="part-time",
        )
        score, reasons = score_job(job)
        self.assertGreaterEqual(score, 55)
        self.assertIn("Part-time/minijob role", reasons)

    def test_stable_id_ignores_case_and_whitespace(self):
        a = stable_job_id(" Acme ", "Junior Developer", "Berlin")
        b = stable_job_id("acme", " junior  developer ", "BERLIN")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
