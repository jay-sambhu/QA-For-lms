import unittest
import json
import os
import tempfile
from bug_triage import BugTriageEngine

class TestBugTriageEngine(unittest.TestCase):
    def setUp(self):
        self.fd, self.path = tempfile.mkstemp()
        self.data = {
            "root_cause_candidates": [
                {
                    "id": "CANDIDATE-001",
                    "type": "http_error",
                    "status": 401,
                    "url": "https://api.example.com/api/auth/me",
                    "first_party": True,
                    "confidence": "medium",
                    "occurrences": 30
                },
                {
                    "id": "CANDIDATE-002",
                    "type": "responsive_issue",
                    "url": "https://example.com/product",
                    "severity": "high",
                    "title": "Responsive layout overflow on https://example.com/product",
                    "first_party": True,
                    "confidence": "high",
                    "occurrences": 3
                },
                {
                    "id": "CANDIDATE-003",
                    "type": "http_error",
                    "status": 500,
                    "url": "https://example.com/api/checkout",
                    "first_party": True,
                    "confidence": "high",
                    "occurrences": 12
                },
                {
                    "id": "CANDIDATE-004",
                    "type": "console_error",
                    "url": "https://analytics.thirdparty.com/track",
                    "first_party": False,
                    "confidence": "medium",
                    "occurrences": 1
                }
            ]
        }
        with open(self.path, 'w') as f:
            json.dump(self.data, f)
            
    def tearDown(self):
        os.close(self.fd)
        os.remove(self.path)

    def test_triage(self):
        engine = BugTriageEngine(self.path)
        engine.triage()
        
        with open(self.path, 'r') as f:
            result = json.load(f)
            
        candidates = result['root_cause_candidates']
        self.assertEqual(len(candidates), 4)
        
        # Candidate 1: 401 Authentication API
        c1 = next(c for c in candidates if c['id'] == 'CANDIDATE-001')
        self.assertEqual(c1['triage']['category'], 'authentication')
        self.assertEqual(c1['triage']['priority'], 'P3')
        self.assertEqual(c1['triage']['classification'], 'needs_manual_review')
        self.assertTrue('fingerprint' in c1)
        
        # Candidate 2: Responsive
        c2 = next(c for c in candidates if c['id'] == 'CANDIDATE-002')
        self.assertEqual(c2['triage']['category'], 'responsive_layout')
        self.assertEqual(c2['triage']['priority'], 'P1')
        self.assertEqual(c2['triage']['user_impact'], 'high')
        self.assertEqual(c2['triage']['classification'], 'confirmed_bug')
        self.assertTrue('fingerprint' in c2)
        
        # Candidate 3: 500 API > 10 occurrences -> P0
        c3 = next(c for c in candidates if c['id'] == 'CANDIDATE-003')
        self.assertEqual(c3['triage']['category'], 'server_error')
        self.assertEqual(c3['triage']['priority'], 'P0')
        self.assertEqual(c3['triage']['user_impact'], 'critical')
        self.assertEqual(c3['triage']['classification'], 'confirmed_bug')
        self.assertTrue('fingerprint' in c3)
        
        # Candidate 4: Third Party Console Error
        c4 = next(c for c in candidates if c['id'] == 'CANDIDATE-004')
        self.assertEqual(c4['triage']['category'], 'client_runtime_error')
        self.assertEqual(c4['triage']['priority'], 'P4')
        self.assertEqual(c4['triage']['user_impact'], 'low')
        self.assertEqual(c4['triage']['classification'], 'informational')
        self.assertTrue('fingerprint' in c4)
        
        metrics = result['triage_metrics']
        self.assertEqual(metrics['total_candidates'], 4)
        self.assertEqual(metrics['confirmed_bug'], 2)
        self.assertEqual(metrics['needs_manual_review'], 1)
        self.assertEqual(metrics['informational'], 1)
        
if __name__ == '__main__':
    unittest.main()
