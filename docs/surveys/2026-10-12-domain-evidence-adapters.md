# Domain Evidence Adapters — Full-Coverage Survey

- **Date:** 2026-10-12 · **Directive:** owner, 2026-10-12 (Part 2, expanded to full coverage the same day).
- **Rule of the program (DN-010 / Spec 004 §2):** an adapter = (artifact type, independent checker, registered scope claim stating what the check does NOT establish). Adapters supply **lane-1 evidence only** and can never settle a claim alone. No adapter is specified until its blind spots are written down as claims.
- **Method:** every candidate below was verified from primary sources (standards bodies, project repos/docs, regulator pages) retrieved 2026-10-12. Where a seed claim did not survive verification, the candidate was reclassified or dropped, with the reason recorded (§5). Blind spots are the most important field in every record.

## 1. Pattern taxonomy

| Pattern | Meaning | Exemplars in this survey |
|---|---|---|
| P1 | Machine-checked proof | Lean (Spec 004), Dafny, SPARK, Frama-C, CBMC (bounded), TLA+, SymbiYosys, riscv-formal, Catala (partial) |
| P2 | Automated validation suites on structured artifacts | checkCIF/PLATON, UD validator, TEI schemas, ORD validation, libSBML |
| P3 | Independent re-execution | CODECHECK, REANA (+CAP capture layer), QCArchive, GA4GH WES, nf-core/CWL |
| P4 | Curated benchmarks with reference answers | NAFEMS, NASA TMR, OECD/NEA blind benchmarks, SPE comparative projects, CODATA values |
| P5 | Model intercomparison protocols | CMIP + ESMValTool |
| P6 | Institutional replication verification | AEA Data Editor / LDI lab, cascad, BioModels curation |
| P7 | Reporting-consistency checkers | statcheck, GRIM/GRIMMER/SPRITE, OMOP DQD (P9+P7) |
| P8 | Credibility frameworks (graded mixed evidence) | ASME V&V 10/20/40 + FDA 2023 guidance, NASA-STD-7009B, EPA model guidance |
| P9 | Standards with machine validators | BCO (IEEE 2791), OPTIMADE, FHIR, CF + cf-checker, OGC CITE, IVOA, LegalRuleML, UNF, RO-Crate |

**Universal finding (evidenced across the P9 records):** schema/interface validators guarantee *form and interoperability only* — BCO, CAPE-OPEN, OPTIMADE, IVOA, LegalRuleML, and ThermoML each explicitly disclaim, or structurally cannot deliver, truth of the content carried. Any adapter built on a P9 checker must carry that sentence in its scope claim, verbatim in substance.

**Second universal finding:** bounded checkers must label their bound in every record (CBMC's unwinding bound, SymbiYosys `bmc` depth, TLC's finite model instance). An unlabeled bound is a false proof claim.

## 2. Coverage matrix — domain families × patterns

Legend: ● strong candidate verified · ◐ candidate verified with caveats / partial · ○ infrastructure or doctrine only (not a checker) · — no machine checker exists (honest verdict; the engine's offer in that domain is preregistration, provenance, and digestion tracking only).

| Domain family | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 |
|---|---|---|---|---|---|---|---|---|---|
| Mathematics / formal logic | ● Lean, Rocq, Isabelle | — | ◐ CODECHECK | — | — | — | — | — | — |
| Software / CS | ● Dafny, SPARK, Frama-C, CBMC◐, TLA+◐ | ◐ testbench tiers (cocotb/OSVVM/UVM = simulation, never P1) | ● CODECHECK | ◐ SWE-bench — **excluded as evidence** (gradability risk; a benchmark score is not a verdict, DN-010 point 5) | — | ◐ ACM artifact badging (institutional, human) | — | — | ◐ DO-178C/DO-333 (certification standard; reclassified from P8) |
| Electrical engineering | ● SymbiYosys, riscv-formal, OpenTitan FPV | ● cocotb/OSVVM/UVM (simulation tier) | ◐ Yosys/OpenROAD flows | — | — | — | — | — | — |
| Mechanical / civil / aerospace eng. | — | — | — | ● NAFEMS | — | — | — | ● ASME V&V 10, NASA-STD-7009B | — |
| CFD / fluids | — | — | — | ● NASA TMR | — | — | — | ● ASME V&V 20 | — |
| Nuclear | — | — | — | ● OECD/NEA blind benchmarks (restricted data) | — | — | — | ◐ | — |
| Petroleum / subsurface | — | — | — | ● SPE comparative projects | — | — | — | — | — |
| Chemical engineering / chemistry | — | ● checkCIF, InChI, ORD | ● QCArchive | ● ThermoML (reference data) | ◐ simulator intercomparison is user-built (DWSIM dropped as checker) | — | — | ● ASME V&V 20 | ● ThermoML, CAPE-OPEN (interface only) |
| Materials | — | — | ◐ NOMAD (normalisation) | — | — | — | ◐ NOMAD | — | ● OPTIMADE |
| Biomedical / bioscience | — | ● libSBML/COMBINE | ● GA4GH TRS/WES, nf-core, CWL | — | — | ● BioModels curation | — | ● ASME V&V 40 + FDA 2023 | ● BCO, RO-Crate, FHIR, OMOP |
| Medicine / clinical | — | — | ○ trial registries = lane-2 registration infrastructure, **not checkers** | — | — | — | ◐ CONSORT/SPIRIT machine checkers are research-grade only (best article-level F1 ≈0.87; presence ≠ adequate reporting) | ● V&V 40 + FDA | ● FHIR, OMOP |
| Physics / astronomy | — | — | ● CERN REANA (+CAP capture) | ● CODATA/NIST constants | — | — | — | — | ● IVOA |
| Earth / environmental | — | — | — | — | ● CMIP + ESMValTool | — | — | ● EPA guidance (reclassified from P5) | ● CF + cf-checker |
| Social sciences | — | — | ● CODECHECK | — | — | ● AEA Data Editor, cascad | ● statcheck, GRIM family | — | ● UNF (fixity), Dataverse |
| Philosophy / humanities | ◐ proof assistants for formal logic only; AIF+ASPIC+ (weakest checker story in the survey — adapter must supply its own solver) | ● UD validator, TEI schemas | — | — | — | — | — | — | ◐ TEI; CIDOC-CRM **dropped** (no validator exists) |
| Law | ◐ Catala (verified compiler core; formalisation fidelity is the blind spot) | — | — | — | — | — | — | — | ◐ LegalRuleML (form only; "nothing runs a document") |
| Archaeology / history | — | — | — | — | — | — | — | — | ○ tDAR / Open Context = provenance repositories, **dropped as checkers** |
| Systems engineering | — | — | — | — | — | — | — | — | — **No machine checker exists**: SysML tooling **dropped** (a modelling language with vendor-proprietary, non-canonical validation; traceability links prove existence of a link, nothing more) |
| Qualitative humanities / interpretive disciplines | — | — | — | — | — | — | — | — | — **No machine checker exists.** The engine's offer is preregistration, provenance, and digestion tracking only — stated plainly, per the owner's instruction |

## 3. Candidate records (condensed; full verification notes in the survey working record)

Each record: artifact · checker + guarantee · **blind spots** · maintainer · ingestion · license. (All retrieved 2026-10-12 from primary sources.)

### P1 — machine-checked proof
- **Dafny** — `.dfy` + specs · verifier (Boogie→Z3) guarantees code meets specs *as written*, all inputs · **vacuous/weak `ensures` verifies trivially; spec-intent gap; Boogie/Z3/compiler in trusted base** · Dafny community (ex-MS Research, AWS) · CLI, MIT.
- **SPARK/GNATprove** — Ada subset + contracts · at full proof: no run-time errors + contract conformance · **nothing outside SPARK_Mode; contracts may not express the requirement; source-level only** · AdaCore · CLI; Pro commercial, sources GPL-3.
- **Frama-C** — C + ACSL · WP deductive proof; Eva sound over-approximation · **Eva alarms are may-alarms; only written ACSL properties, against Frama-C's C model** · CEA List · OPAM/CLI, LGPL-2.1 core.
- **CBMC** — C/C++ + assertions · **bounded**: no violation within unwinding bound k, counterexample on failure · **nothing beyond the bound without a separate completeness argument; stubbed environment is assumed** · Diffblue/CProver · CLI XML/JSON, BSD-style.
- **TLA+ (TLC/Apalache)** — `.tla` + model config · exhaustive over the *finite configured instance* (TLC); SMT bounded/inductive (Apalache) · **implementation↔spec refinement not checked; outside configured constants, nothing** · TLA+ Foundation; Apalache independent (currently unfunded) · CLI, MIT/Apache-2.
- **Catala** — literate `.catala` statute encodings · compiler core (default calculus→λ-calculus) proved in F*; lawyer-readable rendering from same source · **the formalisation's reading of the law is human and unproved; only core steps proved; research compiler** · Inria · CLI, Apache-2.0.
- **SymbiYosys** — RTL + SVA + `.sby` · BMC to depth, or unbounded k-induction, PASS/FAIL + VCD counterexample · **`bmc` pass is depth-bounded; over-constrained `assume`s = vacuous proof; no analogue/timing** · YosysHQ · CLI, ISC. *(Reclassified P2→P1 during verification.)*
- **riscv-formal** — RVFI wrapper + formal ISA spec · every modelled instruction retires consistently with the formal ISA model · **unmodelled extensions/peripherals/timing out of scope; wrapper + RVFI are trusted base** · SymbioticEDA/community · git + sby, ISC. *Cleanest P1 in the survey.*
- **OpenTitan DV/FPV** — per-IP SVA + testplans, V1–V3 stage gates with coverage thresholds · stated assertions under reviewed assumptions · **design-specific, does not transfer; assumption validity in silicon unproved** · lowRISC · repo + dvsim, Apache-2.0; FPV upstream needs commercial tooling.
- **Yosys/OpenROAD** — RTL→netlist→GDS · SAT equivalence checking; DRC/timing vs supplied PDK · **RTL intent, PDK↔silicon fidelity, property completeness all out of scope** · YosysHQ / OpenROAD Project · CLI, ISC / BSD-3.

### P2 — automated validation suites
- **checkCIF/PLATON** ★ — CIF + structure factors · graded alerts (A serious / B / C / G) over syntax, cell, geometry, symmetry, displacement, structure factors; **journal-mandatory** in IUCr journals (Spek 2009); ~1.2M checkCIF runs/yr (IUCr figure c.2015 — unit is *runs*, not assertions; not re-verified for 2026) · **IUCr states in every report: absence of alerts does not guarantee correctness; a competently fabricated, internally consistent dataset passes** · IUCr / Spek (Utrecht) · web service or local PLATON (`platon -u`); no public REST API; PLATON author-distributed, not OSI.
- **InChI** — structure records · regeneration-and-compare gives canonical identity (v1.07, MIT) · **input structure's chemical truth unchecked; tautomer normalisation merges distinct tautomers; organometallic/polymer coverage incomplete by the Trust's own statement** · InChI Trust/IUPAC · C library/CLI.
- **ORD validation** — reaction records (protobuf, ~266 fields) · `ord-schema validate_dataset`: schema + semantic checks (identifier formats, pH ranges, atom-mapping flags) · **whether the reaction occurred / yield is real is unchecked; corpus inherits literature's publication bias** · ORD community · Python/CLI; corpus CC-BY-SA-family (per-repo).
- **UD validator** — CoNLL-U treebanks · conformance to UD specification (format, tags, relations, tree well-formedness); release gate for UD · **annotation *accuracy* is never checked — a valid file can be wrongly annotated throughout** · UD consortium · CLI (`validate.py`/`udtools`); licence not stated in retrieved README — verify before redistribution.
- **TEI schemas** — TEI P5 XML vs ODD-derived schema · schema validity (RELAX NG/XSD/DTD) · **TEI itself: no schema language captures all conformance constraints; validity ≠ conformance; "TEI-valid" without the named ODD is an underspecified claim** · TEI Consortium · standard XML tooling, CC-BY/BSD-family.

### P3 — independent re-execution
- **CODECHECK** ★ — paper + code/data + `codecheck.yml` · a named, unaffiliated codechecker re-executes and issues a timestamped certificate (register: 132 certificates, 13 venues, Sept 2026) · **certificates state explicitly: no guarantee of correctness or scientific validity; scope may be partial (one figure/table); plausible-but-wrong outputs pass** · CODECHECK community (Eglen/Nüst) · GitHub register, YAML, Zenodo DOIs.
- **CERN REANA** — `reana.yaml` containerised workflows · platform guarantees declarative re-runnability *if* containers/inputs persist · **nobody independent necessarily re-ran anything; self-declared reproducibility ≠ verification — needs a CODECHECK/CAP-style second party** · CERN/reanahub · CLI/REST, MIT. **CAP** is its capture layer (preservation, not a checker).
- **GA4GH TRS/WES** — workflow descriptors + run requests · API-level portability across backends (P9 in form, P3 in function) · **output equivalence across backends not guaranteed; a listed tool is not thereby validated** · GA4GH · REST/OpenAPI, Apache-2.0-family.
- **nf-core / CWL / WDL** — pinned pipelines / workflow descriptions · nf-core lint+CI+release discipline; CWL conformance suite for runners · **mutable container tags, differing reference data, unrecorded parameters all break reproducibility silently; description portability ≠ result identity** · Seqera / nf-core community; CWL WG; Broad/OpenWDL · CLI; Apache-2.0 / MIT.
- **QCArchive** — QCFractal records (molecule, method/basis, program+version, inputs/outputs, provenance) · execution harness guarantees the record was produced by the named program with the recorded inputs, stored immutably, at thousands–millions scale · **method/basis adequacy and program correctness unchecked; benchmark curation bias is upstream** · MolSSI · QCPortal Python client, BSD-family.

### P4 — curated benchmarks
- **NAFEMS** — published FE benchmark problems + target values · user/vendor code reproduces a specified quantity within stated tolerance · **verification against reference solutions, mostly not experiment; no runner, no tolerance-as-verdict service; paywalled PDFs, manual transcription** · NAFEMS · publications (proprietary).
- **NASA TMR / TMBWG** — canonical CFD cases, grids, reference + experimental data · implementation consistency with NASA reference implementations on canonical flows · **a model can pass flat-plate and fail separation; validity for industrial geometries not established** · NASA Langley → TMBWG · web download, no API.
- **OECD/NEA blind benchmarks** — integral-facility datasets, blind phases · un-tuned code-to-experiment comparison for the specified transient · **facilities are scaled (distortion uncertainty); many datasets restricted to participants — an outsider cannot ingest or re-check** · OECD NEA · restricted Data Bank packages.
- **SPE comparative projects** — fully specified synthetic reservoir problems · inter-simulator comparability; the ensemble *is* the reference (SPE10/11 have no single true solution) · **synthetic geology; consensus can be jointly wrong/unconverged** · SPE · papers (paywalled); SPE11 dataset open (DaRUS DOI).

### P5 — model intercomparison
- **CMIP + ESMValTool** — CMOR-standardised model output + ESMValTool recipes · the same diagnostics applied comparably across models, reproducibly from recipes · **good scores can arise from compensating errors and tuning to the evaluation observations; models share code/parameterisations, so ensemble spread understates structural uncertainty** · WCRP/CMIP Panel; ESMValGroup · ESGF + CLI, Apache-2.0 (tool).

### P6 — institutional replication verification
- **AEA Data Editor / LDI Replication Lab** — replication packages at openICPSR · pre-publication institutional check: package completeness, data citations, and attempted reproduction of tables/figures · **identification strategy and data truth unchecked; confidential-data exemptions exist; "reproduced as coded" ≠ "conclusion true"** · AEA (Data Editor; Cornell LDI lab) · openICPSR deposit.
- **cascad** — code+data + README · independent auditor re-runs, including on original confidential data inside a CASD secure enclave · **nothing beyond submitted code/data; small, fee/project-based; no machine-readable certificate API** · cascad (HEC Paris / Orléans / CNRS) · manual submission.
- **BioModels curation** — SBML/SED-ML in COMBINE archives · libSBML validation (numbered rules) + **curators re-run the model and check correspondence to the paper** before a curated ID · **biological correctness and parameter truth unchecked; SED-ML coverage historically partial (~373/1058 entries in the retrieved study)** · COMBINE / EMBL-EBI · REST API, .omex; models CC0.

### P7 — reporting-consistency checkers
- **statcheck** ★ — manuscripts with APA-style NHST results · recomputes p from statistic+df, flags inconsistencies and decision errors; guarantees *internal arithmetic consistency of extracted triples* · **only exact-APA-format, extractable results; cannot say which element is wrong; silent on everything it cannot parse — no flags ≠ clean paper; corrections (Bonferroni etc.) can false-flag** · Nuijten et al. · R package / web app, GPL-family (verify DESCRIPTION).
- **GRIM / GRIMMER / SPRITE** ★ — reported mean/SD + N (integer-granular data) · GRIM fail = *mathematical impossibility* given N and granularity; GRIMMER extends to SDs; SPRITE reconstructs candidate datasets (plausibility display) · **a fail proves inconsistency, not its cause; power collapses at large N / few decimals / continuous data; most fabricated means pass; SPRITE outputs are not "the real data"** · Brown & Heathers; Anaya; `scrutiny` R package (Jung) · R/web, open.
- **CONSORT/SPIRIT machine checkers** — trial manuscripts/protocols · research-grade NLP only (SPIRIT-CONSORT-TM corpus; best article-level F1 ≈0.87) · **presence detection ≠ adequate reporting; no journal- or EQUATOR-endorsed automated validator exists — honest verdict: emerging P7, not a production checker** · EQUATOR (checklists); Kilicoglu lab (models) · human checklist / research code.

### P8 — credibility frameworks (doctrine, not checkers)
- **ASME V&V 40-2018 + FDA guidance (final 2023-11-16, Docket FDA-2021-D-0980)** — credibility assessment vs context of use; **model risk = model influence × decision consequence** (verified in FDA/ASME primary descriptions); graded, risk-commensurate evidence · **no automated checker exists; the framework explicitly does not prescribe specific activities or quantitative rigor; FDA scope is physics/mechanistic models — standalone ML/AI excluded; extrapolation outside the COU is undetectable by the framework** · ASME V&V 40 Subcommittee; FDA CDRH/OSEL · document submission; ASME paywalled, FDA public.
- **ASME V&V 10-2019 (R2025)** (solid mechanics) and **V&V 20-2009 (R2021)** (CFD: validation uncertainty u_val; |E| < u_val is a quantitative, falsifiable statement at the validation point) · **model-form adequacy is inferred residually, never measured; no software checker ships with either standard** · ASME · PDF reports, paywalled.
- **NASA-STD-7009B (2024-03-05, current)** — M&S credibility assessment, Technical Authority acceptance · **institutional process compliance only; credibility factors are judgment-scored and gameable** · NASA · free PDF.
- **EPA model evaluation guidance** — reclassified P5→P8: procedural reviewability under an agreed protocol · **no checker, no ensemble; "preferred" status is not best physics** · US EPA · guidance documents.

### P9 — standards with validators
- **BioCompute Object (IEEE 2791-2020)** — BCO JSON (8 domains) · JSON-Schema validation guarantees structural completeness of the *description* · **the workflow's actual execution and results are not checked; provenance is self-asserted; FDA Data Standards Catalog inclusion is the adoption signal** · IEEE 2791 WG / BioCompute community · JSON/API; schema BSD-3-family, standard IEEE copyright.
- **RO-Crate / Workflow Run RO-Crate** — JSON-LD provenance packages · profile validators (`ro-crate-py`, `roc-validator`) guarantee profile conformance · **provenance is authored by the runner — self-attested unless engine-generated; re-execution reproducibility not implied** · RO-Crate community · library/CLI; spec open.
- **OPTIMADE** — materials APIs · `optimade-validator` guarantees response conformance to the spec version · **underlying structures/properties can be wrong under a compliant API; "fuzzy" validation tolerates deviations; ~22 providers / ~22M structures** · OPTIMADE Consortium · CLI, MIT.
- **FHIR validator (HL7)** — FHIR resources vs Implementation Guides · structure, cardinality, profile constraints, terminology (with a terminology server) · **clinical correctness out of scope; base validity ≪ IG validity — record IG + version; terminology checks degrade silently without a server** · HL7 · Java CLI/Docker, Apache-2.0.
- **OMOP CDM + DataQualityDashboard** — CDM v5.4 instances · >3,500 checks (conformance/completeness/plausibility); required before OHDSI network studies · **a systematically wrong ETL concept mapping can pass; ETL information loss is unrecoverable by the checker; thresholds are heuristics** · OHDSI · R package, Apache-2.0.
- **CF conventions + cf-checker** — NetCDF-CF files · metadata conformance to the named CF version (two independent checkers: CEDA cf-checker, IOOS compliance-checker) · **data values can be nonsense in a compliant file; checker/convention version skew is documented — record all three versions** · CF Governance; NCAS-CMS/CEDA · CLI, BSD-family.
- **OGC CITE (TEAM Engine)** — geospatial services vs OGC standards · executable test suites; official-installation pass grounds OGC certification · **only the tested conformance classes are certified; data accuracy out of scope; self-run results are not certification** · OGC · web/CLI, Apache-2.0-family.
- **IVOA** — astronomy services (TAP/VOTable/…) · protocol validators guarantee conformant, discoverable, interoperable responses · **calibration and data correctness unchecked; metadata truthfulness is the provider's** · IVOA · REST/pyvo, CC-family.
- **CAPE-OPEN** — process-simulation component interfaces · compliance testing guarantees a component *implements the interface contract* · **interoperability ≠ validity: two compliant components can disagree and both be "compliant"** · CO-LaN · spec PDFs, free-to-use.
- **NIST ThermoML** — thermophysical data in ThermoML XML · XSD validation + NIST's *representation-fidelity* check · **NIST's own disclaimer: archive values were "not critically evaluated in any way" — transcription fidelity, not measurement truth; static archive coverage ends ~2019** · NIST TRC for IUPAC · XML/JSON + API.
- **UNF (Dataverse)** — tabular datasets · format-independent semantic fingerprint; a mismatch proves content changed · **a fabricated dataset fingerprints perfectly; conveys nothing about accuracy or provenance** · Altman/King lineage; IQSS Dataverse · automatic at ingest, Apache-2.0. *(Reclassified P6→P9.)*
- **LegalRuleML (OASIS Core 1.0, 2021)** — legal-rule XML · schema validation guarantees well-formed legal markup only · **"only a way of writing rules down; nothing runs a document, and a document carries no tests" (integration docs); encoding↔statute isomorphism is author-asserted** · OASIS LegalRuleML TC · XML + validators, open standard.
- **CODATA/NIST constants** — reference values (2022 adjustment, SP 959) · as a P4-style comparison target: deviation-from-adjusted-value within stated uncertainty is a falsifiable check · **the adjustment itself rests on input selection and discrepancy-handling judgment; values shift between adjustments** · CODATA Task Group; NIST · tables/database, US-gov public.

## 4. Shortlist — pattern coverage first (owner's gate; builds NOT started)

Lean (P1) is already the reference adapter (Spec 004). The next three, chosen to span distinct patterns:

1. **checkCIF/PLATON adapter (P2) — Spec 006.** The strongest institutional adoption in the survey (journal-mandatory, ~1.2M runs/yr on IUCr's figure), graded alert levels that map naturally onto evidence masses, and a checker whose own reports state its blind spot. Maintainer: IUCr (service) / A. L. Spek (PLATON). Teaches the engine the *validation-suite* pattern: structured artifact in, graded findings out, no truth claim.
2. **CODECHECK adapter (P3) — Spec 007.** The only candidate whose checker is a *named independent human* re-executing — the closest structural analogue to digestion-adjacent lane-1 work, with timestamped certificates as evidence artifacts and an explicit correctness disclaimer to inherit. Cross-domain (any computational scholarship), so the pattern generalises. Maintainer: CODECHECK community.
3. **statcheck + GRIM-family adapter (P7) — Spec 008.** The cheapest deterministic checkers in the survey, with the hardest falsifiers (a GRIM fail is a mathematical impossibility, not a probability), opening the social-sciences domain family. Maintainers: Nuijten et al. (statcheck); Brown & Heathers / Anaya / Jung's `scrutiny` (GRIM family).

Deferred deliberately: P4 benchmark harnesses (the benchmark is the evidence source; the adapter is a comparison harness any study can already express), P5 ESMValTool (heavy infrastructure, one domain), P6 institutional verification (AEA/cascad are *services performed by institutions* — the engine consumes their certificates as evidence, CODECHECK-style, rather than re-implementing them), P8 frameworks (doctrine for credibility grading inside studies, not checkers), P9 validators (form-only guarantees; adopt per-domain when a study needs one, with the §1 universal finding in the scope claim).

## 5. Dropped / reclassified — with reasons

- **DROPPED — SysML model checking / requirements traceability:** no canonical independent validator exists; vendor tools are proprietary and inconsistent (incl. broken XMI interchange). Re-admit only as a named vendor tool + version (P2) or a named SysML→model-checker transform (P1).
- **DROPPED as checker — DWSIM:** a simulator, not a checker; no validation layer or conformance suite. Salvageable only as a re-execution *engine* inside a P3/P5 adapter whose checker is a separate comparison module.
- **DROPPED as checker — OpenSees:** the object under test, not a checker; its example scripts are developer self-tests.
- **DROPPED — CIDOC-CRM (as P9):** a real ISO standard (21127:2023) with **no official validator, test suite, or certification**; project-local SHACL would make checker and claimant the same party. Re-admit a named profile + maintained validator if one appears.
- **DROPPED as checkers — tDAR / Open Context:** preservation repositories / editorial publishers. Valid provenance sources; never verification.
- **DROPPED as distinct candidate — "ASME V&V benchmark cases" (P4):** no ASME-run case library exists; V&V 20 is a method (P8), applied to NAFEMS/NASA/NEA cases.
- **EXCLUDED as evidence — SWE-bench (and leaderboard benchmarks generally):** gradability risk named by the owner; a benchmark score is a metric, not evidence for a claim (DN-010 point 5).
- **RECLASSIFIED:** DO-178C/DO-333 P8→P9-certification (+P1-enabling supplement). EPA guidance P5→P8. CERN CAP P3→P3-enabling capture layer. UNF P6→P9. SymbiYosys P2→P1. GA4GH TRS/WES and CWL: P9 in form, P3 in function (counted once, under P3). Trial registries + OSF preregistration + TOP Guidelines: **lane-2 registration infrastructure, not a checker pattern at all** — scoring preregistration as lane-1 evidence would be exactly the lane conflation DN-010 forbids; the engine consumes them as provenance/priority records (its own freeze machinery is the same kind of thing).
- **Verification gaps left open (not published as facts):** current UD release treebank/language counts; UD tools licence; statcheck package licence per CRAN DESCRIPTION; CBMC-at-AWS adoption from a primary AWS source; SPRITE details from primary sources (this pass used a secondary summary). Each is flagged where it appears above.
