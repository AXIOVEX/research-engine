# Records, bundles & anchors

## The record layer

Every study is a ledger in
[Axiomere](https://github.com/AXIOVEX/axiomere) (the record layer,
documented in its own repositories): a single `.axmr` file of hash-chained,
Ed25519-signed events — SHA-256 chain over canonical event encodings,
content-addressed snapshots, signed Merkle checkpoints. There is no
update and no delete, in the API or beneath it; a ledger that fails
verification refuses to open for appends. Tekmerion's service layer
adds a whole-second-timestamp discipline on its platform ledgers.

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

A bundle that only its operator can check is a sole-copy claim, so
bundles are anchored where the operator does not control the record:

- **Zenodo** deposits (DOIs) for study bundles — the worked study,
  the Phase 7 evaluation, and the demonstration are all deposited.
- **OSF** registration (Spec 010): the demonstration study is
  publicly registered at [osf.io/84dk7](https://osf.io/84dk7/)
  (DOI 10.17605/OSF.IO/84DK7), with the deposit transport built to
  the same refusal discipline (provider errors verbatim, rate limits
  are a stop, never a retry storm).

`verify_anchor` checks a bundle's carried receipt and registration
against the independently fetched public record. One precision the
records insist on: the anchor binds the deposited bundle version and
the freeze checkpoint root; a re-exported bundle carrying the receipt
is verifiable in contents and registration, but its own hash is
anchored nowhere — self-attested as an artifact, and stated as such.
