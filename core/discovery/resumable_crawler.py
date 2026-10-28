"""
Resumable Autonomous Discovery Engine Manager for JASUSS.
Extends base crawler capabilities with checkpointing, dynamic route mapping, and interactive element extraction.
"""
import json
import os
import time
from typing import Dict, Optional, Any, List

from crawler.crawler import WebsiteCrawler
from core.discovery.route_normalizer import extract_route_template
from core.schemas.discovery import ElementModel, FormModel


def _bare_url(page: Dict[str, Any]) -> str:
    """The requested URL without the crawler's ' [Device]' suffix."""
    return page.get("actual_url") or str(page.get("url", "")).rsplit(" [", 1)[0]


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

    @staticmethod
    def _merge_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """One record per URL with the list of viewports it was rendered on.

        The crawler emits one record per URL per device; routes and test
        cases must be derived per URL, otherwise a 10-page crawl becomes 30
        routes named '/ [Desktop Chrome]'."""
        merged: Dict[str, Dict[str, Any]] = {}
        order: List[str] = []
        for p in pages:
            url = _bare_url(p)
            if not url:
                continue
            device = p.get("device") or ""
            entry = merged.get(url)
            if entry is None:
                entry = {
                    "url": url,
                    "viewports": [],
                    "errors": [],
                    "renders": [],
                }
                merged[url] = entry
                order.append(url)
            if device and device not in entry["viewports"]:
                entry["viewports"].append(device)
            if p.get("error"):
                entry["errors"].append(str(p.get("error")))
                continue
            entry["renders"].append(p)
        return [merged[u] for u in order]

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
        try:
            raw_result = await crawler.crawl()
        except Exception as crawl_err:
            print(f"[DISCOVERY] Unexpected crawler error: {crawl_err}")
            raw_result = {
                "target": self.start_url,
                "run_id": self.run_id,
                "pages_crawled": 0,
                "pages_attempted": 1,
                "pages": [{"url": self.start_url, "actual_url": self.start_url, "error": str(crawl_err)}],
                "output_file": None,
            }
            # A partially written crawl file (the crawler persists after
            # every URL) is still usable evidence.
            partial_file = getattr(crawler, "output_file", None)
            if partial_file and os.path.exists(partial_file):
                try:
                    with open(partial_file, "r", encoding="utf-8") as f:
                        partial = json.load(f)
                    if partial.get("pages"):
                        partial["output_file"] = partial_file
                        partial["partial"] = True
                        partial.setdefault("crawl_error", str(crawl_err))
                        raw_result = partial
                except Exception:
                    pass

        # Enrich raw crawl output with dynamic route normalization & typed discovery model
        pages = raw_result.get("pages", [])
        routes_set = set()
        enriched_pages = []

        for merged in self._merge_pages(pages):
            url = merged["url"]
            renders = merged["renders"]
            primary = None
            for r in renders:
                if "desktop" in str(r.get("device", "")).lower():
                    primary = r
                    break
            if primary is None and renders:
                primary = renders[0]
            primary = primary or {}

            route_template = extract_route_template(url)
            if renders:
                routes_set.add(route_template)

            # Map raw elements into typed ElementModels
            raw_elements = primary.get("interactive_elements", [])
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
            raw_forms = primary.get("forms", [])
            form_models = [
                FormModel(
                    form_id=f"form_{idx}",
                    action=fm.get("action"),
                    method=fm.get("method", "POST"),
                    inputs=fm.get("inputs", []),
                )
                for idx, fm in enumerate(raw_forms)
            ]

            page_id_prefix = f"{url} ["
            page_api_calls = [
                call for call in raw_result.get("api_calls", []) or []
                if str(call.get("page", "")).startswith(page_id_prefix)
            ]
            page_console = [
                err.get("text", "") for err in raw_result.get("console_errors", []) or []
                if str(err.get("page", "")).startswith(page_id_prefix)
            ]

            enriched_pages.append({
                "page_id": f"page_{len(enriched_pages)+1}",
                "url": url,
                "route": route_template,
                "title": primary.get("title"),
                "status": primary.get("status"),
                "final_url": primary.get("final_url"),
                "redirected": bool(primary.get("redirected")),
                "auth_wall": bool(primary.get("auth_wall")),
                "viewports": merged["viewports"],
                "screenshot": primary.get("screenshot"),
                "timings": primary.get("timings"),
                "a11y_checks": primary.get("a11y_checks"),
                "responsive_checks": primary.get("responsive_checks"),
                "elements": [el.model_dump() for el in element_models],
                "forms": [fm.model_dump() for fm in form_models],
                "api_calls": page_api_calls,
                "console_errors": page_console,
                # Kept so run_qa can report *why* discovery failed. Only set
                # when no viewport rendered the page.
                "error": (merged["errors"][0] if merged["errors"] and not renders else None),
            })

        discovery_summary = {
            "scan_id": self.run_id,
            "target_url": self.start_url,
            "start_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pages_crawled": raw_result.get("pages_crawled", len([p for p in enriched_pages if not p.get("error")])),
            "pages_attempted": raw_result.get("pages_attempted", len(pages)),
            "pages_failed": raw_result.get("pages_failed", len([p for p in enriched_pages if p.get("error")])),
            "pages_discovered": raw_result.get("pages_discovered", len(enriched_pages)),
            "max_pages": raw_result.get("max_pages", self.max_pages),
            "devices_tested": raw_result.get("devices_tested"),
            "viewports_tested": raw_result.get("devices", []),
            "partial": bool(raw_result.get("partial")),
            "auth_wall_pages": raw_result.get("auth_wall_pages", 0),
            "routes_discovered": sorted(routes_set),
            "pages": enriched_pages,
            "api_calls": raw_result.get("api_calls", []) or [],
            "output_file": raw_result.get("output_file"),
        }

        self.save_checkpoint(discovery_summary)
        return discovery_summary
