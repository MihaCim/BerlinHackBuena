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

Academic Cloud is the default optional AI provider. Set `ACADEMIC_CLOUD_API_KEY`, then pass `--use-ai`.

```bash
$env:ACADEMIC_CLOUD_API_KEY="..."
python -m context_engine bootstrap --source data --output outputs --use-ai
```

The engine remains deterministic without an AI provider. The provider is used only for advisory notes and natural-language answer synthesis over retrieved context.

Troubleshooting:

- `401` or `403`: check `ACADEMIC_CLOUD_API_KEY`.
- `404`: check `ACADEMIC_CLOUD_MODEL`; `llama-3.3-70b-instruct` has been tested.
- `429`: wait or try a smaller/faster model.

## Local Env File

The CLI auto-loads a `.env` file from the repository root. Put your key there:

```env
AI_PROVIDER=academiccloud
ACADEMIC_CLOUD_API_KEY=your_academic_cloud_key_here
ACADEMIC_CLOUD_BASE_URL=https://chat-ai.academiccloud.de/v1
ACADEMIC_CLOUD_MODEL=llama-3.3-70b-instruct
```

If you want a template, use `.env.example`.
