import unittest

from jobs_agent.core import Job, classify_role, score_job, stable_job_id


class CoreTests(unittest.TestCase):
    def test_classifies_werkstudent_role(self):
        self.assertEqual(classify_role("Werkstudent Softwareentwicklung"), "werkstudent")

    def test_classifies_entry_level_role(self):
        self.assertEqual(classify_role("Junior Backend Developer"), "entry-level")

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
            source="test", role_type="werkstudent"
        )
        score, reasons = score_job(job)
        self.assertGreaterEqual(score, 70)
        self.assertIn("Werkstudent role", reasons)
        self.assertIn("Computer-science relevance", reasons)

    def test_stable_id_ignores_case_and_whitespace(self):
        a = stable_job_id(" Acme ", "Junior Developer", "Berlin")
        b = stable_job_id("acme", " junior  developer ", "BERLIN")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
