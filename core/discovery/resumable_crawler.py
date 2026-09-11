"""
Resumable Autonomous Discovery Engine Manager for JASUSS.
Extends base crawler capabilities with checkpointing, dynamic route mapping, and interactive element extraction.
"""
import json
import os
import time
from typing import Dict, Optional, Any

from crawler.crawler import WebsiteCrawler
from core.discovery.route_normalizer import extract_route_template
from core.schemas.discovery import ElementModel, FormModel


class ResumableDiscoveryEngine:
    def __init__(self, start_url: str, run_id: str, results_dir: str, max_pages: int = 30, progress_cb: Optional[Any] = None, **kwargs):
        self.start_url = start_url
        self.run_id = run_id
        self.results_dir = results_dir
        self.max_pages = max_pages
        self.progress_cb = progress_cb
        self.kwargs = kwargs
        self.checkpoint_path = os.path.join(results_dir, f"discovery_checkpoint_{run_id}.json")

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Loads checkpoint data if available."""
        if os.path.exists(self.checkpoint_path):
            try:
                with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def save_checkpoint(self, discovery_data: Dict[str, Any]):
        """Saves current discovery state to checkpoint file."""
        os.makedirs(self.results_dir, exist_ok=True)
        with open(self.checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(discovery_data, f, indent=2)

    async def execute_discovery(self) -> Dict[str, Any]:
        """Executes autonomous discovery with checkpointing."""
        checkpoint = self.load_checkpoint()
        if checkpoint and checkpoint.get("pages_crawled", 0) > 0:
            print(f"Resuming autonomous discovery from checkpoint: {self.checkpoint_path}")
            return checkpoint

        crawler = WebsiteCrawler(
            self.start_url,
            max_pages=self.max_pages,
            run_id=self.run_id,
            output_dir=os.path.dirname(self.results_dir),
            progress_cb=self.progress_cb,
            **self.kwargs
        )
        raw_result = await crawler.crawl()

        # Enrich raw crawl output with dynamic route normalization & typed discovery model
        pages = raw_result.get("pages", [])
        routes_set = set()
        enriched_pages = []

        for p in pages:
            url = p.get("url", "")
            route_template = extract_route_template(url)
            routes_set.add(route_template)

            # Map raw elements into typed ElementModels
            raw_elements = p.get("interactive_elements", [])
            element_models = [
                ElementModel(
                    element_id=f"el_{idx}",
                    tag_name=el.get("tag", "button"),
                    text=el.get("text"),
                    attributes={"href": el.get("href", "")} if el.get("href") else {},
                    is_visible=True,
                )
                for idx, el in enumerate(raw_elements)
            ]

            # Map forms into typed FormModels
            raw_forms = p.get("forms", [])
            form_models = [
                FormModel(
                    form_id=f"form_{idx}",
                    action=fm.get("action"),
                    method=fm.get("method", "POST"),
                    inputs=fm.get("inputs", []),
                )
                for idx, fm in enumerate(raw_forms)
            ]

            enriched_pages.append({
                "page_id": f"page_{len(enriched_pages)+1}",
                "url": url,
                "route": route_template,
                "title": p.get("title"),
                "elements": [el.model_dump() for el in element_models],
                "forms": [fm.model_dump() for fm in form_models],
                "api_calls": p.get("api_calls", []),
                "console_errors": p.get("console_errors", []),
            })

        discovery_summary = {
            "scan_id": self.run_id,
            "target_url": self.start_url,
            "start_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pages_crawled": raw_result.get("pages_crawled", len(pages)),
            "pages_attempted": raw_result.get("pages_attempted", len(pages)),
            "routes_discovered": list(routes_set),
            "pages": enriched_pages,
            "output_file": raw_result.get("output_file"),
        }

        self.save_checkpoint(discovery_summary)
        return discovery_summary
