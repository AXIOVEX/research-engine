# Self-Hosted Packaging — Spec 005 (T546)

The self-hosted deployment shape: a single-tenant deployment of
the same Tekmerion codebase, run inside the institution's own
boundary, under the same role model — the shape CLM-005-12 claims
and CLM-005-31's boundary names as the fully capable CUI path
while the hosted shape's DFARS 252.204-7012 equivalency question
stands open as an owner/legal decision.

## What ships

- **The same codebase.** `src/tekmerion/platform/packaging.py`
  defines the `DeploymentProfile` descriptor both shapes are
  described by; the parity battery
  (`tests/test_e6_packaging.py`) runs one scenario — bootstrap,
  tenant creation, IdP configuration, login, role grant, gated
  study append, audit export — against a hosted profile and a
  self-hosted profile and compares outcomes. The role model is
  compared by fingerprint (`role_model_fingerprint()`): two shapes
  run the same model iff the fingerprints match, and the battery
  asserts they do.
- **Its own data root.** A self-hosted deployment's ledgers live
  under its own root on the institution's storage. Nothing about
  the shape phones home: there is no telemetry path in the
  codebase, and the hosted deployment's ledgers never contain a
  self-hosted tenant's data — the battery asserts the absence of
  the self-hosted tenant's identifiers and payloads in the hosted
  deployment's record, not merely that the configuration intends
  it.
- **Recorded shape facts.** Shape, region (the residency pin,
  T541), custody mode, and signer reference are recorded
  configuration — the same records the hosted shape keeps.

## Institution KMS option

Key custody is the E1 seam (CLM-005-03/04): self-custody (the
identity holder's own key) or delegated custody, where signing is
performed by a signer the deployment designates *by reference*.
A self-hosted institution records its KMS/HSM-backed signer as
the delegated signer reference; the platform never holds the
institution's key material, and seeds never appear in a ledger,
config export, or this document's machinery. What exists is the
integration surface and the custody record — no specific cloud
KMS integration is built or claimed.

## Upgrade path

Install a newer signed release of the same codebase over the same
data root. Ledgers open in place — the Axiomere format is
versioned (`AXMR1`) and forward-readable — tenant configuration
is ledger state and survives, and each release's claims bundle
version is the compatibility record an operator checks before
upgrading. There is no migration tool because the format
discipline removes the need; a release that ever broke
forward-readability would be a claims event (a defect against
CLM-005-12's one-codebase claim), not a silent upgrade step.

## Honest limits

- The parity battery exercises the service layer in-process; it
  is not a packaged installer, a container image, or a load test.
  Packaging in the distribution sense (installers, images) is
  deployment work that follows a named institution's requirements.
- The self-hosted shape answers the *boundary* question (whose
  systems CUI rests on), not the FIPS question: §3.13.11's gap is
  a property of the cryptographic modules in both shapes
  (crypto-inventory.md), closed only by the recorded migration
  decision, with the institution's own validated boundary controls
  as the interim posture the matrix describes.
