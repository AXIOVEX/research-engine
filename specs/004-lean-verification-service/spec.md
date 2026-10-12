# Spec 004 — Lean Verification Service (first-class engine component)

- **Date:** 2026-10-12 · **Status:** Draft (claims first; assessed before code)
- **Doctrine:** DN-010 (Tao realignment). This service is lane-1 machinery: it produces *evidence*, never verdicts.
- **Owner directive:** 2026-10-12 — Lean as a persistent service any study can call; this service is the reference implementation of the domain-adapter interface (Part 2 survey, docs/surveys/2026-10-12-domain-evidence-adapters.md).

## 1. Purpose

A persistent Lean verification service: given a Lean repo or artifact, it returns lane-1 evidence for the claim the artifact supports —

1. a compile check against a **pinned toolchain + pinned Mathlib commit** (both recorded in every output);
2. a **sorry/admit count** over comment-stripped bytes;
3. an **axiom audit via `#print axioms`**: the standard axioms (propext, Classical.choice, Quot.sound) are allowed; **any other axiom is named in the output**, and `sorryAx` presence is a falsifying observation for proof claims;
4. the **formal statement pinned** beside the claim it supports (and, where a faithfulness pair exists, beside the original problem statement).

## 2. The adapter interface (this service is its reference implementation)

An **adapter** = (artifact type, independent checker, registered scope claim). The scope claim states, as a first-class registered claim with its own falsifier, **what the check does NOT establish**. Rules:

- Adapters supply lane-1 evidence only; an adapter result can never settle a claim alone (composition stays with the register/verdict machinery, Specs 002–003).
- No adapter is specified until its blind spots are written down as claims (the scope claim's falsifiers enumerate the blind spots).
- Every adapter output carries: artifact hash, checker identity + version pins, compile honesty state (`run_by_us` / `not_runnable_here` / `claimed_by_source` / `not_attempted` — inherited from Spec 003 §3), and the scope claim's id.

**This service's scope claim (blind spots, stated up front):** a clean compile + clean axiom audit establishes that the pinned formal statement has a kernel-checked proof under the pinned Mathlib. It does NOT establish that the formal statement is faithful to any informal problem (that is the faithfulness sub-claim, judged from the pinned pair); it does NOT establish novelty, attribution, or significance; it does NOT audit the transitive dependency tree beyond what the kernel itself checks when the *whole project* is built (a single-file check against precompiled dependencies inherits those dependencies' own sorry-freedom from their build, which the service must state); and a compile the service did not run is never recorded as run.

## 3. Narrow vs full — the sequencing decision (owner-delegated, recorded here)

**Decision: the narrow version already exists and serves the worked study; the full service is specified here and built later, gated on demand.**

- *Narrow (built, Spec 003):* `tekmerion.mathclaims` ingestion + `LeanRunner` — per-artifact fetch + SHA-256, sorry/admit counts, `#print axioms` probe where the artifact is runnable in the caller's environment, compile honesty states, statement pinning. It served the 2026 AI-math worked study (DOI 10.5281/zenodo.23317259). Its limits, observed in that study: every real-world artifact was `not_runnable_here` (claimants pin Lean v4.27.0 / v4.32.0 / v4.34.0-rc2 + full Mathlib; the local toolchain is v4.33.1 with no Mathlib build), so lane-1 evidence rested on parse + claimant compile claims. That is precisely the gap the full service closes.
- *Full (this spec, not yet built):* a persistent service holding **pinned toolchain + pinned Mathlib builds** (per-pin build cache under ~/workspace/tools), accepting a repo/artifact + target declaration and returning the §1 evidence bundle, with whole-project builds so transitive sorry-freedom is kernel-checked rather than inherited on trust. Build is gated: it starts when a study actually needs run-by-us compiles at claimant pins (the worked study demonstrated the need; scheduling is the owner's call alongside the adapter shortlist gate).
- *Justification:* building the full service before the study would have delayed the study for infrastructure whose requirements (which pins? whole-project or single-file? build-time budgets for 400k-line repos?) only the study's real artifacts could reveal. The narrow increment was genuinely cheaper: it reused the study's own ingestion path and produced the study's lane-1 evidence with honest compile states.

## 4. Requirements

- **FR-1** Pin management: toolchains and Mathlib commits are content-addressed; a check names its pins; a result produced under different pins is a different result.
- **FR-2** Whole-project build mode: for a repo artifact, the service builds the project (or restores the pinned build cache) so the kernel checks the transitive closure; single-file mode must label inherited-dependency trust explicitly.
- **FR-3** Axiom audit: `#print axioms` on the target declaration(s); output names every non-standard axiom; `sorryAx` ⇒ falsifying observation attached to the evidence, not a footnote.
- **FR-4** Statement pinning: the service returns the exact formal statement text (from the artifact bytes) beside the registered claim id it supports; where a faithfulness pair exists, the pair is returned together.
- **FR-5** Compile honesty: the four Spec 003 states, unchanged; a timeout or environment failure is `not_runnable_here` with the reason, never a proof failure and never a pass.
- **FR-6** Evidence shape: outputs are Spec 003 `proof_evidence`-compatible items (origin group = the service run), ledgered by the calling study (the service itself keeps no verdicts).
- **FR-7** Resource discipline: per-check time/space budgets recorded in the output; a budget-exceeded check returns its partial state honestly (e.g. parse + sorry count with compile `not_attempted`).

## 5. Non-goals

No verdicts; no faithfulness judgments (the service pins statements; humans/register judge the pair); no support for non-Lean provers in this spec (other P1 provers are separate adapters under the survey's pattern taxonomy); no hosted multi-tenant operation (that is Spec 005 enterprise territory, if ever).
