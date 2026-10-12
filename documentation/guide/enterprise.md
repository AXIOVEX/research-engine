# Enterprise platform

Spec 005 extends Tekmerion from a single-operator engine to a platform
institutions can run — without diluting the record discipline the
engine exists for. Direction is recorded in design note DN-011;
deployment shapes are hosted multi-tenant and self-hosted
single-tenant, on one codebase and one role model.

## Identity: SSO that enrolls keys, not replaces them

- **OIDC and SAML 2.0, both.** Campus/cloud tenants authenticate
  through Entra ID or Google Workspace, using OIDC (the modern sign-in
  standard); the research/education federation world — Shibboleth
  identity providers, InCommon — speaks SAML 2.0, the federation
  sign-in standard. One protocol only would exclude half of higher
  education. Each tenant configures its own identity provider (IdP —
  the institution's sign-in service); SAML accepts signed assertions
  only, checked against the tenant's own federation record (its
  metadata trust anchor).
- **Identity binds to the signing key; it does not replace it.** Every
  append is an Ed25519-signed act by an actor. An IdP-authenticated
  identity (issuer + subject) is bound to a keypair by a recorded
  enrollment event with proof of possession; rotation and revocation
  are ledger events. There are **no local passwords** — session login
  proves who is at the keyboard; the key is what the record believes.
- **Provisioning is lifecycle.** SCIM 2.0 — the standard protocol by
  which an institution creates and removes accounts — plus
  just-in-time creation; deprovisioning ends the identity's
  ability to append or read, promptly — and deletes nothing.
  Deactivation and reactivation preserve the identity's history.
- **Break-glass, as a governed exception:** tenant-declared,
  dual-authorized, scope-restricted to administrative actions (never
  study powers), hard-capped at 4 hours, every use recorded in both
  the tenant ledger and the deployment security log, with a post-use
  review item created automatically.

## Authorization

The role matrix (WS6: researcher / reviewer / adjudicator /
integrity) plus two admin planes (tenant admin, platform admin) that
confer **no** study powers — enforced in the service layer,
deny-by-default, with cross-tenant and cross-plane refusals recorded
in the addressed tenant's ledger before the refusal is raised. A
control hidden in the user interface is presentation, never
enforcement. The admin console itself shipped only after its
wireframes were approved under the project's
wireframes-are-constitutional rule (Article XIV).

## Compliance posture — alignment, mapped, never overstated

- **CMMC Level 2 alignment / compliance support** against NIST SP
  800-171 Rev 2 (the federal rulebook for protecting sensitive
  unclassified information). CMMC — the Defense Department's
  cybersecurity certification program for its contractors — certifies
  *organizations and boundaries*, never products, and Tekmerion claims
  no product certification. All 110 requirements are classified in a
  responsibility matrix:
  **17 Platform / 51 Supports / 42 Organizational**.
- **Open gap, on the record:** §3.13.11 (FIPS-validated cryptography
  — cryptography validated under the federal FIPS program). The
  platform's cryptographic operations are inventoried (13
  operations, none FIPS-validated today) and the gap is carried on
  the formal list of known gaps and planned fixes (a POA&M — Plan of
  Action and Milestones) as item **POAM-0001**; migration waits until
  a real requirement to handle controlled unclassified information
  (CUI) names it — a recorded decision, not an oversight.
- **Supplier-risk self-score (SPRS): −156.** On the Defense
  Department's scoring method, an operator's score falls as
  requirements go unmet; the figure at the head of this item is what
  the matrix computes today. It is an output of the machinery, never
  evidence of quality,
  and there is deliberately no submission path in the product;
  submission is the operator's act.
- **SOC 2** (the standard audit framework for service providers):
  the platform ships a *readiness* mapping from criteria
  to machinery that exists. Readiness is not certification, and is
  never worded as such.
- **DFARS 252.204-7012** (the defense contract clause on protecting
  covered defense information; equivalency with FedRAMP Moderate —
  the federal cloud-security authorization program — for the hosted
  shape) is a **standing open owner/legal flag**; the self-hosted
  shape is the capable CUI path meanwhile.
- Custody honesty: the current delegated signer is a software
  development signer with seeds in process memory — **not a managed
  key service (KMS) or hardware security module (HSM)** —
  and the console labels it as such.

## Stated limits

No external identity provider has yet been exercised against the
platform (all protocol work is verified against simulated providers
run inside the test process — in-process mocks — and test batteries
that try every forbidden action and check that it is refused); no
live SCIM client (Entra/Okta) has been run; the audit export has not
been verified by an external auditor against a live deployment.
These are the records' own "not understood" statements, carried here
unchanged.
