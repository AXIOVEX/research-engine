# Spec 012 — CORE Connector — tasks

Requirements source: owner directive 2026-10-12 ("Add CORE, this is
still needed"); WS1 registry (CORE = designed full-text content
channel); Spec 002 Phase 7 EVALUATION-REPORT §2.1/§2.3/§2.5/§4.5.

- [x] T0 Spec + claims bundle v0.1.0 + assessor run at after_specify
      (CLM-012-01…08 drafted; scores recorded as computed).
- [x] T1 Live shape probe: real v3 calls (key from the owner's env
      file at runtime only) — DOI route, field names, licence field,
      placeholder string, 401/404 shapes; sanitized shapes → fixtures.
- [x] T2 `CoreConnector` + `CoreApiError` in connectors.py: key gate,
      Bearer auth, budget reserve/settle, field mapping, licence
      capture + content-drop rule, NC flag, status translation
      (CLM-012-01, -03, -04, -05).
- [x] T3 Pipeline enrichment in verification._resolve: contentless
      primary → same-DOI candidates, agreement-gated, provenance in
      source/detail, failure non-fatal; primary order unchanged
      (CLM-012-06, -07).
- [x] T4 Assembly: MCP `_default_connectors` appends CORE when
      CORE_API_KEY is present (CLM-012-08).
- [x] T5 Tests: connector fixtures + pipeline tests incl. two-source
      DOI fold, enrichment fire/degrade/guard/no-fire, outage→ERROR
      (CLM-012-01…08). Full suite green.
- [x] T6 Live smoke through the built connector: 3 DOI resolves + 1
      search; outcomes + call count + what CORE added, recorded.
- [x] T7 Records: after_implement assessment + dated assessment
      record; DESIGN F4 dated correction; subprocessor inventory
      CORE entry activated with dated line.
- [x] T8 Commit, push, PR (no merge — coordinator's).
