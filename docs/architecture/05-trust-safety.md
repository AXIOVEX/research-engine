# WS5 — Trust & Safety for Institutions

**Status:** Draft v0.1, 2026-10-11 · Governs: FR-005, FR-010, FR-012 · Constitution: Articles VIII, IX, XI

## 1. Citation verification — the non-negotiable pipeline

Fabricated references are the signature failure of AI research tools, so verification is a pipeline stage, not a model instruction:

1. **Resolution.** Every citation must resolve against a source of record: DOI → Crossref/DataCite metadata; no DOI → source-native record (WS1 connector) matched on title + authors + venue + year. Resolution produces a *retrieved metadata record*, stored as provenance.
2. **Agreement check.** The fields the study relies on (title, authorship, year, venue, and — where the claim depends on it — the specific result) are compared between the citing context and the resolved record. Material mismatch → the item is quarantined and the run cannot proceed to verdicts until an adjudicator resolves it.
3. **Content check.** Where the claim attributes a finding to a source, the stance extraction (WS2) is performed on the retrieved content, not on the model's memory of the paper. If content cannot be retrieved (paywall, terms), the item is marked `metadata-only` and its evidentiary weight is capped by rule — a citation whose content nobody checked cannot carry a claim by itself.

No stage is prompt-based. "The model was told not to hallucinate citations" is not a control; resolution against a source of record is.

## 2. Uncertainty surfacing

- Every verdict displays its interval and the origin-group basis (WS3 §6); a SUPPORTED verdict resting on one group looks different from one resting on twelve, and the UI/API must make that visible without drilling down.
- Ignorance is a shown quantity, not a hidden residue: the proportion of a claim's potential evidence space that is `metadata-only`, paywalled, or unretrieved is reported as part of the verdict record.
- Abstention is a designed outcome (INCONCLUSIVE), presented as a result with a reason code — insufficient groups, conflicting groups, margin straddle — never as an error state and never silently converted to a weak SUPPORTED.

## 3. Human adjudication points (Article IX)

Judgment enters at designed points, each recorded as an event with a named person:

| Point | Decision | Default if unstaffed |
|-------|----------|----------------------|
| Registration approval | This design is worth freezing | No freeze, no confirmation run |
| Grouping disputes | Near-duplicate items: one origin or two (WS2 §2) | Conservative: counted as one origin (lower count wins) until decided |
| Quarantine resolution | A mismatched citation: error, variant, or fabrication | Item excluded; run continues only if claim basis remains sufficient |
| Verdict sign-off | This verdict set may leave the system | Nothing is exported as institutional output |
| Deposit approval | This bundle may be deposited publicly (OSF/Zenodo) | Bundle stays internal |

Roles map to institutional identity (SSO) rather than engine-local accounts wherever deployed inside a university (WS6).

## 4. Data-licensing boundaries (Article XI)

Per-source rights are recorded in the WS1 registry with three separate answers per source: **query** (API terms, rate limits), **store** (may full text be retained, or metadata/stubs only), **redistribute** (may content appear in exported bundles). The export generator enforces the strictest applicable answer mechanically: content a source does not permit redistributing is replaced by its provenance stub in the bundle, automatically, with the substitution visible in the manifest. Convenience never overrides the table; an unknown rights answer defaults to *stub-only* until researched and recorded.

## 5. Abuse and failure cases designed for

- **Citation laundering** — citing a real paper for a claim it does not make. Countered by the content check (§1.3), not by resolution alone.
- **Origin flooding** — manufacturing apparent independence via many derivative summaries. Countered by origin grouping (WS2) and the group-count display rule.
- **Freeze shopping** — re-registering until a design yields the desired verdict. Countered structurally: all registrations, including abandoned ones, remain in the record; a study's bundle discloses prior registrations on the same question.
- **Selective export** — exporting only favorable claims. Countered by the manifest: bundles contain the full claim register for the registration; partial exports are labeled partial on every page and in metadata.
- **Silent model change** — an upstream model update shifting extraction between freeze and run. Countered by recording extractor identity + version per item (WS2), and by replay variance reporting (WS4 §3).

## 6. Open questions

- OQ-5.1 Retraction watching: when a source is retracted after a verdict, the revisit loop (WS2/WS3) flags dependent claims — but who is *notified*, and is a post-publication flag an engine duty or an institutional one? Needs an owner/institution-policy decision before MVP.
- OQ-5.2 Student data: graduate-program use may involve unpublished student work as evidence. Storage terms for user-supplied corpora need a dedicated decision in WS6 deployment shapes.
