# E5 conformance — the built console against the approved wireframes

**Captured:** 2026-10-12, from a locally served fixture instance of
the console itself (no public network involved). **Build identity:**
every page in this set carries the footer stamp
`BUILD_ID git-73306a753859+src-32fc32ca8003`, and `/build-id`
returned the same value during capture — the set is a single build,
verified by the stamp, not by liveness.

**Method:** the console was served in its labeled fixture mode
(`--fixture`; specimen identities, a real in-process OIDC provider,
real service calls throughout) and driven with Playwright at
1440×900 (desktop) and 390×844 (mobile). Each capture is the built
screen named for the approved wireframe screen it implements.

## Screen-by-screen verdicts

| Built screen | Wireframe | Verdict |
|---|---|---|
| signin (both) | `signin.html` | Matches, with the ratified Q8 deviation: the tenant picker is replaced by identifier entry, exactly as the owner-ratified recommendation block directs; the page enumerates no tenants. No password field exists. |
| tenants (both) | `tenants.html` | Matches. Dark platform shell, counts computed from the directory at request time. |
| tenant (both) | `tenant.html` | Matches. IdP configuration shown by secret reference and certificate fingerprint only. |
| tenant-idp (desktop) | `tenant.html` (IdP cards) | The tenant plane's own IdP screen renders the same approved cards from `/tenant/idp`; it is the tenant-scoped door to the same surface, not a new design. |
| users (both) | `users.html` | Matches. Tenant landing screen (Q3 as drawn). Grantor names resolve across the directory, including platform-plane grantors. |
| keys (both) | `keys.html` | Matches. All recorded key states render (enrolled / rotated / revoked / closed); custody is labeled in the wireframe's own honest terms ("not a KMS/HSM custody claim"). API-key scopes display as recorded; long action names wrap mid-token in narrow columns — a rendering property of the approved table, not a deviation. |
| events (both) | `events.html` | Matches, including Q4 inline row expansion of the full event record. |
| break-glass (both) | `break-glass.html` + step-1 extension pages | Matches the extension drawings for the states the fixture exercises (declared, active, closed/reviewed in the log). See the pending-confirmation note below. |
| break-glass-platform (both) | `break-glass.html` (platform variant) | Matches: per-tenant policy state, session logs, and the authorize/deny door where this plane is the declared second authorizer. |
| audit (both) | `audit.html` | Matches. Verification is a real action; the absence of any external anchor is stated on the screen, not implied away. |
| compliance (both) | `compliance.html` | Matches. The SPRS self-score is computed by the E6 machinery at request time (the battery proves it moves when a recorded state changes); the FIPS panel states the recorded position (0 of 13 operations on a validated module). The mobile capture is tile-stitched: the page is taller than Chromium's single-capture limit at that width — a capture artifact only. |
| status (both) | `status.html` | Matches. Ledger files, chain state, and delivery counts read live. |

## Standing differences, all ratified or recorded — none silent

1. **Q8 (ratified):** sign-in uses identifier entry instead of the
   drawn enumerated picker. The wireframe package's README records
   the ratification; the built page follows it.
2. **Q5 (ratified):** phase chips do not ship. State labels from the
   wireframes ship; task ids appear nowhere in the built console
   (asserted by the battery).
3. **Specimen values vs live values:** the wireframes draw specimen
   names, counts, and timestamps; the built screens show the served
   world's real records. Layout, structure, and copy are the
   wireframes'; the data is the service's.
4. **BUILD_ID footer:** every built page adds one line the
   wireframes do not draw — the served-artifact stamp (standing
   owner rule, 2026-10-12). It sits below the content in the footer
   position and changes no drawn element.
5. **CSP adjustment (recorded in the E5 exit record):** the §9
   baseline CSP (`default-src 'self'`) makes the design system's
   inline styles inert — under it the sign-in brand rendered
   white-on-paper (screenshot-verified during this work). The
   console serves the baseline headers with `style-src 'self'
   'unsafe-inline'` added; script posture is unchanged
   (`default-src 'self'` still governs scripts, and the console
   emits no inline script). `baseline.py` is untouched.
6. **Break-glass extension states:** the pending / declared /
   active / closed / review screens were implemented to the step-1
   extension wireframes drawn in this branch from the as-built E4
   mechanism. At capture time, coordinator confirmation of those
   renders was still in flight; the E5 exit record flags this
   prominently rather than treating it as settled.
