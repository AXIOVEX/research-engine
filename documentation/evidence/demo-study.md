# The Phase 5 demonstration — an INVALID run, on the record

The first end-to-end demonstration (Spec 002, Phase 5) is the study
this project shows people who ask whether the machinery can fail
*itself*.

A small demo study was built through the production paths with live
Crossref: the real 1905 Einstein citation resolved and was judged a
translated-title *variant* — the same work under a translated title,
with the catalogue record as the only evidence (metadata-only, no
full text); a fabricated DOI returned not-found and was judged
*exclude*. The study froze at
Merkle checkpoint root
`7434209696ea39ba8e97a33b5caa0ae08928269ea81c7d6407f423191e86e317`,
its audit bundle was exported, verified standalone, and deposited to
Zenodo: [DOI 10.5281/zenodo.23311479](https://doi.org/10.5281/zenodo.23311479).

**The run itself was INVALID, and issued no verdicts.**

The defect: the study was single-actor, and the swap control's
fixed lines-1/2 actor exchange exchanged two events by the same actor
— a no-op the verifier correctly treated as an intact chain. A control
that cannot fail is a failed control, so the run was invalid by the
engine's own rules. The deposited record says exactly that.

## What happened next — append-only, as designed

- The Zenodo v1 description, drafted expecting a different outcome,
  was corrected in place (metadata only, same DOI) to state INVALID
  with an explicit correction note. The original text was public for
  an interval before the correction; that interval cannot be
  unpublished, and the audit says so.
- The control's event selection was fixed as Phase 7 preparation (it
  now exchanges the first distinct-actor pair); the historical
  INVALID stands as issued — the fixed control detects the swap on
  the demo ledger, and the demo verdict does not change.
- The stage-model audit appended stage-assignment events to the demo ledger
  (new checkpoint root `52e08f7a…7223`): the demo claim stands at
  *checked* (metadata level only), the run at "invalid — no stage
  earned", and the anchor demonstration at *accepted* — the one stage
  earned by a human act, the owner's formal go-ahead for the anchor
  demonstration (gate G2, recorded in DN-008).
- The anchored v1/v2 bundles carry no run-outcome statement of their
  own — a limitation of the frozen artifacts, labelled as such, and
  since fixed in the exporter (bundles now state their run outcome
  in-bundle).
