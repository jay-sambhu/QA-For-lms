import unittest
from unittest.mock import AsyncMock, patch
import os
import json
import tempfile
from test_case_generator import TestCaseGenerator

class TestTestCaseGenerator(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.crawl_file = os.path.join(self.temp_dir.name, "crawl.json")
        with open(self.crawl_file, "w") as f:
            json.dump({
                "run_id": "123",
                "target": "https://example.com",
                "pages": [{"url": "https://example.com"}]
            }, f)
            
    def tearDown(self):
        self.temp_dir.cleanup()

    def test_destructive_keywords(self):
        gen = TestCaseGenerator(self.crawl_file)
        self.assertTrue(gen._is_destructive("Delete Account"))
        self.assertTrue(gen._is_destructive("Pay now"))
        self.assertFalse(gen._is_destructive("Read more"))

    def test_categorize(self):
        gen = TestCaseGenerator(self.crawl_file)
        self.assertEqual(gen._categorize("form", {"name": "password"}), "authentication")
        self.assertEqual(gen._categorize("link", {"href": "/login"}), "links")
        self.assertEqual(gen._categorize("link", {"href": "/nav"}), "navigation")
        self.assertEqual(gen._categorize("button", {}), "buttons")

    @patch("test_case_generator.async_playwright")
    async def test_generate_success(self, mock_playwright):
        mock_p = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright.return_value.__aenter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        # Mock elements
        mock_page.evaluate.return_value = [
            {
                "tag": "button",
                "type": "button",
                "text": "Submit",
                "selector": "button",
                "isVisible": True,
                "isEnabled": True
            },
            {
                "tag": "a",
                "type": "link",
                "text": "Delete",
                "selector": "a.delete",
                "isVisible": True,
                "isEnabled": True
            }
        ]
        
        gen = TestCaseGenerator(self.crawl_file, output_dir=self.temp_dir.name)
        output_file = await gen.generate()
        
        self.assertIsNotNone(output_file)
        with open(output_file, "r") as f:
            data = json.load(f)
            
        self.assertEqual(len(data["test_cases"]), 2)
        tc1 = data["test_cases"][0]
        self.assertEqual(tc1["title"], "Verify button 'Submit'")
        self.assertEqual(tc1["execution_policy"], "manual_review") # 'Submit' is a destructive keyword
        
        tc2 = data["test_cases"][1]
        self.assertEqual(tc2["title"], "Verify link 'Delete'")
        self.assertEqual(tc2["execution_policy"], "manual_review")

if __name__ == "__main__":
    unittest.main()
