# Spec 012 — Plan

## Sequence

1. **Claims first.** `aee-claims.json` v0.1.0 (8 claims, all draft) assessed
   at `after_specify` with the pinned assessor (engine 1.0.4, threshold
   0.70) before any implementation. Scores at this stage are expected low
   (asserted evidence only) and are recorded, not massaged.
2. **Live shape probe (read-only).** A handful of real CORE v3 calls with
   the owner's key loaded from `~/workspace/glossa-run/research-api-keys.env`
   at runtime (value never printed, logged, or committed): confirm the
   `/v3/works/doi:{doi}` route, the work-object field names (esp. the
   licence field and the fullText placeholder), and the 401/404/429 shapes.
   The probe's sanitized response shapes become the recorded fixtures.
3. **Connector.** `CoreConnector` + `CoreApiError` in
   `src/tekmerion/connectors.py`, mirroring `OpenAlexConnector`'s
   structure (key gate, budget reserve/settle, injectable `HttpJson`).
   `HttpJson` gains a `post`-free header path only as needed — v3 reads
   are GETs; the Bearer header rides the existing `headers` parameter.
   HTTP status awareness: `HttpJson.get` surfaces `urllib` HTTPError;
   the connector translates statuses per spec (404 → None on resolve;
   401/403/429/5xx → CoreApiError).
4. **Pipeline enrichment.** `verification._resolve` gains the enrichment
   pass described in spec.md (contentless primary → same-DOI candidates
   from the remaining connectors, agreement-gated, provenance in
   `source`/`detail`, failures non-fatal). `_run_stages` unchanged: it
   already stance-checks whatever record resolution returns.
5. **Assembly.** `mcp/server.py::_default_connectors` appends CORE when
   `CORE_API_KEY` is set.
6. **Tests** (`tests/test_core_connector.py`, recorded fixtures, no
   network, no key): parser + licence capture; content dropped without
   an asserted licence; fullText fallback + placeholder-as-absent;
   NC → hosted_ok False; key gate; budget reserve/exhaustion; 404 → None;
   401/429/5xx → CoreApiError; pipeline tests with stub connectors —
   two-source DOI fold to one origin group; enrichment fires (metadata-
   only primary + licensed CORE content → content verdict, source=core);
   enrichment licence-degradation (CORE content without licence → stays
   metadata_only); enrichment disagreement guard (disagreeing CORE
   candidate passed over); no-enrichment-when-content (content-bearing
   primary → CORE never called, outcomes unchanged); CORE-only citation
   during CORE outage → ERROR, not NOT_FOUND.
7. **Live smoke.** The built connector against the real API, key loaded
   at runtime only: resolve 3 DOIs (a Crossref-resolvable control; the
   Phase 7 metadata-only Schuch record 10.1016/j.jpsychires.2016.02.023;
   one further Phase 7 record) + 1 title search. Outcomes, call count,
   and *what CORE added* recorded in the dated assessment. If the API is
   unreachable from this VM, that is recorded honestly and the spec ships
   fixture-proven (no fabricated live result).
8. **Records.** Re-assess at `after_implement`; dated assessment record;
   DESIGN F4 dated correction note (owner scope change); subprocessor
   inventory CORE entry moved to active with a dated line. PR; the
   coordinator merges.

## Risks / open questions carried into the build

- The v3 licence field's exact name/shape is unverified until the probe
  (step 2). If v3 serves licence under a different key, the parser
  follows the probe's evidence, and the spec's mapping line is corrected
  in the assessment record (the rule — no asserted licence, no content —
  does not change).
- `/v3/works/doi:{doi}` may return a deposit record rather than the
  deduplicated work for DOIs held by many repositories; if the probe
  shows that, resolve falls back to the search route `q=doi:"…"` and
  picks the first candidate carrying licence-permitted content (else the
  first), with the choice recorded.
- The lexical stance checker on full text (when CORE serves fullText but
  no abstract) inherits Phase 7 §4.2's recorded brittleness — more text
  means more chances for a stray negated sentence to dominate. This spec
  does not fix the checker; the limitation is recorded as a boundary on
  CLM-012-07, and full text is used only when no abstract exists.
