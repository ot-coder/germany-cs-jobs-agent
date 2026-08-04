import unittest
from pathlib import Path


class WorkflowTests(unittest.TestCase):
    def test_manual_dispatch_can_force_a_telegram_test_notification(self):
        workflow = Path(".github/workflows/refresh-jobs.yml").read_text()
        self.assertIn("send_test_notification:", workflow)
        self.assertIn("Send Telegram daily update", workflow)
        self.assertIn("inputs.send_test_notification", workflow)
        self.assertIn("Cloud workflow test", workflow)


if __name__ == "__main__":
    unittest.main()
