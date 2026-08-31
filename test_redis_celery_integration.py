import os
import sys
import time
import threading
import unittest
import fakeredis
from unittest.mock import patch, MagicMock

from worker.celery_app import celery_app
from worker.tasks import process_query_task
from models import Scan, Base
from db import SessionLocal, engine


class TestRealRedisCeleryIntegration(unittest.TestCase):
    """Integration test suite using real Redis TCP server and Celery task dispatch."""

    @classmethod
    def setUpClass(cls):
        # Initialize in-memory SQLite schema
        Base.metadata.create_all(bind=engine)

        # Start real TCP Redis server on port 6389 to avoid port conflicts
        cls.redis_port = 6389
        cls.redis_server = fakeredis.TcpFakeServer(("127.0.0.1", cls.redis_port))
        cls.server_thread = threading.Thread(target=cls.redis_server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.2)

        # Configure Celery app with real Redis TCP broker/backend
        cls.redis_url = f"redis://127.0.0.1:{cls.redis_port}/0"
        celery_app.conf.update(
            broker_url=cls.redis_url,
            result_backend=cls.redis_url,
            task_always_eager=False,
        )

    @classmethod
    def tearDownClass(cls):
        try:
            cls.redis_server.shutdown()
        except Exception:
            pass

    def test_redis_tcp_ping(self):
        """Step 3 — verify Redis accepts real TCP connections and responds to PING."""
        import redis
        client = redis.Redis(host="127.0.0.1", port=self.redis_port)
        self.assertTrue(client.ping())

    def test_celery_task_dispatch_to_redis(self):
        """Step 5 & 7 — verify task submission into Redis qa_queue."""
        import redis
        client = redis.Redis(host="127.0.0.1", port=self.redis_port)

        # Dispatch task to qa_queue in Redis
        async_res = process_query_task.apply_async(
            args=["scan-test-redis-01", "user-01", "https://example.com", 5, None],
            queue="qa_queue"
        )
        self.assertIsNotNone(async_res.id)

        # Verify Redis queue key exists and has length >= 1
        queue_len = client.llen("qa_queue")
        self.assertGreaterEqual(queue_len, 1)

    @patch("worker.tasks.run_qa_pipeline")
    def test_task_execution_flow(self, mock_pipeline):
        """Step 6 — verify task execution when processed by worker/apply."""
        scan_id = "scan-exec-101"
        user_id = "user-exec-101"
        url = "https://example.com/course"
        max_pages = 8
        auth_token = "tok-123"

        # Execute task
        res = process_query_task.apply(args=[scan_id, user_id, url, max_pages, auth_token])
        self.assertTrue(res.successful())
        mock_pipeline.assert_called_once_with(scan_id, user_id, url, max_pages, auth_token)

    @patch("worker.tasks.run_qa_pipeline", side_effect=RuntimeError("Controlled failure in QA stage"))
    @patch("api.main.update_scan")
    def test_task_failure_updates_status(self, mock_update_scan, mock_pipeline):
        """Step 8 — verify failure in pipeline updates database status to failed."""
        scan_id = "scan-fail-202"
        user_id = "user-fail-202"

        with self.assertRaises(RuntimeError):
            process_query_task.apply(args=[scan_id, user_id, "https://bad-url.com", 2, None], throw=True)

        mock_update_scan.assert_called_once_with(scan_id, "failed")

    def test_transient_error_retry_configuration(self):
        """Step 9 — verify retry behavior is bounded for transient connection errors."""
        self.assertIn(ConnectionError, process_query_task.autoretry_for)
        self.assertIn(TimeoutError, process_query_task.autoretry_for)
        self.assertEqual(process_query_task.retry_kwargs["max_retries"], 3)
        self.assertEqual(process_query_task.retry_kwargs["countdown"], 5)
