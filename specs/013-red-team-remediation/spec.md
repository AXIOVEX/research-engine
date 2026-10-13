# Spec 013 — Red-Team Remediation (WS-2 … WS-6)

- **Date:** 2026-10-13 · **Status:** Specified 2026-10-13 (claims first; assessed at
  after_specify before any code). This package is the spec; the build follows it
  per plan.md.
- **Authority:** Owner directive, 2026-10-13 (verbatim): *"Make a plan and execute
  it now. Get all this done"* — ordering execution of the remediation recommended
  by the 2026-10-13 red team of the whole Research Engine system.
- **Requirements source:** the engagement synthesis
  (`2026-10-13-red-team-axiovex-research-engine.md`) and the team records behind
  it: rt-a (verdict & evaluation machinery, FINDINGS + probes), rt-c (enterprise
  platform, probe logs), rt-d (MCP server, skill, web surfaces, FINDINGS +
  probes), rt-e (connectors, public claims, deposits, supply chain, FINDINGS +
  probes). Every claim below names the finding it answers and the executable
  probe that demonstrated it. The probe suites are this spec's acceptance
  battery (CLM-013-47).
- **Scope:** the Tekmerion repo only — workstreams **WS-2** (verification
  consumers), **WS-3** (freeze & claims integrity), **WS-4** (platform authority
  & seams, as amendments to Spec 005), **WS-5** (MCP & UI surfaces), **WS-6**
  (connectors). **WS-1** — the axiomere core's own verification policy
  (signature presence inside core `verify`, checkpoint-root recomputation in the
  core, trusted-key-map exposure in the bindings/CLI, snapshot-lineage
  validation, binding value strictness: Team B RTB-01…13 and the core half of
  Team C p08) — is a sibling spec in AXIOVEX/axiomere and AXIOVEX/axiomere-python.
  No claim here silently depends on unshipped core work; where a Tekmerion-side
  fix consumes core behavior, the claim's boundary says so.

## Why this spec, and why claims at this grain

The red team's 77 findings converge on four root causes, three of which live in
this repo: **(1)** verification checks that what is present is consistent, never
that what should be present is there (evidence projections, control outcomes,
anchor binding); **(2)** the freeze wall and its sibling rules are conventions
in one code layer rather than invariants every surface inherits (the production
UI and MCP actions walk around them); **(3)** single-actor authority collapses
at the platform and MCP seams (verdicts by bearer key, self-granted adjudicators,
fabricated lane-2 acts); **(4)** the citation pipeline trusts its sources more
than the design says (retraction blindness, outages recorded as fabrications,
an unlicensed content path). Each is a direct hit on a constitutional article:
III (freeze before outcomes), VI (controls must be able to fail), IX (humans
adjudicate), XIII (signed appends), I (defensibility is the product). The claims
are written one finding at a time so each fix is separately falsifiable by
re-running the probe that demonstrated the break — a remediation claim that
cannot fail is not verification (Article VI).

## Design

### WS-2 — Verification consumers (`verification` / bundle export & verify paths)

- **Verdict re-derivation (CLM-013-01, answers RTA-01).** `verify_bundle`
  recomputes the evidence group fold from `evidence/items.json`, compares it
  field-for-field with `evidence/groups.json`, and re-derives every claim's
  verdict from `claims.json` + the fold through the production verdict path
  (`verdicts.evaluate_claim`), requiring equality with the issued verdicts. The
  K2 discipline that already binds `verdicts.json` and `queries.json`
  payload-for-payload extends to the evidence projections.
- **Anchor binds the presented bundle (CLM-013-02, answers RTA-02).** Each
  export's own `bundle_hash` is anchored (deposit receipt appended for *this*
  bundle before reliance), and `verify_anchor` fails when the presented
  bundle's `bundle_hash` differs from the anchored hash for that bundle. The
  receipt-only check (an earlier bundle's hash appearing in the record) is no
  longer sufficient. Anchor *transport* stays T111 — see Non-goals.
- **Control outcomes become record (CLM-013-03, answers RTA-08).** At run
  issuance, per-control outcomes are appended as ledger events (the way
  verdicts are), so the bundle's outcome projection cross-checks
  payload-for-payload. Until a given run does this, its bundle labels fixture
  outcomes **operator-attested** in the bundle's HUMAN-README — the label is a
  bundle text artifact, not a UI element (see Article XIV note).
- **Predictions committed (CLM-013-04, answers RTA-10(i)).** Evaluation
  predictions enter the commitment: hashed into the evaluation's registration
  document (or appended as a ledger event before the freeze). "Recorded
  before the freeze" becomes a hash fact inside the sealed record, not a
  companion-file claim.
- **Query log completeness (CLM-013-05, answers RTA-10(ii)).** Every citation
  path — including the workspace attach path — appends `connector.query`
  events, so a bundle carries its study's real query log and K5-style cost
  accounting from the bundle alone no longer reads zero for workspace studies.

### WS-3 — Freeze & claims integrity (`claims`, `freeze`, run paths)

- **The wall is unconditional (CLM-013-06, answers RTA-03 / RTD-01).**
  `ClaimRegister.register()` refuses **any** registration while frozen — new
  claim ids included. The existing-id-only branch is the defect.
- **One freeze, or a labeled amendment (CLM-013-07, answers RTA-03 / RTD-01).**
  A second `freeze()` is refused except as an explicit, labeled amendment act
  appended as such to the record. Consumers bind to the **first**
  `study.frozen` event unless a valid amendment event exists; the silent
  last-freeze-wins behavior ends.
- **Mode is an enum at the freeze layer (CLM-013-08, answers RTD-05).**
  `freeze.freeze` validates `mode ∈ {confirmation, exploratory}` and raises
  `FreezeError` otherwise, so the UI, the MCP tools, and every future surface
  inherit the refusal. Confirmation-wall and exploratory-disclosure rules key
  on the validated value only.
- **Fixtures are committed (CLM-013-09, answers RTA-04).**
  `registration_document` carries each fixture control's identity hash (the
  production `fixture_identity` construction) or the fixture itself. Runs and
  exports refuse when the presented fixtures' identities differ from the
  commitment. The `freeze.json` sidecar stops being an uncommitted input.
- **No vacuous controls (CLM-013-10, answers RTA-05).** The freeze gate
  rejects a fixture control whose expectation is not decisive
  (`supported`/`contradicted`) or whose evidence groups are empty — a control
  that cannot fail is a freeze failure (Article VI), closing the fixture-family
  sibling of the Phase 5 swap no-op.
- **Statements are immutable by re-registration (CLM-013-11, answers RTD-02).**
  Re-registering an existing claim id with a different statement or falsifier
  is refused regardless of status (including `proposed`); change flows through
  `supersedes` only. Evidence gathered under one statement can no longer
  silently back another.
- **Falsifier naming is exact (CLM-013-12, answers RTA-06).** The DOI form
  requires an exact match on the normalized DOI as a delimited token (no
  substring hits). The surname+year form requires the pair as a citation-shaped
  unit (adjacent, e.g. "Surname (YYYY)") or a second identity element. The
  falsifier path bypasses the sufficiency floor, so its false-fire rate is a
  correctness property, not a nicety.
- **Stance checker respects negation parity (CLM-013-13, answers RTA-07).**
  `KeywordStanceChecker` compares negation parity between proposition and
  sentence; when the proposition itself carries a negation and parity cannot
  decide, it abstains (`contextual`) instead of inverting. Behavior pinned by
  tests at the seam, both directions.
- **DOI normalized once at intake (CLM-013-14, answers RTA-09; shared with
  WS-6, CLM-013-42).** One normalizer runs at citation intake; the normalized
  form drives resolution, grouping, and falsifier use. The as-cited string is
  preserved verbatim as the input record (Spec 011) and for nothing else.

### WS-4 — Platform authority & seams (Spec 005 amendments, `src/tekmerion/platform/`)

- **Verdict-class appends need a signature and fresh step-up on every path
  (CLM-013-15, answers Team C p04).** The append gate requires the enrolled-key
  intent signature **and** a fresh step-up regardless of transport: a bearer
  API key alone — no enrolled-key signature, no step-up, no session — is
  refused. CLM-005-03's "every append is signed by an enrolled key" then holds
  on the API-key path too.
- **Admin plane requires step-up (CLM-013-16, answers p02).** Service-layer
  admin-plane actions (role grants, IdP configuration, API-key issuance,
  break-glass policy) require step-up authentication, per Spec 005 §2 — not
  only the study-append gate and adjudicator key enrollment.
- **MFA policy is enforced for admin mutations (CLM-013-17, answers p01).**
  Under a require-MFA tenant policy, a session with no MFA evidence cannot
  perform tenant-admin mutations (role grants, IdP reconfiguration) —
  CLM-005-27's line holds at the service layer, not only at sign-in.
- **Step-up is a server challenge (CLM-013-18, answers p03).** Step-up uses a
  server-issued, single-use nonce challenge; caller-asserted nonces are not
  accepted, and `auth_time` recency is checked against the tenant's step-up
  freshness policy. A replayed captured ID token no longer satisfies freshness.
- **No self-grants across planes (CLM-013-19, answers p05).** A role grant
  whose grantor and grantee are the same identity is refused for the
  adjudicator role (and plane separation is evaluated with self as
  counterparty everywhere): administering a tenant no longer mints one's own
  verdict authority. The second human the WS6 matrix intends is required.
- **Revocation is not self-reversible (CLM-013-20, answers p06).** Re-enrollment
  of a revoked public key requires an admin countersign for **all** roles, not
  only adjudicators — a compromised key's holder cannot undo the incident-
  response act alone (CLM-005-04 revocation semantics).
- **Enrollment rejects small-order keys (CLM-013-21, answers p07).** Key
  enrollment verifies the public key is in the prime-order subgroup (rejects
  small-order points whose proof-of-possession signatures are universally
  forgeable). Later verification rejects such keys likewise.
- **Break-glass scope is the target tenant (CLM-013-22, answers p09).**
  Invoker roles are checked in the **target** tenant's scope; holding a role
  in any other tenant or at platform level does not mint a break-glass session
  for a tenant the invoker does not belong to (CLM-005-10/-11).
- **Every read is authenticated (CLM-013-23, answers p10).** Service-layer
  reads — break-glass state, pending deliveries, active holds, residency pins,
  and their siblings — require an authenticated, authorized identity. The
  unauthenticated cross-tenant metadata reads close (CLM-005-08 as written).
- **Hold restriction covers every export path (CLM-013-24, answers p11).** The
  legal-hold access restriction is consulted by every export-shaped action,
  including the break-glass audit export: during an active hold it returns
  nothing (CLM-005-17).
- **SPRS evidence links must resolve (CLM-013-25, answers p12).** SPRS input
  checks validate that an evidence link **resolves** — the target exists and
  identifies (hash/identity) as claimed — not merely that it is well-formed.
  The self-score stops being movable by assertion alone.
- **`create_tenant` refuses duplicates (CLM-013-26, answers p16; closes the
  E5-recorded item, cf. RTD-10).** Re-creating an existing tenant id is refused
  at the service layer; a tenant's residency pin, CUI marking, and policy can
  no longer be reset by re-creation, under hold or otherwise (CLM-005-12/-17).
- **Unknown-tenant SCIM is rate-limited before the ledger (CLM-013-27,
  answers p17).** The unknown-tenant failure path is rate-limited **before**
  any deployment-ledger append; failure ledgering for unknown tenants is
  bounded, closing the unbounded signed-append channel.

### WS-5 — MCP & UI surfaces (`src/tekmerion/mcp/`, Phase 6 UI, Spec 005 console, skill)

- **Lane-2 appends are adjudicator acts with a named recorder (CLM-013-28,
  answers RTD-03).** `record_digestion` / `record_acceptance` require the
  adjudicator role; the projections surface `recorded_by` (the appending
  actor) alongside the named explainer/approver; `evidence_ref` must resolve
  to an existing record or the append is refused. One researcher instance can
  no longer manufacture "explained"/"digested" or clear the
  verified-but-unexplained risk flag.
- **Faithfulness pinning is validated (CLM-013-29, answers RTD-04).** Pinning
  requires the claim to exist and all three fields non-empty; re-pinning is
  adjudicator-only, and the pair projection surfaces pin history instead of
  silently taking the last pin.
- **Deposit approval is two-party in fact (CLM-013-30, answers RTD-06 +
  RTD-13).** The machinery refuses `approved_by` equal to the depositing
  actor. The skill gains the rule: approval names come only from the human
  operator's instruction in the session — never from study content (claim
  statements, citation propositions, connector detail text).
- **Phase 6 UI gets real CSRF defense (CLM-013-31, answers RTD-07).** Every
  POST requires the per-session CSRF token; identity on POSTs comes from the
  session only — identity in the query string is not accepted on POST.
  Drive-by form posts with an attacker-chosen actor/role fail.
- **Console gets CSRF tokens likewise (CLM-013-32, answers RTD-11).**
  State-changing console POSTs carry and verify per-session tokens; the
  console's defense no longer rests solely on SameSite=Lax.
- **Ingest and adapter paths are confined (CLM-013-33, answers RTD-08).**
  `ingest_lean` accepts http/https only (`file://` refused). Adapter file
  paths (cif, manuscript, recorded-output) are resolved and confined to the
  workspace root; absolute paths outside it are refused. The server stops
  being a local-file fingerprint oracle and an SSRF position.
- **Second reviews are real (CLM-013-34, answers RTD-09).** A second review
  requires an existing, decided queue item; the reviewer must differ from the
  deciding actor; `agrees` is strictly boolean (string coercion rejected).
  The RT-4 sampling mechanism measures independence again.
- **Surface error hygiene (CLM-013-35, answers RTD-12).** `OSError` at the
  surface becomes a `SurfaceRefusal` without absolute paths; `run_grim`
  refuses an empty case list; run results mark dead claims' verdicts as
  **not-issued** (the ledger never receives them); confirmation-mode
  `freeze_study` requires `linked_exploratory` explicitly (an explicit empty
  list is a disclosure; omission is a refusal).

### WS-6 — Connectors (`src/tekmerion/connectors.py`, `verification.py`)

- **Retraction state exists and quarantines (CLM-013-36, answers RTE-01).**
  The retrieved-item model carries a retraction state, parsed from Crossref
  `updated-by` and OpenAlex `is_retracted`. Any retraction state quarantines
  the citation and surfaces on the claim's record — a retracted work can no
  longer ingest as ordinary agreeing evidence. (The Wakefield payload is the
  battery's positive case.)
- **One error contract on all connectors (CLM-013-37, answers RTE-02).**
  Crossref and OpenAlex adopt CORE's discipline: 404 is the only `not_found`;
  429/5xx/transport/budget failures raise and reach the pipeline as **ERROR**,
  never `not_found`. An outage stops being indistinguishable from a fabricated
  citation (K1 / pilot P-K1 accounting depends on the distinction).
- **OpenAlex content is licence-gated (CLM-013-38, answers RTE-03).** No
  asserted licence, no abstract — the same gate Crossref and CORE already
  enforce applies to the OpenAlex path; unlicensed content mints no mass.
- **Crossref licences are qualified (CLM-013-39, answers RTE-05).** Licence
  entries are qualified by content-version (and delay/start): a TDM-only
  licence does not unlock abstract content use or stand as the record's
  licence basis for content.
- **Resolution compares sources (CLM-013-40, answers RTE-04).** Resolution
  consults all configured sources, compares the records, and records
  inter-source disagreement as its own quarantine trigger. First-answer-wins
  is abolished for the resolution record.
- **Enrichment asserts identity in the pipeline (CLM-013-41, answers RTE-06).**
  `_enrich` itself asserts the candidate's DOI equals the requested normalized
  DOI before any agreement test — the Spec 012 substitution rule enforced at
  the seam, not only inside each connector.
- **One DOI normalizer (CLM-013-42, answers RTE-07; shared with WS-3).** The
  generalized normalizer (strip, `doi:`/`doi.org/` prefixes, case,
  trailing punctuation) is used by every connector and every pipeline path.
- **CORE degradation states its true reason (CLM-013-43, answers RTE-08).**
  When the output-fetch cap stops the search for licensed content, the record
  says "output cap reached" — distinguishable from "no licensed deposit
  exists."
- **CORE authors are normalized (CLM-013-44, answers RTE-09).** Work-level
  author names are normalized (name order) and deduplicated at ingestion, so
  polluted aggregates stop flowing into records and stage-2 authorship
  judgments.
- **Errors classified once; queries logged before execution (CLM-013-45,
  answers RTE-10).** Search-route and resolve-route failures classify through
  the same connector-layer code, and the query is logged before execution on
  both routes, so a raising call still leaves its `connector.query` record
  (with CLM-013-05, the log is complete on every path).

### Cross-cutting

- **Backward compatibility (CLM-013-46).** All frozen bundles — the Phase 5
  demo lineage, the Phase 7 bundle, the Spec 003 math-study bundle, the
  Spec 010 / OSF copies — and the deposited copies verify post-remediation to
  **identical verdicts**, measured the way Spec 011 measured it (the frozen
  set re-verified end-to-end, verdicts compared). Stricter verifiers must
  pass honest frozen records; legacy runs keep the operator-attested label
  path (CLM-013-03) rather than failing for events that did not exist when
  they ran.
- **The probe suites are the acceptance battery (CLM-013-47).** Every
  DEMONSTRATED attack in rt-a / rt-c / rt-d / rt-e within this spec's
  workstreams must fail post-remediation, and every HELD defense must still
  hold, measured by re-running the suites against the remediated build and by
  regression tests in the repo suite embodying each attack.

## Article XIV note — no UI appearance change is in this scope

Every WS-5 UI/console item is a security mechanic that does not alter layout
or appearance: hidden CSRF token fields, session/identity handling on POST,
role gates, validation refusals. Existing verbatim refusal texts do not change
wording (the F4 discipline); new refusals are behavior, recorded in the
assessment. Two boundary items are flagged, and both are handled by keeping
the change off the rendered surface:

1. **CLM-013-03's interim "operator-attested" label** applies to the bundle's
   HUMAN-README — a text artifact inside the audit bundle — not to any
   rendered UI. If the Phase 6 UI or the console ever renders fixture
   outcomes, presenting the label there **is** an appearance change and is
   out of scope here; it would need wireframes updated and owner approval
   first, per Article XIV.
2. **CLM-013-28's `recorded_by`** is an additive field in MCP tool output
   data, not a wireframed screen. Any later decision to display it on a
   wireframed surface follows Article XIV separately.

No other item in this spec touches a wireframed surface. If the build finds
one that does, it stops and flags it — it does not improvise UI changes under
a security charter.

## Non-goals — honest non-claims (what this spec does NOT fix)

- **T111 anchor transport** (axiomere): how checkpoint roots reach third
  parties. CLM-013-02 fixes the comparison logic on the Tekmerion side; the
  transport remains open, as recorded.
- **T112 payload encryption / erasure-certificate execution**: not addressed.
  Payloads remain plaintext in the current format; the DPA's
  specified-not-executable erasure dependency stands.
- **The axiomere core verification policy (WS-1)**: signature presence inside
  core verification, core checkpoint-root recomputation, trusted-map exposure
  in the Python bindings/CLI, snapshot-lineage validation on read, binding
  value strictness (Team B RTB-01…13; the core half of Team C p08). Sibling
  spec in the axiomere repos — this spec neither implements nor implies it,
  and CLM-013-46/47 are scoped so they do not claim it.
- **Trusted Publishing** for the wheel workflow, and its sibling release
  hygiene (RTE-11 core pinning in wheel builds, RTE-12 smoke-test depth,
  RTE-13 PyPI metadata, RTE-14 Actions SHA-pinning): separate authorized work
  in the axiomere-python repo and PyPI account, not this spec.
- **Public-record corrections** (RTE-15 vendor packet §2/§3/§9, RTE-16
  install.md, RTE-20/21 deposit metadata, RTE-22/23 record anchoring of spec
  bundles): documentation and record work under the papers/website currency
  rule, prepared separately; this build spec changes code behavior, and any
  public text whose truth depends on the new behavior is updated under that
  rule, not silently inside this build.
- **Live-IdP exercise**: no real Shibboleth/Entra SAML IdP, no live Entra/Okta
  SCIM client, and no live webhook receiver is exercised by this remediation.
  WS-4 is verified against the in-process mocks — the same stated limit as
  Spec 005, unchanged by this spec. Live PLATON and live statcheck (R)
  verification are likewise untouched, as is Spec 004 (Lean service).
- **OSF approval mechanics** (RTE-29) and **pilot governance** (RTE-31): the
  mailbox-as-trust-boundary and partner-adjudicator items are governance
  records for the pilot package, not code claims here.

## Risks carried into the build

- **Stricter verifiers vs frozen records** (CLM-013-01/02 vs CLM-013-46): the
  re-derivation and anchor-binding checks must pass every honest frozen
  bundle. The backward-compatibility measurement runs **before** merge, and a
  frozen bundle failing post-remediation is treated as a remediation defect,
  not a record defect, until proven otherwise.
- **Run issuance changes shape** (CLM-013-03): control-outcome ledger events
  are new event types; replay of pre-remediation runs must not reinterpret
  them, and Spec 011-style backward-compat replay covers this.
- **All-source resolution changes call patterns** (CLM-013-40): more connector
  calls per citation, now completely logged (CLM-013-05/45). Budget semantics
  are unchanged, but measured costs will move; the evaluation K5 accounting
  reads the now-complete log.
- **Platform gate tightening vs console flows** (WS-4/WS-5): step-up and
  signature requirements on every path must keep the E5 console's legitimate
  flows working; the console conformance captures are re-run as part of the
  battery (CLM-013-47), with appearance unchanged (Article XIV note).
