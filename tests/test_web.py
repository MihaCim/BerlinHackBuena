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

    def test_agent_api_is_mounted_on_main_web_app(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(DATA, Path(tmp)))
            client.post("/api/bootstrap", json={"use_ai": False})

            response = client.post(
                "/api/v1/agents/chat",
                json={"question": "Who owns WE 01?", "building_id": "LIE-001"},
                headers={"X-Agent-Role": "viewer"},
            )
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["building_id"], "LIE-001")
            self.assertIn("trace", body)

    def test_artifact_context_edit_is_saved_with_user_tags_and_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(DATA, Path(tmp)))
            client.post("/api/bootstrap", json={"use_ai": False})

            original = client.get("/api/context").text
            edited = original.replace(
                "This is the canonical working context",
                "Human confirmed this is the canonical working context",
                1,
            )
            response = client.put(
                "/api/context",
                json={
                    "content": edited,
                    "author": "test-user",
                },
            )
            self.assertEqual(response.status_code, 200)

            context = client.get("/api/context")
            self.assertIn("<user ", context.text)
            self.assertIn("</user>", context.text)
            self.assertIn("Human confirmed this is the canonical working context", context.text)

            delta = client.post("/api/apply-delta", json={"day": "day-01", "use_ai": False})
            self.assertEqual(delta.status_code, 200)
            context_after_delta = client.get("/api/context")
            self.assertIn("Human confirmed this is the canonical working context", context_after_delta.text)

    def test_resource_intake_stages_text_for_future_ingestion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(DATA, Path(tmp)))

            response = client.post(
                "/api/resources",
                json={
                    "name": "new-owner-email.txt",
                    "kind": "email",
                    "content": "Subject: Eigentumer update\nPlease add this to the next ingestion run.",
                    "notes": "Manual test resource",
                },
            )
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["status"], "staged")
            self.assertEqual(body["resource"]["status"], "staged_for_ingestion")

            resources = client.get("/api/resources")
            self.assertEqual(resources.status_code, 200)
            self.assertEqual(len(resources.json()["resources"]), 1)
            self.assertEqual(resources.json()["resources"][0]["kind"], "email")

    def test_agentic_intake_writes_valid_resource_to_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(DATA, Path(tmp)))
            client.post("/api/bootstrap", json={"use_ai": False})
            client.post(
                "/api/resources",
                json={
                    "name": "heating-vendor-email.txt",
                    "kind": "email",
                    "content": "Subject: Heating repair update\nVendor confirms the heating repair appointment on 2026-04-27 for the WEG.",
                    "notes": "Should become communication context",
                },
            )

            response = client.post("/api/process-intake", json={"use_ai": False})
            self.assertEqual(response.status_code, 200)
            processed = response.json()["processed"]
            self.assertEqual(processed[0]["status"], "written_to_context")
            self.assertEqual(processed[0]["target_section"], "recent_communications")

            context = client.get("/api/context")
            self.assertIn("AGENT_INTAKE_START", context.text)
            self.assertIn("heating-vendor-email.txt", context.text)
            self.assertIn("Heating repair update", context.text)

            delta = client.post("/api/apply-delta", json={"day": "day-01", "use_ai": False})
            self.assertEqual(delta.status_code, 200)
            context_after_delta = client.get("/api/context")
            self.assertIn("AGENT_INTAKE_START", context_after_delta.text)
            self.assertIn("Heating repair update", context_after_delta.text)

    def test_agentic_intake_rejects_spam_without_changing_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(DATA, Path(tmp)))
            client.post("/api/bootstrap", json={"use_ai": False})
            before = client.get("/api/context").text
            client.post(
                "/api/resources",
                json={
                    "name": "spam.txt",
                    "kind": "text",
                    "content": "Buy now! Limited time offer. Click here to claim free money. https://spam.example",
                    "notes": "Should be rejected",
                },
            )

            response = client.post("/api/process-intake", json={"use_ai": False})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["processed"][0]["status"], "rejected")
            after = client.get("/api/context").text
            self.assertEqual(before, after)

            resources = client.get("/api/resources").json()["resources"]
            self.assertEqual(resources[0]["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
