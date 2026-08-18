import unittest

from jobs_agent.core import (
    BROADER_PROFESSIONAL,
    BUSINESS_TECH,
    CORE_TECH,
    ENTERPRISE_IT,
    IRRELEVANT,
    PRODUCT_PROJECT,
    Job,
    classify_role,
    score_job,
    stable_job_id,
)


def make_job(title, description="", location="Berlin, Germany", company="Acme") -> Job:
    return Job(
        id="x", title=title, company=company, location=location,
        url="https://example.com/x", description=description, source="test",
    )


class ClassificationTests(unittest.TestCase):
    def test_swe_intern_is_core_tech(self):
        family, seniority = classify_role("Software Engineering Intern")
        self.assertEqual(family, CORE_TECH)
        self.assertEqual(seniority, "junior")

    def test_junior_data_analyst_is_core_tech(self):
        family, _ = classify_role("Junior Data Analyst")
        self.assertEqual(family, CORE_TECH)

    def test_product_management_intern_is_product_project(self):
        family, _ = classify_role("Product Management Intern")
        self.assertEqual(family, PRODUCT_PROJECT)

    def test_junior_project_manager_is_product_project(self):
        family, _ = classify_role("Junior Project Manager")
        self.assertEqual(family, PRODUCT_PROJECT)

    def test_pmo_analyst_is_product_project(self):
        family, _ = classify_role("PMO Analyst")
        self.assertEqual(family, PRODUCT_PROJECT)

    def test_junior_business_analyst_is_business_tech(self):
        family, _ = classify_role("Junior Business Analyst")
        self.assertEqual(family, BUSINESS_TECH)

    def test_junior_it_service_manager_is_enterprise_it(self):
        family, _ = classify_role("Junior IT Service Manager")
        self.assertEqual(family, ENTERPRISE_IT)

    def test_application_manager_is_enterprise_it(self):
        family, _ = classify_role("Application Manager")
        self.assertEqual(family, ENTERPRISE_IT)

    def test_implementation_consultant_junior_is_enterprise_or_business(self):
        family, _ = classify_role("Implementation Consultant (Junior)")
        self.assertIn(family, (ENTERPRISE_IT, BUSINESS_TECH))

    def test_operations_analyst_is_broader_professional(self):
        family, _ = classify_role("Operations Analyst")
        self.assertEqual(family, BROADER_PROFESSIONAL)

    def test_senior_engineering_manager_is_rejected(self):
        family, seniority = classify_role("Senior Engineering Manager")
        self.assertEqual(family, IRRELEVANT)
        self.assertEqual(seniority, "senior")

    def test_werkstudent_still_recognized(self):
        family, seniority = classify_role("Werkstudent Softwareentwicklung")
        self.assertEqual(family, CORE_TECH)
        self.assertEqual(seniority, "junior")


class ManagerRegressionTests(unittest.TestCase):
    def test_junior_project_manager_not_rejected(self):
        family, _ = classify_role("Junior Project Manager")
        self.assertNotEqual(family, IRRELEVANT)

    def test_product_manager_intern_not_rejected(self):
        family, _ = classify_role("Product Manager Intern")
        self.assertNotEqual(family, IRRELEVANT)

    def test_application_manager_not_rejected_solely_for_manager(self):
        family, _ = classify_role("Application Manager")
        self.assertNotEqual(family, IRRELEVANT)

    def test_junior_it_service_manager_not_rejected(self):
        family, _ = classify_role("Junior IT Service Manager")
        self.assertNotEqual(family, IRRELEVANT)

    def test_senior_product_manager_rejected(self):
        family, _ = classify_role("Senior Product Manager")
        self.assertEqual(family, IRRELEVANT)

    def test_lead_project_manager_rejected(self):
        family, _ = classify_role("Lead Project Manager")
        self.assertEqual(family, IRRELEVANT)

    def test_principal_engineer_rejected(self):
        family, _ = classify_role("Principal Engineer")
        self.assertEqual(family, IRRELEVANT)

    def test_head_of_it_rejected(self):
        family, _ = classify_role("Head of IT")
        self.assertEqual(family, IRRELEVANT)

    def test_director_of_product_rejected(self):
        family, _ = classify_role("Director of Product")
        self.assertEqual(family, IRRELEVANT)

    def test_staff_engineer_rejected(self):
        family, _ = classify_role("Staff Engineer")
        self.assertEqual(family, IRRELEVANT)

    def test_senior_application_manager_rejected(self):
        family, _ = classify_role("Senior Application Manager")
        self.assertEqual(family, IRRELEVANT)

    def test_engineering_manager_requiring_5plus_years_rejected(self):
        family, _ = classify_role("Engineering Manager requiring 5+ years")
        self.assertEqual(family, IRRELEVANT)

    def test_vp_technology_rejected(self):
        family, _ = classify_role("VP Technology")
        self.assertEqual(family, IRRELEVANT)

    def test_head_of_product_rejected(self):
        family, _ = classify_role("Head of Product")
        self.assertEqual(family, IRRELEVANT)


class ScoringTests(unittest.TestCase):
    def test_realistic_adjacent_role_can_outrank_elite_ineligible_role(self):
        realistic = make_job(
            "Junior IT Service Manager", "Enrolled students welcome, English speaking team.",
            location="Leipzig, Germany", company="Mid-Size GmbH",
        )
        elite_but_ineligible = make_job(
            "Software Engineer", "Requires 5+ years experience. Google-scale systems.",
            location="Berlin, Germany", company="Google",
        )
        realistic.score, realistic.reasons = score_job(realistic)
        elite_but_ineligible.score, elite_but_ineligible.reasons = score_job(elite_but_ineligible)
        self.assertGreater(realistic.score, elite_but_ineligible.score)

    def test_b2_compatible_german_scores_higher_than_c1_mandatory(self):
        open_german = make_job("Junior Consultant", "Gute Deutschkenntnisse von Vorteil. English team.")
        strict_german = make_job("Junior Consultant", "Deutsch C1 zwingend erforderlich, muttersprachlich.")
        open_score, _ = score_job(open_german)
        strict_score, _ = score_job(strict_german)
        self.assertGreater(open_score, strict_score)

    def test_entry_level_scores_higher_than_5_years_required(self):
        entry = make_job("Junior Software Engineer", "Great for graduates and career starters.")
        experienced = make_job("Software Engineer", "5+ years of professional experience required.")
        entry_score, _ = score_job(entry)
        experienced_score, _ = score_job(experienced)
        self.assertGreater(entry_score, experienced_score)

    def test_germany_role_scores_appropriately(self):
        germany = make_job("Werkstudent Data", "Python and SQL.", location="Munich, Germany")
        elsewhere = make_job("Werkstudent Data", "Python and SQL.", location="New York, USA")
        germany_score, _ = score_job(germany)
        elsewhere_score, _ = score_job(elsewhere)
        self.assertGreater(germany_score, elsewhere_score)

    def test_keyword_density_alone_cannot_reach_95(self):
        stuffed = make_job(
            "Software Engineer",
            "software developer engineer backend frontend full stack python java "
            "javascript typescript cloud devops platform engineer data engineer",
            location="Unknown location",
        )
        score, _ = score_job(stuffed)
        self.assertLess(score, 95)

    def test_scores_relevant_cs_student_role(self):
        job = make_job(
            "Werkstudent Software Engineer",
            "Python backend role for enrolled computer science students. English.",
            location="Berlin, Germany",
        )
        score, reasons = score_job(job)
        self.assertGreaterEqual(score, 70)
        self.assertTrue(any("entry-level" in reason.lower() for reason in reasons))

    def test_july_2027_availability_not_penalized_by_ceremony_date(self):
        base = make_job("Graduate Software Engineer 2027", "Start date July 2027.")
        with_ceremony_text = make_job(
            "Graduate Software Engineer 2027",
            "Start date July 2027. Candidates who graduate in October 2027 are welcome to apply.",
        )
        base_score, _ = score_job(base)
        ceremony_score, _ = score_job(with_ceremony_text)
        self.assertEqual(base_score, ceremony_score)


class StableIdTests(unittest.TestCase):
    def test_stable_id_ignores_case_and_whitespace(self):
        a = stable_job_id(" Acme ", "Junior Developer", "Berlin")
        b = stable_job_id("acme", " junior  developer ", "BERLIN")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
