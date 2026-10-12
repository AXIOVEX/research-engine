# WS4 — Records & Export

**Status:** Draft v0.1, 2026-10-11 · Governs: FR-008, FR-009 · Constitution: Articles IV, X

## 1. The record is an event store

One append-only event log per study (the ledger's adopted write model, WS2 §4). Event families:

- `registration.frozen` / `registration.amended`
- `query.executed` (connector, full query text, timestamp, result count)
- `evidence.retrieved` (item, provenance stub, content hash)
- `evidence.grouped` (item → origin group assignment, with grouping key used)
- `claim.registered` / `claim.superseded`
- `control.executed` (control, outcome, failure-mode reference)
- `verdict.issued` (claim, verdict, margin, interval, evidence-group basis)
- `adjudication.signed` (adjudicator identity, scope, timestamp)
- `export.generated` (bundle manifest hash)

All derived state — claim registers, verdict tables, dashboards — is a projection rebuilt from events. If a projection and the log disagree, the log wins and the projection is rebuilt; the disagreement itself is recorded.

**Sequencing (RED-TEAM-01 RT-2):** each study log has a *single sequencing point* — every append serializes through it, so the chain has exactly one head at any moment. If a fork is ever detected (two events claiming the same predecessor), the study record is INVALID until an appended adjudication event selects the surviving chain; the forked branch is preserved in the record, never silently merged or dropped.

## 2. Hash chaining and integrity

Each event carries the hash of the previous event in its study log plus its own content hash (SHA-256), forming a chain an external checker can verify without the engine: given the exported log, recompute the chain; any altered, reordered, inserted, or deleted event breaks verification at that point. Study bundles additionally carry a manifest hash over all member files. (Claim CLM-001-04 states the falsifiable form: a tampered record that replays clean kills this design.)

Known limit, stated plainly: a hash chain proves *internal consistency since the chain head*, not that the head itself is genuine. Anchoring — depositing the chain head hash with an external timestamping party (the OSF/Zenodo deposit in §4 doubles as one anchor; institutional repositories are another) — is what binds a record to real time. The design treats deposit as part of the record's life, not an afterthought.

## 3. What replay hashes, what replay compares

Content hashes bind: registration text, evidence item content (or, where redistribution is prohibited, the provenance stub + the source-side identifier, WS5), verdict rule parameters. Replay *recomputes* verdicts from hashed inputs where computation is deterministic, and *compares recorded vs. re-derived* verdicts where a component is nondeterministic (LLM extraction), logging variance per claim (WS3 §5). Both outcomes are first-class results in the replay report.

## 4. Exports — the audit bundle

One export action produces a self-describing bundle:

```
bundle/
├── manifest.json          # file list, hashes, bundle hash, schema versions
├── registration.json      # frozen design (+ amendments, as separate files)
├── claims.json            # claim register with falsifiers and statuses
├── evidence/
│   ├── items.json         # provenance stubs for every item
│   ├── groups.json        # origin groups and grouping keys
│   └── content/           # full text ONLY where source terms permit (WS5)
├── queries.json           # every query, verbatim, with timestamps and counts
├── verdicts.json          # per-claim verdicts, margins, intervals, basis links
├── controls.json          # controls, failure modes, outcomes
├── adjudication.json      # sign-offs
└── HUMAN-README.md        # plain-language guide to auditing this bundle
```

Formats are deliberately boring: JSON + Markdown, UTF-8, no proprietary envelope. A university must be able to read a bundle in twenty years with generic tools — the bundle's readability must not depend on the engine still existing. A PDF rendering of `HUMAN-README.md` + verdicts is generated for human circulation but is a *view*, never the record.

**Deposit paths:** OSF (project + registration components map naturally onto the bundle structure) and Zenodo (DOI-minted archival record; the bundle hash in the deposit metadata closes the anchoring loop in §2). Deposit is an explicit adjudicator-approved action, never automatic — what leaves the institution is a human decision (WS5).

## 5. Retention and the privacy tension

Append-only collides with legitimate deletion duties (privacy law, embargoed or withdrawn sources). Resolution, adopted from the ledger's governance work: **redaction by tombstone** — the event stays, its payload is replaced by a redaction event citing the authority and reason, and hashes are maintained over the redacted form with the break explicitly marked. The record then honestly shows *that* something was removed, when, and under what authority — instead of silently rewriting history or refusing a lawful removal. A bundle exported after a redaction can never verify against pre-redaction hashes, and says so in its manifest.

## 6. Open questions

- OQ-4.1 Bundle size for large reviews (thousands of items): content inclusion is rights-gated anyway; is a stubs-only bundle with resolvable identifiers sufficient for audit? Leaning yes — audit re-retrieves from sources of record; the bundle proves what was seen via hashes.
- OQ-4.2 Schema versioning across years: bundles carry schema versions; a standalone verifier tool (small, dependency-light) is a likely MVP companion artifact.
