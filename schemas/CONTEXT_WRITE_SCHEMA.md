# Context Write Schema

Purpose: tell the intake agent exactly where validated staged resources may write into `context.md`.

The agent is not allowed to rewrite arbitrary files. It may only update:

```text
outputs/properties/LIE-001/context.md
outputs/intake/*.resource.json
```

## Section Routing

Route by resource `kind`:

| Kind | Target section anchor | Reason |
|---|---|---|
| `email` | `recent_communications` | Emails become communication evidence. |
| `letter` | `meetings_decisions` | Letters often contain meetings, notices, or decisions. |
| `invoice` | `invoices_payments` | Invoices belong with payment evidence. |
| `bank` | `financial_state` | Bank rows affect financial context. |
| `text` | `open_topics` | Free text usually captures an issue, decision, or topic. |
| `other` | `open_topics` | Unknown valid evidence should become reviewable topic context. |

## Write Format

Every agent write must be inserted inside the chosen section, after the section heading and before generated section content.

Use this exact block shape:

```markdown
<!-- AGENT_INTAKE_START id="INTAKE-..." kind="email" target="recent_communications" created_at="ISO_DATE" schema="CONTEXT_WRITE_SCHEMA.md" -->
### Intake: resource name

- Status: validated and written by intake agent.
- Reason: validation reason.
- Source: staged resource id.
- Notes: optional operator notes.

Summary of the accepted evidence in natural language.
<!-- AGENT_INTAKE_END -->
```

## Guardrails

- Preserve all existing `<user>...</user>` blocks.
- Preserve all existing `AGENT_INTAKE` blocks unless replacing the same resource id.
- Do not edit frontmatter except through the normal compiler.
- Do not invent source facts.
- Keep the written summary short.
- If the target section is missing, write to `open_topics`.
