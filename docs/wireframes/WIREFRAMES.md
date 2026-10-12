# Tekmerion — Wireframes (the UI requirements)

**Status:** Phase 6 wireframe package, 2026-10-12 — **awaiting owner approval.**
**Governs:** Spec 002 Phase 6 (T219) and every later UI change.
**Companion draft:** constitution Article XIV (v1.2.0) — takes effect on the owner's approval of this package.

## 1. Governance (the rule)

> **The wireframes are the requirements for the UI's layout and appearance; no UI change ships without the wireframes being updated first and the rendered wireframes approved by the owner.**

Process for any UI change, in order:

1. Update the wireframe HTML in this directory (`*.html` + `style.css`) so the *rendered* screens show the proposed change.
2. Re-render the screenshots (`screens/*-desktop.png`, `screens/*-mobile.png`) at both widths.
3. The owner approves the **rendered** wireframes — screenshots, not source.
4. Only then does implementation change, and it changes to match the approved wireframes. A shipped UI that differs from the approved wireframes is a defect against this document, not a design iteration.

This document and the screens are amended the same way the constitution is: visibly, in git, with the reason recorded (plan.md phase record + the commit).

## 2. Screens

Sample data for every screen is the **Phase 5 AR-1 demonstration study** (`~/workspace/phase5-demo/`, bundle v2) — real states only, including its INVALID run, its metadata-only evidence, its fabricated-and-excluded citation, and its live Zenodo anchor. States that exist in the machinery but not in that study (a dead claim, a pending adjudication, claim-level verdict badges) are specified as clearly-labeled specimens in `components.html`, never fabricated into the study screens.

| # | Screen | File | Screenshots |
|---|--------|------|-------------|
| (a) | Register home — first screen is the claim register | `register.html` | `screens/register-desktop.png` · `screens/register-mobile.png` |
| (b) | Claim registration — shown in the engine-refused state (falsifier empty) | `register-claim.html` | `screens/register-claim-desktop.png` · `screens/register-claim-mobile.png` |
| (c) | Claim detail — evidence groups, citation stage outcomes, retrieved record | `claim.html` | `screens/claim-desktop.png` · `screens/claim-mobile.png` |
| (d) | Adjudication queue — decided items, rationales, RT-4 second-review state | `queue.html` | `screens/queue-desktop.png` · `screens/queue-mobile.png` |
| (e) | Freeze & verdicts — frozen registration, controls, the INVALID run | `freeze-verdicts.html` | `screens/freeze-verdicts-desktop.png` · `screens/freeze-verdicts-mobile.png` |
| (f) | Export & anchor — bundle v2, standalone verification, the Zenodo anchor record | `export-anchor.html` | `screens/export-anchor-desktop.png` · `screens/export-anchor-mobile.png` |
| (g) | Component specimens — verdict badges, dead row, pending-decision form, valid-run banner, role matrix | `components.html` | `screens/components-desktop.png` · `screens/components-mobile.png` |

Rendering: serve this directory (`python3 -m http.server`) and screenshot at desktop 1440×900 and mobile 390×844, full page. The `.screen-note` footer on each page names the screen and the data it shows; it is part of the wireframe package, not of the product UI.

## 3. Design tokens

All values live in `style.css` `:root` — the CSS is the token source of record; this section is its index.

### Color — surfaces and ink

| Token | Hex | Role |
|-------|-----|------|
| `--paper` | `#F6F4EE` | app background (warm paper) |
| `--surface` | `#FFFFFF` | cards, tables |
| `--surface-2` | `#FBFAF6` | table headers, inset areas |
| `--ink` | `#182230` | primary text |
| `--ink-2` | `#4C586A` | secondary text |
| `--ink-3` | `#7A8494` | captions, table headers, notes |
| `--line` | `#DCD6C9` | hairlines, card borders |
| `--line-strong` | `#C2BAA6` | input borders, emphasized rules |
| `--brand` | `#1E3A5C` | sidebar, primary buttons, headings' accents |
| `--brand-2` | `#2F5D8A` | links, meter fill |
| `--brand-tint` | `#E7EDF4` | neutral/brand chips (frozen, registered) |

### Color — status semantics (never decorative)

| Status | Text | Background | Border | Used for |
|--------|------|-----------|--------|----------|
| SUPPORTED | `#177245` | `#E2F1E7` | `#9CCBAA` | claim verdict; stage outcome "resolved"; PASS chips |
| INCONCLUSIVE | `#8A6100` | `#FAF0CB` | `#DEC97E` | claim verdict; quarantine/pending chips |
| CONTRADICTED | `#B3261E` | `#F8E4E1` | `#E0A49E` | claim verdict; stage failure ("not found", "disagree"); exclusion decisions; refusal banner |
| INVALID | `#7F1D1D` | `#F6E0E0` | `#C98A8A` | run verdict only — banner head is solid `#7F1D1D` with white text; register strip uses the tinted banner |
| DEAD | `#5A636E` | `#E9EBED` | `#B9BFC6` | dead (withdrawn) records: muted row, DEAD chip, statement struck, reason verbatim, score 0.0 |
| METADATA-ONLY | `#5B4B9E` | `#EAE6F8` | `#BDB1E3` | metadata-only evidence/groups/citation outcomes — always a labeled chip, never a footnote |

Rules: a status color is used *only* for that status. Verdict colors appear on claims only when a valid run issued the verdict; INVALID never appears as a claim badge (it attaches to runs). PASS/verification chips reuse the SUPPORTED palette.

### Typography

| Role | Font | Sizes |
|------|------|-------|
| Headings (h1/h2), study name, claim statements, rationales | Georgia, "Iowan Old Style", serif | h1 27px · h2 20px · statement 14.5–17px |
| UI text, tables, forms | system sans (-apple-system, "Segoe UI", Roboto) | body 14px · tables 13.5px · small 12px · micro 11px |
| Hashes, DOIs, IDs, scores | ui-monospace, "SF Mono", Consolas | 12px, break-all (IDs in tables: no wrap) |

### Spacing, shape, layout

- Spacing scale: 4 / 8 / 12 / 16 / 20 / 24 / 32 (card padding 16–18, page padding 24–28).
- Radius: cards 8px, controls/chips 6px, chips pill.
- Desktop shell: 236px brand sidebar + content column (max 1120px). Nav order is the workflow order: Register → Queue → Freeze & verdicts → Export & anchor.
- Breakpoint **760px**: sidebar becomes a top bar (brand, study, horizontally scrolling nav, actor/roles), grids go single-column, stat cards 2-up, and tables restack as labeled rows (each cell shows its column label). Responsive behavior is a requirement of every screen, not a theme.

## 4. Component rules

- **Chips** are the only status carriers: small, pill, colored per §3, text always names the status (color is never the only signal).
- **Banners**: a run verdict gets a full-width banner at the top of the register and on Freeze & verdicts — INVALID in `--invalid` treatment with the engine's reasons stated; a refusal (registration, export) gets the refusal banner carrying the engine's message verbatim in mono. Banners never paraphrase the engine into something softer.
- **The falsifier field** is visually mandatory: "Required · Article II" chip, and in the missing state a 2px contradicted border + tinted background. Its help text states the rule and who enforces it (the register — not the form, not an adjudicator).
- **Dead records** render in place, muted, statement struck through, with DEAD chip + verbatim reason + score 0.0. Never omitted, never shown live, never behind a "show deleted" toggle.
- **Metadata-only** is a chip on the group, the citation row, and the claim's evidence cell — visible at every level of aggregation, with the folded masses (0.00) and the RT-5 cap consequence stated where verdicts are discussed.
- **Coverage meters** always print the numeric fraction beside the bar and never round up (0 of 1 groups = 0%).
- **Tables → labeled rows** on mobile: no horizontal scrolling of record tables; hashes wrap (break-all) rather than overflow.
- **Buttons**: one primary action per view (brand solid). Destructive-looking actions do not exist; withdrawal is a normal button labeled with what it does ("Withdraw claim (marks it dead)") plus its consequence in text. There are no edit or delete buttons anywhere.
- **Role views**: affordances follow the WS6 §1 matrix (specimen in `components.html`). In the integrity view, mutating controls are *absent*, not disabled. Decision controls appear only on pending queue items, only in the adjudicator view.
- **Actor block** is always visible: who you are acting as, the active role, and the note that identity arrives via the SSO hook and every action is appended under that name.

## 5. Content rules

- Every value on screens (a)–(f) is a real value from the demo study's record (bundle v2 / ledger). Hashes and the DOI are shown in full where the record's verifiability is the point (freeze, anchor), shortened with an ellipsis only in summary lines.
- Empty states say what is absent and why ("No claim verdicts — an INVALID run issues none"), never a generic "nothing here".
- Explanatory text cites its authority inline (Article II, WS3 §1, RT-5, DN-003…) in the same terse style as the codebase's comments. The UI teaches the discipline it enforces — but the enforcement is always the engine's, and refusals are shown as the engine's.

## 6. What approval covers

Approving this package approves: the shell and navigation, the six screens' layouts at both widths, the token palette and status semantics, the component rules above, and Article XIV. It does not approve any implementation — implementation is T219, gated on this approval (tasks.md, gate T219-WF).
