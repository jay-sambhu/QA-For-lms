import unittest
import copy
from evidence_engine import EvidenceEngine

class TestEvidenceEngine(unittest.TestCase):
    def setUp(self):
        self.crawl_result = {
            "target": "https://example.com"
        }
        self.engine = EvidenceEngine(self.crawl_result)
        
        self.base_candidate = {
            "id": "CANDIDATE-001",
            "type": "",
            "url": "https://example.com/test",
            "evidence": {}
        }

    def _run_engine(self, candidate):
        result = self.engine.enrich({"root_cause_candidates": [candidate]})
        return result["root_cause_candidates"][0]

    def test_01_http_evidence_generation(self):
        """1. HTTP evidence generation"""
        c = copy.deepcopy(self.base_candidate)
        c["type"] = "http_error"
        c["evidence"]["http_errors"] = [{
            "url": "https://api.example.com/data",
            "method": "POST",
            "status": 500,
            "resource_type": "xhr"
        }]
        
        res = self._run_engine(c)
        
        ev = res["evidence_structured"]["http_error"]
        self.assertIsNotNone(ev)
        self.assertEqual(ev["request"]["url"], "https://api.example.com/data")
        self.assertEqual(ev["request"]["method"], "POST")
        self.assertEqual(ev["request"]["status"], 500)
        self.assertEqual(ev["request"]["resource_type"], "xhr")

    def test_02_console_evidence_generation(self):
        """2. Console evidence generation"""
        c = copy.deepcopy(self.base_candidate)
        c["type"] = "console_error"
        c["evidence"]["console_errors"] = [{
            "text": "TypeError: null is not an object",
            "page": "https://example.com/test"
        }]
        
        res = self._run_engine(c)
        
        ev = res["evidence_structured"]["console_errors"]
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["message"], "TypeError: null is not an object")

    def test_03_responsive_evidence_generation(self):
        """3. Responsive evidence generation"""
        c = copy.deepcopy(self.base_candidate)
        c["type"] = "responsive_issue"
        c["affected_devices"] = ["iPhone 13"]
        c["evidence"]["responsive_checks"] = {
            "horizontal_overflow": True,
            "overflow_pixels": 240,
            "forms_outside_viewport": 1
        }
        
        res = self._run_engine(c)
        
        ev = res["evidence_structured"]["responsive"]
        self.assertEqual(ev["device"], "iPhone 13")
        self.assertEqual(ev["overflow"]["amount"], 240)
        self.assertEqual(ev["element"]["type"], "form")
        self.assertEqual(ev["element"]["count"], 1)

    def test_04_screenshot_association(self):
        """4. Screenshot association"""
        c = copy.deepcopy(self.base_candidate)
        c["type"] = "http_error"
        c["screenshots"] = ["screenshots/001.png"]
        
        res = self._run_engine(c)
        self.assertEqual(res["evidence_structured"]["screenshot"], "screenshots/001.png")
        
        # Test page_screenshots fallback
        c2 = copy.deepcopy(self.base_candidate)
        c2["page_screenshots"] = [{"page": "x", "screenshot": "screenshots/002.png"}]
        res2 = self._run_engine(c2)
        self.assertEqual(res2["evidence_structured"]["screenshot"], "screenshots/002.png")

    def test_05_device_viewport_preservation(self):
        """5. Device/viewport preservation"""
        c = copy.deepcopy(self.base_candidate)
        c["type"] = "responsive_issue"
        c["affected_devices"] = ["iPhone 13"]
        c["evidence"]["responsive_checks"] = {"horizontal_overflow": True}
        
        res = self._run_engine(c)
        vp = res["evidence_structured"]["responsive"]["viewport"]
        # iPhone 13 is 390x844
        self.assertEqual(vp["width"], 390)
        self.assertEqual(vp["height"], 844)

    def test_06_reproduction_step_generation(self):
        """6. Reproduction step generation"""
        c = copy.deepcopy(self.base_candidate)
        c["type"] = "http_error"
        c["evidence"]["http_errors"] = [{"url": "https://api.example.com/data", "status": 401}]
        
        res = self._run_engine(c)
        steps = res["reproduction"]["steps"]
        self.assertIn("Open browser developer tools", steps)
        self.assertTrue(any("401" in s for s in steps))

    def test_07_expected_actual_fallback_generation(self):
        """7. Expected/actual fallback generation"""
        c = copy.deepcopy(self.base_candidate)
        c["type"] = "http_error"
        c["evidence"]["http_errors"] = [{"url": "http://api", "status": 500}]
        
        res = self._run_engine(c)
        self.assertNotEqual(res.get("expected_result", "Not specified."), "Not specified.")
        self.assertTrue("500 response" in res.get("actual_result", ""))

    def test_08_missing_evidence_handling(self):
        """8. Missing evidence handling"""
        c = copy.deepcopy(self.base_candidate)
        c["type"] = "unknown_type"
        c["evidence"] = {} # Totally empty
        
        res = self._run_engine(c)
        self.assertIsNotNone(res.get("evidence_structured"))
        self.assertFalse(res["reproduction"]["evidence_available"])
        self.assertTrue(len(res["reproduction"]["steps"]) > 0)

    def test_09_http_console_correlation(self):
        """9. HTTP + console evidence correlation"""
        c = copy.deepcopy(self.base_candidate)
        c["type"] = "http_error"
        c["evidence"]["http_errors"] = [{"url": "http://api", "status": 404}]
        c["evidence"]["console_errors"] = [{"text": "Failed to load resource: 404"}]
        
        res = self._run_engine(c)
        
        self.assertIsNotNone(res["evidence_structured"]["http_error"])
        self.assertEqual(len(res["evidence_structured"]["console_errors"]), 1)

    def test_10_schema_compatibility(self):
        """10. Existing finding schema compatibility"""
        c = copy.deepcopy(self.base_candidate)
        
        res = self._run_engine(c)
        
        # And must have the new ones
        self.assertIn("reproduction", res)
        self.assertIn("evidence_structured", res)

if __name__ == '__main__':
    unittest.main()
