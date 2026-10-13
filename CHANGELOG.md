# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-13

Initial public release. Published to PyPI on 2026-10-13; the git tag `v0.1.0` marks the exact commit the published files were built from (e545ad5).

### Added

- Claim registration where every claim must carry a falsifier — the test that would show it is wrong — before it can be registered.
- Citation checking through Crossref, OpenAlex, and CORE, with the licence for each record recorded alongside it.
- Study freezing, adjudication, and pre-registered evaluation checks, so verdict rules and predictions are fixed before results are seen.
- Signed, append-only audit bundles that can be verified on their own, without the engine.
- Deposit of study records to OSF and Zenodo.
- An MCP server with 29 tools, plus an agent skill, so other programs can run studies end to end.
- Domain adapters — crystallography validation (checkCIF/PLATON scope), reproducibility certification (CODECHECK), and statistical-consistency checking (GRIM/statcheck) — each with a registered statement of what its check cannot establish.
- The enterprise platform: sign-in by OIDC and SAML, SCIM provisioning, role-based access, multi-tenancy, break-glass emergency access that requires a second authorizer, and compliance evidence including the CMMC responsibility matrix and the POA&M register.
- Public worked studies: the Phase 7 evaluation and the mathematics-claims study, both frozen before they ran and deposited with their records.

### Fixed

- The evaluation caught a verifier defect that compared only verdict counts, which let a rehashed verdict-flip pass as unchanged. Fixed with full payload comparison and a regression test, before the frozen evaluation run.
