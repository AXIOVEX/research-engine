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
| `phase5-demo/bundle-v4/` (15 files) | The Phase 5 bundle exported after the version 2 deposit's receipt was recorded in the ledger — both deposit receipts are inside it (`anchors/00-zenodo.json`, `anchors/01-zenodo.json`). Deposited 2026-10-13 (red-team follow-up RTE-23) so the study's current head state is public, not only a local working copy. | Zenodo version 3, DOI [10.5281/zenodo.23355310](https://doi.org/10.5281/zenodo.23355310) |
| `math-study/bundle-v1/` (13 files) | The Spec 003 worked study of contested 2026 AI-mathematics claims — verdicts as issued: two CONTESTED, two INCONCLUSIVE, one SUPPORTED. | Zenodo, DOI [10.5281/zenodo.23317259](https://doi.org/10.5281/zenodo.23317259) |

Each bundle carries its own `manifest.json`, which lists the SHA-256 of every
file in it; every file in the copies above was checked against its manifest
when they were committed (55 files, all matching), and the copies were diffed
byte-for-byte against the working copies they came from. The deposited zip
files' own hashes are recorded in the anchor receipts (`anchors/`) inside the
later bundles.

Not included: the working exports that were never deposited (Phase 5
`bundle-v2`; math study `bundle-v2`). Those are intermediate states of the
same records — each deposited bundle's ledger already carries the history up
to its own freeze, and the anchor receipts inside the bundles name the
deposits they belong to.

One state is deliberately not a bundle yet: the receipt for the Phase 5
version 3 deposit is recorded in the study ledger (event 21, appended
2026-10-13), but no `bundle-v5` has been exported. The current exporter
stamps a fresh replay outcome into `verdicts.json` for a study of this
vintage, and that replay — run without the original control fixtures —
reports the run as invalid with zero verdicts issued, which would misstate
this study's issued record. The export waits on that exporter fix rather
than shipping a bundle that says the wrong thing; the ledger event is the
record in the meantime.
