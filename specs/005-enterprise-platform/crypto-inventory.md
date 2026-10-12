# Cryptographic Inventory — Platform Plane (Spec 005, T549)

Produced at E1 under the CMMC amendment (§13.3). Purpose: make the
FIPS boundary explicit — every cryptographic operation the platform
performs, with its implementing module and its validation status, so
the §3.13.11 gap is a list, not an impression. **No entry in this
inventory is a FIPS-validated module today.** The §3.13.11 matrix row
stays "Supports — OPEN GAP" until an entry that protects CUI changes
its status on evidence.

| # | Operation | Where | Algorithm | Implementation | FIPS 140-3 validated? |
|---|---|---|---|---|---|
| 1 | Ledger hash chain (integrity) | Axiomere core (record layer) | SHA-256 | Rust `sha2` crate | **No** |
| 2 | Ledger append signatures | Axiomere core | Ed25519 | Rust `ed25519-dalek` | **No** |
| 3 | Ledger checkpoints (Merkle) | Axiomere core | SHA-256 | Rust `sha2` crate | **No** |
| 4 | Actor key derivation, intent signing, gate verification | Platform service layer (`platform/ed25519.py`) | Ed25519 (RFC 8032) | Pure-Python implementation in this repo — prototype-grade, correctness cross-checked against #2's key derivation in tests | **No** |
| 5 | Delegated-custody signing (dev signer) | Platform service layer (`platform/keys.py`) | Ed25519 (RFC 8032) | Same module as #4; seeds held in process memory — stands in for KMS/HSM, is not one | **No** |
| 6 | OIDC ID-token signature verification | Platform service layer (`platform/oidc.py`) | RS256 (RSASSA-PKCS1-v1_5 + SHA-256), verify-only | Pure-Python modular arithmetic in this repo | **No** |
| 7 | PKCE (S256) challenge/verifier | Platform service layer | SHA-256 | Python `hashlib` (OpenSSL-backed, not in FIPS mode) | **No** |
| 8 | API-key secret hashing at rest | Platform service layer | SHA-256 | Python `hashlib` | **No** |
| 9 | Key fingerprints | Platform service layer | SHA-256 | Python `hashlib` | **No** |
| 10 | Session tokens, enrollment nonces, API secrets (generation) | Platform service layer | CSPRNG output | Python `secrets` (OS entropy) | Not a module-validation question; listed for completeness |
| 11 | TLS to IdP endpoints | Platform runtime | TLS 1.2+ | Python `urllib`/OpenSSL as deployed | Deployment-dependent; **no claim** |
| 12 | SAML assertion/response signature verification (E2) | Platform service layer (`platform/saml.py`, `platform/xmlc14n.py`, `platform/x509.py`) | XML-DSig: RSA PKCS#1 v1.5 + SHA-256 (verify-only), SHA-256 reference digests, exclusive C14N | Pure-Python in this repo — the RS256 verifier is #6's; the canonicalizer and X.509 key extraction are new in E2, prototype-grade | **No** |
| 13 | Webhook egress payload signing (E4) | Platform service layer (`platform/webhooks.py`) | HMAC-SHA256 over `timestamp + "." + body` | Python `hmac`/`hashlib` (OpenSSL-backed, not in FIPS mode) | **No** |

**E3 note (2026-10-12):** E3 adds SCIM provisioning credentials (per-tenant Bearer secrets). Their generation uses the row-10 CSPRNG and their at-rest hashing is row 8’s operation (SHA-256 via the existing `hash_api_secret`, the same function that hashes API-key secrets) — no new algorithm, implementation, or operation class was introduced, so no new row is added. Credential IDs and secret hashes are what ledgers record; secret material never appears in a ledger, config, or SCIM resource.

**E4 note (2026-10-12):** E4 adds webhook egress signing, which gains row 13 (HMAC-SHA256). The Ed25519 egress signing mode is row 4's implementation (same module, `platform/ed25519.py`) and gains no row. Break-glass, rate limiting, and the T554 detectors introduce no new cryptographic operation: session ids and delivery ids are row-10 CSPRNG output, egress-secret generation is row 10, and subscription records carry row 9 fingerprints — secret material never appears in a ledger, config, or delivery record.

**E6 note (2026-10-12):** E6 adds no new cryptographic operation and no new row. The audit export's manifest/file hashing and the SPRS seed-set hash are row 9's operation (SHA-256 via Python `hashlib`); the checkpoints an export binds are produced by the ledger's existing machinery (rows 1–3); the export verifier introduces no cryptography of its own. Marking, holds, POA&M, and control-state machinery are record-keeping over existing operations. The §3.13.11 gap is unchanged — all 13 rows still report **No** — and it is now also carried as POA&M item POAM-0001 in the deployment register (T553).

## Reading this table

- Rows 1–3 are the **Axiomere dependency**: closing them is a
  cross-repo decision (DN-011, CMMC amendment §13.3) — validated
  Rust crypto (e.g. an AWS-LC-based route) or a boundary redesign
  that places a validated module around the record layer. Not
  Tekmerion's unilateral roadmap to commit.
- Rows 4–9 are **Tekmerion's own surface**: the platform services can
  adopt a validated module (e.g. an OpenSSL FIPS provider route)
  without touching the record layer. That substitution is the first
  FIPS work item when the CMMC track is scheduled; until then these
  rows are the honest gap.
- **Operational consequence, stated plainly:** a deployment that must
  satisfy §3.13.11 for CUI today cannot point at any row of this
  table. That is the platform's recorded position — the self-hosted
  shape inside an existing compliant boundary, with CUI encrypted by
  that boundary's validated modules at the storage/transport layers,
  is the interim posture the matrix (3.13.11, "Supports") describes.

Updated when: any row's implementation changes, a custody provider
(KMS/HSM) integrates, or the Axiomere dependency's status changes.
Owner of the update: the phase that makes the change.
