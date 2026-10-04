import unittest
from unittest.mock import MagicMock, patch
import os

from core.supabase_storage import (
    USER_STORAGE_LIMIT_BYTES,
    BUCKET_NAME,
    get_user_storage_usage,
    upload_scan_reports,
    get_scan_report_file,
    delete_scan_reports,
)


class TestSupabaseStorage(unittest.TestCase):
    def test_quota_constant_is_20_mb(self):
        self.assertEqual(USER_STORAGE_LIMIT_BYTES, 20 * 1024 * 1024)

    def test_get_user_storage_usage_calculation(self):
        mock_client = MagicMock()
        mock_from = MagicMock()
        mock_client.storage.from_.return_value = mock_from

        # Mock root listing with 2 scan folders
        mock_from.list.side_effect = [
            # Root user folder list
            [
                {"name": "scan_1", "id": None, "metadata": None},
                {"name": "scan_2", "id": None, "metadata": None},
            ],
            # scan_1 folder list
            [
                {"name": "report.json", "metadata": {"size": 1024 * 1024}},  # 1 MB
                {"name": "report.md", "metadata": {"size": 512 * 1024}},   # 0.5 MB
            ],
            # scan_2 folder list
            [
                {"name": "report.pdf", "metadata": {"size": 2 * 1024 * 1024}},  # 2 MB
            ],
        ]

        usage = get_user_storage_usage("test_user_1", client=mock_client)
        self.assertEqual(usage["file_count"], 3)
        expected_bytes = (1 + 0.5 + 2) * 1024 * 1024
        self.assertEqual(usage["used_bytes"], expected_bytes)
        self.assertEqual(usage["used_mb"], 3.5)
        self.assertEqual(usage["limit_mb"], 20.0)
        self.assertFalse(usage["is_quota_exceeded"])
        self.assertAlmostEqual(usage["used_percent"], 17.5, delta=0.5)

    def test_upload_scan_reports_within_quota(self):
        mock_client = MagicMock()
        mock_from = MagicMock()
        mock_client.storage.from_.return_value = mock_from
        mock_client.storage.list_buckets.return_value = [MagicMock(name="reports")]

        # Mock user currently using 5 MB
        with patch("core.supabase_storage.get_user_storage_usage") as mock_usage:
            mock_usage.return_value = {
                "used_bytes": 5 * 1024 * 1024,
                "used_mb": 5.0,
                "limit_bytes": 20 * 1024 * 1024,
            }

            with patch("os.path.isfile", return_value=True), \
                 patch("os.path.getsize", return_value=1024 * 1024), \
                 patch("builtins.open", unittest.mock.mock_open(read_data=b"test data")):

                res = upload_scan_reports(
                    user_id="user_1",
                    scan_id="scan_1",
                    local_files={"json": "/tmp/fake.json", "pdf": "/tmp/fake.pdf"},
                    client=mock_client,
                )

                self.assertTrue(res["success"])
                self.assertIn("json", res["uploaded"])
                self.assertIn("pdf", res["uploaded"])

    def test_upload_scan_reports_exceeding_20_mb_quota(self):
        mock_client = MagicMock()
        mock_client.storage.list_buckets.return_value = [MagicMock(name="reports")]

        # User currently using 19.5 MB
        with patch("core.supabase_storage.get_user_storage_usage") as mock_usage:
            mock_usage.return_value = {
                "used_bytes": int(19.5 * 1024 * 1024),
                "used_mb": 19.5,
                "limit_bytes": 20 * 1024 * 1024,
            }

            # New upload is 1 MB -> total would be 20.5 MB (> 20 MB limit)
            with patch("os.path.isfile", return_value=True), \
                 patch("os.path.getsize", return_value=1024 * 1024):

                res = upload_scan_reports(
                    user_id="user_1",
                    scan_id="scan_1",
                    local_files={"pdf": "/tmp/large.pdf"},
                    client=mock_client,
                )

                self.assertFalse(res["success"])
                self.assertEqual(res["reason"], "quota_exceeded")
                self.assertIn("20 MB", res["message"])

    def test_get_scan_report_file_direct_download(self):
        mock_client = MagicMock()
        mock_from = MagicMock()
        mock_client.storage.from_.return_value = mock_from
        mock_from.download.return_value = b"%PDF-1.4 test content"

        content = get_scan_report_file("user_1", "scan_1", "pdf", client=mock_client)
        self.assertEqual(content, b"%PDF-1.4 test content")
        mock_from.download.assert_called_with("user_1/scan_1/report.pdf")

    def test_delete_scan_reports(self):
        mock_client = MagicMock()
        mock_from = MagicMock()
        mock_client.storage.from_.return_value = mock_from
        mock_from.list.return_value = [{"name": "report.json"}, {"name": "report.pdf"}]

        success = delete_scan_reports("user_1", "scan_1", client=mock_client)
        self.assertTrue(success)
        mock_from.remove.assert_called_with([
            "user_1/scan_1/report.json",
            "user_1/scan_1/report.pdf",
        ])


if __name__ == "__main__":
    unittest.main()
