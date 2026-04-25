from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from context_engine.web import create_app


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class WebAppTests(unittest.TestCase):
    def test_status_before_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(DATA, Path(tmp)))
            response = client.get("/api/status")
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["property_id"], "LIE-001")
            self.assertFalse(body["context_exists"])

    def test_bootstrap_and_ask_through_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(DATA, Path(tmp)))
            response = client.post("/api/bootstrap", json={"use_ai": False})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["watermark"], "bootstrap")

            context = client.get("/api/context")
            self.assertEqual(context.status_code, 200)
            self.assertIn("Property Context", context.text)

            answer = client.post("/api/ask", json={"question": "What unresolved financial anomalies exist?", "use_ai": False})
            self.assertEqual(answer.status_code, 200)
            self.assertIn("financial attention", answer.json()["answer"])


if __name__ == "__main__":
    unittest.main()
