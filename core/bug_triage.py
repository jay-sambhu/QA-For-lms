#!/usr/bin/env python3
"""
AI Bug Triage and Root-Cause Analysis Engine.

Consumes root cause candidates and applies deterministic logic to assign:
- Classification (confirmed_bug, high_confidence_candidate, needs_manual_review, expected_behavior, informational, duplicate)
- Severity, Confidence, Priority (P0-P4)
- User Impact (critical, high, medium, low, none, unknown)
- Root Cause Category
- Stable Fingerprint (for regression tracking)
"""

import json
import hashlib
from urllib.parse import urlparse

class BugTriageEngine:
    def __init__(self, findings_file):
        self.findings_file = findings_file
        with open(findings_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

    def _normalize_path(self, url):
        if not url:
            return ""
        parsed = urlparse(url)
        return parsed.path.rstrip('/')

    def _determine_category(self, candidate):
        """Determine the root cause category."""
        c_type = candidate.get('type')
        status = candidate.get('status')
        if c_type == 'responsive_issue':
            return 'responsive_layout'
        if c_type == 'console_error':
            return 'client_runtime_error'
        if c_type == 'network_failure':
            return 'network_failure'
        if c_type == 'interactive_failure':
            return 'ui_interaction_failure'
        
        if c_type == 'http_error':
            if status in (401, 403):
                return 'authentication' if status == 401 else 'authorization'
            if status == 404:
                return 'broken_link'
            if status == 400:
                return 'form_validation'
            if status and status >= 500:
                return 'server_error'
            return 'api_failure'
            
        return 'unknown'

    def _determine_user_impact(self, candidate, category, is_first_party, is_api):
        """Determine the user impact level."""
        if not is_first_party:
            return 'low' if category != 'network_failure' else 'none'
            
        if category == 'server_error':
            return 'critical'
        
        if category == 'authentication':
            # Unauthenticated endpoints might be expected, so impact is unknown or low
            return 'unknown'
            
        if category == 'client_runtime_error':
            return 'high'
            
        if category == 'responsive_layout':
            severity = candidate.get('severity', 'low')
            if severity == 'high':
                return 'high'
            return 'low'
            
        if category == 'broken_link':
            return 'medium'
            
        return 'medium'

    def _determine_priority(self, candidate, category, impact, is_first_party):
        """Calculate developer priority P0-P4."""
        status = candidate.get('status')
        
        # Third party stuff is P4 or P3
        if not is_first_party:
            return 'P4'
            
        if impact == 'critical':
            return 'P0'
            
        if category == 'authentication' and status == 401:
            # Often false positives on public pages
            return 'P3'
            
        if category == 'server_error':
            return 'P0' if candidate.get('occurrences', 0) > 10 else 'P1'
            
        if category == 'client_runtime_error':
            return 'P1'
            
        if category == 'responsive_layout':
            return 'P1' if impact == 'high' else 'P3'
            
        if category == 'broken_link':
            return 'P2'
            
        return 'P2'

    def _determine_classification(self, candidate, category, priority, confidence):
        """Calculate the classification of the finding."""
        status = candidate.get('status')
        
        if category == 'authentication' and status == 401:
            return 'needs_manual_review'
            
        if not candidate.get('first_party', True):
            return 'informational'
            
        if confidence == 'high' and priority in ('P0', 'P1', 'P2'):
            return 'confirmed_bug'
            
        if confidence == 'medium':
            return 'high_confidence_candidate'
            
        return 'needs_manual_review'

    def _generate_deterministic_explanation(self, candidate, category, is_api):
        """Generate a deterministic root cause summary and recommendation."""
        summary = candidate.get('description', 'Unknown error.')
        action = "Investigate the failure and resolve."
        owner = "unknown"
        
        if category == 'authentication':
            summary = f"The application made an unauthenticated request to an API endpoint resulting in HTTP {candidate.get('status')}."
            action = "Verify whether unauthenticated requests are expected on these pages and suppress them if no session exists."
            owner = "frontend"
        elif category == 'broken_link':
            summary = "A resource or page could not be found (HTTP 404)."
            action = "Ensure the resource exists or remove the broken reference."
            owner = "backend" if is_api else "frontend"
        elif category == 'server_error':
            summary = "The server encountered an internal error while processing the request."
            action = "Check server logs for the stack trace and fix the underlying exception."
            owner = "backend"
        elif category == 'responsive_layout':
            summary = candidate.get('description', 'Layout elements overflowed the device viewport.')
            action = "Update CSS rules (e.g., max-width, overflow) to ensure the component is responsive."
            owner = "frontend"
        elif category == 'client_runtime_error':
            summary = "A JavaScript exception was thrown during execution."
            action = "Fix the unhandled exception in the client code."
            owner = "frontend"
            
        return summary, action, owner

    def triage(self):
        candidates = self.data.get('root_cause_candidates', [])
        
        triage_metrics = {
            "total_candidates": len(candidates),
            "confirmed_bug": 0,
            "needs_manual_review": 0,
            "expected_behavior": 0,
            "informational": 0,
            "high_confidence_candidate": 0,
            "duplicate": 0,
            "priority": {"P0": 0, "P1": 0, "P2": 0, "P3": 0, "P4": 0}
        }

        for candidate in candidates:
            is_first_party = candidate.get('first_party', True)
            url = candidate.get('url', '')
            is_api = 'api' in url.lower()
            
            category = self._determine_category(candidate)
            impact = self._determine_user_impact(candidate, category, is_first_party, is_api)
            priority = self._determine_priority(candidate, category, impact, is_first_party)
            
            # Use deterministic confidence from bug_detector if available, otherwise fallback
            confidence = candidate.get('confidence', 'medium')
            
            classification = self._determine_classification(candidate, category, priority, confidence)
            
            # Generate deterministic explanations
            summary, action, owner = self._generate_deterministic_explanation(candidate, category, is_api)
            
            candidate['triage'] = {
                'classification': classification,
                'priority': priority,
                'category': category,
                'user_impact': impact,
                'confidence': confidence,
                'root_cause': {
                    'category': category,
                    'summary': summary,
                    'confidence': confidence
                },
                'recommendation': {
                    'action': action,
                    'priority': priority,
                    'owner': owner
                }
            }
            
            # Generate stable fingerprint
            # Base it on category + normalized path + method + status
            path = self._normalize_path(url)
            status = candidate.get('status', '')
            method = candidate.get('method', '')
            # If no URL, use title/description (e.g., responsive issues)
            if not path:
                path = candidate.get('title', '')
                
            fingerprint_raw = f"{category}|{path}|{status}|{method}"
            candidate['fingerprint'] = hashlib.md5(fingerprint_raw.encode('utf-8')).hexdigest()
            
            # Update metrics
            triage_metrics[classification] = triage_metrics.get(classification, 0) + 1
            triage_metrics['priority'][priority] += 1
            
        self.data['triage_metrics'] = triage_metrics
        
        with open(self.findings_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
            
        print(f"Triaged {len(candidates)} candidates.")
        return self.findings_file

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        engine = BugTriageEngine(sys.argv[1])
        engine.triage()
