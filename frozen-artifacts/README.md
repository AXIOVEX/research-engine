# Frozen artifacts

The directories here are **frozen records**: byte-identical copies of study
audit bundles exactly as they were deposited with Zenodo. Do not edit anything
in them — a changed file would no longer be the deposit it claims to copy.
Corrections in this program are new records and new deposits, never edits to
frozen ones.

Until 2026-10-13 these bundles existed only in local working directories, so a
clone-only auditor could not reproduce the deposited comparisons from this
repository alone (red-team follow-up RTE-22). They are committed here so the
record is complete in one place.

## What is here

| Directory | What it is | Public deposit |
|---|---|---|
| `phase5-demo/bundle-v1/` (13 files) | The Phase 5 demonstration study's first audit bundle. Its evaluation run was later judged **INVALID** — a control in the run could not fail — and that judgment stands on the record; the bundle is kept exactly as deposited. | Zenodo, DOI [10.5281/zenodo.23311479](https://doi.org/10.5281/zenodo.23311479) |
| `phase5-demo/bundle-v3/` (14 files) | The corrected Phase 5 bundle: the same study record with the stage-model audit corrections appended to its ledger. | Zenodo version 2, DOI [10.5281/zenodo.23317023](https://doi.org/10.5281/zenodo.23317023) |
| `math-study/bundle-v1/` (13 files) | The Spec 003 worked study of contested 2026 AI-mathematics claims — verdicts as issued: two CONTESTED, two INCONCLUSIVE, one SUPPORTED. | Zenodo, DOI [10.5281/zenodo.23317259](https://doi.org/10.5281/zenodo.23317259) |

Each bundle carries its own `manifest.json`, which lists the SHA-256 of every
file in it; every file in the copies above was checked against its manifest
when they were committed (40 files, all matching), and the copies were diffed
byte-for-byte against the working copies they came from. The deposited zip
files' own hashes are recorded in the anchor receipts (`anchors/`) inside the
later bundles.

Not included: the working exports that were never deposited (Phase 5
`bundle-v2` and `bundle-v4`; math study `bundle-v2`). Those are intermediate
states of the same records — each deposited bundle's ledger already carries
the history up to its own freeze, and the anchor receipts inside the bundles
name the deposits they belong to.
