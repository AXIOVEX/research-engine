# WS6 — Product Shape

**Status:** Draft v0.1, 2026-10-11 · Governs: OD-1, OD-2 · Constitution: Articles I, IX

## 1. Who does what

| Role | Does | Never does |
|------|------|------------|
| **Researcher** | Frames questions, drafts claims/falsifiers, runs exploratory work, drafts registrations | Sign off their own institutional verdicts alone |
| **Reviewer / screener** | Screens evidence, resolves grouping disputes, performs extraction where automation is unsuitable | Alter a frozen registration |
| **Adjudicator** | Approves freezes, resolves quarantines, signs verdict sets, approves deposits | Edit the record (their decisions are appended events, not edits) |
| **Integrity officer** (read-mostly) | Audits any bundle, replays runs, inspects full history | Participate silently — inspection access is itself logged |
| **System** | Retrieval, dedup, grouping proposals, verification pipeline, weighing, replay, export | Issue an unsigned institutional verdict; promote exploratory results; hide an INVALID run |

The interface is **register-first**: the home object is the *study* (registration → claims → evidence → verdicts → bundle), not a chat box. A conversational assistant may help draft claims and falsifiers, but it operates *on* register objects, and everything it proposes enters as a proposal a human or a freeze check accepts. This is the deliberate inversion of incumbent tools, where chat is the product and the record is an afterthought.

## 2. API sketch

The engine is API-first (the UI is one client):

- `POST /studies` · `POST /studies/{id}/registrations` (draft) · `POST /registrations/{id}/freeze`
- `POST /registrations/{id}/runs` · `GET /studies/{id}/claims` · `GET /claims/{id}` (full provenance walk)
- `POST /runs/{id}/replay` · `POST /studies/{id}/exports` (bundle) · `POST /exports/{id}/deposit`
- `GET /verify?bundle=…` — standalone bundle verification (chain + manifest), usable without an account

Every mutating call appends events (WS4); there is no update-in-place endpoint for record objects.

## 3. Deployment shapes (OD-2 — RATIFIED 2026-10-11, DN-003: hybrid, hosted-first pilot)

| Shape | Fits | Trade-offs |
|-------|------|------------|
| **Hosted (Axiovex-operated)** | Small programs, pilots, cross-institution reviews | Fastest to adopt; institutions must trust Axiovex custody of records — mitigated by export-anytime bundles and hash anchoring, so custody is verifiable rather than blind |
| **Institution-local** | Integrity offices, sensitive/unpublished corpora (OQ-5.2) | Strongest data control; heavier IT lift; updates and connector keys are the institution's |
| **Hybrid** (local record store, hosted connectors/verification) | Most universities, long-term | Record never leaves campus; verification and discovery use shared services |

**Recommendation — RATIFIED (DN-003):** design for hybrid from the start — the record store and the connector layer are separate deployables precisely so custody of the record can sit with the institution. Hosted-first for the pilot (speed of learning), with the bundle export guaranteeing no lock-in: an institution can leave with a complete, verifiable record. That exit guarantee is a feature of the defensibility pitch, not a concession.

## 4. MVP slice (OD-1 — proposed in spec 001 §6)

One workflow, complete: a systematic-review-style evidence question for a research team (U2):

registration → Crossref + OpenAlex retrieval → claim register → origin-grouped evidence → per-claim verdicts with controls → adjudicator sign-off → OSF/Zenodo-depositable audit bundle.

Everything else — other audiences' workflows, additional connectors, cross-study dependencies (OQ-2.2) — is explicitly later. Kill criteria K1–K5 (spec 001 §6) govern the slice's evaluation run, which is itself a frozen registration inside the engine: the product's first study is the evaluation of the product.

## 5. What success looks like, honestly stated

Not adoption numbers (none exist; Article X). Success for the design phase is SC-1..SC-4 in spec 001. Success for the MVP is surviving its own kill criteria under a frozen evaluation — including the possibility that it does not, recorded the same way.

## Appendix — competitor gap (researched 2026-10-11, sources linked)

Method/competitor references studied, not integrated. Summary of the researched analysis; the load-bearing facts carry their sources.

| Tool | Citation basis | Support-check? | Protocol freeze / replay | Core documented risk |
|------|---------------|----------------|--------------------------|----------------------|
| **Scite** | Extracted from full text; classifies citing sentences supporting/contrasting/mentioning; flags retractions | Intent only | No | Independent evaluation found low recall for supporting/contrasting classes — most citations default to "mentioning," so a missing "contrasting" flag is weak evidence ([Hypothesis journal evaluation](https://journals.indianapolis.iu.edu/index.php/hypothesis/article/download/26528/25101)); its own paper concedes ~30% of PDF citation statements missed in ingestion |
| **Elicit** | Retrieved (Semantic Scholar) + model extraction into tables | Passage link; human must click | **No — and search is non-repeatable:** the same search run three times returned materially different result sets in a *BMC Medical Research Methodology* study ([Bernard et al. 2025](https://link.springer.com/article/10.1186/s12874-025-02528-y)) | Extraction accuracy 51.4% in a PRISMA-reproduction study (Meliante et al.); criteria editable mid-run with no amendment log; model version not pinned in exports |
| **Consensus** | Retrieved, corpus-only | No (claim↔paper, not clause↔passage) | No | The Consensus Meter is **vote counting** — no quality weighting, effect-size pooling, or bias adjustment; a pile of small weak studies outvotes one large rigorous one |
| **Undermind** | Retrieved, iterative agent | Relevance rationale only | No — adaptive search is path-dependent by design | Opaque stopping rule; the completeness estimate is a model output, not a recountable denominator; headline performance claims are vendor claims without a public pre-registered benchmark |
| **OpenAI Deep Research** | Retrieved web + generated synthesis | No post-draft re-verification | No | ~3.5% invented links in one large URL-validity comparison; output is a report, not a replayable dossier |
| **Gemini Deep Research** | Retrieved web + generated synthesis | No | Editable plan approval — the closest any incumbent gets to pre-registration, but not timestamp-locked, hashed, or deviation-logged | Highest invented-link rate in comparative testing (~13.3%) |
| **Perplexity** | Retrieved web, inline footnotes | No | No | Columbia Tow Center: failed 37% of citation tasks — *best in class* in a field failing >60% overall; a 2026 audit found ~1 in 3 references not backing the numbers attached to them; under forced non-retrieval its model fabricated citation markers in 35.3% of rounds instead of abstaining |

**The gap, stated once:** incumbents optimize speed, coverage, or narrative. None offers a frozen, hash-locked protocol bound to execution; claim-level falsifiers with a verdict taxonomy that can abstain; post-draft support verification (WS5's stage 3); an append-only audit bundle with excluded-with-reasons as the *primary* output; replay-and-diff of past verdicts (including retraction surveillance of delivered dossiers — Scite's manuscript-level Reference Check is the only incumbent feature that touches retraction at all); contradiction adjudicated on the record rather than vote-counted; or logged human sign-off. That bundle — not a better summary — is this product.
