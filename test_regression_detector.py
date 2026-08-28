import unittest
import json
import os
import tempfile
from regression_detector import RegressionDetector

class TestRegressionDetector(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.results_dir = self.temp_dir.name
        
        # Previous run
        self.prev_file = os.path.join(self.results_dir, "final_qa_report_100.json")
        prev_data = {
            "run_id": "run-100",
            "findings": [
                {
                    "candidate": {
                        "id": "CANDIDATE-1",
                        "fingerprint": "hash_abc",
                        "occurrences": 5
                    }
                },
                {
                    "candidate": {
                        "id": "CANDIDATE-2",
                        "fingerprint": "hash_def",
                        "occurrences": 3
                    }
                }
            ]
        }
        with open(self.prev_file, 'w') as f:
            json.dump(prev_data, f)
            
        # Current run
        self.curr_file = os.path.join(self.results_dir, "qa_findings_101.json")
        curr_data = {
            "run_id": "run-101",
            "root_cause_candidates": [
                {
                    "id": "CANDIDATE-3",
                    "fingerprint": "hash_abc",
                    "occurrences": 5  # Unchanged
                },
                {
                    "id": "CANDIDATE-4",
                    "fingerprint": "hash_def",
                    "occurrences": 10 # Worsened
                },
                {
                    "id": "CANDIDATE-5",
                    "fingerprint": "hash_xyz",
                    "occurrences": 1 # New
                }
                # hash_ghi is missing (Fixed - wait, it wasn't in previous. Let's add it to previous!)
            ]
        }
        
        # Add hash_ghi to previous
        prev_data["findings"].append({
            "candidate": {
                "id": "CANDIDATE-6",
                "fingerprint": "hash_ghi",
                "occurrences": 2
            }
        })
        with open(self.prev_file, 'w') as f:
            json.dump(prev_data, f)
            
        with open(self.curr_file, 'w') as f:
            json.dump(curr_data, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_regression_detection(self):
        engine = RegressionDetector(self.curr_file, self.results_dir)
        engine.detect()
        
        with open(self.curr_file, 'r') as f:
            result = json.load(f)
            
        candidates = result['root_cause_candidates']
        self.assertEqual(len(candidates), 3)
        
        c_unchanged = next(c for c in candidates if c['fingerprint'] == 'hash_abc')
        self.assertEqual(c_unchanged['regression_status'], 'UNCHANGED')
        
        c_worsened = next(c for c in candidates if c['fingerprint'] == 'hash_def')
        self.assertEqual(c_worsened['regression_status'], 'WORSENED')
        
        c_new = next(c for c in candidates if c['fingerprint'] == 'hash_xyz')
        self.assertEqual(c_new['regression_status'], 'NEW')
        
        metrics = result['triage_metrics']['regression_summary']
        self.assertEqual(metrics['unchanged'], 1)
        self.assertEqual(metrics['worsened'], 1)
        self.assertEqual(metrics['new'], 1)
        self.assertEqual(metrics['fixed'], 1) # hash_ghi is gone
        
    def test_explicit_baseline(self):
        engine = RegressionDetector(self.curr_file, self.results_dir, baseline_file=self.prev_file)
        engine.detect()
        
        with open(self.curr_file, 'r') as f:
            result = json.load(f)
            
        metrics = result['triage_metrics']['regression_summary']
        self.assertEqual(metrics['new'], 1)
        self.assertEqual(metrics['fixed'], 1)

if __name__ == '__main__':
    unittest.main()
