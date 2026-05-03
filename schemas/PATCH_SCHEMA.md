# Patch Schema

Purpose: define which sections can be patched and which blocks must be preserved.

The patch executor must apply only the sections listed here unless a caller explicitly narrows the set further.

## Patchable Sections

| order | anchor | reason |
|---:|---|---|
| 10 | agent_brief | Runtime summary and advisory note. |
| 20 | service_providers | Provider counts can change with new invoices. |
| 30 | financial_state | Bank and financial data change with deltas. |
| 40 | open_topics | Operational topics change with communications. |
| 50 | meetings_decisions | Letters and meeting references can change. |
| 60 | recent_communications | Emails change with deltas. |
| 70 | invoices_payments | Invoice/payment status changes with deltas. |
| 80 | risks_review | Anomalies and review items change with deltas. |
| 90 | timeline | Timeline changes with new events. |
| 100 | source_register | Source counts change with deltas. |

## Locked Block Patterns

These blocks must survive every automated patch:

```regex
<user\b[^>]*>.*?</user>
```

```regex
<!-- AGENT_INTAKE_START\b[^>]*>.*?<!-- AGENT_INTAKE_END -->
```

## Human Notes Pattern

```regex
<!-- HUMAN_NOTES_START -->.*?<!-- HUMAN_NOTES_END -->
```
