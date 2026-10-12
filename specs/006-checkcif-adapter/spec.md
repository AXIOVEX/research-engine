# Spec 006 — checkCIF Adapter (P2: automated validation suite)

- **Date:** 2026-10-12 · **Status:** Draft (claims first; assessed before code) · **Build: NOT started — gated on the owner's shortlist approval.**
- **Pattern:** P2 (automated validation suite on structured artifacts). **Survey record:** docs/surveys/2026-10-12-domain-evidence-adapters.md §3/P2.
- **Adapter triple:** artifact = CIF + structure-factor file (FCF) · independent checker = IUCr checkCIF service / PLATON check.def suite · scope claim = CLM-006-02 (blind spots).
- **Function:** run checkCIF on a deposited CIF; map graded alerts (A serious / B / C / G, per category) onto an evidence item for the claim the structure supports; record checker identity + PLATON/check.def version + the CIF's SHA-256 in every output. Ingestion: web service (no public REST API — adapter must drive the service or a local PLATON install, `platon -u`); PLATON is author-distributed, not OSI-licensed — redistribution terms are a build-time gate.

## Requirements

- **CLM-006-01** (requirement): The adapter's evidence item records the CIF SHA-256, the checker (checkCIF service vs local PLATON), and the PLATON/check.def version for every run; an alert record without all three is not evidence.
- **CLM-006-02** (requirement): BLIND SPOT (scope claim): a clean checkCIF result (no A/B alerts) establishes only that the CIF is internally consistent under the check.def suite. It does NOT establish that the structure is chemically correct, that the claimed chemistry is the chemistry in the crystal, or that the dataset is genuine — IUCr states in every report that the absence of alerts does not guarantee there are no aspects needing attention, and internally consistent fabricated datasets are known to pass.
- **CLM-006-03** (requirement): Alert mapping is monotone and disclosed: A alerts attach contradiction mass to the supported claim's structure sub-claim; B alerts attach partial contradiction; C/G attach context only. The mapping table is part of this spec's record and may not be tuned per-study.
- **CLM-006-04** (requirement): The adapter supplies lane-1 evidence only: it issues no verdicts, and a checkCIF pass can never be the sole evidence for a supported verdict on a structure claim.

## Non-goals

No verdicts (lane-1 only, Spec 004 §2); no per-study tuning of mappings or applicability tables; no build before owner shortlist approval.
