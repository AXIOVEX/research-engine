# Enterprise platform

Spec 005 extends Tekmerion from a single-operator engine to a platform
institutions can run — without diluting the record discipline the
engine exists for. Direction is recorded in design note DN-011;
deployment shapes are hosted multi-tenant and self-hosted
single-tenant, on one codebase and one role model.

## Identity: SSO that enrolls keys, not replaces them

- **OIDC and SAML 2.0, both.** Campus/cloud tenants authenticate
  through Entra ID or Google Workspace (OIDC); the research/education
  federation world — Shibboleth IdPs, InCommon — speaks SAML 2.0. One
  protocol only would exclude half of higher education. Per-tenant IdP
  configuration; SAML accepts signed assertions only, against the
  tenant's metadata trust anchor.
- **Identity binds to the signing key; it does not replace it.** Every
  append is an Ed25519-signed act by an actor. An IdP-authenticated
  identity (issuer + subject) is bound to a keypair by a recorded
  enrollment event with proof of possession; rotation and revocation
  are ledger events. There are **no local passwords** — session login
  proves who is at the keyboard; the key is what the record believes.
- **Provisioning is lifecycle.** SCIM 2.0 provisioning/deprovisioning
  plus just-in-time creation; deprovisioning ends the identity's
  ability to append or read, promptly — and deletes nothing.
  Deactivation and reactivation preserve the identity's history.
- **Break-glass, as a governed exception:** tenant-declared,
  dual-authorized, scope-restricted to administrative actions (never
  study powers), hard-capped at 4 hours, every use recorded in both
  the tenant ledger and the deployment security log, with a post-use
  review item created automatically.

## Authorization

The WS6 role matrix (researcher / reviewer / adjudicator / integrity)
plus two admin planes (tenant admin, platform admin) that confer **no**
study powers — enforced in the service layer, deny-by-default, with
cross-tenant and cross-plane refusals recorded in the addressed
tenant's ledger before the refusal is raised. UI-hidden affordances
are presentation, never enforcement. The admin console itself shipped
only after its wireframes were approved under the project's
wireframes-are-constitutional rule (Article XIV).

## Compliance posture — alignment, mapped, never overstated

- **CMMC Level 2 alignment / compliance support** against NIST SP
  800-171 Rev 2. CMMC certifies *organizations and boundaries*, never
  products, and Tekmerion claims no product certification. All 110
  requirements are classified in a responsibility matrix:
  **17 Platform / 51 Supports / 42 Organizational**.
- **Open gap, on the record:** §3.13.11 (FIPS-validated cryptography).
  The platform's cryptographic operations are inventoried (13
  operations, none FIPS-validated today) and the gap is carried as
  POA&M item **POAM-0001**; migration waits for a named CUI/defense
  requirement — a recorded decision, not an oversight.
- **SPRS self-score: −156** — an output of the machinery from the
  matrix, never evidence of quality, and there is deliberately no
  submission path in the product; submission is the operator's act.
- **SOC 2:** the platform ships a *readiness* mapping from criteria
  to machinery that exists. Readiness is not certification, and is
  never worded as such.
- **DFARS 252.204-7012** (FedRAMP Moderate equivalency for the hosted
  shape) is a **standing open owner/legal flag**; the self-hosted
  shape is the capable CUI path meanwhile.
- Custody honesty: the current delegated signer is a software
  development signer with seeds in process memory — **not KMS/HSM** —
  and the console labels it as such.

## Stated limits

No external identity provider has yet been exercised against the
platform (all protocol work is verified against in-process mocks and
refusal batteries); no live SCIM client (Entra/Okta) has been run;
the audit export has not been verified by an external auditor against
a live deployment. These are the records' own "not understood"
statements, carried here unchanged.
