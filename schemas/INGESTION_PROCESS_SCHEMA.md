# Ingestion Process Schema

Purpose: define the bounded agentic process for staged resources.

The process is intentionally agentic but not unbounded. The schema guides the agent; file safety is enforced by code.

## Steps

1. Load all staged resource records from `outputs/intake/`.
2. For each record with status `staged_for_ingestion`, read its `raw_path`.
3. Validate it using `RESOURCE_VALIDATION_SCHEMA.md`.
4. If invalid:
   - Do not edit `context.md`.
   - Update the resource record status to `rejected`.
   - Store the rejection reason.
5. If valid:
   - Route it using `CONTEXT_WRITE_SCHEMA.md`.
   - Produce a concise evidence summary from the resource content.
   - Insert an `AGENT_INTAKE` block into the target section.
   - Update the resource record status to `written_to_context`.
   - Store target section, validation reason, confidence, and write timestamp.

## Agent Autonomy Boundaries

The agent may decide:

- Whether a resource is valid.
- Which allowed target section to use.
- What concise summary to write.

The agent may not:

- Write outside `context.md`.
- Delete user-authored `<user>` blocks.
- Delete existing `AGENT_INTAKE` blocks for other resources.
- Apply writes for rejected or suspicious resources.
- Change source data under `data/`.

## Expected Result

After processing, each staged resource has one of these statuses:

- `written_to_context`
- `rejected`
- `staged_for_ingestion`

The frontend should show the resulting statuses in Resource Intake.
