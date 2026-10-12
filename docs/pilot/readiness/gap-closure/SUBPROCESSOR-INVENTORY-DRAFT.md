# Subprocessor Inventory — Tekmerion (DRAFT)

**DRAFT — for owner review — not yet adopted.** This inventory is versioned; the
change-notification process in §3 takes effect on adoption.
**Adoption (2026-10-12):** adopted as an Axiovex working document by owner
ratification, 2026-10-12 — the §3 change-notification process is therefore in
effect as a working process from that date. **Counsel review is required before
execution with any partner.** The header above stands as this document's
drafting provenance; adoption changes nothing substantive in the text.
**Date:** 2026-10-12 · **Version:** 0.1 (first inventory) ·
**Closes:** HECVAT register item 4 · **Sources:** `src/tekmerion/connectors.py`,
`src/tekmerion/deposit.py`, `src/tekmerion/osf_deposit.py`, `.github/workflows/ci.yml`,
`docs/pilot/DESIGN.md` (§2.2 F4, §5.4), `docs/architecture/01-source-layer.md`.
Rule applied throughout: a service is listed only if the *shipped* code or the
operated process actually sends it data today. Designed-but-unshipped channels are
in §4, explicitly not subprocessors yet.

---

## 1. The inventory

| # | Subprocessor | Function in the stack | What data it touches | Notes from the records |
|---|---|---|---|---|
| 1 | **GitHub, Inc.** | Source hosting and CI for the three public repositories (tekmerion, axiomere, axiomere-python) | Source code, specifications, claim/assessment records, and Axiovex's **own** published study records committed to the public repo; CI build/test execution | The repositories are public by design. **Partner pilot data is not committed to GitHub** — partner study data lives in the tenant deployment and in partner-directed registry anchors only (§2). CI checks out the Axiomere repo to build bindings; no partner data is present in CI |
| 2 | **Zenodo** (operated by CERN) | Public deposit and anchoring of audit bundles | Deposited audit bundles: ledger bytes, registration, claims, evidence, verdicts, manifest — for Axiovex's own studies, public. For partner studies: only content with a recorded licence basis, in the least-public form the anchor allows, absent written partner direction (DESIGN §5.4) | Deposits are effectively immutable (changes = new versions); deposit approval is a named-human act gated in the machinery, never a configuration default |
| 3 | **OSF — Open Science Framework** (Center for Open Science) | Registration anchoring (registry snapshot of a deposited project) | Same bundle content class as Zenodo, as an OSF project + registration stating the bundle's anchor values; partner content under embargo/private terms by default (DESIGN §5.4) | Demonstrated live on an Axiovex study (registration 84dk7, DOI 10.17605/OSF.IO/84DK7; Spec 010 records) |
| 4 | **Crossref** | Scholarly metadata API (citation resolution and search) | **Queries only:** DOIs and bibliographic search terms for published literature; the polite-pool contact `research@axiovexsystems.com` in the User-Agent/mailto. Responses are publisher-supplied metadata, stored under per-work licence basis (abstracts are *not* assumed CC0) | No partner personal data is sent. No account or key is required for the access used |
| 5 | **OpenAlex** (OurResearch) | Scholarly graph API (works/concepts, origin tracing) | **Queries only:** search terms and work/DOI identifiers for published literature | No partner personal data is sent. Access uses a free API key on an Axiovex account; the key is a credential, never data shared |
| 6 | **CORE** (core.ac.uk) | Full-text content channel (WS1; Spec 012): citation content enrichment — records metadata-only at Crossref/OpenAlex can become content-checkable from repository deposits | **Queries + deposited-content lookups:** DOIs and bibliographic search terms for published literature; per-deposit record lookups. Returned content is stored only where the record's per-deposit licence basis permits (Spec 012 licence discipline) | Added 2026-10-12 (Spec 012, owner directive of the same date). No partner personal data is sent. Access uses a free registered API key on an Axiovex account; the key is a credential, never data shared. CORE receives **no deposits** from Tekmerion — it is a read-only content source, not an anchor |

**Personal data summary.** Of the six, only the registry deposits (2, 3) can carry
partner-authored content at all, and they carry it only under §2's discipline.
Directory identity data (names, emails, IdP subjects) is processed by **none** of
the six — it lives in the platform directory of the operating deployment and the
partner's own IdP.

## 2. The discipline that bounds this list

- **Licence basis before content** (WS5): per-source rights (query / store /
  redistribute) are recorded before content is stored; content a source does not
  permit redistributing appears in exports only as a provenance stub.
- **No partner data in public channels by default:** partner deposits default to
  the least-public anchored form (embargoed/private with public anchor values)
  until the partner directs otherwise in writing.
- **Queries are published-literature identifiers.** Connector traffic is DOIs and
  bibliographic terms for literature the partner's question is *about* — the same
  queries any literature search sends. Queries never include directory data,
  falsifiers, or adjudication content.

## 3. Change-notification process (to operate on adoption)

1. This inventory is maintained as a versioned document in the public repository;
   every change is a dated commit.
2. Before any new subprocessor touches **partner data**, pilot partners receive
   notice **[30 days — OWNER TO CONFIRM]** in advance, naming the subprocessor,
   its function, and the data classes involved; objections are handled under the
   DPA (`DPA-TEMPLATE-DRAFT.md` §7).
3. Changes that touch no partner data (e.g. a CI tooling swap) are recorded in the
   version history without the notice period, and the version history says which
   class each change was.
4. Emergency substitutions for security reasons are notified as soon as
   practicable with the reason stated **[OWNER TO CONFIRM this clause]**.
5. A subprocessor is removed from this list only when the data flow actually
   stops, not when it is merely planned to stop.

## 4. Explicitly NOT subprocessors today (designed, not shipped)

The architecture's source layer (WS1) *designs* a broader channel set than the
shipped product uses. Pilot fit criterion F4 is explicit: **the MVP connectors are
Crossref + OpenAlex**. The following are designed-only and receive no data today;
each becomes an inventory entry — with §3 notice — only when a connector ships:

- **CORE** — designed full-text content channel (WS1); **no CORE connector exists
  in the shipped codebase** (`src/tekmerion/connectors.py` ships Crossref and
  OpenAlex only). Status: **TO CONFIRM** before any CORE-connected build.
  **Update (2026-10-12): status changed by Spec 012 — the CORE connector has
  been built under the owner's directive of 2026-10-12 ("Add CORE, this is
  still needed") and CORE is entered as subprocessor #6 in §1; this §4 entry
  is retained as the dated record of its designed-only period and lapses on
  that spec's merge.**
- **Semantic Scholar, BASE, Internet Archive Scholar, HathiTrust, DSAL** —
  designed source-layer channels; not shipped; BASE additionally carries a
  recorded non-commercial-access condition (RED-TEAM-02 RT2-1) that excludes it
  from the hosted connector set until commercial terms are confirmed in writing.
- **Package distribution (PyPI)** — publication of the Spec 009 wheels is an owner
  decision not yet taken; packages are currently built from the public repos.
  PyPI would distribute code, not process partner data.

---

*Draft prepared from repo records only, 2026-10-12. Provider identities are as the
providers publicly state them; counsel confirms contracting entities at DPA
execution.*
