# Lovable Prompt: Buena Context Engine Frontend

Build a premium, minimal, warm web app frontend for a product called **Buena Context Engine**. This is only the frontend/UI. The product is a property-management context dashboard that compiles scattered operational data into one editable `context.md` artifact.

The UI should feel like a polished AI productivity product, inspired by the visual direction of Wispr Flow: warm cream background, soft glassy cards, editorial serif hero typography, pill-shaped controls, subtle gradients, beautiful spacing, and calm premium details. Do not make it look like a generic admin dashboard. Do not use a purple SaaS theme. Keep one consistent visual language.

## Product Concept

Buena Context Engine helps property managers turn noisy operational data into one trustworthy property memory file.

The dashboard should let a user:

1. Run the context pipeline.
2. See system status and metrics.
3. Stage new resources like emails, text, letters, invoices, bank records, or files.
4. Ask questions against the compiled property context.
5. See activity logs and patch history.
6. Preview and directly edit the generated `context.md` artifact.
7. Save direct artifact edits inside protected `<user>...</user>` tags, because user edits are authoritative and must not be overwritten by future AI/ingestion updates.

This is frontend-only, so use mock/local state for API responses unless backend endpoints are provided later.

## Overall Layout

Create a full-page responsive dashboard with two main zones:

1. A sticky left sidebar command rail.
2. A main stage on the right containing the hero, metrics, resource intake, ask panel, activity panel, and artifact editor.

Desktop layout:

- Main wrapper class idea: `app-shell`
- CSS grid: `310px minmax(0, 1fr)`
- Gap: `22px`
- Padding: `22px`
- Max width: around `1760px`
- Min height: `100vh`
- Center the app horizontally.

Tablet/mobile:

- Collapse to one column below around `1260px`.
- Sidebar becomes non-sticky and displayed as a grid.
- Below around `900px`, all cards stack vertically.

## Visual Theme

Use these exact design tokens or very close equivalents:

```css
:root {
  --ink: #171812;
  --ink-soft: #3f4338;
  --muted: #77796d;
  --hairline: rgba(38, 42, 32, 0.12);
  --hairline-strong: rgba(38, 42, 32, 0.2);
  --canvas: #f5ecdc;
  --cream: #fffaf0;
  --paper: rgba(255, 251, 241, 0.82);
  --paper-solid: #fffaf0;
  --moss: #254f3e;
  --moss-soft: #dce9d7;
  --teal: #2d8c7d;
  --coral: #ef7b5d;
  --ochre: #d9aa4a;
  --rose: #f4d9ce;
  --shadow: 0 30px 90px rgba(49, 42, 30, 0.16);
  --shadow-soft: 0 16px 40px rgba(49, 42, 30, 0.1);
  --radius-xl: 34px;
  --radius-lg: 26px;
  --radius-md: 18px;
}
```

Use a warm layered background:

- Base: `#f5ecdc`
- Radial coral glow near top-left.
- Radial teal glow near top-right.
- Subtle grid pattern overlay using 1px lines.
- Two blurred ambient orbs:
  - Coral orb, top-right area.
  - Teal orb, lower/mid area.

The background should feel airy, warm, and premium. Cards should have translucent cream/glass surfaces with blur and soft shadows.

## Typography

Use:

- Headline serif: `EB Garamond`, fallback Georgia.
- UI font: `Figtree`, fallback Aptos/Segoe UI/sans-serif.
- Monospace for context and logs: `Cascadia Mono`, fallback `SFMono-Regular`, Consolas.

Load fonts:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@500;600&family=Figtree:wght@450;600;700;800&display=swap" rel="stylesheet" />
```

Typography style:

- Main hero headline: serif, very large, elegant, letter-spacing around `-0.055em`, line-height around `0.88`.
- Card headings: clean Figtree, `21px`, slightly tight letter-spacing.
- Eyebrows: uppercase, moss color, `11px`, heavy weight, letter-spaced.
- Body text: soft ink, readable, around `14px` to `17px`.

## Page Structure

### Background Elements

Render before the main shell:

- `.ambient-orb.orb-one`
- `.ambient-orb.orb-two`

They are fixed, blurred, and behind the app.

### Main Shell

Use:

```html
<main class="app-shell">
  <aside class="side-rail">...</aside>
  <section class="main-stage">...</section>
</main>
```

## Left Sidebar: `side-rail`

The sidebar should be sticky on desktop.

Style:

- Width from grid: `310px`
- Sticky top: `22px`
- Height: `calc(100vh - 44px)`
- Padding: `18px`
- Border radius: `34px`
- Glass/cream background.
- Soft shadow.
- Internal gap: `18px`

### Brand Block

Top of sidebar:

- A square rounded brand mark with letter `B`.
- Gradient from coral to teal/moss.
- Serif letter.
- Text:
  - Eyebrow: `Buena`
  - Heading: `Context` line break `Engine`

Structure:

```html
<div class="brand-block">
  <span class="brand-mark">B</span>
  <div>
    <p class="eyebrow">Buena</p>
    <h1>Context<br />Engine</h1>
  </div>
</div>
```

### Sidebar Section: Run Pipeline

Card-like section inside sidebar.

Text:

- Section title: `Run Pipeline`
- Copy: `Build context, apply deltas, and keep the property memory current.`

Controls:

- AI synthesis toggle, checked by default.
- Primary button: `Bootstrap context`
- Delta row:
  - Select with options `day-01` through `day-10`
  - Button: `Apply`
- Button: `Replay all deltas`

IDs to preserve:

- `useAi`
- `bootstrapBtn`
- `daySelect`
- `deltaBtn`
- `replayBtn`

### Sidebar Section: System Health

Text:

- Section title: `System Health`
- Copy: `Quick check for the current generated artifact and patch history.`

Controls:

- Button: `Refresh status`
- Button: `Load context`

Status rows:

- Watermark: `<strong id="watermark">loading</strong>`
- Context: `<strong id="contextState">checking</strong>`
- Patches: `<strong id="patchCount">0</strong>`

IDs:

- `refreshBtn`
- `loadContextBtn`
- `watermark`
- `contextState`
- `patchCount`

### Sidebar Note

Bottom note card:

Title: `Human edits are treated as source of truth.`

Copy: `Protected blocks stay intact when the engine applies future ingestion patches.`

Use moss-soft/cream background, rounded `24px`, subtle border.

## Main Stage

Use `.main-stage`, display grid, gap `18px`.

### Hero Panel

Class: `hero-panel`

Should be the most beautiful element on the page.

Style:

- Rounded `38px`
- Padding `32px`
- Min height around `300px`
- Glass cream background.
- Soft huge shadow.
- Decorative radial circular pattern in bottom-right.

Hero content:

Eyebrow:

`WEG Immanuelkirchstrasse 26`

Headline:

`A calm command center for building memory.`

Body:

`Convert noisy bank rows, invoices, emails, letters, and manual decisions into one trustworthy context artifact that can be patched, questioned, and reviewed.`

Right-side status pills:

- `<span id="langgraph">LangGraph ready</span>`
- `<span id="latestPatch">latest patch: none</span>`

Workflow strip at bottom:

Four rounded pill cards:

1. `01` / `Ingest`
2. `02` / `Compile`
3. `03` / `Protect`
4. `04` / `Ask`

Class: `flow-strip`

Numbers should use serif, coral color. Labels use soft ink.

### Metrics Grid

Class/id:

```html
<section class="metrics-grid" id="metricsGrid"></section>
```

Render six metric cards:

1. `bank tx`
2. `invoices`
3. `emails`
4. `letters`
5. `topics`
6. `anomalies`

Each metric card:

- Rounded `26px`
- Cream glass surface.
- Small uppercase label.
- Large serif numeric value.

Mock values can be:

- bank tx: `1622`
- invoices: `196`
- emails: `6558`
- letters: `135`
- topics: `30`
- anomalies: `450`

### Resource Intake Card

This is one full-width card below metrics.

Class layout:

```html
<section class="intake-grid">
  <section class="feature-card intake-card">...</section>
</section>
```

Header:

- Eyebrow: `Resource Intake`
- Heading: `Add email, text, or file`
- Pill: `staged`, amber background

Copy:

`Drop in new evidence now. For this frontend phase it is staged in outputs/intake, ready for the next ingestion pipeline update.`

Form fields:

- Select `resourceType`
  - Options:
    - `Email`
    - `Plain text`
    - `Letter`
    - `Invoice`
    - `Bank record`
    - `Other`
- Text input `resourceName`, placeholder `Name or subject`
- File drop label with hidden file input `resourceFile`
  - Text: `Choose a file or paste content below`
- Textarea `resourceContent`
  - Placeholder: `Paste email body, notes, extracted PDF text, CSV rows, or any source text...`
- Text input `resourceNotes`
  - Placeholder: `Optional note for the future ingestion agent`
- Button: `Stage resource`

Status:

- `<div id="resourceStatus" class="soft-status">Nothing staged in this browser session yet.</div>`
- `<div id="resourceList" class="resource-list"></div>`

Frontend behavior:

- If a user chooses a readable text file, read it into `resourceContent` and set `resourceName` to the filename if empty.
- If `resourceContent` is empty on submit, show: `Paste content or choose a readable text file first.`
- On submit, add a staged resource item to local state and show it in `resourceList`.
- Staged resource item should show resource name and `kind / staged_for_ingestion`.

### Work Grid

Two-column layout:

```html
<section class="work-grid">
  <section class="answer-panel">...</section>
  <section class="activity-panel">...</section>
</section>
```

Desktop:

- Left: ask panel, larger.
- Right: activity panel.

Mobile:

- Stack vertically.

## Ask Panel

Header:

- Eyebrow: `Ask`
- Heading: `Ask the compiled context`

Form:

- ID: `askForm`
- Input ID: `questionInput`
- Default value: `What unresolved financial anomalies exist?`
- Submit button: `Ask`

Prompt bank buttons:

1. `Financial risks`
   - Data question: `What unresolved financial anomalies exist?`
2. `Owner lookup`
   - Data question: `Who owns WE 01?`
3. `Providers`
   - Data question: `Who are the main service providers?`
4. `Open topics`
   - Data question: `What open operational topics are active?`
5. `Recent invoices`
   - Data question: `Which invoices were added after the January deltas?`
6. `Today focus`
   - Data question: `What should a property manager review first today?`

Answer box:

```html
<pre id="answerBox" class="answer-box">Ask a question after bootstrap or replay.</pre>
```

Mock ask behavior:

- On submit, show `Thinking...`
- After a short delay, display a natural-language mock answer based on the question.
- Do not return raw JSON.
- Example answer for financial risks:
  `The main financial attention items are unmatched invoices and review items in the compiled context. Start with invoices that have no matching bank transaction, then check high-severity anomaly rows.`

## Activity Panel

Header:

- Eyebrow: `Activity`
- Heading: `Run log and patches`

Run log:

```html
<pre id="runLog">Ready.</pre>
```

Patch list:

```html
<div id="patchList" class="patch-list"></div>
```

Mock behavior:

- Clicking `Bootstrap context` should update log with a timestamp and message like `Bootstrapping context...`, then `Run completed`.
- Clicking `Apply` should update log with selected day.
- Clicking `Replay all deltas` should update log and patch list.
- Patch list items should look like rounded rows with patch name and size.
- Example patch names:
  - `day-10.patch.json`
  - `day-09.patch.json`
  - `day-08.patch.json`

## Artifact Panel: Context Preview And Direct Editing

This is the most important product behavior.

Class:

```html
<section class="context-panel">...</section>
```

Header:

- Eyebrow: `Artifact`
- Heading: `context.md preview and edit`

Controls on right:

- Tab button active: `Context`
  - `data-view="context"`
- Tab button: `Latest patch`
  - `data-view="patch"`
- Button: `Edit context`
  - ID: `editContextBtn`
- Button hidden until editing: `Save with <user> tags`
  - ID: `saveContextBtn`
  - Primary style
- Button hidden until editing: `Cancel`
  - ID: `cancelContextBtn`

Status text:

```html
<div id="contextEditStatus" class="context-edit-status">
  Edit the artifact here when a human knows the correct context. Saved changes are wrapped in protected &lt;user&gt; tags.
</div>
```

Preview:

```html
<pre id="contextPreview">The compiled markdown will appear here.</pre>
```

Editor:

```html
<textarea
  id="contextEditor"
  class="context-editor"
  spellcheck="false"
  hidden
  aria-label="Editable context.md artifact"
></textarea>
```

### Artifact Editing Behavior

This behavior is required:

1. By default, show `contextPreview`.
2. When user clicks `Edit context`:
   - Hide `contextPreview`.
   - Show `contextEditor`.
   - Put the current full `context.md` text into the editor.
   - Show `Save with <user> tags` and `Cancel`.
   - Hide `Edit context`.
   - Status text becomes:
     `Editing context.md directly. Your changed lines will be saved inside protected <user> tags.`
3. When user clicks `Cancel`:
   - Hide editor.
   - Show preview.
   - Discard local changes.
4. When user clicks `Save with <user> tags`:
   - Compare original context text and edited text.
   - Any changed or inserted human-edited text should be wrapped in:

```markdown
<user id="USEREDIT-YYYYMMDDHHMMSS-1" author="frontend-user" created_at="ISO_DATE" action="replace">
The changed user-authored context goes here.
</user>
```

For deleted generated context, represent it as:

```markdown
<user id="USEREDIT-YYYYMMDDHHMMSS-1" author="frontend-user" created_at="ISO_DATE" action="delete">
Deleted generated context:

The original deleted context goes here.
</user>
```

5. After save:
   - Hide editor.
   - Show preview.
   - Preview should include the resulting context with `<user>` tags visible.
   - Status text becomes:
     `Saved direct artifact edits with protected <user> tags.`

This direct artifact editor replaces any separate manual-edit card. Do not create a separate "manual context edit" form outside the artifact section.

### Mock Context Content

Use this as initial mock `context.md` if no backend is connected:

```markdown
---
property_id: LIE-001
property_name: WEG Immanuelkirchstrasse 26
address: Immanuelkirchstrasse 26, 10405 Berlin
generated_at: 2026-04-25T12:00:00+02:00
schema_version: 1
source_watermark: day-03
---

# Property Context: WEG Immanuelkirchstrasse 26

<!-- HUMAN_NOTES_START -->
## Human Notes

Human-maintained notes live here and must never be overwritten by the engine.
<!-- HUMAN_NOTES_END -->

<!-- SECTION:agent_brief START -->
## Agent Brief

This is the canonical working context for the property. Use it before drafting emails, answering owner or tenant questions, reconciling invoices, or planning maintenance.

- Watermark: `day-03`.
- Coverage: 1622 bank transactions, 196 invoices, 6558 emails, 135 letters.
- Current topics: 30 open/high-signal topics.
- Review queue: 450 anomaly or attention items.
- Use source IDs before taking irreversible financial or legal action.
- Human notes and locked blocks are protected from automated patches.
<!-- SECTION:agent_brief END -->

<!-- SECTION:financial_state START -->
## Financial State

- Operating account: Berliner Sparkasse, IBAN `DE00000000000000000000`.
- Transactions loaded: 1622.
- Total credits: 410.240,00 EUR.
- Total debits: 388.120,00 EUR.
- Net movement in loaded rows: 22.120,00 EUR.
<!-- SECTION:financial_state END -->
```

### Latest Patch Tab

When user clicks `Latest patch`:

- Show patch JSON in `contextPreview`.
- Hide edit controls or disable direct editing in patch view.
- Example mock patch:

```json
{
  "mode": "patch",
  "patches_applied": [
    "frontmatter",
    "SECTION:agent_brief",
    "SECTION:financial_state"
  ],
  "human_notes_preserved": true,
  "lines_changed": 42
}
```

## Buttons And Inputs

Button style:

- Pill shape.
- Min height: `44px`.
- Cream translucent background.
- Border: `1px solid rgba(38, 42, 32, 0.12)`.
- On hover:
  - Slight upward transform: `translateY(-1px)`.
  - Stronger border.
  - Soft shadow.

Primary button:

- Gradient: moss to teal.
- Text: warm cream.
- Soft teal shadow.

Inputs:

- Rounded `18px`.
- Cream translucent background.
- Soft border.
- Focus ring: teal at low opacity.

Textarea:

- Same as inputs.
- Artifact editor uses monospace, white-space preserving, height around `clamp(420px, 42vh, 700px)`.

## Card Styling

Shared card style:

- Border: `1px solid rgba(255, 255, 255, 0.68)`.
- Background: linear translucent white overlay plus `--paper`.
- Box shadow: `0 30px 90px rgba(49, 42, 30, 0.16)`.
- Backdrop blur: `18px`.
- Border radius:
  - Large panels: `34px`
  - Metrics: `26px`
  - Inputs/buttons: `18px` or full pill.

## Responsive Rules

At max width `1260px`:

- Main shell becomes one column.
- Sidebar becomes non-sticky.
- Sidebar grid: two columns.
- Brand block and rail note span full width.
- Metrics grid becomes three columns.

At max width `900px`:

- Main shell padding: `12px`.
- Hero becomes one column.
- Flow strip becomes one column.
- Sidebar, intake grid, work grid, metrics grid, ask box, split row all become one column.
- Panel heads stack vertically.
- Hero headline around `42px` to `64px`.
- Context preview/editor height: `520px`.

## Required IDs And Classes

Preserve these IDs because future backend integration will rely on them:

- `useAi`
- `bootstrapBtn`
- `daySelect`
- `deltaBtn`
- `replayBtn`
- `refreshBtn`
- `loadContextBtn`
- `watermark`
- `contextState`
- `patchCount`
- `langgraph`
- `latestPatch`
- `metricsGrid`
- `resourceForm`
- `resourceType`
- `resourceName`
- `resourceFile`
- `resourceContent`
- `resourceNotes`
- `resourceStatus`
- `resourceList`
- `askForm`
- `questionInput`
- `answerBox`
- `runLog`
- `patchList`
- `contextPreview`
- `contextEditor`
- `contextEditStatus`
- `editContextBtn`
- `saveContextBtn`
- `cancelContextBtn`

Use these classes for styling:

- `ambient-orb`
- `orb-one`
- `orb-two`
- `app-shell`
- `side-rail`
- `brand-block`
- `brand-mark`
- `eyebrow`
- `rail-section`
- `section-title`
- `rail-copy`
- `switch`
- `delta-row`
- `status-list`
- `rail-note`
- `main-stage`
- `hero-panel`
- `hero-copy`
- `header-actions`
- `flow-strip`
- `metrics-grid`
- `metric`
- `intake-grid`
- `feature-card`
- `intake-card`
- `panel-head`
- `pill`
- `amber`
- `helper-copy`
- `stack-form`
- `split-row`
- `file-drop`
- `soft-status`
- `resource-list`
- `resource-item`
- `work-grid`
- `answer-panel`
- `activity-panel`
- `ask-box`
- `prompt-bank`
- `answer-box`
- `patch-list`
- `patch-item`
- `context-panel`
- `context-head`
- `context-tools`
- `tab`
- `context-edit-status`
- `context-editor`

## Interaction Summary

Implement these frontend interactions with mock data:

### Bootstrap Context

When clicked:

- Set busy state.
- Log `Bootstrapping context...`
- After short delay:
  - Update watermark to `bootstrap`.
  - Context state to `ready`.
  - Patch count to at least `1`.
  - Load mock context into artifact preview.
  - Log `Run completed`.

### Apply Delta

When clicked:

- Use selected `daySelect`.
- Log `Applying day-XX...`
- Add patch item like `day-XX.patch.json`.
- Update latest patch pill.

### Replay All Deltas

When clicked:

- Log `Replaying all deltas...`
- Populate patch list with several day patches.
- Update watermark to `day-10`.

### Refresh Status

When clicked:

- Log current mock status as formatted JSON.

### Load Context

When clicked:

- Reload mock context into preview.

### Ask Question

When submitted:

- Show `Thinking...`
- Then show a natural-language answer.
- Prompt buttons should fill the input and submit automatically.

### Stage Resource

When submitted:

- Validate content.
- Add resource to local staged list.
- Show latest staged resources.

### Edit Context

As described above, direct edit in the artifact panel only.

## Design Quality Bar

The result should look like a premium AI tool landing/dashboard hybrid, not Bootstrap, not Tailwind defaults, not a plain admin template.

Specific quality requirements:

- Generous spacing.
- Elegant hero section.
- Warm, memorable color palette.
- Soft glass cards with depth.
- High readability for dense operational text.
- Clear workflow hierarchy.
- Buttons feel tactile.
- Forms feel calm, not corporate.
- Artifact editor is visually large and important.
- Resource intake and ask panels should be useful but not visually louder than the artifact editor.

## Final Deliverable

Create a single-page responsive frontend that matches this structure and behavior. Use React if available, otherwise standard HTML/CSS/JS is fine. Keep the code clean and componentized. This is frontend-only, but make it ready for future API integration by preserving the IDs and state names above.
