import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import os
import json
import tempfile
from test_case_executor import TestCaseExecutor
from playwright.async_api import TimeoutError

class TestTestCaseExecutor(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tc_file = os.path.join(self.temp_dir.name, "test_cases.json")
        self.findings_file = os.path.join(self.temp_dir.name, "findings.json")
        
        with open(self.tc_file, "w") as f:
            json.dump({
                "run_id": "123",
                "test_cases": [
                    {
                        "id": "TC-001",
                        "execution_policy": "safe",
                        "source_page": "https://example.com",
                        "target_element": {"type": "button", "selector": "btn"},
                        "title": "Test button"
                    },
                    {
                        "id": "TC-002",
                        "execution_policy": "manual_review"
                    }
                ]
            }, f)
            
        with open(self.findings_file, "w") as f:
            json.dump({"findings": []}, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("test_case_executor.async_playwright")
    async def test_execute_safe_passed(self, mock_playwright):
        mock_p = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_locator = AsyncMock()
        
        mock_playwright.return_value.__aenter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.locator = MagicMock()
        mock_page.get_by_text = MagicMock()
        mock_page.locator.return_value.first = mock_locator
        mock_page.get_by_text.return_value.first = mock_locator
        mock_locator.is_visible = AsyncMock(return_value=True)
        mock_page.remove_listener = MagicMock()
        mock_page.on = MagicMock()
        
        executor = TestCaseExecutor(self.tc_file, self.findings_file, self.temp_dir.name)
        res_file = await executor.execute()
        
        self.assertIsNotNone(res_file)
        with open(res_file, "r") as f:
            data = json.load(f)
            
        self.assertEqual(len(data["results"]), 2)
        r1 = data["results"][0]
        if r1["status"] != "passed":
            print(f"FAILED: {r1['actual_result']}")
        self.assertEqual(r1["status"], "passed")
        
        r2 = data["results"][1]
        self.assertEqual(r2["status"], "manual_review")

    @patch("test_case_executor.async_playwright")
    async def test_execute_timeout_creates_finding(self, mock_playwright):
        mock_p = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_locator = AsyncMock()
        
        mock_playwright.return_value.__aenter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.locator = MagicMock()
        mock_page.get_by_text = MagicMock()
        mock_page.locator.return_value.first = mock_locator
        mock_page.get_by_text.return_value.first = mock_locator
        mock_locator.is_visible = AsyncMock(return_value=True)
        mock_page.remove_listener = MagicMock()
        mock_page.on = MagicMock()
        
        # Simulate timeout on click
        mock_locator.click.side_effect = TimeoutError("Timeout")
        
        executor = TestCaseExecutor(self.tc_file, self.findings_file, self.temp_dir.name)
        await executor.execute()
        
        with open(self.findings_file, "r") as f:
            data = json.load(f)
            
        self.assertEqual(len(data["findings"]), 1)
        finding = data["findings"][0]
        self.assertEqual(finding["finding_type"], "interactive_failure")
        self.assertIn("Test Failure:", finding["title"])

if __name__ == "__main__":
    unittest.main()
