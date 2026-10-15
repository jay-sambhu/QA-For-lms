import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from worker.celery_app import celery_app
from worker.tasks import process_query_task
from api.main import app, require_user, update_scan, get_scan
from models import Scan, Base
from db import SessionLocal, engine


class TestCeleryConfiguration(unittest.TestCase):
    """Verify worker/celery_app.py configuration."""

    def test_celery_task_registration(self):
        """Test C — verify process_query_task is registered with Celery."""
        self.assertIn("worker.tasks.process_query", celery_app.tasks)
        registered_task = celery_app.tasks["worker.tasks.process_query"]
        self.assertEqual(registered_task.name, "worker.tasks.process_query")

    def test_celery_routing_and_queues(self):
        """Verify queue routing for QA jobs."""
        routes = celery_app.conf.task_routes
        self.assertIn("worker.tasks.process_query", routes)
        self.assertEqual(routes["worker.tasks.process_query"]["queue"], "qa_queue")

    def test_celery_production_settings(self):
        """Verify broker, backend, timeouts, prefetch, and ack settings."""
        self.assertTrue(celery_app.conf.broker_url)
        self.assertTrue(celery_app.conf.result_backend)
        # The pipeline's own timeout must fire before Celery's limits.
        from api.main import PIPELINE_TIMEOUT_SECONDS
        self.assertGreater(celery_app.conf.task_soft_time_limit, PIPELINE_TIMEOUT_SECONDS)
        self.assertGreater(celery_app.conf.task_time_limit, celery_app.conf.task_soft_time_limit)
        self.assertEqual(celery_app.conf.worker_prefetch_multiplier, 1)
        self.assertTrue(celery_app.conf.task_acks_late)


class TestWorkerTasks(unittest.TestCase):
    """Unit tests for worker/tasks.py."""

    @patch("worker.tasks.run_qa_pipeline")
    def test_process_query_task_success(self, mock_pipeline):
        """Test A — successful execution calls run_qa_pipeline with expected args."""
        scan_id = "test-scan-123"
        user_id = "user-456"
        url = "https://example.com"
        max_pages = 10
        auth_token = "token-xyz"

        # Execute the task synchronously with the full updated signature
        process_query_task(scan_id, user_id, url, max_pages, auth_token)

        # The task now passes login_url, username, password positionally (all None)
        # plus keyword args for the AI provider configuration
        mock_pipeline.assert_called_once_with(
            scan_id,
            user_id,
            url,
            max_pages,
            auth_token,
            None,   # login_url
            None,   # username
            None,   # password
            gemini_api_key=None,
            ai_keys_pool=None,
            provider_id=None,
            model_name=None,
            endpoint=None,
        )

    @patch("worker.tasks.run_qa_pipeline", side_effect=RuntimeError("Pipeline crash"))
    @patch("api.main.update_scan")
    def test_process_query_task_failure(self, mock_update_scan, mock_pipeline):
        """Test B — pipeline failure marks scan as failed and re-raises exception."""
        scan_id = "test-scan-err"
        user_id = "user-456"
        url = "https://example.com"
        max_pages = 5
        auth_token = None

        with self.assertRaises(RuntimeError) as ctx:
            process_query_task(scan_id, user_id, url, max_pages, auth_token)

        self.assertIn("Pipeline crash", str(ctx.exception))
        mock_pipeline.assert_called_once_with(
            scan_id,
            user_id,
            url,
            max_pages,
            auth_token,
            None,   # login_url
            None,   # username
            None,   # password
            gemini_api_key=None,
            ai_keys_pool=None,
            provider_id=None,
            model_name=None,
            endpoint=None,
        )
        mock_update_scan.assert_called_once_with(scan_id, "failed")

    def test_process_query_task_retry_configuration(self):
        """Verify retry behavior and bounds on the Celery task."""
        self.assertIn(ConnectionError, process_query_task.autoretry_for)
        self.assertIn(TimeoutError, process_query_task.autoretry_for)
        self.assertEqual(process_query_task.retry_kwargs.get("max_retries"), 3)
        self.assertEqual(process_query_task.retry_kwargs.get("countdown"), 5)


class TestApiScanEnqueue(unittest.TestCase):
    """Unit tests for POST /api/scans endpoint and Celery task enqueueing."""

    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)

        # Mock authenticated user
        self.mock_user = MagicMock()
        self.mock_user.id = "test-user-uuid-123"

        app.dependency_overrides[require_user] = lambda: self.mock_user

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch("api.main.supabase")
    @patch("worker.tasks.process_query_task.apply_async")
    def test_create_scan_enqueues_celery_task(self, mock_apply_async, mock_supabase):
        """Test API endpoint enqueues Celery task with valid parameters."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])

        # Build a mock DB user that has a gemini_api_key so the BYOK check passes.
        mock_db_user = MagicMock()
        mock_db_user.id = "test-user-uuid-123"
        mock_db_user.gemini_api_key = "test-gemini-key-abc"
        mock_db_user.plan_tier = "free"

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []           # No UserApiKey rows
        mock_query.first.return_value = mock_db_user
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()
        mock_session.rollback = MagicMock()

        payload = {
            "url": "https://example.com/lms",
            "max_pages": 15,
            "auth_token": "bearer-token-abc"
        }

        with patch("api.main.SessionLocal", return_value=mock_session):
            response = self.client.post("/api/scans", json=payload)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("scan_id", data)
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["url"], "https://example.com/lms")

        # Verify Celery apply_async was called once with the correct scan/user IDs.
        # The args list is now 13 elements (full provider config); check key positions.
        scan_id = data["scan_id"]
        self.assertTrue(mock_apply_async.called, "apply_async should have been called once")
        call_args = mock_apply_async.call_args
        task_id = call_args.kwargs.get("task_id")
        self.assertEqual(task_id, scan_id)
        args_list = call_args.kwargs.get("args", [])
        self.assertEqual(args_list[0], scan_id, "First arg should be scan_id")
        self.assertEqual(args_list[1], "test-user-uuid-123", "Second arg should be user_id")
        self.assertEqual(args_list[2], "https://example.com/lms", "Third arg should be URL")
        # Free-tier cap: max_pages must be <= 10
        self.assertLessEqual(args_list[3], 10, "max_pages should be capped by free-tier limit")


    @patch.dict(os.environ, {"ALLOW_LOCAL_TARGETS": "false"})
    def test_create_scan_ssrf_validation_rejects_invalid_url(self):
        """Test API endpoint validates URLs and blocks private/reserved IPs."""
        payload = {
            "url": "http://169.254.169.254/latest/meta-data",
            "max_pages": 5
        }

        response = self.client.post("/api/scans", json=payload)
        self.assertEqual(response.status_code, 422)


class TestDatabaseStatusLifecycle(unittest.TestCase):
    """Verify database status transitions (pending -> running -> completed / failed)."""

    def setUp(self):
        Base.metadata.create_all(bind=engine)

    def test_status_lifecycle_transitions(self):
        scan_id = "lifecycle-scan-001"
        with SessionLocal() as db:
            from models import User
            user = User(id="user-lifecycle", email="user-lifecycle@example.com")
            db.merge(user)
            db.commit()
            scan = Scan(
                id=scan_id,
                user_id="user-lifecycle",
                url="https://example.com",
                status="pending"
            )
            db.merge(scan)
            db.commit()

        # Check pending
        s = get_scan(scan_id)
        self.assertIsNotNone(s)
        self.assertEqual(s["status"], "pending")

        # Transition to running
        update_scan(scan_id, "running")
        s = get_scan(scan_id)
        self.assertEqual(s["status"], "running")

        # Transition to completed with report paths
        update_scan(scan_id, "completed", report_path="reports/scan.md", json_path="results/scan.json")
        s = get_scan(scan_id)
        self.assertEqual(s["status"], "completed")
        self.assertEqual(s["report_path"], "reports/scan.md")
        self.assertEqual(s["json_path"], "results/scan.json")
        self.assertIsNotNone(s["completed_at"])

        # Transition to failed
        update_scan(scan_id, "failed")
        s = get_scan(scan_id)
        self.assertEqual(s["status"], "failed")

