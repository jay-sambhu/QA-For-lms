import unittest
from crawler.devices import DeviceConfigManager
from bug_detector import QAFindingClassifier
from qa_report_generator import QAReportGenerator


class TestResponsiveEngine(unittest.TestCase):

    def test_01_desktop_configuration(self):
        config = DeviceConfigManager.get_devices_config()
        self.assertIn("Desktop Chrome", config)
        desktop = config["Desktop Chrome"]
        self.assertEqual(desktop["viewport"]["width"], 1366)
        self.assertEqual(desktop["viewport"]["height"], 768)
        self.assertFalse(desktop["is_mobile"])

    def test_02_iphone_configuration(self):
        config = DeviceConfigManager.get_devices_config()
        self.assertIn("iPhone 13", config)
        iphone = config["iPhone 13"]
        self.assertEqual(iphone["viewport"]["width"], 390)
        self.assertEqual(iphone["viewport"]["height"], 844)
        self.assertTrue(iphone["is_mobile"])

    def test_03_ipad_configuration(self):
        config = DeviceConfigManager.get_devices_config()
        self.assertIn("iPad (gen 7)", config)
        ipad = config["iPad (gen 7)"]
        self.assertEqual(ipad["viewport"]["width"], 810)
        self.assertEqual(ipad["viewport"]["height"], 1080)
        self.assertTrue(ipad["is_mobile"])

    def test_04_horizontal_overflow_detection(self):
        crawl_data = {
            "target": "https://example.com",
            "pages": [{
                "url": "https://example.com/page1 [iPhone 13]",
                "actual_url": "https://example.com/page1",
                "device": "iPhone 13",
                "responsive_checks": {
                    "horizontal_overflow": True,
                    "overflow_pixels": 45,
                    "elements_outside_viewport": 2,
                    "forms_outside_viewport": 0,
                    "clipped_buttons": 0,
                    "navigation_visible": True,
                    "viewport_width": 390,
                    "viewport_height": 844
                }
            }]
        }
        classifier = QAFindingClassifier("example.com", crawl_data)
        findings = classifier.classify()
        responsive = [f for f in findings if f.get("type") == "responsive_issue"]
        self.assertEqual(len(responsive), 1)
        self.assertIn("Horizontal page overflow", responsive[0]["description"])

    def test_05_no_overflow_clean_case(self):
        crawl_data = {
            "target": "https://example.com",
            "pages": [{
                "url": "https://example.com/clean [Desktop Chrome]",
                "actual_url": "https://example.com/clean",
                "device": "Desktop Chrome",
                "responsive_checks": {
                    "horizontal_overflow": False,
                    "overflow_pixels": 0,
                    "elements_outside_viewport": 0,
                    "forms_outside_viewport": 0,
                    "clipped_buttons": 0,
                    "navigation_visible": True,
                    "viewport_width": 1366,
                    "viewport_height": 768
                }
            }]
        }
        classifier = QAFindingClassifier("example.com", crawl_data)
        findings = classifier.classify()
        responsive = [f for f in findings if f.get("type") == "responsive_issue"]
        self.assertEqual(len(responsive), 0)

    def test_06_element_outside_viewport(self):
        crawl_data = {
            "target": "https://example.com",
            "pages": [{
                "url": "https://example.com/element [iPhone 13]",
                "actual_url": "https://example.com/element",
                "device": "iPhone 13",
                "responsive_checks": {
                    "horizontal_overflow": False,
                    "overflow_pixels": 0,
                    "elements_outside_viewport": 3,
                    "forms_outside_viewport": 0,
                    "clipped_buttons": 0,
                    "navigation_visible": True
                }
            }]
        }
        classifier = QAFindingClassifier("example.com", crawl_data)
        findings = classifier.classify()
        responsive = [f for f in findings if f.get("type") == "responsive_issue"]
        self.assertEqual(len(responsive), 1)
        self.assertEqual(responsive[0]["severity"], "low")

    def test_07_form_outside_viewport(self):
        crawl_data = {
            "target": "https://example.com",
            "pages": [{
                "url": "https://example.com/form [iPhone 13]",
                "actual_url": "https://example.com/form",
                "device": "iPhone 13",
                "responsive_checks": {
                    "horizontal_overflow": True,
                    "overflow_pixels": 120,
                    "elements_outside_viewport": 5,
                    "forms_outside_viewport": 1,
                    "clipped_buttons": 1,
                    "navigation_visible": True
                }
            }]
        }
        classifier = QAFindingClassifier("example.com", crawl_data)
        findings = classifier.classify()
        responsive = [f for f in findings if f.get("type") == "responsive_issue"]
        self.assertEqual(len(responsive), 1)
        self.assertEqual(responsive[0]["severity"], "high")

    def test_08_responsive_finding_schema(self):
        crawl_data = {
            "target": "https://example.com",
            "pages": [{
                "url": "https://example.com/schema [iPad (gen 7)]",
                "actual_url": "https://example.com/schema",
                "device": "iPad (gen 7)",
                "responsive_checks": {
                    "horizontal_overflow": True,
                    "overflow_pixels": 30,
                    "elements_outside_viewport": 1,
                    "forms_outside_viewport": 0,
                    "clipped_buttons": 0,
                    "navigation_visible": True
                }
            }]
        }
        classifier = QAFindingClassifier("example.com", crawl_data)
        findings = classifier.classify()
        f = findings[0]
        self.assertIn("type", f)
        self.assertEqual(f["type"], "responsive_issue")
        self.assertIn("severity", f)
        self.assertIn("affected_devices", f)
        self.assertIn("iPad (gen 7)", f["affected_devices"])

    def test_09_cross_device_grouping_and_deduplication(self):
        crawl_data = {
            "target": "https://example.com",
            "pages": [
                {
                    "url": "https://example.com/page [iPhone 13]",
                    "actual_url": "https://example.com/page",
                    "device": "iPhone 13",
                    "responsive_checks": {
                        "horizontal_overflow": True,
                        "overflow_pixels": 50,
                        "elements_outside_viewport": 2,
                        "forms_outside_viewport": 0,
                        "clipped_buttons": 0,
                        "navigation_visible": True
                    }
                },
                {
                    "url": "https://example.com/page [iPad (gen 7)]",
                    "actual_url": "https://example.com/page",
                    "device": "iPad (gen 7)",
                    "responsive_checks": {
                        "horizontal_overflow": True,
                        "overflow_pixels": 20,
                        "elements_outside_viewport": 1,
                        "forms_outside_viewport": 0,
                        "clipped_buttons": 0,
                        "navigation_visible": True
                    }
                }
            ]
        }
        classifier = QAFindingClassifier("example.com", crawl_data)
        classifier.classify()
        candidates = classifier.root_cause_candidates
        self.assertEqual(len(candidates), 1)
        cand = candidates[0]
        self.assertEqual(cand["type"], "responsive_issue")
        self.assertEqual(sorted(cand["affected_devices"]), ["iPad (gen 7)", "iPhone 13"])

    def test_10_severity_assignment(self):
        crawl_data = {
            "target": "https://example.com",
            "pages": [
                {
                    "url": "https://example.com/high [iPhone 13]",
                    "actual_url": "https://example.com/high",
                    "device": "iPhone 13",
                    "responsive_checks": {
                        "horizontal_overflow": True,
                        "overflow_pixels": 100,
                        "elements_outside_viewport": 4,
                        "forms_outside_viewport": 2,
                        "clipped_buttons": 0,
                        "navigation_visible": True
                    }
                },
                {
                    "url": "https://example.com/med [iPad (gen 7)]",
                    "actual_url": "https://example.com/med",
                    "device": "iPad (gen 7)",
                    "responsive_checks": {
                        "horizontal_overflow": True,
                        "overflow_pixels": 10,
                        "elements_outside_viewport": 1,
                        "forms_outside_viewport": 0,
                        "clipped_buttons": 0,
                        "navigation_visible": True
                    }
                }
            ]
        }
        classifier = QAFindingClassifier("example.com", crawl_data)
        findings = classifier.classify()
        by_url = {f["actual_url"]: f for f in findings}
        self.assertEqual(by_url["https://example.com/high"]["severity"], "high")
        self.assertEqual(by_url["https://example.com/med"]["severity"], "medium")

    def test_11_expected_responsive_difference_ignored(self):
        crawl_data = {
            "target": "https://example.com",
            "pages": [
                {
                    "url": "https://example.com/menu [Desktop Chrome]",
                    "actual_url": "https://example.com/menu",
                    "device": "Desktop Chrome",
                    "responsive_checks": {
                        "horizontal_overflow": False,
                        "overflow_pixels": 0,
                        "elements_outside_viewport": 0,
                        "forms_outside_viewport": 0,
                        "clipped_buttons": 0,
                        "navigation_visible": True
                    }
                },
                {
                    "url": "https://example.com/menu [iPhone 13]",
                    "actual_url": "https://example.com/menu",
                    "device": "iPhone 13",
                    "responsive_checks": {
                        "horizontal_overflow": False,
                        "overflow_pixels": 0,
                        "elements_outside_viewport": 0,
                        "forms_outside_viewport": 0,
                        "clipped_buttons": 0,
                        "navigation_visible": False
                    }
                }
            ]
        }
        classifier = QAFindingClassifier("example.com", crawl_data)
        findings = classifier.classify()
        responsive = [f for f in findings if f.get("type") == "responsive_issue"]
        self.assertEqual(len(responsive), 0)

    def test_12_screenshot_path_generation(self):
        crawl_data = {
            "target": "https://example.com",
            "pages": [{
                "url": "https://example.com/snap [iPhone 13]",
                "actual_url": "https://example.com/snap",
                "device": "iPhone 13",
                "screenshot": "screenshots/run123/001_iPhone_13_page.png",
                "responsive_checks": {
                    "horizontal_overflow": True,
                    "overflow_pixels": 30,
                    "elements_outside_viewport": 1,
                    "forms_outside_viewport": 0,
                    "clipped_buttons": 0,
                    "navigation_visible": True
                }
            }]
        }
        classifier = QAFindingClassifier("example.com", crawl_data)
        findings = classifier.classify()
        self.assertEqual(findings[0]["screenshot"], "screenshots/run123/001_iPhone_13_page.png")

    def test_13_report_metrics_generation(self):
        raw_data = {
            "target": "https://example.com",
            "findings": [
                {
                    "type": "responsive_issue",
                    "title": "Responsive layout issue on iPhone 13",
                    "severity": "medium",
                    "affected_devices": ["iPhone 13", "iPad (gen 7)"]
                }
            ]
        }
        generator = QAReportGenerator()
        json_report = generator.generate_json_report("fake_gemini.json", raw_data)
        metadata = json_report.get("report_metadata", {})
        self.assertIn("cross_device_metrics", metadata)
        cdm = metadata["cross_device_metrics"]
        self.assertEqual(cdm["devices_tested"], 3)
        self.assertEqual(cdm["responsive_findings"], 1)
        self.assertEqual(cdm["device_breakdown"]["iphone"], 1)
        self.assertEqual(cdm["device_breakdown"]["ipad"], 1)


if __name__ == "__main__":
    unittest.main()
