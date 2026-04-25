# Render Schema

Purpose: define the section order and markdown anchors for the generated `context.md`.

The renderer must follow this order. Section bodies are produced by bounded renderer tools, but placement and titles come from this schema.

## Render Sections

| order | anchor | title | renderer |
|---:|---|---|---|
| 10 | agent_brief | Agent Brief | render_agent_brief |
| 20 | property_snapshot | Property Snapshot | render_property_snapshot |
| 30 | buildings_units | Buildings And Units | render_buildings_units |
| 40 | owners | Owners | render_owners |
| 50 | tenants | Tenants | render_tenants |
| 60 | service_providers | Service Providers | render_service_providers |
| 70 | financial_state | Financial State | render_financial_state |
| 80 | open_topics | Open Operational Topics | render_topics |
| 90 | meetings_decisions | Meetings And Decisions | render_meetings |
| 100 | recent_communications | Recent Communications | render_recent_communications |
| 110 | invoices_payments | Invoices And Payments | render_invoices |
| 120 | risks_review | Risks, Anomalies, And Review Items | render_anomalies |
| 130 | timeline | Timeline | render_timeline |
| 140 | source_register | Source Register | render_source_register |

## Human Notes Contract

The renderer must include a human notes block immediately after the H1 title:

```markdown
<!-- HUMAN_NOTES_START -->
## Human Notes

Human-maintained notes live here and must never be overwritten by the engine.
<!-- HUMAN_NOTES_END -->
```

## Guardrails

- Do not render user-confirmed `<user>` blocks from generated data.
- Existing `<user>` and `AGENT_INTAKE` blocks are preserved by the patch schema.
- Every generated section must have `<!-- SECTION:{anchor} START -->` and `<!-- SECTION:{anchor} END -->`.
