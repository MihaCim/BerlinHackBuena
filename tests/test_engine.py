from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from context_engine.agent import run_engine
from context_engine.parsers import build_context_data
from context_engine.qa import answer_from_context
from context_engine.schema_registry import parser_contract, patch_contract, render_contract
from context_engine.utils import read_text


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class ContextEngineTests(unittest.TestCase):
    def test_schema_contracts_drive_core_pipeline(self) -> None:
        parser = parser_contract()
        render = render_contract()
        patch = patch_contract()
        self.assertIn("emails", parser["families"])
        self.assertEqual(render["sections"][0]["anchor"], "agent_brief")
        self.assertIn("financial_state", patch["patchable_sections"])
        self.assertIn("recent_communications", patch["patchable_sections"])

    def test_build_context_data_counts(self) -> None:
        data = build_context_data(DATA)
        self.assertEqual(data["master"]["liegenschaft"]["id"], "LIE-001")
        self.assertGreaterEqual(data["metrics"]["bank_transactions"], 1600)
        self.assertGreaterEqual(data["metrics"]["emails"], 6500)
        self.assertGreaterEqual(data["metrics"]["invoices"], 190)

    def test_bootstrap_outputs_context_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = run_engine(DATA, out)
            context = Path(state["context_path"])
            self.assertTrue(context.exists())
            text = read_text(context)
            self.assertIn("Property Context", text)
            self.assertIn("SECTION:financial_state", text)
            self.assertTrue((out / "properties" / "LIE-001" / "context.meta.json").exists())
            self.assertTrue((out / "properties" / "LIE-001" / "provenance.sqlite").exists())

    def test_delta_patch_preserves_human_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = run_engine(DATA, out)
            context = Path(state["context_path"])
            text = read_text(context).replace(
                "Human-maintained notes live here and must never be overwritten by the engine.",
                "HUMAN CUSTOM NOTE: keep this exact sentence.",
            )
            context.write_text(text, encoding="utf-8")
            state = run_engine(DATA, out, mode="delta", delta_path=DATA / "incremental" / "day-01")
            patched = read_text(Path(state["context_path"]))
            self.assertIn("HUMAN CUSTOM NOTE: keep this exact sentence.", patched)
            self.assertIn("source_watermark: day-01", patched)
            self.assertTrue(state["patch_log"]["human_notes_preserved"])

    def test_replay_all_deltas_reaches_day_10(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = run_engine(DATA, out)
            for day in sorted((DATA / "incremental").glob("day-*")):
                state = run_engine(DATA, out, mode="delta", delta_path=day)
            context = Path(state["context_path"])
            text = read_text(context)
            self.assertIn("source_watermark: day-10", text)
            self.assertTrue((out / "properties" / "LIE-001" / "patches" / "day-10.patch.json").exists())

    def test_ask_from_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = run_engine(DATA, out, mode="delta", delta_path=DATA / "incremental" / "day-01")
            answer = answer_from_context(Path(state["context_path"]), "What unresolved financial anomalies exist?")
            self.assertIn("financial attention", answer)
            self.assertNotIn("Answer from", answer)


if __name__ == "__main__":
    unittest.main()
