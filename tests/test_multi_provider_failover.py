import asyncio
import json
import unittest
from unittest.mock import patch, MagicMock
import urllib.error

from core.gemini_analyzer import GeminiQAAnalyzer


class TestMultiProviderAndFailover(unittest.TestCase):
    def test_failover_advances_key_pool(self):
        pool = [
            {"api_key": "key-1", "provider_id": "gemini", "model": "gemini-2.5-flash"},
            {"api_key": "key-2", "provider_id": "openai", "model": "gpt-4o"},
            {"api_key": "key-3", "provider_id": "deepseek", "model": "deepseek-chat"},
        ]
        analyzer = GeminiQAAnalyzer(
            api_key="key-1",
            provider_id="gemini",
            model_name="gemini-2.5-flash",
            key_pool=pool,
        )
        self.assertEqual(analyzer.api_key, "key-1")
        self.assertEqual(analyzer.provider_id, "gemini")
        self.assertEqual(analyzer.current_key_idx, 0)

        # First failover -> switch to OpenAI key-2
        adv = analyzer._failover_to_next_key()
        self.assertTrue(adv)
        self.assertEqual(analyzer.api_key, "key-2")
        self.assertEqual(analyzer.provider_id, "openai")
        self.assertEqual(analyzer.model_name, "gpt-4o")
        self.assertEqual(analyzer.current_key_idx, 1)

        # Second failover -> switch to DeepSeek key-3
        adv2 = analyzer._failover_to_next_key()
        self.assertTrue(adv2)
        self.assertEqual(analyzer.api_key, "key-3")
        self.assertEqual(analyzer.provider_id, "deepseek")
        self.assertEqual(analyzer.model_name, "deepseek-chat")
        self.assertEqual(analyzer.current_key_idx, 2)

    def test_call_model_seamless_failover_on_429(self):
        pool = [
            {"api_key": "rate-limited-gemini", "provider_id": "gemini", "model": "gemini-2.5-flash"},
            {"api_key": "backup-openai-key", "provider_id": "openai", "model": "gpt-4o"},
        ]
        analyzer = GeminiQAAnalyzer(
            api_key="rate-limited-gemini",
            provider_id="gemini",
            model_name="gemini-2.5-flash",
            key_pool=pool,
        )

        calls = []

        def fake_urlopen(req, timeout=None):
            url = req.full_url
            calls.append((url, req.headers))
            if "generativelanguage.googleapis.com" in url:
                # Simulate 429 Too Many Requests
                fp = MagicMock()
                fp.read.return_value = b'{"error": {"code": 429, "message": "Resource exhausted: quota exceeded"}}'
                raise urllib.error.HTTPError(url, 429, "Too Many Requests", req.headers, fp)
            else:
                # OpenAI success
                resp = MagicMock()
                resp.read.return_value = json.dumps({
                    "choices": [{
                        "message": {"content": "{\"classification\": \"confirmed_bug\", \"severity\": \"high\"}"}
                    }]
                }).encode("utf-8")
                resp.__enter__.return_value = resp
                return resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(analyzer._call_model("test prompt"))
            finally:
                loop.close()

            # Verify failover happened seamlessly
            self.assertIn("confirmed_bug", result)
            self.assertEqual(len(calls), 2)
            # First call was to Gemini endpoint
            self.assertIn("generativelanguage.googleapis.com", calls[0][0])
            # Second call failed over to OpenAI endpoint
            self.assertIn("api.openai.com", calls[1][0])
            self.assertEqual(analyzer.provider_id, "openai")
            self.assertEqual(analyzer.api_key, "backup-openai-key")

    def test_provider_anthropic_payload_and_extraction(self):
        analyzer = GeminiQAAnalyzer(
            api_key="sk-ant-test",
            provider_id="anthropic",
            model_name="claude-3-5-sonnet-20241022",
        )

        captured_req = []

        def fake_urlopen(req, timeout=None):
            captured_req.append(req)
            resp = MagicMock()
            resp.read.return_value = json.dumps({
                "content": [
                    {"type": "text", "text": "{\"classification\": \"informational\"}"}
                ]
            }).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(analyzer._call_model("prompt"))
            finally:
                loop.close()

            self.assertEqual(result, "{\"classification\": \"informational\"}")
            req = captured_req[0]
            self.assertEqual(req.full_url, "https://api.anthropic.com/v1/messages")
            self.assertEqual(req.headers.get("X-api-key"), "sk-ant-test")
            self.assertEqual(req.headers.get("Anthropic-version"), "2023-06-01")

            body = json.loads(req.data.decode("utf-8"))
            self.assertEqual(body["model"], "claude-3-5-sonnet-20241022")
            self.assertEqual(body["messages"][0]["content"], "prompt")


if __name__ == "__main__":
    unittest.main()
