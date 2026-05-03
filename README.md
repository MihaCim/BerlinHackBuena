# Buena Context Engine

Buena Context Engine is a hackathon prototype for property management teams. It turns scattered real-estate data into one durable, source-backed, agent-readable property context.

Property managers usually answer questions by jumping across emails, invoices, bank files, PDFs, owner records, tenant data, contractor notes, and previous decisions. This project compiles those fragments into a living `context.md` artifact, then lets an AI-assisted workspace read, explain, update, and protect that context.

## Highlights

- Ingests bank rows, invoices, emails, letters, master data, and incremental daily updates.
- Builds a canonical `context.md` for property `LIE-001`.
- Supports natural-language Q&A with evidence retrieval before AI synthesis.
- Uses Claude or Gemini optionally; the deterministic engine works without an AI key.
- Lets users add new resources through the frontend and preview guarded writes.
- Lets users manually edit the artifact while preserving human-confirmed text in protected `<user>...</user>` blocks.
- Shows an interactive mechanism page that visualizes how data moves from sources to context, chat answers, patches, audit logs, and rollback.
- Provides a bounded FastAPI agent layer with role-aware read, write, intake, audit, and rollback actions.

## Screenshots

### Context Workspace

![Buena Context Engine main workspace](docs/screenshots/main-app.png)

### Interactive Mechanism

![Buena Context Engine mechanism page](docs/screenshots/mechanism.png)

## Demo Flow

Use the guided script in [docs/DEMO.md](docs/DEMO.md).

Quick path:

1. Open `http://127.0.0.1:3000`.
2. Ask `Who owns WE 01?`.
3. Open the agent trace and show the retrieval and synthesis steps.
4. Ask `Add note: Heating contractor confirmed a follow-up appointment for 2026-04-27.`.
5. Show the highlighted context update in the artifact.
6. Open `http://127.0.0.1:3000/mechanism` to explain the system visually.

## Architecture

```text
source data
  -> parsers and schema contracts
  -> entity and source registry
  -> context compiler
  -> protected context.md
  -> chat, graph, resource intake, patch preview, audit, rollback
```

Repository map:

```text
.
|-- app/                   # FastAPI bounded agent supervisor API
|-- context_engine/        # CLI, parsers, patcher, renderer, AI adapter, web API
|-- data/                  # Hackathon source data and incremental deltas
|-- docs/                  # Demo, deployment notes, and screenshots
|-- frontend/              # Next.js frontend
|-- schemas/               # Markdown task schemas used by agentic flows
|-- tests/                 # Python tests for engine, web API, and agents
|-- .env.example           # Safe environment template
|-- requirements.txt
`-- pyproject.toml
```

## Quick Start

Requirements:

- Python 3.11+
- Node.js 20+
- npm

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Install frontend dependencies:

```powershell
cd frontend
npm install
cd ..
```

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Optional Claude configuration:

```env
AI_PROVIDER=claude
CLAUDE_API_KEY=your_claude_api_key_here
CLAUDE_BASE_URL=https://api.anthropic.com
CLAUDE_MODEL=claude-sonnet-4-20250514
```

AI is optional. Without a key, the context compiler, retrieval, patching, intake guards, and UI still work deterministically.

## Run Locally

Start the Python API:

```powershell
python -m context_engine serve --host 127.0.0.1 --port 8765
```

Start the Next.js frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://127.0.0.1:3000
```

The frontend proxies `/api/*` to `http://127.0.0.1:8765` by default. To point it at another backend:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL="https://your-backend-url"
npm run dev
```

## CLI Usage

Compile the base context:

```powershell
python -m context_engine bootstrap --source data --output outputs
```

Apply one incremental day:

```powershell
python -m context_engine apply-delta --source data --output outputs --delta data/incremental/day-01
```

Replay all incremental days:

```powershell
python -m context_engine replay-deltas --source data --output outputs
```

Ask from the compiled context:

```powershell
python -m context_engine ask --context outputs/properties/LIE-001/context.md --question "What unresolved financial anomalies exist?"
```

Use optional AI synthesis:

```powershell
python -m context_engine ask --context outputs/properties/LIE-001/context.md --question "What should a property manager review first today?" --use-ai
```

Show current status:

```powershell
python -m context_engine status --output outputs
```

Process staged intake resources:

```powershell
python -m context_engine process-intake --output outputs
```

## Agentic Guardrails

The repo uses markdown schemas to keep agentic behavior bounded and inspectable:

- `schemas/RESOURCE_VALIDATION_SCHEMA.md`: validates resource text and rejects spam/noise.
- `schemas/CONTEXT_WRITE_SCHEMA.md`: maps accepted resources to safe context sections.
- `schemas/INGESTION_PROCESS_SCHEMA.md`: describes the end-to-end ingestion process.
- `schemas/PARSER_SCHEMA.md`: describes source families, filename patterns, and entity patterns.
- `schemas/RENDER_SCHEMA.md`: defines the `context.md` section order and renderer contract.
- `schemas/PATCH_SCHEMA.md`: defines patchable sections and locked block patterns.
- `schemas/CHAT_AGENT_SCHEMA.md`: defines the safe read-only chat contract.

The important rule: AI can assist with validation, routing, summarization, and answer synthesis, but source-backed context and protected human edits remain the authority.

## Agent API

The `app/` FastAPI layer exposes a bounded agent API:

- `GET /api/v1/agents/tools`
- `POST /api/v1/agents/chat`
- `POST /api/v1/agents/intake`
- `POST /api/v1/agents/patch`
- `POST /api/v1/agents/rollback`
- `GET /api/v1/agents/audit/{building_id}`

Roles are passed with `X-Agent-Role`:

- `viewer`: chat and read-only access.
- `editor`: dry-run patch and intake.
- `approver`: write patch and intake.
- `admin`: rollback plus all lower permissions.

## Useful Chat Examples

```text
Who owns WE 01?
```

```text
What should a property manager review first today?
```

```text
Add note: Heating contractor confirmed a follow-up appointment for 2026-04-27.
```

```text
Remember: WE 01 owner asked for a payment status review after the next bank import.
```

## Testing

Run Python tests:

```powershell
python -m pytest -q
```

Validate the frontend:

```powershell
cd frontend
npm run typecheck
npm run build
```

Current coverage includes:

- Context compilation and delta replay
- Protected `<user>` edit preservation
- Resource intake staging and guarded writes
- Agent citations and visual trace nodes
- Claude/Gemini model-synthesis path when `use_ai=true`
- Multi-building auto-routing
- Role-based write and rollback permissions
- Frontend production build

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

Recommended free split:

- Backend: Render or Railway Python service
- Frontend: Vercel Next.js project

Only the backend should receive API keys. The frontend should only receive:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend-url
```

## Security

- `.env` is ignored by git.
- `outputs/` is ignored by git.
- Do not commit generated audio/video files or local demo exports.
- Do not expose API keys with `NEXT_PUBLIC_`.
- Keep protected `<user>` blocks intact when changing patch logic.
- Prefer deterministic behavior first; AI should advise or synthesize from retrieved evidence, not become the source of truth.

## Current Limitations

- The demo targets property `LIE-001`.
- Resource intake writes accepted staged text into `context.md`; deeper native parsing for arbitrary binary uploads remains future work.
- PDF extraction is represented by the existing sample parsers and hackathon data assumptions.
- Human edits are intentionally visible in `context.md` so future ingestion and AI steps can treat them as authoritative.
