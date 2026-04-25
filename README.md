# BerlinHackBuena

Property management runs on context. Every ticket, email, and owner question requires knowing a hundred things about one specific building: Who owns it, what the last assembly decided, whether the roof leak is open, who the heating contractor is.

Today, that context is scattered across ERPs, Gmail, Slack, Google Drive, scanned PDFs, and the head of the property manager who's been there twelve years. AI agents have to crawl all of it for every single task.

**The Goal**

Build an engine that produces a single Context Markdown File per property. That's a living, self-updating document containing every fact an AI agent needs to act. Dense, structured, traced to its source, surgically updated without destroying human edits. Think CLAUDE.md, but for a building, plus it writes itself.

**Why this is hard**

1. Schema alignment: "owner" is called Eigentümer, MietEig, Kontakt, or owner depending on the source system. You must resolve identities across ERPs.

2. Surgical updates: when an new email arrives you can't generate a whole new file. Regenerating the file destroys human edits and burns tokens. You must patch exactly the right section.

3. Signal vs. noise: 90% of emails are irrelevant. The engine must judge what belongs in the context and what doesn't.

## Overview

BerlinHackBuena is an early-stage hackathon project focused on turning scattered business context into usable, searchable, and explainable information. The repository currently contains a sample data set under `hackathon/` with documents such as invoices, emails, letters, bank data, master data, and incremental updates.

The goal is to build a system that can ingest these sources, extract relevant facts, preserve provenance, and help users answer operational questions with the right context.

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

The repository now includes a FastAPI ingestion service that scans `data/`, ignores `data/DATA_SUMMARY.md`, checkpoints batch/source ingestion in local SQLite, and normalizes raw files into LLM-friendly Markdown under `normalize/`.

Possible first milestones:

1. Add a document ingestion script.
2. Extract metadata....

## Data Notes

## Development Notes

Add stack-specific setup instructions here once the project has a runtime, for example:

```bash
uv sync

uv run uvicorn app.main:app --reload

curl -X POST 'http://127.0.0.1:8000/api/v1/ingest/base'

curl -X POST 'http://127.0.0.1:8000/api/v1/normalize/base'

curl -X POST 'http://127.0.0.1:8000/api/v1/ingest/incremental/day-01'

curl -X POST 'http://127.0.0.1:8000/api/v1/normalize/incremental/day-01'
```

## License

License not specified yet.
