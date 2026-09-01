#!/usr/bin/env python3
"""
Regression Detector

Compares the current triaged findings against the most recent historical scan 
to determine if bugs are NEW, FIXED, UNCHANGED, WORSENED, or IMPROVED.
"""

import json
import os
import glob

class RegressionDetector:
    def __init__(self, current_file, results_dir, baseline_file=None):
        self.current_file = current_file
        self.results_dir = results_dir
        self.baseline_file = baseline_file
        with open(current_file, 'r', encoding='utf-8') as f:
            self.current_data = json.load(f)

    def _get_previous_report(self):
        """Find the most recent final QA report or use the explicit baseline."""
        if self.baseline_file and os.path.exists(self.baseline_file):
            return self.baseline_file

        current_run_id = self.current_data.get('run_id')
        # We can look for final_qa_report_*.json
        files = glob.glob(os.path.join(self.results_dir, "final_qa_report_*.json"))
        
        # Sort by modification time (descending) — file names may be UUIDs,
        # not timestamps, so alphabetical sort gives the wrong ordering.
        files.sort(key=os.path.getmtime, reverse=True)
        
        for f in files:
            # Check run_id if it's in the file or just by filename
            if current_run_id and current_run_id in f:
                continue
            return f
            
        # Fallback to qa_findings if no final report
        files = glob.glob(os.path.join(self.results_dir, "qa_findings_*.json"))
        files.sort(reverse=True)
        for f in files:
            if current_run_id and current_run_id in f:
                continue
            if f != self.current_file:
                return f
                
        return None

    def detect(self):
        previous_file = self._get_previous_report()
        
        previous_fingerprints = {}
        if previous_file:
            print(f"Comparing against previous report: {previous_file}")
            with open(previous_file, 'r', encoding='utf-8') as f:
                try:
                    prev_data = json.load(f)
                    # Support both final_qa_report and qa_findings structure
                    prev_candidates = prev_data.get('findings', [])
                    if not prev_candidates:
                        prev_candidates = prev_data.get('root_cause_candidates', [])
                        
                    for c in prev_candidates:
                        # final_qa_report might wrap candidate
                        if 'candidate' in c:
                            candidate_data = c['candidate']
                        else:
                            candidate_data = c
                            
                        # Extract fingerprint (if missing, we can't track it)
                        fp = candidate_data.get('fingerprint')
                        if fp:
                            previous_fingerprints[fp] = candidate_data
                except Exception as e:
                    print(f"Failed to read previous report {previous_file}: {e}")

        candidates = self.current_data.get('root_cause_candidates', [])
        
        regression_summary = {
            "new": 0,
            "fixed": 0,
            "unchanged": 0,
            "worsened": 0,
            "improved": 0
        }

        current_fingerprints = set()

        for candidate in candidates:
            fp = candidate.get('fingerprint')
            if not fp:
                candidate['regression_status'] = "NEW"
                regression_summary["new"] += 1
                continue
                
            current_fingerprints.add(fp)
            
            if fp in previous_fingerprints:
                prev_candidate = previous_fingerprints[fp]
                
                # Check for improved/worsened (could be based on occurrences or severity)
                curr_occ = candidate.get('occurrences', 0)
                prev_occ = prev_candidate.get('occurrences', 0)
                
                if curr_occ > prev_occ:
                    candidate['regression_status'] = "WORSENED"
                    regression_summary["worsened"] += 1
                elif curr_occ < prev_occ:
                    candidate['regression_status'] = "IMPROVED"
                    regression_summary["improved"] += 1
                else:
                    candidate['regression_status'] = "UNCHANGED"
                    regression_summary["unchanged"] += 1
            else:
                candidate['regression_status'] = "NEW"
                regression_summary["new"] += 1

        # Check for fixed issues (in previous but not current)
        for fp in previous_fingerprints:
            if fp not in current_fingerprints:
                regression_summary["fixed"] += 1

        # We inject the summary into triage_metrics or as a separate block
        if 'triage_metrics' not in self.current_data:
            self.current_data['triage_metrics'] = {}
        self.current_data['triage_metrics']['regression_summary'] = regression_summary

        with open(self.current_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_data, f, indent=2, ensure_ascii=False)
            
        print(f"Regression detection complete. Summary: {regression_summary}")
        return self.current_file

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        baseline = sys.argv[3] if len(sys.argv) > 3 else None
        engine = RegressionDetector(sys.argv[1], sys.argv[2], baseline)
        engine.detect()
