`# BerlinHackBuena

Context management project for a Berlin hackathon.

## Overview

BerlinHackBuena is an early-stage hackathon project focused on turning scattered business context into usable, searchable, and explainable information. The repository currently contains a sample data set under `hackathon/` with documents such as invoices, emails, letters, bank data, master data, and incremental updates.

The goal is to build a system that can ingest these sources, extract relevant facts, preserve provenance, and help users answer operational questions with the right context.

## Repository Structure

```text
.
├── hackathon/
│   ├── bank/          # Bank-related source data
│   ├── briefe/        # Letters and written correspondence
│   ├── emails/        # Email source files
│   ├── incremental/   # Incremental data drops or updates
│   ├── rechnungen/    # Invoice PDFs
│   └── stammdaten/    # Master data
└── README.md
```

## Project Goals

- Ingest structured and unstructured business documents.
- Extract entities, dates, amounts, relationships, and document metadata.
- Link information across emails, invoices, bank records, letters, and master data.
- Provide a context layer that supports reliable search, retrieval, and question answering.
- Keep source references available so answers can be traced back to original documents.

## Initial Ideas

- Document parsing pipeline for PDFs, emails, and tabular files.
- Normalized data model for contacts, companies, invoices, payments, messages, and events.
- Vector and keyword search over extracted content.
- Context API for retrieving the most relevant facts and source snippets.
- Simple user interface for exploring documents and asking questions.

## Getting Started

The repository now includes a runnable LangGraph-powered Python context engine.

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Create a local `.env` file in the repo root and paste your Academic Cloud key:

```env
AI_PROVIDER=academiccloud
ACADEMIC_CLOUD_API_KEY=your_academic_cloud_key_here
ACADEMIC_CLOUD_BASE_URL=https://chat-ai.academiccloud.de/v1
ACADEMIC_CLOUD_MODEL=llama-3.3-70b-instruct
```

The CLI auto-loads `.env` from the working directory, so you do not need to export it manually every time.

Run tests:

```bash
python -m pytest -q
```

Compile the base context:

```bash
python -m context_engine bootstrap --source data --output outputs
```

Apply a single incremental day:

```bash
python -m context_engine apply-delta --source data --output outputs --delta data/incremental/day-01
```

Replay all incremental days:

```bash
python -m context_engine replay-deltas --source data --output outputs
```

Ask from the compiled markdown context:

```bash
python -m context_engine ask --context outputs/properties/LIE-001/context.md --question "What unresolved financial anomalies exist?"
```

Ask with AI synthesis enabled:

```bash
python -m context_engine ask --context outputs/properties/LIE-001/context.md --question "What should a property manager review first today?" --use-ai
```

Show current output status:

```bash
python -m context_engine status --output outputs
```

AI synthesis is optional. Set `ACADEMIC_CLOUD_API_KEY` and pass `--use-ai` to enable Academic Cloud for advisory notes and natural-language answers.
The tested default model is `llama-3.3-70b-instruct`; you can override it with `ACADEMIC_CLOUD_MODEL` in `.env`.

Start the web dashboard:

```bash
python -m context_engine serve --host 127.0.0.1 --port 8765
```

Then open:

```text
http://127.0.0.1:8765
```

Manual test flow:

```bash
python -m context_engine bootstrap --source data --output outputs --use-ai
python -m context_engine apply-delta --source data --output outputs --delta data/incremental/day-01 --use-ai
python -m context_engine replay-deltas --source data --output outputs --use-ai
python -m context_engine status --output outputs
python -m context_engine ask --context outputs/properties/LIE-001/context.md --question "What unresolved financial anomalies exist?"
```

## Data Notes

The `hackathon/` directory appears to contain hackathon data and should be treated as project input. Avoid committing generated indexes, embeddings, temporary parse outputs, or local databases unless the team explicitly decides they belong in version control.

## Development Notes

Add stack-specific setup instructions here once the project has a runtime, for example:

```bash
# install dependencies

# run tests

# start the app
```

## License

License not specified yet.
