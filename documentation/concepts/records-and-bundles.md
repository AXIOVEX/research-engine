# Records, bundles & anchors

## The record layer

Every study is a ledger in
[Axiomere](https://github.com/AXIOVEX/axiomere) (the record layer,
documented in its own repositories): a single `.axmr` file of
hash-chained, Ed25519-signed events — each event written in one fixed
format (its canonical encoding), chained with SHA-256 hashes,
with content-addressed snapshots and signed Merkle checkpoints. There is no
update and no delete, in the API or beneath it; a ledger that fails
verification refuses to open for appends. On its platform ledgers,
Tekmerion's service layer records timestamps to whole seconds only.

Corrections — to claims, citations, verdicts' inputs — are appends:
a superseding claim, an adjudication decision, a withdrawal with a
reason. Frozen artifacts and issued verdicts are never edited.

## The audit bundle

A study's standard output is an **audit bundle**: the registration,
the claim register, the evidence items with their origin groups, the
adjudication record, the verdicts with the run outcome stated
in-bundle, and the ledger itself — under a manifest with a bundle
hash. The bundle is verifiable **standalone**: the verifier consumes
only the bundle, replays the register, reproduces the verdicts, and
checks the projections against the ledger's events payload-for-payload
(the check whose absence the Phase 7 evaluation caught — see
[the evaluation](../evidence/phase7-evaluation.md)).

## External anchors

If only the operator can check a bundle, everyone else has to take
the operator's word for it — so bundles are anchored where the
operator does not control the record:

- **Zenodo** deposits (DOIs) for study bundles — the worked study,
  the Phase 7 evaluation, and the demonstration are all deposited.
- **OSF** registration (Spec 010): the demonstration study is
  publicly registered at [osf.io/84dk7](https://osf.io/84dk7/)
  (DOI 10.17605/OSF.IO/84DK7). The deposit code follows the same
  rules as the engine: a provider's error is passed through word for
  word, and a rate limit is a full stop, never something to push
  against with retries.

`verify_anchor` checks a bundle's carried receipt and registration
against the independently fetched public record. One precision the
records insist on: the anchor binds the deposited bundle version and
the freeze checkpoint root; a re-exported bundle carrying the receipt
is verifiable in contents and registration, but its own hash is
anchored nowhere: as a file it vouches for itself, and the record
says exactly that.
