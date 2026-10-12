# Spec 009 — Close-out record: CLM-009-09 decided (2026-10-12)

**Bundle**: `aee-claims.json` v0.3.0. **Assessment**:
`aee-assessment-after-implement.json` regenerated with the pinned
assessor (AEE engine 1.0.4, threshold 0.70, phase after_implement).
Result: **0 of 12 claims below threshold**; CLM-009-09 confidence
**0.999**, status `supported`, lifecycle stage `checked`. Bundle
outcome remains `iterate` (29 failure modes stand across the bundle,
as at build exit; the outcome is reported as computed, not rounded
up). Previously (build exit): CLM-009-09 draft at 0.481, held by
design — its falsifier was the coordinator's skill-only run.

## The deciding evidence

CLM-009-09 is a prediction: the agent skill suffices for an operator
with only the skill to complete the documented flow. It was tested
by three coordinator runs from the main environment, using only the
installed skill + the MCP tool schemas, against the clean-room
installed server. Drivers and full transcripts are committed as this
claim's evidence (`exercise/drive*.py`, `exercise/transcript*.jsonl`).

- **Run 1** (pre-fix build): F-009-9 **fired**. The skill's step 6
  controls guidance contradicted the shipped freeze (RT-6 refusal);
  the run then exposed F1 (exploratory re-moding issuing unexportable
  verdicts) and the falsifier-omission error shape (F3). Claim held.
- **Run 2** (post F1/F2/F3 fixes): the wall, the freeze, the schema
  refusal shape, the deposit gate, and export + standalone verify all
  behaved as documented on the wire. The run was INVALID for one
  reason: the coordinator's one-origin-group positive-control
  fixture verdicted inconclusive (G1), and live resolution failed
  under a stripped server environment the skill said nothing about
  (G2). Claim held; skill amended (worked controls example +
  same-machinery note; Configuration egress note).
- **Run 3** (deciding run, amended skill, full inherited
  environment, the skill's worked controls example verbatim):
  **completed end-to-end.** Both falsifier-omission shapes refused
  as documented — the empty falsifier produced the engine's Article
  II refusal *verbatim on the wire* (`CLM-Z-000: no falsifier — not
  registered (Article II)`, nothing appended); the F1 wall refused
  the unfrozen run with the WS3 §4 reason and issued nothing; the
  real DOI resolved live (`resolved`, `metadata_only`, title
  mismatch flagged honestly — an as-cited umlaut transliteration);
  the fabricated DOI returned `not_found` and was excluded; freeze
  succeeded first attempt; the run was **VALID** with verdicts
  issued and read back (both study claims INCONCLUSIVE on the
  record as it stands — the machinery's answers, reported as
  issued); the deposit gate refused in its documented shape; the
  bundle exported and **verified standalone** (bundle hash
  `f707f885…`, ledger verify ok, 12 events, chain intact).

## Judgment notes (recorded, not laundered)

- Run 3's one divergence from the skill's finer guidance was the
  operator's, not the skill's: the title-transliteration quarantine
  was *excluded* by the exercise script's blanket fallback where the
  skill offers `variant`. Both paths are documented; the outcome
  was unaffected (metadata-only evidence carries zero verdict mass).
- Playbooks B (adapters) and C (math/Lean) were exercised in the
  builders' clean-room acceptance (21/21, twice) rather than in the
  coordinator's runs; the claim's boundary states this.
- F4 (see acceptance addendum) stands as the program's reminder
  that records are claims: the branch's committed state, not its
  paperwork, is what the coordinator's runs actually tested — and
  runs 2–3 ran against the restored, committed code.

**Disposition**: CLM-009-09 moves draft → supported, created →
checked, on the evidence above. Spec 009 is complete: 12/12 claims
supported/checked. Remaining owner decisions (unchanged): PyPI
publication; hosted/streamable-HTTP MCP; cross-session adapter
evidence replay.
