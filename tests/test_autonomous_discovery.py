"""
Unit tests for Autonomous Discovery Engine & Dynamic Route Normalizer.
"""
import asyncio
import os
import tempfile
from core.discovery.route_normalizer import extract_route_template
from core.discovery.resumable_crawler import ResumableDiscoveryEngine


def test_extract_route_template():
    assert extract_route_template("https://example.com/users/123/profile") == "/users/:id/profile"
    assert extract_route_template("https://example.com/scans/550e8400-e29b-41d4-a716-446655440000") == "/scans/:uuid"
    assert extract_route_template("https://example.com/dashboard") == "/dashboard"


def test_resumable_discovery_engine_checkpoint():
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ResumableDiscoveryEngine("https://example.com", "scan_disc_001", tmp_dir)
        mock_discovery = {
            "scan_id": "scan_disc_001",
            "target_url": "https://example.com",
            "pages_crawled": 2,
            "routes_discovered": ["/login", "/dashboard"],
            "pages": [],
        }
        engine.save_checkpoint(mock_discovery)
        assert os.path.exists(engine.checkpoint_path)

        resumed = asyncio.run(engine.execute_discovery())
        assert resumed["pages_crawled"] == 2
        assert "/dashboard" in resumed["routes_discovered"]
