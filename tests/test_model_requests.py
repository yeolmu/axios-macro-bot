"""Exercise real SDK request serialization without network or credentials."""

import json
import os
import unittest
from unittest.mock import patch

import httpx2
from openai import OpenAI

import analyzer
import global_news as g


class ModelRequestTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.outputs = []
        self.client = OpenAI(
            api_key="test-key", max_retries=0,
            http_client=httpx2.Client(transport=httpx2.MockTransport(self.respond)),
        )
        self.addCleanup(self.client.close)
        env = patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
        env.start()
        self.addCleanup(env.stop)

    def respond(self, request):
        body = json.loads(request.content)
        self.requests.append(body)
        content, reason = self.outputs.pop(0)
        return httpx2.Response(200, json={
            "id": "chatcmpl-test", "object": "chat.completion", "created": 0,
            "model": body["model"], "choices": [{
                "index": 0, "finish_reason": reason,
                "message": {"role": "assistant", "content": content},
            }],
        })

    def test_luna_request_serializes_with_nonreasoning_options(self):
        self.outputs = [("Korean briefing", "stop")]
        with patch.object(analyzer, "OpenAI", return_value=self.client):
            self.assertEqual(analyzer.analyze("Original 2.5% source"), "Korean briefing")
        body = self.requests[0]
        self.assertEqual(body["model"], "gpt-6-luna")
        self.assertEqual(body["reasoning_effort"], "none")
        self.assertEqual(body["temperature"], 0.2)
        self.assertEqual(body["max_completion_tokens"], 6000)
        self.assertNotIn("max_tokens", body)
        self.assertEqual(body["messages"][1]["content"], "Original 2.5% source")

    def test_sol_draft_repair_and_review_use_compatible_options(self):
        sources = [{"id": "s1", "kind": "Flagship", "text": "A bill is proposed."}]
        digest = {"sections": [{"title": "Policy", "bullets": [
            {"text": "A bill is proposed.", "details": [], "sources": ["s1"]}]}]}
        self.outputs = [("{}", "stop"), (json.dumps(digest), "stop"),
                        (json.dumps(digest), "stop")]
        with patch.object(g, "OpenAI", return_value=self.client):
            self.assertEqual(g.analyze_sources(sources), digest)
        self.assertEqual(len(self.requests), 3)
        for body in self.requests:
            self.assertEqual(body["model"], "gpt-6.1-sol")
            self.assertEqual(body["reasoning_effort"], "low")
            self.assertEqual(body["max_completion_tokens"], 10000)
            self.assertEqual(body["response_format"], {"type": "json_object"})
            self.assertNotIn("temperature", body)
            self.assertNotIn("max_tokens", body)
            self.assertEqual(json.loads(body["messages"][1]["content"]), sources)
        self.assertIn("sections", self.requests[1]["messages"][-1]["content"])
        self.assertEqual(self.requests[2]["messages"][-2]["role"], "assistant")

    def test_sol_truncated_response_is_rejected(self):
        self.outputs = [("{}", "length")]
        with patch.object(g, "OpenAI", return_value=self.client):
            with self.assertRaisesRegex(ValueError, "Incomplete Semafor"):
                g.analyze_sources([{"id": "s1", "kind": "Flagship", "text": "Source"}])
        self.assertEqual(len(self.requests), 1)


if __name__ == "__main__":
    unittest.main()
