# Tekmerion — Admin Console Wireframes (Spec 005, Phase E5)

**Status:** T534-WF gate package, 2026-10-12 — **delivered for owner approval; NOT yet approved.**
**Gate:** task **T534-WF** (Spec 005, Phase E5). Under constitution Article XIV, **no admin-console implementation (T535+) may begin before the owner approves the rendered screenshots in this package.** Approving this package approves the console's layout and appearance as rendered — nothing else. This package contains **no implementation code**: no files under `src/` were added or changed, and the Phase 6 study UI and its approved wireframes (`docs/wireframes/*.html`, `style.css`, `WIREFRAMES.md`) are untouched.
**Companions:** Spec 005 `spec.md` §7 (console functional scope) · `plan.md` (E5 build order) · `tasks.md` (T534-WF…T540) · `cmmc-responsibility-matrix.md` · `crypto-inventory.md`.

## 1. Location & format

The console package lives with the wireframes Article XIV names — `docs/wireframes/` — in its own subdirectory (`console/`) so the approved Phase 6 package stays byte-identical. It mirrors that package's conventions exactly:

- Same shell, tokens, typography, chips, banners, tables, and 760px responsive behavior, inherited by linking `../style.css` **unmodified**, with console-only additions in `console.css` (plane system, sign-in layout, phase chips, gap panel, scope control). If this package is approved, `console.css` is part of what is approved.
- One `.screen-note` footer per page naming the screen and its data — package furniture, not product UI (Phase 6 convention).
- Screenshots in `screens/`, rendered by serving `docs/wireframes/` (`python3 -m http.server`) and capturing each page full-page at **1440×900** (desktop) and **390×844** (mobile) — the Phase 6 dimensions.

## 2. Screen inventory

| # | Screen | File | Plane | Screenshots |
|---|--------|------|-------|-------------|
| 1 | Sign-in & plane selection | `signin.html` | — | `screens/signin-desktop.png` · `screens/signin-mobile.png` |
| 2 | Tenant list | `tenants.html` | platform | `screens/tenants-desktop.png` · `screens/tenants-mobile.png` |
| 3 | Tenant detail — IdP (OIDC/SAML), SCIM, policy | `tenant.html` | platform | `screens/tenant-desktop.png` · `screens/tenant-mobile.png` |
| 4 | Users & roles — lifecycle state, role grants | `users.html` | tenant | `screens/users-desktop.png` · `screens/users-mobile.png` |
| 5 | Keys & bindings — lifecycle, custody, API keys | `keys.html` | tenant | `screens/keys-desktop.png` · `screens/keys-mobile.png` |
| 6 | Lifecycle events — ledger event stream | `events.html` | tenant | `screens/events-desktop.png` · `screens/events-mobile.png` |
| 7 | Audit-ledger inspector — chain state, export | `audit.html` | platform | `screens/audit-desktop.png` · `screens/audit-mobile.png` |
| 8 | Break-glass — policy & session log | `break-glass.html` | tenant | `screens/break-glass-desktop.png` · `screens/break-glass-mobile.png` |
| 9 | Compliance evidence — matrix, SPRS, POA&M, FIPS gap, CUI, DFARS | `compliance.html` | platform | `screens/compliance-desktop.png` · `screens/compliance-mobile.png` |
| 10 | System status — ledger verification, §9 baseline | `status.html` | platform | `screens/status-desktop.png` · `screens/status-mobile.png` |

This covers every surface T534-WF and Spec 005 §7 name — tenant, IdP, user, role, key, audit, break-glass log — plus the compliance views §13.7 assigns to E6 machinery (drawn now because the console is where they will live) and system status.

## 3. Plane separation (the structural requirement)

The two admin planes are **disjoint** (Spec 005 §5, CLM-005-09): no plane's authority implies the other's, and a platform admin holds no study powers. The wireframes make the disjointness *visible and structural*, not a label:

- **Platform plane** — the dark brand sidebar (deployment scope block, platform nav: Tenants · Audit ledger · Compliance · System status) + a solid brand **plane strip** at the top of every screen naming the plane and its scope.
- **Tenant plane** — a **light sidebar** on paper (tenant block, tenant nav: Users & roles · Keys & bindings · Lifecycle events · Break-glass) + a tinted plane strip naming the tenant and stating the session can reach no other tenant.
- **Sign-in** (screen 1) is where the planes divide: two distinct entry cards, authentication always at an IdP. **There is no password field anywhere in the console** — there are no local credentials (CLM-005-01); a screen asking for one is not this product.
- Affordances follow the Phase 6 rule: in a plane, the other plane's controls are **absent, not disabled** (a tenant session's inspector has no deployment-ledger segment to grey out; it does not exist in that view).

## 4. Data grounding — what is real, what is specimen

Wireframes promise only views the platform data can fill (E1/E2 surface: `src/tekmerion/platform/` — tenants with shape/region, per-tenant OIDC + SAML configs, identities with lifecycle state, the key registry, scoped API keys, the two-scope audit ledgers, the AU event vocabulary).

- **Real formats and vocabularies:** event names (`key.enrolled`, `auth.login_failed`, `authz.decision_denied`, …) are the shipped ledger constants; key states (enrolled / rotated / revoked / closed), custody modes, role names, session defaults (idle 30 min, absolute 12 h, step-up freshness 600 s), and policy fields are the service layer's own.
- **Real numbers:** the compliance matrix counts (110 requirements — 17 Platform · 51 Supports · 42 Organizational, and every per-family row) were computed from `cmmc-responsibility-matrix.md` on main, 2026-10-12; the crypto inventory's 12 operations / 0 FIPS-validated is its recorded state.
- **Specimen values, labeled as such on every screen:** tenants `uni-a` / `uni-b`, issuer and SAML entity IDs, and users (alice, mallory) are modeled on the E1/E2 **test fixtures** — no deployment exists yet. Fingerprints, checkpoint roots, counts, and timestamps are specimen values in the record's real formats. Secrets and certificates appear **by reference / fingerprint only**, on every screen, without exception; no key material exists in this package.
- **Honest not-yet states are drawn, not omitted:** SCIM "not configured" (E3), SPRS "not computed" with CLM-005-29 draft, break-glass "no policy declared — cannot be invoked," external anchor "none recorded," webhook egress "not built." The dashed **phase chips** (`E6 · T552`) name the work that makes each depicted element real — see Q5.

## 5. Screen → phase mapping

| Screen | Built by | Depends on (state today) |
|--------|----------|---------------------------|
| 1 Sign-in & planes | T535 | E1/E2 session + step-up (landed) |
| 2 Tenant list | T535 | tenant service (landed, E1) |
| 3 Tenant detail / IdP | T536 | OIDC config (E1 ✓) · SAML config (E2 ✓) · SCIM card (E3, in flight) · residency-pin change flow (E6 · T541) |
| 4 Users & roles | T537 | grants/lifecycle (E1 ✓) · deprovisioning completion (E3) |
| 5 Keys & bindings | T538 | key registry + API keys (E1 ✓) · countersign flows (T538) |
| 6 Lifecycle events | T537/T539 | AU event stream (E1 ✓) · SCIM outcomes join the stream (E3) |
| 7 Audit inspector | T539 | ledger core (E1 ✓) · export machinery (E6 · T542) · anchored demo (E6 · T543) · platform↔study join (E4 · CLM-005-22) |
| 8 Break-glass | T539 | mechanism — policy, dual auth, alarming, review items (E4 · T529; IR egress E4 · T554) |
| 9 Compliance | console surface E5; content E6 | matrix (maintained ✓) · SPRS inputs (E6 · T552) · POA&M register (E6 · T553) · CUI marking render (E6 · T551) · SOC 2 mapping doc (E6 · T544) |
| 10 System status | T535/T539 | ledger verification (✓) · session/transport battery (E4 · T530) · webhook egress (E4 · T531) |

Variants noted on the screens themselves: tenant.html's IdP/policy sections reappear under the tenant shell for tenant-admin self-service (T536); audit.html's inspector is fixed to the tenant's own ledger in the tenant plane; break-glass.html's platform variant lists all tenants' policy states. Variants change shell and scope, not layout.

## 6. Design tokens (additions only)

Inherited unchanged from `WIREFRAMES.md` §3. Console additions, all in `console.css`: `--brand` plane strip (platform) and `--brand-tint` strip (tenant); the light tenant sidebar treatment; `.phase-chip` (mono, dashed border — deliberately *not* a status color); `.gap-card` (invalid-palette left rule for standing non-satisfactions); `.seg` scope control; `.chip.custody` (neutral — custody is a fact, not a status). No status color is used decoratively; verdict palettes remain reserved to their statuses.

## 7. Open design questions for the owner

Each is a genuine choice the build will otherwise have to guess at; the package as drawn takes the first option in each case.

- **Q1 — Density.** The console inherits the study UI's comfortable density. Ledger-scale admin data often runs denser (tighter rows, 13px tables). Keep inherited density for one-product consistency, or approve a denser console table treatment?
- **Q2 — Navigation model.** Drawn: two separate plane shells with disjoint navs — disjointness made structural. Alternative: one shell with an explicit plane switcher for the rare operator who holds both. Switcher is faster; separate shells can never be mistaken for each other.
- **Q3 — Tenant-plane landing screen.** Drawn: tenant admins land on Users & roles. Alternative: a tenant overview (counts, IdP state, recent events, open items) as the landing screen — one more screen to approve and build under T535.
- **Q4 — Event detail depth.** Event rows (screens 6–7) show the AU content set. A payload-level event detail (full event JSON, signature, chain links) is not drawn: row-expansion, a dedicated detail view, or unnecessary because export + standalone verification is the inspection path?
- **Q5 — Phase chips in the product.** The dashed phase chips are honesty furniture on the wireframes. Do they ship in the product UI — a visible "this lands in E6" label until the phase lands, then removed by wireframe amendment — or are they wireframe-only annotations the build strips?
- **Q6 — Break-glass invocation flow.** This package draws policy + log (the states that exist). The invoke → second-authorizer → active-session flow belongs to E4's mechanism (T529): draw and approve those screens with E4, or draw specimens now so the E5 shell already accounts for an active-session banner?
- **Q7 — Compliance audience.** Drawn in the platform plane (the deployment's own evidence). Tenant admins will need their slice (their POA&M items, their marking fields). Same screen under the tenant shell at tenant scope, or platform-only in v1?
- **Q8 — Sign-in tenant discovery.** Drawn: a picker enumerating tenants. For the hosted shape that discloses tenant names to anyone who reaches the page; the alternative is tenant-by-identifier entry (type your tenant ID or domain, no list). Which posture for hosted? (Self-hosted single-tenant is unaffected.)

## 8. What approval does and does not do

Approving this package (the rendered screenshots, per Article XIV) passes gate **T534-WF** and authorizes T535+ implementation to build *to these screens*. It does not approve: any E3/E4/E6 machinery the screens depend on (each keeps its own phase gate), any change to the Phase 6 study UI, or any claim state — the claims these screens touch (CLM-005-13 above all) are re-assessed at E5's phase exit with build evidence, per the Spec 005 plan. Changes after approval follow the Phase 6 process: amend the wireframes here, re-render, re-approve, then build.
