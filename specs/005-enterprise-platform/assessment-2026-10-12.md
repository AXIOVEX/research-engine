# AEE Assessment — Spec 005 (after_specify)

**Date:** 2026-10-12 · **Tooling:** spec-kit 1.0.10, AEE extension v1.2.0, AEE engine 1.0.4 (glossa venv pin), threshold 0.70
**Claims assessed:** 22 (`aee-claims.json` v0.1.0) · **Machine record:** `aee-assessment.json`
**Outcome: gather_evidence** — 7 claims at/above threshold; 15 below, all of them build commitments whose evidence does not exist yet. That is the correct state for a spec whose implementation is gated (G-ENT-1): the assessment was run *before* the design prose was finalized and before any code, per Article XII and the standing claims-first rule.

## Per-claim state

| Claim | Score | State |
|-------|-------|-------|
| CLM-005-01 OIDC only via tenant IdP; PKCE; no local passwords | 0.75 | draft — rests on DN-011 + the wireframes' SSO-hook record |
| CLM-005-02 SAML 2.0 SP, signed assertions, per-tenant IdP | 0.68 | **draft** — E2 commitment |
| CLM-005-03 appends only under enrolled identity-bound keys | 0.75 | draft — Article XIII + StudyStore actor machinery exist; the gate does not |
| CLM-005-04 key lifecycle as events; history keeps verifying | 0.68 | **draft** — E1/E3 commitment |
| CLM-005-05 deprovisioning ends access, never history | 0.68 | **draft** — E3 commitment |
| CLM-005-06 SCIM 2.0 lifecycle honored | 0.68 | **draft** — E3 commitment |
| CLM-005-07 JIT = asserting tenant only, no role by default | 0.68 | **draft** — E3 commitment |
| CLM-005-08 service-layer RBAC on the WS6 matrix | 0.75 | draft — matrix + actor model exist (WS6 §1, store.py); enforcement service does not |
| CLM-005-09 admin planes disjoint from study powers | 0.68 | **draft** — E1 model, E4 battery |
| CLM-005-10 break-glass: named, dual, boxed, alarmed, ledgered | 0.68 | **draft** — E4 commitment |
| CLM-005-11 tenant isolation by construction + battery | 0.68 | **draft** — E4 commitment; highest-uncertainty claim in the bundle |
| CLM-005-12 one codebase/model across shapes; residency pin | 0.68 | **draft** — E6 commitment |
| CLM-005-13 console gated on rendered-wireframe approval | 0.90 | draft — the Article XIV process itself is observed operating (T219-WF discharged 2026-10-12) |
| CLM-005-14 platform audit ledger: every admin action an event | 0.68 | **draft** — E1 core, E4 completion |
| CLM-005-15 platform audit export verifies standalone | 1.00 | draft — the Phase 5 pattern it reuses is built and test-evidenced; the platform-plane instance is E6 |
| CLM-005-16 readiness, not certification; mapping entries real | 0.97 | draft — DN-011's non-claims + the observed DN-008 wording correction |
| CLM-005-17 hold = export + anchor; erasure only via DN-005 certificate | 0.68 | **draft** — E6 commitment |
| CLM-005-18 scoped, expiring, revocable, attributed API keys | 0.68 | **draft** — E1 commitment |
| CLM-005-19 session/transport baseline, enumerated | 0.68 | **draft** — E4 battery commitment |
| CLM-005-20 enterprise build weakens no Spec 002 guarantee | 1.00 | draft (prediction) — scored on the existing battery it must keep green (68/68, CI 38214358137); discharged per phase exit |
| CLM-005-21 signed webhooks; receiver rejects bad/replayed | 0.68 | **draft** — E4 commitment |
| CLM-005-22 platform ↔ study records join on the binding | 0.68 | **draft** — E4 commitment |

## Reading

`gather_evidence` is the honest verdict for this package today. The seven claims at/above threshold divide into two kinds, and the record should not blur them: CLM-005-15 and CLM-005-20 score on **observed test evidence that already exists** (the Phase 5 bundle/verifier machinery and the Spec 002 battery) — they are claims about reusing and not breaking real machinery. CLM-005-01/03/08/13/16 score on **primary decision records plus observed process** (DN-011, the constitution, the WS6 matrix, the discharged wireframe gate) — strong direction evidence, no build evidence. The fifteen at 0.68 are the build itself, stated as requirements with falsifiers; each maps to a phase exit in `plan.md`, where it either gains evidence or fails in the open.

The engine's challenges, dispositioned per house practice — recorded, answered where they were right, never gamed:

- **Irreducibility** fired on all 22. Two were genuinely compound and were split before this run was finalized: CLM-005-14 (audit completeness) → +CLM-005-22 (platform↔study joinability), and CLM-005-19 (session/transport baseline) → +CLM-005-21 (webhook signing). The rest are single propositions; the challenge stands on them as a record.
- **Negation-conflict** pairs (54) are the engine's pairwise heuristic. The substantively tense pairs are this spec's named design tensions, resolved in the prose rather than by weakening claims: deprovisioning vs. historical verifiability (CLM-005-04/05 — resolved by separating authentication state from the record, spec §4); tenant isolation vs. auditor export (CLM-005-11/15 — resolved by per-tenant platform ledgers, spec §8); break-glass existence vs. no-backdoor (CLM-005-10 — the mechanism is the audit trail, spec §5).
- **Authority** challenges remain on CLM-005-13/16 (compliance kind): their evidence is directive- and process-level until E5/E6 produce build evidence. Recorded as standing.
- **Precision** on CLM-005-19 stands after one tightening pass (the claim was rewritten into enumerable checks — named cookie attributes, named headers, the 429 behavior); the residual challenge is recorded.

*Process note:* claims preceded the spec prose (DN-011 and `aee-claims.json` were written and assessed before `spec.md`/`plan.md`/`tasks.md`), and this spec was authored on its own branch/worktree (`enterprise-spec`, `~/workspace/tekmerion-ent`) writing only new files, so the running Tao-audit and Phase 6 UI workstreams are untouched. No implementation exists for any claim above; statuses are drafts and will move only on build evidence at phase exits.

---

## Amendment — CMMC (2026-10-12, after gate G-ENT-1, before E1 code)

**Trigger:** owner directives the same day — G-ENT-1 given (*"start E1 identity core"*), then *"also make this tool CMMC compliant."* The amendment was assessed **before any E1 code**, so E1 absorbs the CMMC deltas that touch it (Spec 005 §13; DN-011 CMMC section).

**Framing (Article X discipline, not optional):** CMMC (32 CFR Part 170) certifies organizations and assessment boundaries, not products. The amendment therefore claims **CMMC Level 2 alignment / compliance support** against NIST SP 800-171 Rev 2 (110 requirements); Level 1 is implied; Level 3 (SP 800-172) is out of scope (§11). The responsibility matrix (`cmmc-responsibility-matrix.md`) classifies all 110 requirements — Platform / Supports / Organizational — and records that SP 800-171 Rev 2 has no SA family (acquisition is organizational/contractual; platform support is provenance evidence only), so the 15-code list in the owner's brief is fully accounted: 14 families in the standard + SA recorded as absent-from-standard.

**New claims (bundle v0.2.0, 31 total), re-assessed at `after_specify`, outcome `gather_evidence` (11 ≥ 0.70, 20 below):**

| Claim | Score | Reading |
|-------|-------|---------|
| CLM-005-23 CMMC framing honesty | 0.756 | Rests on DN-011 + §13.1 records; discharged continuously, swept at E6 (T544) |
| CLM-005-24 matrix complete, 110/110 | 0.958 | The matrix artifact exists and was verified complete at authoring; classifications re-checked per phase exit |
| CLM-005-25 FIPS position + inventory obligation | 0.968 | Scores the *position* (gap + routes + dependency recorded; zero FIPS claims). The inventory itself is an E1 deliverable (T549); §3.13.11 satisfaction is an owner-decision-gated migration, **not** claimed |
| CLM-005-26 AU event-class completeness | 0.68 | **draft** — E1 core (T550 sweep is its instrument), E4 completion |
| CLM-005-27 MFA at IdP, platform-enforced | 0.68 | **draft** — E1 (joins T503) |
| CLM-005-28 CUI marking in artifacts | 0.68 | **draft** — E6 (T551); specced now so payloads never re-shape |
| CLM-005-29 SPRS self-assessment support | 0.958 | **Score flagged as ahead of its machinery:** the evidence is the matrix artifact (its data source) + §13.7. The matrix does not yet carry per-requirement SPRS deduction classes — that is T552 (E6). Recorded here so the 0.958 is never quoted as the feature existing; re-examined at E6 exit |
| CLM-005-30 IR hooks + append-only POA&M | 0.68 | **draft** — E4 hooks (T554) + E6 register (T553), seeded with the FIPS gap |
| CLM-005-31 DFARS/FedRAMP hosted-shape flag | 0.68 | **draft** — standing flag; an open owner/legal decision engineering does not resolve |

The original 22 claims' scores are unchanged by the amendment run (same evidence; the seven above-threshold claims stand as recorded in the first section). Tasks absorbed the deltas in place: [CMMC] flags on T503, T507, T510, T529, T531, T542, T544; new tasks T549 (crypto inventory, E1), T550 (AU completeness, E1), T551 (CUI marking, E6), T552 (SPRS support, E6), T553 (POA&M register, E6), T554 (IR event classes, E4). E6 is retitled "Compliance evidence (SOC 2 readiness + CMMC Level 2 support) + self-hosted shape" in plan and tasks.

---

## Phase exit — E1 identity core (2026-10-12)

**Built:** branch `enterprise/e1-identity` @ `2c4afbd` (15 files: `src/tekmerion/platform/` — directory, oidc, keys, authz, gate, ledger, service, ed25519 — plus tests and the crypto inventory). CI: PR #2, run **38253126192, success**; local suite 122 passed (82 prior unchanged + 40 new E1 tests, incl. the brief's seeded negatives: unenrolled append refused; revoked key refused with history verifying; plane disjointness both directions; service-layer RBAC denial with no UI; deactivation effective at next request; the T550 AU sweep over every E1 path incl. failures).

**Re-assessment** (`after_implement`, bundle v0.3.0): outcome **gather_evidence**; 14 of 31 claims remain below 0.70 — every one is unbuilt E2–E6 scope, which is the outcome working as intended. E1-moved claims (scores are the engine's index; the *status* carries the scoping):

| Claim | Score | Status at exit | Mechanism / residue |
|-------|-------|----------------|---------------------|
| CLM-005-01 OIDC only, no local passwords | 1.00 | supported | Mock-IdP flow tests + AST audit (no password path exists in the package) |
| CLM-005-03 key binding enforced at the gate | 1.00 | supported | Gate battery on production paths; boundary clarified: API-key appends are CLM-005-18's mode (attributed, not key-signed) |
| CLM-005-04 key lifecycle as events | 1.00 | **partially_supported** | Lifecycle core tested (PoP, rotation, revocation, closure); SCIM-driven completion is E3 |
| CLM-005-08 service-layer RBAC | 1.00 | supported | WS6 matrix as policy; denials enforced + recorded with the UI absent |
| CLM-005-09 disjoint planes | 1.00 | **partially_supported** | E1 model + cross-plane denial tests; the adversarial battery is E4 |
| CLM-005-14 platform audit ledger | 1.00 | **partially_supported** | E1 admin actions all ledgered (sweep-verified, chains verify); SCIM outcomes + break-glass events do not exist yet |
| CLM-005-18 scoped API keys | 1.00 | supported | Scope-subset at construction, ≤1y expiry, revocation/expiry refusal, attributed appends |
| CLM-005-25 FIPS position + inventory | 0.997 | supported | Inventory delivered (11 operations, all "No" on validation); §3.13.11 stays OPEN GAP — supported *as a position claim*, not as FIPS progress |
| CLM-005-26 AU event-class completeness | 1.00 | **partially_supported** | E1 emission half discharged by the sweep; E4 review/retention half outstanding, per the claim's own boundary |
| CLM-005-27 MFA platform-enforced | 1.00 | supported | No-MFA session refused at the gate; non-MFA step-up refused |

**Custody honesty (repeated from the code, where it is also recorded):** delegated custody's signer is a software development signer holding seeds in process memory — the custody *plumbing* (mode on every append, session binding, step-up) is real and tested; it is not a KMS/HSM and is never described as one. The service-layer Ed25519 and RS256 verification are prototype-grade pure-Python (the CI environment is stdlib + Axiomere only); key derivation is cross-checked against the Rust core in tests.

**Finding surfaced by E1 testing (record layer, cross-repo):** Axiomere events whose payloads carry certain high-precision floats (reproduced with `1791810119.6349843`) fail hash verification on reopen — Python/Rust float-serialization divergence, not tampering. Platform payloads now carry whole-second timestamps only (`platform/ledger.py` documents the discipline). The record-layer fix belongs to the Axiomere repo's own flow; it is reported here and in the E1 commit, not patched from this worktree.

**What remains not understood:** real-IdP interoperability (no external IdP exercised — the mock enforces genuine PKCE/RS256 but is ours), KMS/HSM custody behavior, and audit-ledger behavior at institutional volumes. E2 (SAML) is the next phase; it starts on the coordinator's merge of this branch, not before.

---

## Phase exit — E2 SAML 2.0 SP (2026-10-12)

**Owner decisions recorded (plan.md, commit `cba3349`):** E2 starts now (block ratification); the FIPS-validated crypto migration waits for a named CUI/defense requirement — the §13.3 open-gap posture (inventory + POA&M) stands, and no FIPS work was started in this phase. **Built:** branch `enterprise/e2-saml` @ `bb5a985` (PR #4 opened for CI, run **38257747324, success**; merging is the coordinator's). New modules: `platform/saml.py` (metadata import + validation; SP-initiated AuthnRequest over the Redirect binding, IdP-initiated unsolicited responses where the tenant allows; full response validation), `platform/xmlc14n.py` (in-repo exclusive C14N — stdlib-only posture), `platform/x509.py` (metadata certificate → RSA key + validity + fingerprint). Directory gains `SamlIdPConfig` (certificates stored by reference into the secrets store — fingerprints in config/ledger, material never in a payload) and the consumed-ID replay register. Service gains SAML configuration (platform provisioning + tenant-admin self-service under `TENANT_IDP_MANAGE`), the SAML login lifecycle, and SAML step-up: a second door into the **same** identity model — SAML-born identities enroll keys, are role-granted, and append through the identical gate (T517 parity battery). Every refusal is recorded as an `auth.login_failed` event (reason prefixed `saml:`) in the tenant ledger before the generic raise.

**Tests:** 37 new in `tests/test_e2_saml.py` + the Shibboleth-class harness `tests/e2_world.py` (T516: pure-Python self-signed certs, real XML-DSig signing, runs in CI; test tenants only, no external federation). Full suite **210 passed** locally and in CI (173 prior + 37 new; the Spec 002 battery is unchanged — CLM-005-20's per-phase obligation). The refusal battery covers F-005-02's three clauses directly: unsigned assertion (and response-signature-cannot-rescue), wrong signing key, KeyInfo naming an unconfigured cert, tampered content (digest mismatch), expired / not-yet-valid (beyond the named 300s skew, `CLOCK_SKEW_SECONDS`), wrong audience, wrong Recipient, wrong Issuer, InResponseTo mismatch, replayed assertion (IdP-initiated bytes presented twice), non-success status, encrypted assertion refused by name, DOCTYPE refused, a tenant with no SAML IdP (refusal ledgered in that tenant's own ledger), and the seeded cross-tenant case — tenant B's validly-signed assertion refused at tenant A's ACS, and B's flow state refused at A's ACS (a presented state is consumed by the attempt: fail-closed). Two defects were caught by the battery during the build and fixed in-phase: attribute values double-counted when an attribute's Name equaled its FriendlyName (mapping), and the Response-level Issuer lookup initially used the protocol namespace — Issuer is an assertion-namespace element, so the check was silently skipped and the refusal landed later at KeyInfo (now fixed, with the reason in the code).

**Re-assessment** (`after_implement`, bundle v0.4.0): outcome **gather_evidence**; 13 of 31 claims remain below 0.70 — all unbuilt E3–E6 scope (E3: 005-05/06/07; E4: 005-10/11/19/21/22; E6: 005-12/17/28/30; 005-31 is the standing DFARS flag). E2-moved claims:

| Claim | Score | Status at exit | Mechanism / residue |
|-------|-------|----------------|---------------------|
| CLM-005-02 SAML SP | 1.00 | **supported** | The battery above, on production paths; boundary holds as written (no artifact binding, no MDQ aggregate automation — per-tenant metadata, imported explicitly) |
| CLM-005-14 platform audit ledger | 1.00 | **partially_supported** (unchanged) | SAML config + auth events now also ledgered and chain-verified after the battery; residue unchanged: SCIM outcomes (E3) and break-glass events (E4) do not exist yet |
| CLM-005-27 MFA platform-enforced | 1.00 | supported (unchanged) | New evidence: SAML AuthnContext MFA parity at the gate + MFA-required SAML step-up |

**CMMC maintenance (§13.2):** the responsibility matrix was reviewed at this exit; no classification changes — the IA rows are written protocol-neutrally ("IdP assertion required", row 3.5.4 "signed assertions"), and E2 makes the SAML half of that basis true. The crypto inventory gains row 12 (SAML XML-DSig verification; pure-Python, **not** FIPS-validated — the §3.13.11 gap is unchanged, per the owner's recorded FIPS timing decision).

**Scope facts recorded in code:** SP AuthnRequests are unsigned in v1 (no SP request-signing key story yet); encrypted assertions are refused by name (no decryption-key custody story); one identity per (tenant, issuer, subject) triple — a person arriving through both doors of the same institution holds two identities until an account-linking rule is specced (the model's convergence is downstream of the boundary: authorization, key binding, and audit never branch on protocol).

**What remains not understood:** real-IdP interoperability — **no real Shibboleth or Entra SAML IdP has been exercised**; all evidence is against the in-repo harness, whose signatures are real but whose message shapes are ours. The in-repo exclusive canonicalizer is validated for determinism, content sensitivity, and attribute-order equivalence by unit tests and by the harness round-trips, NOT against a reference implementation or a production IdP's canonicalization edge cases (namespace-heavy assertions from real Shibboleth deployments are the known unknown). Certificate path validation is deliberately absent (trust = the tenant's metadata-import act); metadata refresh/MDQ automation is v1.1 scope. E3 (SCIM + lifecycle) is the next phase.
