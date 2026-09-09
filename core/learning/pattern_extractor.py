"""
Historical Learning and Failure Pattern Extraction Engine (Phase 13).
"""
import json
import os
import time
from typing import Dict, List, Any
from pydantic import BaseModel


class FailurePatternModel(BaseModel):
    pattern_id: str
    affected_route: str
    failure_type: str
    frequency: int = 1
    last_observed: str
    recommended_priority: str = "P0"


class HistoricalLearningEngine:
    def __init__(self, application_id: str, knowledge_dir: str):
        self.application_id = application_id
        self.knowledge_dir = knowledge_dir
        self.learning_file = os.path.join(knowledge_dir, f"learning_patterns_{application_id}.json")

    def record_run_outcomes(self, scan_defects: List[Dict[str, Any]]) -> List[FailurePatternModel]:
        patterns_map: Dict[str, FailurePatternModel] = {}
        if os.path.exists(self.learning_file):
            try:
                with open(self.learning_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    for item in raw:
                        pm = FailurePatternModel(**item)
                        patterns_map[pm.pattern_id] = pm
            except Exception:
                pass

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for defect in scan_defects:
            url = defect.get("affected_url", "unknown_route")
            title = defect.get("title", "failure")
            pid = f"pat_{hash(url + title) & 0xffffff:06x}"

            if pid in patterns_map:
                existing = patterns_map[pid]
                existing.frequency += 1
                existing.last_observed = now
            else:
                patterns_map[pid] = FailurePatternModel(
                    pattern_id=pid,
                    affected_route=url,
                    failure_type=title,
                    frequency=1,
                    last_observed=now,
                    recommended_priority="P0" if defect.get("severity") == "critical" else "P1",
                )

        patterns_list = list(patterns_map.values())
        os.makedirs(self.knowledge_dir, exist_ok=True)
        dump_data = [p.model_dump() for p in patterns_list]
        with open(self.learning_file, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=2)

        return patterns_list
