import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from interactive_tester import InteractiveTester

class TestInteractiveTester(unittest.TestCase):
    def setUp(self):
        self.crawl_result = {
            "target": "https://dplms.com/",
            "run_id": "TEST_RUN_001",
            "pages": [
                {
                    "url": "https://dplms.com/",
                    "actual_url": "https://dplms.com/",
                    "status": 200,
                    "error": None
                }
            ]
        }
        self.tester = InteractiveTester(self.crawl_result, max_interactions_per_page=3)

    def test_destructive_filtering(self):
        self.assertTrue(self.tester._is_destructive("Delete User"))
        self.assertTrue(self.tester._is_destructive("Cancel Subscription"))
        self.assertTrue(self.tester._is_destructive("Pay now"))
        self.assertFalse(self.tester._is_destructive("Submit Form"))
        self.assertFalse(self.tester._is_destructive("Next Page"))

    def test_third_party_filtering(self):
        self.assertTrue(self.tester._is_third_party("https://google.com/analytics"))
        self.assertTrue(self.tester._is_third_party("https://stripe.com/checkout"))
        self.assertFalse(self.tester._is_third_party("https://dplms.com/about"))
        self.assertFalse(self.tester._is_third_party("https://api.dplms.com/cart"))

    @patch('interactive_tester.async_playwright')
    def test_interactive_tester_run(self, mock_playwright):
        # Setup mock playwright
        mock_pw_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright.return_value.__aenter__.return_value = mock_pw_context
        mock_pw_context.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        mock_page.url = "https://dplms.com/"
        mock_page.content.return_value = "<html><body>Lots of safe content here to avoid blank page check.</body></html>"
        
        # Setup mock elements (1 safe button, 1 destructive button, 1 third-party link)
        mock_safe_btn = MagicMock()
        mock_safe_btn.is_visible = AsyncMock(return_value=True)
        mock_safe_btn.is_enabled = AsyncMock(return_value=True)
        mock_safe_btn.inner_text = AsyncMock(return_value="Click Me")
        mock_safe_btn.get_attribute = AsyncMock(return_value=None)
        mock_safe_btn.evaluate = AsyncMock(return_value="<button>Click Me</button>")
        mock_safe_btn.click = AsyncMock()
        
        mock_dest_btn = MagicMock()
        mock_dest_btn.is_visible = AsyncMock(return_value=True)
        mock_dest_btn.is_enabled = AsyncMock(return_value=True)
        mock_dest_btn.inner_text = AsyncMock(return_value="Delete Account")
        mock_dest_btn.get_attribute = AsyncMock(return_value=None)
        mock_dest_btn.evaluate = AsyncMock(return_value="<button>Delete Account</button>")
        
        mock_third_link = MagicMock()
        mock_third_link.is_visible = AsyncMock(return_value=True)
        mock_third_link.is_enabled = AsyncMock(return_value=True)
        mock_third_link.get_attribute = AsyncMock(return_value="https://google.com")
        mock_third_link.inner_text = AsyncMock(return_value="Third party")
        mock_third_link.evaluate = AsyncMock(return_value="<a>Third party</a>")
        
        # Configure locator
        def locator_side_effect(selector):
            mock_locator = MagicMock()
            if "button" in selector:
                mock_locator.all = AsyncMock(return_value=[mock_safe_btn, mock_dest_btn])
            elif "a[href]" in selector:
                mock_locator.all = AsyncMock(return_value=[mock_third_link])
            else:
                mock_locator.all = AsyncMock(return_value=[])
            return mock_locator
            
        mock_page.locator = MagicMock(side_effect=locator_side_effect)
        
        # Run
        result = asyncio.run(self.tester.run())
        
        self.assertEqual(result["pages_tested"], 1)
        # Safe button should be tested
        # Destructive button should be skipped (manual_review)
        # Third party link should be filtered out entirely (not in discovered elements for interactions)
        self.assertEqual(result["summary"]["elements_discovered"], 2) # Safe + Destructive
        self.assertEqual(result["summary"]["interactions_attempted"], 1) # Safe
        self.assertEqual(result["summary"]["passed"], 1) # Safe passed
        self.assertEqual(result["summary"]["failed"], 0)
        self.assertEqual(result["summary"]["manual_review"], 1) # Destructive
        
        interactions = result["interactions"]
        self.assertEqual(len(interactions), 2)
        
        # Verify manual review
        dest = next(i for i in interactions if i["result"] == "manual_review")
        self.assertEqual(dest["element_text"], "Delete Account")
        
        # Verify passed interaction
        safe = next(i for i in interactions if i["result"] == "passed")
        self.assertEqual(safe["element_text"], "Click Me")

    @patch('interactive_tester.async_playwright')
    def test_interaction_failure_capture(self, mock_playwright):
        # Setup mock playwright
        mock_pw_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright.return_value.__aenter__.return_value = mock_pw_context
        mock_pw_context.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        mock_page.url = "https://dplms.com/"
        mock_page.content.return_value = "<html><body></body></html>"
        
        mock_btn = MagicMock()
        mock_btn.is_visible = AsyncMock(return_value=True)
        mock_btn.is_enabled = AsyncMock(return_value=True)
        mock_btn.inner_text = AsyncMock(return_value="Crash App")
        mock_btn.get_attribute = AsyncMock(return_value=None)
        mock_btn.evaluate = AsyncMock(return_value="<button>Crash App</button>")
        # Simulate click causing a timeout
        import playwright
        mock_btn.click = AsyncMock(side_effect=playwright.async_api.TimeoutError("Timeout!"))
        
        def locator_side_effect(selector):
            mock_locator = MagicMock()
            if "button" in selector:
                mock_locator.all = AsyncMock(return_value=[mock_btn])
            else:
                mock_locator.all = AsyncMock(return_value=[])
            return mock_locator
            
        mock_page.locator = MagicMock(side_effect=locator_side_effect)
        
        result = asyncio.run(self.tester.run())
        
        self.assertEqual(result["summary"]["failed"], 1)
        self.assertEqual(result["summary"]["passed"], 0)
        self.assertEqual(result["interactions"][0]["result"], "failed")
        self.assertEqual(result["interactions"][0]["severity"], "medium")

if __name__ == '__main__':
    unittest.main()
