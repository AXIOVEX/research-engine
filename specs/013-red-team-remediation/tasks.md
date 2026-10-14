# Spec 013 — Red-Team Remediation — tasks

Requirements source: owner directive 2026-10-13 ("Make a plan and execute
it now. Get all this done"); the 2026-10-13 red team engagement synthesis
and team records rt-a / rt-c / rt-d / rt-e. Claims precede code (Article
XII); the probe suites are the acceptance battery (CLM-013-47).

- [x] T0 Spec + claims bundle v0.1.0 + assessor run at after_specify
      (CLM-013-01…47 drafted; outcome iterate, 0 below the 0.70 threshold —
      recorded as computed in aee-assessment.json).
- [ ] T1 Battery port: in-scope rt-a / rt-c / rt-d / rt-e probes become repo
      regression tests, verified FAILING against the pre-fix code
      (CLM-013-47 groundwork; HELD defenses ported as must-stay-green).

WS-6 — connectors (Lane A; owns verification.py window 1)
- [ ] T2 Retraction state on RetrievedItem (Crossref updated-by, OpenAlex
      is_retracted) + quarantine + claim-record surfacing (CLM-013-36).
- [ ] T3 CORE error contract for Crossref/OpenAlex resolve (404 = the only
      not_found; 429/5xx/transport/budget -> ERROR) (CLM-013-37).
- [ ] T4 OpenAlex licence gate (no asserted licence -> metadata_only);
      Crossref licence qualification by content-version/delay/start
      (CLM-013-38, CLM-013-39).
- [ ] T5 All-source resolution with record comparison + disagreement
      quarantine; _enrich asserts candidate DOI identity in the pipeline
      (CLM-013-40, CLM-013-41).
- [ ] T6 One shared DOI normalizer across connectors + pipeline
      (CLM-013-42; intake call site lands with T14).
- [ ] T7 CORE degradation reason = output-cap-reached; CORE author
      normalization + dedupe at ingestion (CLM-013-43, CLM-013-44).
- [ ] T8 Single connector-layer error classification for search + resolve;
      connector.query logged before execution on both routes
      (CLM-013-45; study-path completeness with T18).

WS-3 — freeze & claims integrity (Lane B; owns verification.py window 2)
- [ ] T9 register() refuses any registration while frozen; second freeze
      only as a labeled amendment act; consumers bind to the first freeze
      unless an amendment exists (CLM-013-06, CLM-013-07).
- [ ] T10 Freeze mode validated in {confirmation, exploratory} at the
      freeze layer (CLM-013-08).
- [ ] T11 Fixture identities committed into the registration document;
      run/export refuse fixture mismatch; freeze gate rejects vacuous
      fixture controls (CLM-013-09, CLM-013-10).
- [ ] T12 Statement/falsifier immutable via re-registration at every
      status; changes only via supersedes (CLM-013-11).
- [ ] T13 Falsifier-naming exactness (DOI token / citation-shaped
      surname+year); stance checker negation parity with abstention
      (CLM-013-12, CLM-013-13).
- [ ] T14 DOI normalized once at citation intake; as-cited preserved as
      record only (CLM-013-14, with T6).

WS-2 — verification consumers (Lane D; claim 03/04/05 mechanics with Lane B)
- [ ] T15 verify_bundle re-derives every verdict from claims + evidence
      fold and requires equality with issued verdicts (CLM-013-01).
- [ ] T16 verify_anchor binds the presented bundle's own bundle_hash;
      per-export anchor receipts (CLM-013-02; frozen-set behavior per
      CLM-013-46).
- [ ] T17 Control outcomes appended as ledger events at issuance; bundle
      projection cross-checked payload-for-payload; pre-remediation runs
      labeled operator-attested in the bundle HUMAN-README (CLM-013-03).
- [ ] T18 Evaluation predictions committed (registration hash or
      pre-freeze ledger event); connector.query logged on every study
      path incl. workspace attach (CLM-013-04, CLM-013-05, with T8).

WS-4 — platform authority & seams (Lane C; Spec 005 amendments)
- [ ] T19 Verdict-class appends require enrolled-key intent signature +
      fresh step-up on every path; API key alone refused (CLM-013-15).
- [ ] T20 Admin-plane step-up required at the service layer; require-MFA
      policy enforced for admin mutations (CLM-013-16, CLM-013-17).
- [ ] T21 Step-up = server-issued single-use nonce challenge; auth_time
      recency checked (CLM-013-18).
- [ ] T22 Self-grant of adjudicator refused; plane separation evaluated
      with self as counterparty (CLM-013-19).
- [ ] T23 Revoked-key re-enrollment requires admin countersign for all
      roles; enrollment rejects small-order public keys (CLM-013-20,
      CLM-013-21).
- [ ] T24 Break-glass invoker roles checked in the target tenant's scope
      (CLM-013-22).
- [ ] T25 Every service-layer read requires an authenticated, authorized
      identity (CLM-013-23).
- [ ] T26 Legal-hold restriction consulted by every export path incl.
      break-glass audit export (CLM-013-24).
- [ ] T27 SPRS evidence links must resolve (exist + identify as claimed)
      (CLM-013-25).
- [ ] T28 create_tenant refuses duplicates at the service layer
      (CLM-013-26; closes the E5-recorded item).
- [ ] T29 Unknown-tenant failures rate-limited before any ledger append
      (CLM-013-27).

WS-5 — MCP & UI surfaces (Lane E; inherits T9/T10/T19–T21 gates)
- [x] T30 Lane-2 appends adjudicator-gated; recorded_by surfaced in
      projections; evidence_ref must resolve (CLM-013-28).
- [x] T31 Faithfulness pinning validated (claim exists, fields non-empty);
      re-pin adjudicator-only; pin history surfaced (CLM-013-29).
- [x] T32 Deposit approver != depositing actor refused; skill gains the
      operator-only approval rule (CLM-013-30).
- [x] T33 Phase 6 UI: per-session CSRF token on all POSTs; identity from
      session only on POST (CLM-013-31; no appearance change).
- [x] T34 Console: per-session CSRF tokens on state-changing POSTs
      (CLM-013-32; no appearance change).
- [x] T35 ingest_lean http/https only; adapter file paths confined to the
      workspace root (CLM-013-33).
- [x] T36 Second reviews validate a real decided item; reviewer !=
      decider; agrees strictly boolean (CLM-013-34).
- [x] T37 Surface hygiene: OSError -> SurfaceRefusal without absolute
      paths; empty GRIM refused; dead-claim run verdicts marked
      not-issued; confirmation freeze requires linked_exploratory
      explicitly (CLM-013-35).

Integration & records
- [ ] T38 Battery re-run: every in-scope DEMONSTRATED attack fails; every
      HELD defense still holds (incl. rt-c SAML/OIDC/SCIM batteries, rt-d
      role matrix); full repo suite green (CLM-013-47).
- [ ] T39 Backward-compatibility measurement over the frozen + deposited
      set, Spec 011-style, BEFORE merge (CLM-013-46). Console conformance
      captures re-run; BUILD_ID identity asserted; no wireframe delta.
- [ ] T40 Records: after_implement re-assessment + dated assessment in
      this package; dated qualification note + affected-claim
      re-assessment in specs/005-enterprise-platform/; CHANGELOG entry.
- [ ] T41 Commit, push, PR (no merge — coordinator's).
