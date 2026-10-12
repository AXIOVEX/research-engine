# WS6 — Product Shape

**Status:** Draft v0.1, 2026-10-11 · Governs: OD-1, OD-2 · Constitution: Articles I, IX

## 1. Who does what

| Role | Does | Never does |
|------|------|------------|
| **Researcher** | Frames questions, drafts claims/falsifiers, runs exploratory work, drafts registrations | Sign off their own institutional verdicts alone |
| **Reviewer / screener** | Screens evidence, resolves grouping disputes, performs extraction where automation is unsuitable | Alter a frozen registration |
| **Adjudicator** | Approves freezes, resolves quarantines, signs verdict sets, approves deposits | Edit the record (their decisions are appended events, not edits) |
| **Integrity officer** (read-mostly) | Audits any bundle, replays runs, inspects full history | Participate silently — inspection access is itself logged |
| **System** | Retrieval, dedup, grouping proposals, verification pipeline, weighing, replay, export | Issue an unsigned institutional verdict; promote exploratory results; hide an INVALID run |

The interface is **register-first**: the home object is the *study* (registration → claims → evidence → verdicts → bundle), not a chat box. A conversational assistant may help draft claims and falsifiers, but it operates *on* register objects, and everything it proposes enters as a proposal a human or a freeze check accepts. This is the deliberate inversion of incumbent tools, where chat is the product and the record is an afterthought.

## 2. API sketch

The engine is API-first (the UI is one client):

- `POST /studies` · `POST /studies/{id}/registrations` (draft) · `POST /registrations/{id}/freeze`
- `POST /registrations/{id}/runs` · `GET /studies/{id}/claims` · `GET /claims/{id}` (full provenance walk)
- `POST /runs/{id}/replay` · `POST /studies/{id}/exports` (bundle) · `POST /exports/{id}/deposit`
- `GET /verify?bundle=…` — standalone bundle verification (chain + manifest), usable without an account

Every mutating call appends events (WS4); there is no update-in-place endpoint for record objects.

## 3. Deployment shapes (OD-2 — owner decision)

| Shape | Fits | Trade-offs |
|-------|------|------------|
| **Hosted (Axiovex-operated)** | Small programs, pilots, cross-institution reviews | Fastest to adopt; institutions must trust Axiovex custody of records — mitigated by export-anytime bundles and hash anchoring, so custody is verifiable rather than blind |
| **Institution-local** | Integrity offices, sensitive/unpublished corpora (OQ-5.2) | Strongest data control; heavier IT lift; updates and connector keys are the institution's |
| **Hybrid** (local record store, hosted connectors/verification) | Most universities, long-term | Record never leaves campus; verification and discovery use shared services |

**Recommendation (for owner decision, not yet decided):** design for hybrid from the start — the record store and the connector layer are separate deployables precisely so custody of the record can sit with the institution. Hosted-first for the pilot (speed of learning), with the bundle export guaranteeing no lock-in: an institution can leave with a complete, verifiable record. That exit guarantee is a feature of the defensibility pitch, not a concession.

## 4. MVP slice (OD-1 — proposed in spec 001 §6)

One workflow, complete: a systematic-review-style evidence question for a research team (U2):

registration → Crossref + OpenAlex retrieval → claim register → origin-grouped evidence → per-claim verdicts with controls → adjudicator sign-off → OSF/Zenodo-depositable audit bundle.

Everything else — other audiences' workflows, additional connectors, cross-study dependencies (OQ-2.2) — is explicitly later. Kill criteria K1–K5 (spec 001 §6) govern the slice's evaluation run, which is itself a frozen registration inside the engine: the product's first study is the evaluation of the product.

## 5. What success looks like, honestly stated

Not adoption numbers (none exist; Article X). Success for the design phase is SC-1..SC-4 in spec 001. Success for the MVP is surviving its own kill criteria under a frozen evaluation — including the possibility that it does not, recorded the same way.

## Appendix — competitor gap (summary)

Method/competitor references studied (not integrated): Scite (citation-statement classification), Elicit (review workflow automation), Consensus and Undermind (answer-oriented discovery), and the platform deep-research tools (OpenAI, Google, Perplexity). Their shared shape: strong retrieval and synthesis, weak or absent pre-registration, no falsifier discipline, no origin-group counting, verdicts as prose rather than per-claim records, and audit trails that end at a reference list. The gap this product occupies: **the record is the product** — registration, falsifiers, controls, per-claim verdicts, and a depositable bundle. (Full analysis with citations to be appended here when the research pass completes; claims in this appendix will be sourced or removed at that point, per Article X.)
