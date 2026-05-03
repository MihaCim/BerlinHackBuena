# Buena Context Engine Implementation

This repository now contains a working LangGraph-powered context compiler for the Buena hackathon dataset.

## What It Builds

- `outputs/properties/LIE-001/context.md`: living per-property markdown context file.
- `outputs/properties/LIE-001/context.meta.json`: metrics, watermark, and patch metadata.
- `outputs/properties/LIE-001/provenance.sqlite`: source register for bank, email, invoice, and letter evidence.
- `outputs/properties/LIE-001/patches/*.patch.json`: patch logs for bootstrap and each incremental day.

## Commands

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run tests:

```bash
python -m pytest -q
```

Compile the base context:

```bash
python -m context_engine bootstrap --source data --output outputs
```

Apply one delta:

```bash
python -m context_engine apply-delta --source data --output outputs --delta data/incremental/day-01
```

Replay all deltas:

```bash
python -m context_engine replay-deltas --source data --output outputs
```

Ask from the compiled context:

```bash
python -m context_engine ask --context outputs/properties/LIE-001/context.md --question "What unresolved financial anomalies exist?"
```

Show status:

```bash
python -m context_engine status --output outputs
```

Start the frontend:

```bash
python -m context_engine serve --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`.

## AI Provider

Claude can be used for optional synthesis. Set `CLAUDE_API_KEY`, `CLAUDE_BASE_URL`, and `CLAUDE_MODEL`, then pass `--use-ai`.

```bash
$env:CLAUDE_API_KEY="..."
python -m context_engine bootstrap --source data --output outputs --use-ai
```

The engine remains deterministic without an AI provider. The provider is used only for advisory notes and natural-language answer synthesis over retrieved context.

Troubleshooting:

- `401` or `403`: check `CLAUDE_API_KEY`.
- `404`: check `CLAUDE_BASE_URL` and `CLAUDE_MODEL`.
- `429`: wait or try a smaller/faster model.

## Local Env File

The CLI auto-loads a `.env` file from the repository root. Put your key there:

```env
AI_PROVIDER=claude
CLAUDE_API_KEY=your_claude_api_key_here
CLAUDE_BASE_URL=https://api.anthropic.com
CLAUDE_MODEL=claude-sonnet-4-20250514
```

If you want a template, use `.env.example`.
