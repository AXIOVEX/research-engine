# AEE Assessment — Spec 001 (after_specify, design phase)

**Date:** 2026-10-11 · **Claims assessed:** 7 (`aee-claims.json` v0.1.0) · **Outcome: ITERATE → gather evidence (expected at design phase)**

## Per-claim state

| Claim | Kind | State | Basis |
|-------|------|-------|-------|
| CLM-001-01 freeze prevents drift | design | asserted-design | Mechanism specified (WS3 §3, hash + amendment rule); no run evidence yet — evidence arrives with the MVP evaluation |
| CLM-001-02 origin-group counting | design | asserted-design | Schema + counting rule specified (WS2 §2); the ledger program's derivative-inflation results are prior art, not this system's measurement |
| CLM-001-03 controls detect defective runs | design | asserted-design | Control patterns specified with named failure modes (WS3 §2, as amended by RT-1/RT-6); falsifier F-001-D3 is directly testable in the MVP evaluation |
| CLM-001-04 hash chain detects tampering | design | asserted-design | Design specified (WS4 §2–3, RT-2 sequencing amendment); AR-1 anchor gate recorded |
| CLM-001-05 citation resolution → zero fabrication | design | asserted-design | Pipeline specified (WS5 §1); this is kill criterion K1 — the MVP evaluation is its test |
| CLM-001-06 per-claim taxonomy preserves information | design | asserted-design | Taxonomy mechanics specified (WS3 §1); adjudicator study is the K3 protocol |
| CLM-001-07 U2 slice is minimal-complete | scope | **proposed — pending owner (OD-1)** | Argued in DN-001 + WS6; not ratified |

## Reading

No claim is marked supported: at design phase every design claim is a *commitment to a test*, and its falsifier names the test. That is the correct epistemic state and the assessment records it rather than inflating it. The gate to implementation is not a better assessment score — it is the owner's OD-1/OD-2 decisions, after which the MVP evaluation (itself a frozen registration, WS6 §4) generates the first real evidence for CLM-001-01…06.

---

**Addendum (2026-10-12):** the claims bundle was normalized to the AEE engine's native claim format (the founding file used a pre-engine vocabulary the assessor cannot load) and re-assessed mechanically: `aee-assessment.json`, outcome **gather_evidence** — the same reading as above, now machine-produced. This hand assessment remains the historical record of the founding review.
