# Design Note 003 — OD-2 Ratified: Hybrid Design, Hosted-First Pilot

**Date:** 2026-10-11 · **Status:** Owner decision record · **Decided by:** Tristen Pierson
**Ratifies:** the WS6 §3 recommendation. Appended record; WS6 §3's original text stands as the reasoning.

## Decision

- **Architecture: hybrid.** The record store and the connector/verification services are separate deployables. Custody of the research record can sit with the institution; discovery and verification can run as shared services. This split is a hard architectural boundary in Spec 002, not a deployment afterthought.
- **Pilot: hosted-first.** The first deployment is Axiovex-hosted, for speed of learning. The audit-bundle export (WS4) is the exit guarantee: a pilot institution can leave at any time with a complete, hash-verifiable record. No lock-in by design — and that guarantee is stated in the product's own materials, because it is part of the defensibility pitch.
- **Institution-local and full-hybrid remain first-class targets** of the same architecture (integrity offices, unpublished corpora — WS5 OQ-5.2 — and institution-held source rights such as HathiTrust keysets and per-shape BASE eligibility, WS1/RT2-1).

## Effect

- Spec 001 task T017 closes. With OD-1 (DN-002) and OD-2 both ratified, Spec 002 (implementation) may be drafted in full.
- Remaining gates before any *code*: the AR-1 hash-anchor requirement (at least one external anchor — OSF/Zenodo deposit or institutional timestamp — implemented before any institutional pilot), OD-5 numeric thresholds (set at the MVP evaluation's freeze), and the owner's go-ahead on Spec 002 itself.
- No spend is authorized by this note. Hosted-pilot infrastructure choices that cost money return to the owner as their own decision when Spec 002's plan reaches them.
