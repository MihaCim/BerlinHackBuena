# Implementation Plan — Buena Context Engine

Hackathon target: 48h MVP. Tests folded into each phase (TDD-style).

## Decisions captured

| Fork | Choice |
|---|---|
| MVP scope | Full vertical slice for `stammdaten`, email, invoice, bank, letter; stubs for chat/voice/ERP/manual/schedule/lint |
| Output unit | Property tree on disk under `wiki/<LIE-id>/`; API serves `index.md` |
| Bootstrap | Hybrid — stammdaten skeleton → batch replay 2024-2025 → live deltas |
| Event delivery | `POST /webhook/ingest` (HMAC-signed) + dev replayer CLI |
| LLM stack | `LLMClient` Protocol; default Anthropic binding configured by env, tests use `FakeLLMClient` |
| Prompt contract | One file-type extractor prompt from `schema/extractors/*.md` + shared rules + normalized file content |
| Indexing | DuckDB with FTS for `stammdaten`, `source_registry`, `normalized_chunks`, `wiki_chunks`, bank, invoices |
| Hermes loops | JSONL substrate only; inner/outer loops stubbed |
| Demo target | Normalize/search + live day replay + wiki patch + reconciliation report |
| PDF parsing | Docling |
| Git scope | `wiki/` is its own git repo, commit per event |
| LLM in tests | `LLMClient` Protocol; `FakeLLMClient` injected via `dependency_overrides` |

`LLMClient` is a `Protocol`; production binds to `AnthropicClient`, tests bind to `FakeLLMClient` returning canned responses keyed by `(model, prompt_hash)`. All injection via `app.dependency_overrides`.

---

## Phase 0 — Foundations (~2h)

- Deps to evaluate before adding: Anthropic SDK vs raw `httpx`, Docling vs `pypdf` fallback, GitPython vs shelling out to git. Likely runtime deps: `anthropic`, `duckdb`, `docling`, `pypdf`, `python-multipart`.
- `.env.example` with `ANTHROPIC_API_KEY`, `APP_WIKI_DIR`, `APP_NORMALIZE_DIR`, `APP_WEBHOOK_HMAC_SECRET`.
- Extend `app/core/config.py`: `wiki_dir`, `normalize_dir`, `anthropic_api_key`, `webhook_hmac_secret`, `classify_model`, `extract_model`.
- Rename route: `app/api/v1/buildings.py` → `properties.py`. Endpoint becomes `GET /properties/{LIE-id}` returning `wiki/<LIE-id>/index.md`. Keep `/buildings/{HAUS-id}` as a sub-route returning `02_buildings/<HAUS-id>/index.md`.
- Request-id middleware bound into structlog context.

**Tests:**

- `tests/test_config.py` — settings load env vars with `APP_` prefix; `get_settings()` is cached.
- `tests/test_health.py` — already exists; update for new shape.
- `tests/test_properties.py` — `GET /properties/{LIE-id}` 404 on missing, 200 on present, rejects `LIE-../etc/passwd`.

## Phase 1 — Storage layer (~3.5h)

- `app/storage/stammdaten.py` — load `data/stammdaten/stammdaten.json` into `stammdaten.duckdb` tables (`liegenschaft`, `gebaeude`, `einheiten`, `eigentuemer`, `mieter`, `dienstleister`). Indexes on email, IBAN, id.
- `app/storage/source_registry.py` — one logical row per source: `(source_id, source_type, raw_path, normalized_path, sha256, document_date, status, signal_class, entity_refs[], property_refs[], created_at, parsed_at)`.
- `app/storage/normalized_chunks.py` — normalized markdown sections/snippets: `(source_id, normalized_path, chunk_id, heading, body, entity_refs[], footnote_ids[], sha256)`. FTS for source search.
- `app/storage/wiki_chunks.py` — `(property_id, file, section, body, entity_refs[], updated_at)`. FTS for wiki search and ingestion-side section locating.
- `app/storage/bank.py` + `invoices.py` — load `bank_index.csv` and invoice metadata.
- `app/storage/idempotency.py` — `(event_id PK, received_at, status)`.
- All DBs created at app startup if missing; loader CLIs idempotent.

**Tests:**

- `tests/storage/test_stammdaten.py` — load fixture stammdaten.json → assert row counts (3 gebäude, 52 einheiten, 35 eigentümer); lookup by email/IBAN/id returns expected entities.
- `tests/storage/test_source_registry.py` — upsert raw + normalized source idempotently by `source_id` and `sha256`; duplicate raw files point to one normalized source.
- `tests/storage/test_normalized_chunks.py` — index normalized email/invoice markdown → FTS finds body text and filters by source/entity refs.
- `tests/storage/test_wiki_chunks.py` — insert sections → FTS query returns ranked hits; entity_refs filter works.
- `tests/storage/test_idempotency.py` — same `event_id` twice → second is rejected.

## Phase 2 — Wiki bootstrap (~3.5h)

- `app/tools/bootstrap_wiki.py` CLI. Reads stammdaten, emits skeleton:
  - `wiki/LIE-001/index.md` (Buildings, Bank Accounts, Open Issues, Recent Events, Procedural Memory, Provenance)
  - `02_buildings/HAUS-{12,13,…}/index.md` + `units/EH-NNN.md`
  - `03_people/eigentuemer/EIG-NNN.md`, `mieter/MIE-NNN.md`
  - `04_dienstleister/DL-NNN.md`
  - `05_finances/{overview,reconciliation}.md`, `06_skills.md`, `07_timeline.md`, `_state.json`, `log.md`
- Each file: `name`/`description` frontmatter + required sections + `# Human Notes` boundary.
- `git init wiki/` + initial commit `bootstrap: skeleton from stammdaten`.

**Tests:**

- `tests/tools/test_bootstrap.py` — run against fixture stammdaten in `tmp_path`. Assert: every required file exists; every file has valid `name`/`description` frontmatter; every required section heading present; `# Human Notes` boundary at EOF; `_state.json` valid JSON; `git log` shows one commit.

## Phase 3 — Patcher (~5h)

Critical foundation — everything downstream depends on Patcher correctness.

- `app/services/patcher/ops.py` — `upsert_bullet`, `delete_bullet`, `upsert_row`, `delete_row`, `prepend_row`, `prune_ring`, `upsert_footnote`, `gc_footnotes`, `update_state`. Pure regex/line ops.
- `app/services/patcher/atomic.py` — tempfile → fsync → rename helper.
- `app/services/patcher/validate.py` — parses `schema/VOCABULARY.md`, validates every keyed value; refuses any byte offset past `# Human Notes`.
- `app/services/patcher/apply.py` — `apply_patch_plan(plan)`: validate → apply ops → append JSONL to `_hermes_feedback.jsonl` → `git commit -m "ingest(<event_id>): <summary>"`.

**Tests:**

- `tests/patcher/test_ops_upsert_bullet.py` — insert new key; update existing key; preserve unrelated bullets; preserve human bullets (no `**ID:**` prefix).
- `tests/patcher/test_ops_upsert_row.py` — same matrix for tables.
- `tests/patcher/test_ops_prepend_row.py` — order preserved; ring buffer cap honored via `prune_ring`.
- `tests/patcher/test_ops_footnote.py` — upsert in `## Provenance` only; `gc_footnotes` drops `ref_count==0`.
- `tests/patcher/test_human_notes_boundary.py` — every op refuses bytes past `# Human Notes` with explicit error.
- `tests/patcher/test_vocab_validation.py` — `status: "in-progress"` accepted; `status: "wip"` → op dropped, entry written to `_pending_review.md`.
- `tests/patcher/test_atomic.py` — kill simulation between tempfile write and rename leaves original intact.
- `tests/patcher/test_apply_plan.py` — full plan → ops applied in order, JSONL line appended, single git commit, idempotent on `event_id`.

## Phase 4 — Normalizers (~3.5h)

Pure functions, no LLM.

- `app/services/normalize/eml.py` — RFC 822 → md with frontmatter (`source, sha256, parser, parsed_at, mime, lang`). Quoted-printable handled.
- `app/services/normalize/pdf.py` — Docling for invoices/letters. Output md table for line items, plain text for prose.
- `app/services/normalize/bank.py` — bank row → md (one file per tx, since events are per-tx).
- `app/services/normalize/index_csv.py` — `emails_index.csv`, `rechnungen_index.csv`, `bank_index.csv`, and manifest rows → normalized md/source records.
- All write to `normalize/<type>/<YYYY-MM>/<id>.md` or `normalize/index/<day>/<file>.md`. Idempotent on sha256.
- Every successful normalization upserts `source_registry` and `normalized_chunks`.
- Normalized markdown is the only file content passed to LLM extractors; raw files remain read-only provenance.

**Tests:**

- `tests/normalize/test_eml.py` — fixture `.eml` → md output has expected frontmatter (sha256, parser, parsed_at), body decoded from quoted-printable.
- `tests/normalize/test_pdf_invoice.py` — fixture invoice PDF → md table with line items + totals; sha256 stable.
- `tests/normalize/test_pdf_letter.py` — fixture letter PDF → markdown prose, frontmatter present.
- `tests/normalize/test_bank.py` — CSV row → md; idempotent on sha256.
- `tests/normalize/test_index_csv.py` — each day-level index CSV becomes deterministic source records and normalized md.

## Phase 5 — LLM steps (~5h)

- `app/services/llm/client.py` — `LLMClient` Protocol; `AnthropicClient` (SDK or httpx binding, depending on Phase 0 decision, prompt caching where supported); `FakeLLMClient`.
- `app/services/prompts.py` — loads `schema/extractors/00_shared_rules.md` plus exactly one file-type prompt (`01_manifest.md`, `02_stammdaten.md`, … `10_coordinator.md`). Rejects missing prompt files at startup.
- `app/services/classify.py` — `classify_model` call on sender + subject + first 500 chars → `{signal, category, priority, confidence}`. ~90% short-circuit at `signal=false`.
- `app/services/resolve.py` — deterministic stammdaten lookups and schema alignment; sender email → `MIE-/EIG-/DL-id`, IBAN → `DL/EIG`, mentioned `EH-/INV-/LTR-` ids validated. Normalizes aliases like `Eigentümer`, `MietEig`, `Kontakt`, `owner`, `Dienstleister`, `vendor` to canonical wiki entity types such as `eigentuemer`, `mieter`, and `dienstleister`; routes ambiguous `Kontakt` matches to review.
- `app/services/locate.py` — DuckDB FTS query: `SELECT path, section FROM wiki_chunks WHERE property_id=? AND list_contains(entity_refs, ?)`. Returns 3-8 candidates.
- `app/services/extract.py` — `extract_model` call given normalized doc + resolved IDs + located section bodies + specific extractor prompt + `schema/CLAUDE.md` + `schema/VOCABULARY.md`. Returns `PatchPlan` JSON.
- `app/services/coordinate.py` — runs `schema/extractors/10_coordinator.md` over per-file extractor JSON for one `day-NN`, producing one final PatchPlan.

**Tests** (all use `FakeLLMClient` injected via `dependency_overrides`):

- `tests/llm/test_classify.py` — fake returns `signal=false` for spam-like fixture; `signal=true, category="mieter/heizung"` for heating fixture.
- `tests/llm/test_prompts.py` — each extractor prompt loads with shared rules; missing prompt raises at startup.
- `tests/llm/test_resolve.py` — deterministic; sender `mueller@…` → MIE-007; mentioned `EH-014` validated; unknown IBAN → null; generic `Kontakt` with no role evidence is `needs_review`.
- `tests/llm/test_locate.py` — given fixture wiki_chunks, query for `MIE-014` returns expected `(file, section)` tuples ranked.
- `tests/llm/test_extract.py` — fake returns canned PatchPlan; assert plan parses, ops well-formed, every keyed value passes vocab.
- `tests/llm/test_signal_filter.py` — newsletter/empty ack/quoted-only email stops before extraction and only logs source metadata.

## Phase 5.5 — Search + context API (~2h)

This is required for the "manage building wiki context for normalization of data files & search" agent use case.

- `app/services/search.py` — unified search over `source_registry`, `normalized_chunks`, and `wiki_chunks`. Supports filters: `property_id`, `entity_id`, `source_type`, `date_from`, `date_to`, `scope=wiki|sources|all`.
- `app/services/context_pack.py` — builds compact task context: top wiki sections, top normalized source snippets, source provenance, unresolved review items.
- `app/api/v1/search.py`:
  - `GET /search?q=&property_id=&scope=&limit=`
  - `GET /sources/{source_id}` returns normalized markdown + raw path metadata
  - `POST /context-pack` with `{task, property_id?, entity_ids?, source_ids?}`
- `app/schemas/search.py` — typed response models with snippets and provenance.

**Tests:**

- `tests/search/test_search_wiki_and_sources.py` — query finds both normalized source text and wiki section text, ranked with source provenance.
- `tests/search/test_search_filters.py` — property/entity/source/date filters work and reject path traversal.
- `tests/search/test_context_pack.py` — task + `MIE-014` returns bounded context containing relevant wiki section, normalized source refs, and no `# Human Notes`.

## Phase 6 — Supervisor + handlers + webhook (~4h)

- `app/api/v1/webhook.py` — `POST /webhook/ingest`, HMAC-SHA256 verification on raw body, idempotency check via `idempotency.duckdb`, dispatch to Supervisor.
- `app/services/supervisor.py` — orchestrates `normalize → source_registry/chunk_index → classify → resolve → locate → extract/coordinate → conflict_scan → apply → reindex → broadcast`. One handler per `event_type`.
- `app/services/handlers/` — MVP handlers: `email.py`, `letter.py`, `invoice.py`, `bank.py`, `manifest.py`, `index_csv.py`. Stub handlers returning 501/queued-review for `chat.py`, `voicenote.py`, `erp.py`, `document.py`, `manual.py`, `schedule.py`, `lint.py`.
- Errors: structured `HTTPException` with status; failed events still log JSONL with `retrieval_success=false`.

**Tests:**

- `tests/api/test_webhook_auth.py` — bad HMAC → 401; missing signature → 401; replayed `event_id` → 200 idempotent (no double-apply).
- `tests/api/test_webhook_dispatch.py` — MVP `event_type`s route to correct handler; non-MVP event types return explicit 501 or queued-review response, not silent success.
- `tests/handlers/test_email_handler.py` — fixture email event → expected PatchPlan ops emitted (using `FakeLLMClient`).
- `tests/handlers/test_invoice_handler.py` — invoice event → `upsert_row` in `Recent Invoices` or `05_finances/invoices/<YYYY-MM>/<INV-id>.md`, reconciliation against bank fixture.
- `tests/handlers/test_bank_handler.py` — bank tx → reconciles vs invoices, updates `Payment History` / `05_finances/reconciliation.md`.
- One smoke test per remaining handler stub (chat, voicenote, erp, document, manual, schedule, lint).

## Phase 7 — Conflict scan + reindex (~2.5h)

- `app/services/conflict.py` — for each `upsert_*`, fetch existing keyed line via Patcher reader; programmatic checks (date drift > N days, status flip, amount delta > X%); uncertain → write entry to `_pending_review.md`, drop op from plan.
- `app/services/reindex.py` — post-commit hook called from `apply_patch_plan`: re-parse touched files (heading scan, extract `entity_refs`), upsert into `wiki_chunks`. Per-file ~10ms.

**Tests:**

- `tests/conflict/test_date_drift.py` — fact 5 days old vs new fact same key, different date > threshold → entry in `_pending_review.md`, op dropped.
- `tests/conflict/test_status_flip.py` — `🔴` → `🟢` upsert deferred without human approval.
- `tests/conflict/test_amount_delta.py` — invoice amount changes >10% → conflict.
- `tests/reindex/test_post_commit.py` — touched files get fresh `wiki_chunks` rows; entity_refs extracted correctly.

## Phase 8 — Replayer + backfill CLIs (~2.5h)

- `app/tools/replay.py` — `--day N` walks `data/incremental/day-NN/`, builds events from manifest, `emails_index.csv`, `.eml` files, `rechnungen_index.csv`, invoice PDFs, `bank_index.csv`, and `kontoauszug_delta.csv`; HMAC-signs and POSTs to `/webhook/ingest`.
- `app/tools/backfill.py` — chronological replay of 2024-2025. **Cost-control**: classify-only mode flag (skips `extract_model` calls for `signal=false`); subsample flag for demo (`--limit 200`).

**Tests:**

- `tests/tools/test_replay.py` — `--day 1` posts manifest + index tables + file-level events with valid HMAC to a test ASGI server; assert each MVP event gets 200.
- `tests/tools/test_backfill.py` — `--limit 10` against fixture month → 10 POSTs in chronological order.

## Phase 9 — SSE live view (~2.5h)

- `app/api/v1/events.py` — `GET /events` SSE endpoint. In-process `asyncio.Queue` per connection; Patcher publishes `{type, file, section, commit_sha}` after commit.
- `app/static/index.html` — minimal page with EventSource subscription, scrolling list of pulses, link to current `index.md`.

**Tests:**

- `tests/api/test_events_sse.py` — connect to SSE endpoint with `httpx.AsyncClient`, trigger a fake patch broadcast, assert event received with expected payload.
- `tests/api/test_events_isolation.py` — events for property A don't leak to subscribers filtering for property B (if filter is in scope).

## Phase 10 — Reconciliation report (~2.5h)

- `app/tools/reconcile.py` — DuckDB joins `bank ⋈ invoices ⋈ stammdaten` on `referenz_id`. Surfaces seeded anomalies via `error_types` (wrong IBAN, missing ref, duplicates, amount mismatch).
- Output: `output/reconciliation.md` + Patcher writes the same data to `wiki/LIE-001/05_finances/reconciliation.md` (table form).

**Tests:**

- `tests/tools/test_reconcile.py` — fixture bank + invoice data with seeded `error_types` → report surfaces each anomaly type (wrong IBAN, missing ref, duplicate, amount mismatch). Counts match expected.

## Phase 11 — Final e2e + demo polish (~1.5h)

**Tests:**

- `tests/e2e/test_day01_replay.py` — full pipeline: bootstrap → replay day-01 → assert specific bullets/rows in `wiki/LIE-001/index.md`, `02_buildings/HAUS-12/index.md`, `_state.json` counters, `_hermes_feedback.jsonl` lines, `git log` commit count.

README demo script, polish pass.

---

## Test conventions (`tests/conftest.py` extensions)

- `tmp_wiki` fixture — bootstraps a fresh wiki tree under `tmp_path`.
- `fake_llm` fixture — yields a `FakeLLMClient`; auto-overrides `get_llm_client` Depends provider; clears in teardown.
- `signed_event` helper — produces HMAC-signed payload for webhook tests.
- Fixture data lives in `tests/fixtures/` (one .eml, one invoice PDF, one letter PDF, one bank CSV row, stammdaten subset).
- All tests run offline. CI gate runs `ruff format --check && ruff check && ty check && pytest`.

---

## Order & critical path

Sequential dependency: **0 → 1 → 2 → 3** (foundations + bootstrap + patcher must be solid before anything else). Then **4 → 5 → 5.5 → 6** converge into the first end-to-end run. Then **7, 8** (production-shape ingestion). Then **9, 10** (demo surface). Then **11**.

## Risks

- **Docling install size** (~200MB models) — pre-warm during `uv sync` or fall back to pypdf for letters.
- **Backfill cost/latency** — 6,500 emails through the classifier model can still cost money and 30+ min. Default to `--limit 200` for demo.
- **Per-event latency** — git commit + DuckDB reindex + SSE per event = ~500ms-2s. Replayer should rate-limit (1 event/sec) for visible demo.
- **Hermes JSONL only** is genuinely substrate-only — be explicit in README that loops are designed but stubbed.
- **Total budget**: ~40h focused work; realistically ~48h with debugging. Phase 9 (SSE) or Phase 10 (reconcile) are the natural candidates to cut if behind.
