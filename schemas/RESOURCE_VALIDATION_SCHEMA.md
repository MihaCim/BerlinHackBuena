# Resource Validation Schema

Purpose: decide whether a staged resource is allowed to change `context.md`.

The agent must reject a resource and leave `context.md` unchanged when any hard reject rule matches.

## Required Fields

- `id`: stable staged resource id.
- `name`: filename, subject, or human label.
- `kind`: one of `email`, `text`, `letter`, `invoice`, `bank`, `other`.
- `content`: raw text extracted from the resource.
- `created_at`: ISO timestamp when staged.

## Hard Reject Rules

- Empty or whitespace-only content.
- Content shorter than 20 meaningful characters.
- Kind outside the allowed kind list.
- Content contains obvious spam phrases:
  - `buy now`
  - `limited time offer`
  - `free money`
  - `crypto giveaway`
  - `work from home`
  - `click here to claim`
  - `viagra`
  - `casino`
  - `lottery winner`
- More than 3 URLs in a resource with fewer than 120 words.
- More than 35 percent of non-empty lines are URLs.
- Text is mostly repeated tokens or repeated lines.

## Accept Signals

At least one of these should be visible:

- Property-management terms: `property`, `tenant`, `owner`, `invoice`, `payment`, `bank`, `maintenance`, `meeting`, `heating`, `water`, `repair`, `vendor`.
- German property-management terms: `Eigentumer`, `Eigentuemer`, `Mieter`, `Rechnung`, `Zahlung`, `Bank`, `Instandhaltung`, `Versammlung`, `Heizung`, `Wasser`, `Schaden`, `Dienstleister`, `WEG`.
- Structured evidence: amount, date, invoice number, IBAN fragment, email subject, sender/recipient, unit id, owner id, vendor id.

## Output Contract

Return a decision object:

```json
{
  "valid": true,
  "reason": "short explanation",
  "confidence": 0.0,
  "signals": ["signal labels"]
}
```

If `valid` is false, the agent must update only the resource record status and must not edit `context.md`.
