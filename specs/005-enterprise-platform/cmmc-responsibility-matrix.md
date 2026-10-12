# CMMC Control Responsibility Matrix — NIST SP 800-171 Rev 2

**Companion to:** Spec 005 §13 (CMMC amendment, 2026-10-12) · **Governs claims:** CLM-005-24, CLM-005-29
**Classification key:** **Platform** — satisfied by construction when the platform is operated as designed (the requirement's mechanism and evidence are the product's). **Supports** — the platform provides the mechanism or the evidence; the operator, IdP, or organization owns the remainder, and the basis column says which part. **Organizational** — outside product scope; listed so the family is never silently dropped.
**Rules:** (1) Requirement short titles are paraphrases; the controlling text is SP 800-171 Rev 2 itself. (2) A phase exit that changes any classification updates this matrix in the same commit (CLM-005-24). (3) "Not applicable by design" is recorded as Supports with the basis naming the owner (never left blank). (4) Totals: 14 families, 110 requirements — 3.1: 22 · 3.2: 3 · 3.3: 9 · 3.4: 9 · 3.5: 11 · 3.6: 3 · 3.7: 6 · 3.8: 9 · 3.9: 2 · 3.10: 6 · 3.11: 3 · 3.12: 4 · 3.13: 16 · 3.14: 7 = **110**.
**SA note:** SP 800-171 Rev 2 has **no SA (System and Services Acquisition) family**. Acquisition and supply-chain obligations (including DFARS flow-downs) are organizational/contractual; platform support is limited to provenance evidence (signed, anchored release and bundle records). The family is recorded here so the 800-53-style code list a reviewer brings is fully accounted for.
**Level scope:** this matrix is the Level 2 target. Level 1 (FAR 52.204-21) is a subset and implied. Level 3 / SP 800-172 is out of scope (Spec 005 §11).

---

## 3.1 Access Control (AC) — 22

| Req | Short title | Class | Basis |
|---|---|---|---|
| 3.1.1 | Limit access to authorized users, processes, devices | Platform | Service-layer append gate + RBAC (T507/T508); no anonymous mutation path |
| 3.1.2 | Limit users to authorized transactions and functions | Platform | WS6 role-action matrix enforced in the service layer (CLM-005-08) |
| 3.1.3 | Control the flow of CUI | Supports | Study-plane flows are platform-mediated and recorded; flow policy is the organization's |
| 3.1.4 | Separate the duties of individuals | Supports | Disjoint role set + admin planes (CLM-005-09) make separation assignable; assigning people is the org's act |
| 3.1.5 | Employ least privilege | Platform | Deny-by-default authorization; JIT identities hold no role until a grant event |
| 3.1.6 | Use non-privileged accounts for nonsecurity functions | Supports | Plane separation is the platform's design; day-to-day usage discipline is the operator's |
| 3.1.7 | Prevent non-privileged users executing privileged functions; log the execution | Platform | Service-layer enforcement + platform audit ledger records privileged executions |
| 3.1.8 | Limit unsuccessful logon attempts | Supports | Performed at the IdP; the platform records authentication failures (T550) and refuses deactivated identities |
| 3.1.9 | Provide privacy and security notices | Supports | Notice text and display policy are the deployment's; surfaces exist in UI/E5 |
| 3.1.10 | Session lock after inactivity / user-initiated | Supports | Session service carries lock + idle primitives (§9); the lock UI is wireframe-gated (E5) |
| 3.1.11 | Terminate session after defined conditions | Platform | Idle (30 min) and absolute (12 h) lifetimes, tenant-configurable downward (§9) |
| 3.1.12 | Monitor and control remote access | Supports | All access is authenticated, session-bound, and recorded; network-level control is the deployment's |
| 3.1.13 | Employ cryptographic mechanisms for remote access sessions | Supports | TLS-only transport required (§9); termination point is deployment-owned |
| 3.1.14 | Route remote access through managed access control points | Organizational | Network architecture of the operator |
| 3.1.15 | Authorize wireless access before connection | Organizational | Operator networks |
| 3.1.16 | Authenticate wireless users and devices | Organizational | Operator networks |
| 3.1.17 | Protect wireless confidentiality and integrity | Organizational | Operator networks |
| 3.1.18 | Control connection of mobile devices | Organizational | Endpoint policy of the organization |
| 3.1.19 | Encrypt CUI on mobile devices and removable media | Organizational | Devices are the organization's; the platform never requires mobile use |
| 3.1.20 | Verify and control/limit connections to external systems | Supports | IdP and webhook-egress endpoints are explicit tenant configuration; the policy decision is the org's |
| 3.1.21 | Limit use of organizational systems on external systems | Organizational | Personnel/system-use policy |
| 3.1.22 | Control CUI posted on publicly accessible systems | Organizational | Publication decisions are the organization's; bundles disclose only what their study record carries |

## 3.2 Awareness and Training (AT) — 3

| Req | Short title | Class | Basis |
|---|---|---|---|
| 3.2.1 | Role-based security awareness training | Organizational | The platform's role records and audit exports can evidence *who held which role when*; training itself is the org's program |
| 3.2.2 | Ensure personnel are trained for their duties | Organizational | As 3.2.1 |
| 3.2.3 | Practical exercises in training | Organizational | — |

## 3.3 Audit and Accountability (AU) — 9

| Req | Short title | Class | Basis |
|---|---|---|---|
| 3.3.1 | Create and retain audit records enabling monitoring, analysis, investigation, reporting | Platform | Platform audit ledger core (T510): append-only, signed, hash-chained, checkpointable |
| 3.3.2 | Audit records capture the enumerated event content | Platform | E1 absorbs the §3.3.1/§3.3.2 event classes now (T550; CLM-005-26): account creation/modification, authentication incl. failures, authorization decisions incl. denials, admin actions, key lifecycle — each with actor, type, timestamp, target, outcome |
| 3.3.3 | Review and report audit records per process | Supports | Exports + audit viewer (E5/E6) supply the records; the review process and cadence are the org's |
| 3.3.4 | Alert on audit logging process failure | Supports | Verification failures are first-class platform events, egressed via IR hooks (T554) |
| 3.3.5 | Correlate audit review, analysis, and reporting | Supports | The identity↔key join (CLM-005-22) yields per-actor timelines across platform and study planes |
| 3.3.6 | Provide audit record reduction and report generation | Supports | Bundle-pattern export machinery (Spec 002 Phase 5; T542) |
| 3.3.7 | Provide system capability for timestamp synchronization | Supports | Platform stamps UTC and records checkpoint times; the authoritative clock source (e.g. NTP) is the operator's |
| 3.3.8 | Protect audit information from unauthorized modification | Platform | No update/delete exists in any plane (DN-005); tampering fails verification from the bundle alone |
| 3.3.9 | Limit management of audit information to a privileged subset | Platform | Audit functions are admin-plane only; study roles hold no audit-management power |

## 3.4 Configuration Management (CM) — 9

| Req | Short title | Class | Basis |
|---|---|---|---|
| 3.4.1 | Establish and maintain baseline configurations | Supports | Platform ships a versioned configuration schema and records tenant/IdP config as events; baselines for the org's own systems are the org's |
| 3.4.2 | Establish and enforce security configuration settings | Supports | The platform enforces its own §9 security settings; other systems are the operator's |
| 3.4.3 | Track, review, approve/disapprove, and log changes | Supports | Vendor side: the constitution/spec/wireframe gate record and signed release history are the platform's change evidence; operator change control is the org's |
| 3.4.4 | Analyze security impact of changes before implementation | Supports | The claims-first spec process (falsifiers + assessments per change) is the vendor-side evidence |
| 3.4.5 | Define and enforce access restrictions associated with changes | Supports | Who may change tenant configuration is governed by the disjoint admin planes (T509) |
| 3.4.6 | Employ least functionality | Platform | Deny-by-default design; no unused services in the platform plane |
| 3.4.7 | Restrict, disable, or prevent nonessential programs, functions, ports, protocols, services | Supports | The platform minimizes its own surface; host/network enforcement is the operator's |
| 3.4.8 | Apply deny/allow-by-exception execution policy for software | Organizational | Host control of the operator |
| 3.4.9 | Control and monitor user-installed software | Organizational | Endpoint policy of the organization |

## 3.5 Identification and Authentication (IA) — 11

| Req | Short title | Class | Basis |
|---|---|---|---|
| 3.5.1 | Identify system users, processes, and devices | Platform | Identity model `(tenant, issuer, subject)` + random actor IDs + service-account principals (§2, §9) |
| 3.5.2 | Authenticate (or verify) identities before access | Platform | IdP assertion required for every interactive action; API keys authenticated for service actions |
| 3.5.3 | Use MFA for privileged and network access | Supports | MFA is performed at the IdP; the platform *requires* MFA evidence (`acr`/`amr`) per §13.5 and refuses step-up without it |
| 3.5.4 | Employ replay-resistant authentication mechanisms | Platform | PKCE S256, OIDC nonce, signed assertions, webhook replay windows |
| 3.5.5 | Prevent reuse of identifiers for a defined period | Supports | Actor IDs are never reassigned (platform); identifier retirement period is directory lifecycle policy (E3) |
| 3.5.6 | Disable identifiers after a defined inactivity period | Supports | Deactivation pipeline (E3, T521); once triggered, refusal is effective at the next request (E1 gate) |
| 3.5.7 | Enforce minimum password complexity | Supports | Not applicable by design — no local passwords exist (CLM-005-01); binds the tenant IdP |
| 3.5.8 | Prohibit password reuse for a specified number of generations | Supports | As 3.5.7 |
| 3.5.9 | Allow temporary password use for immediate change only | Supports | As 3.5.7 |
| 3.5.10 | Store and transmit only cryptographically protected passwords | Supports | As 3.5.7 — and the platform stores no passwords at all |
| 3.5.11 | Obscure feedback of authentication information | Platform | Service responses do not distinguish unknown identity from failed authentication |

## 3.6 Incident Response (IR) — 3

| Req | Short title | Class | Basis |
|---|---|---|---|
| 3.6.1 | Establish an operational incident-handling capability | Supports | Security-significant platform events egress as signed records (T554); the capability and process are the org's |
| 3.6.2 | Track, document, and report incidents | Supports | Platform events (auth-failure bursts, break-glass use, revocation storms, verification failures) are ledgered and exportable; reporting duties are the org's |
| 3.6.3 | Test the organizational incident response capability | Organizational | The org's exercises |

## 3.7 Maintenance (MA) — 6

| Req | Short title | Class | Basis |
|---|---|---|---|
| 3.7.1 | Perform maintenance on systems | Organizational | Operator/vendor maintenance processes; platform releases are signed and anchored records an operator can evidence |
| 3.7.2 | Provide controls on maintenance tools, techniques, mechanisms, personnel | Organizational | — |
| 3.7.3 | Ensure equipment removed for off-site maintenance is sanitized | Organizational | — |
| 3.7.4 | Check media containing diagnostic/test programs for malicious code | Organizational | — |
| 3.7.5 | Require MFA for nonlocal maintenance sessions | Supports | Administrative access to the platform itself is SSO + MFA + step-up (§2, §13.5); maintenance of the host is the operator's |
| 3.7.6 | Supervise maintenance activities of personnel without required access | Organizational | — |

## 3.8 Media Protection (MP) — 9

| Req | Short title | Class | Basis |
|---|---|---|---|
| 3.8.1 | Protect system media containing CUI, in handling and storage | Organizational | Media handling is the operator's; CUI marking support (T551) aids identification |
| 3.8.2 | Limit access to CUI on system media to authorized users | Organizational | As 3.8.1 |
| 3.8.3 | Sanitize or destroy media before disposal or reuse | Organizational | — |
| 3.8.4 | Mark media with distribution/handling notices | Supports | CUI marking fields on bundles/exports (T551) are the platform's marking mechanism for its own artifacts |
| 3.8.5 | Control access to media storage areas | Organizational | Facilities |
| 3.8.6 | Store media in locked/secured areas or containers | Organizational | Facilities |
| 3.8.7 | Protect portable storage devices | Organizational | Endpoint/device policy |
| 3.8.8 | Prohibit portable storage without identifiable owner | Organizational | Endpoint/device policy |
| 3.8.9 | Protect confidentiality of backup CUI at storage locations | Supports | Exports are hash-manifested and anchorable; storage encryption/location is the operator's |

## 3.9 Personnel Security (PS) — 2

| Req | Short title | Class | Basis |
|---|---|---|---|
| 3.9.1 | Screen individuals prior to authorizing access | Organizational | The org's vetting; role grants record *that* access was granted, by whom |
| 3.9.2 | Ensure CUI is protected during and after personnel actions | Supports | The deprovisioning pipeline (E3, T521) executes the platform side promptly — sessions revoked, keys closed, history intact; the personnel action is the org's |

## 3.10 Physical Protection (PE) — 6

| Req | Short title | Class | Basis |
|---|---|---|---|
| 3.10.1 | Limit physical access to systems and operating environments | Organizational | Facilities / hosting provider; the residency pin (§6) records *where*, the provider controls it |
| 3.10.2 | Protect and monitor the physical facility | Organizational | As 3.10.1 |
| 3.10.3 | Escort visitors and monitor visitor activity | Organizational | — |
| 3.10.4 | Maintain audit logs of physical access | Organizational | Facility records |
| 3.10.5 | Control and manage physical access devices | Organizational | — |
| 3.10.6 | Enforce safeguarding measures for CUI at alternate work sites | Organizational | Org policy for remote work |

## 3.11 Risk Assessment (RA) — 3

| Req | Short title | Class | Basis |
|---|---|---|---|
| 3.11.1 | Periodically assess risk to operations, assets, individuals | Organizational | The org's assessment; platform control-state tracking (T552) supplies current inputs |
| 3.11.2 | Scan for vulnerabilities in systems and applications | Supports | The platform codebase is continuously test-built in CI (vendor process); deployment scanning is the operator's |
| 3.11.3 | Remediate vulnerabilities in accordance with risk assessments | Supports | Vendor patch releases are signed, anchored records; applying them is the operator's act |

## 3.12 Security Assessment (CA) — 4

| Req | Short title | Class | Basis |
|---|---|---|---|
| 3.12.1 | Periodically assess security controls for effectiveness | Supports | Platform evidence exports + maintained control states make assessment inputs current; assessment itself is the org's/C3PAO's |
| 3.12.2 | Develop and monitor plans of action and milestones (POA&M) | Supports | The append-only POA&M register (T553) is platform machinery; POA&M content and ownership are the org's |
| 3.12.3 | Perform continuous monitoring of security controls | Supports | Platform audit ledger + per-phase re-assessment rhythm; the monitoring program is the org's |
| 3.12.4 | Develop, document, and periodically update system security plans | Supports | This matrix + control-state tracking are maintained SSP inputs; the SSP is the org's document |

## 3.13 System and Communications Protection (SC) — 16

| Req | Short title | Class | Basis |
|---|---|---|---|
| 3.13.1 | Monitor, control, and protect communications at system boundaries | Supports | Deployment network boundary is the operator's; the platform requires TLS and records every session |
| 3.13.2 | Employ security engineering principles in design and development | Supports | The vendor design record (constitutions, specs, red teams RED-TEAM-01/02) is the evidence; org systems are the org's |
| 3.13.3 | Separate user functionality from system management functionality | Platform | Study plane and admin planes are disjoint in the service design (CLM-005-09) |
| 3.13.4 | Implement cryptographic mechanisms to protect CUI during transmission | Supports | TLS required on every service path (§9); termination and network path are deployment-owned |
| 3.13.5 | Implement subnetworks for publicly accessible components | Supports | A deployment-architecture property; the platform's service split permits it |
| 3.13.6 | Deny network communications traffic by exception (deny by default) | Supports | Application layer is deny-by-default; network rules are the deployment's |
| 3.13.7 | Prevent split tunneling on remote devices | Organizational | Endpoint/network policy |
| 3.13.8 | Employ cryptographic mechanisms for remote access session confidentiality | Supports | As 3.13.4 (TLS-only sessions) |
| 3.13.9 | Terminate network connections at session end or after inactivity | Platform | Session lifetimes and termination enforced in the session service (§9) |
| 3.13.10 | Establish and manage cryptographic keys for required cryptography | Platform | The §3 key lifecycle (enrollment, rotation, revocation, closure) for platform keys; tenant KMS choice remains the tenant's |
| 3.13.11 | Employ FIPS-validated cryptography | **Supports — OPEN GAP** | **Not satisfied today.** Current modules (Axiomere core `sha2`/`ed25519-dalek`; E1 service-layer implementations) are not FIPS 140-3 validated. Platform obligations: the crypto inventory (T549), the recorded migration routes, and the seeded POA&M item — **POAM-0001 in the deployment POA&M register (T553, landed E6)**, carrying the three recorded milestones incl. the owner-decision trigger. The validated-module decision is the owner's, on the Axiomere roadmap (Spec 005 §13.3; CLM-005-25). No surface may state otherwise. |
| 3.13.12 | Prohibit remote activation of collaborative computing devices | Organizational | Endpoint policy |
| 3.13.13 | Control and monitor the use of mobile code | Organizational | Endpoint/browser policy of the org |
| 3.13.14 | Control and monitor the use of VoIP technologies | Organizational | Org communications policy |
| 3.13.15 | Protect the authenticity of communications sessions | Supports | Signed assertions, bound sessions, signed webhook deliveries protect session authenticity on platform channels |
| 3.13.16 | Protect the confidentiality of CUI at rest | Supports | Ledger files are operator-storage; at-rest encryption is the deployment's, and content-level protection awaits Spec 002 T223 (payload encryption) — recorded dependency, not a claim |

## 3.14 System and Information Integrity (SI) — 7

| Req | Short title | Class | Basis |
|---|---|---|---|
| 3.14.1 | Identify, report, and correct information and system flaws in a timely manner | Supports | Vendor release process with signed, anchored history; operator applies updates |
| 3.14.2 | Provide protection from malicious code at designated locations | Organizational | Deployment endpoints and servers |
| 3.14.3 | Monitor system security alerts and advisories and take action | Organizational | The org's monitoring process; vendor advisories are issued as records |
| 3.14.4 | Update malicious code protection mechanisms when new releases are available | Organizational | Deployment tooling |
| 3.14.5 | Perform periodic scans and real-time scans of files | Organizational | Deployment tooling |
| 3.14.6 | Monitor organizational systems to detect attacks and indicators of potential attacks | Supports | Platform-plane security events are ledgered and egressed (T554); network/system monitoring is the operator's |
| 3.14.7 | Identify unauthorized use of organizational systems | Supports | Authentication-failure, revocation, and anomaly events in the platform audit ledger feed the operator's detection |

---

*Maintenance:* classifications for requirements whose machinery lands in E1 (AU, IA, AC subsets) are re-checked at the E1 phase exit; the matrix is re-issued with the E1 re-assessment. Any reclassification records its reason in `assessment-2026-10-12.md` or its successor.

**E6 note (2026-10-12):** at the E6 exit the matrix was reviewed against the landed compliance machinery — **no classification changes**. What changed is evidence, recorded here per this document's own rule: 3.12.2's basis (the append-only POA&M register) is now built machinery (`src/tekmerion/platform/poam.py`), and its first item is 3.13.11's seeded gap (POAM-0001, named in that row above); 3.3.3/3.3.6's exports are built (`src/tekmerion/platform/exports.py`, the T542 pattern, demonstrated in `records/e6-audit-export-demonstration.md`); 3.8.4's marking fields ship in both export families (T551); 3.11.1/3.12.1/3.12.4's "control-state tracking" input is the T552 machinery (`src/tekmerion/platform/compliance.py`), whose classification table is generated from this document and pinned against it by test — the document and the machinery cannot drift silently. The E6 battery re-parses this document and asserts all 110 rows, classes 17 Platform / 51 Supports / 42 Organizational.
