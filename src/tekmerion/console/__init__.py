"""Admin console (Spec 005 Phase E5, T535–T540).

A thin, local, server-side-rendered console over the platform
service layer (`tekmerion.platform`) — the same APIs every other
client uses; there are no console-only mutation paths (Spec 005
§7). The console registers no rules of its own: sign-in is the
platform's OIDC/SAML machinery (there is no local credential path,
CLM-005-01), authorization is the service's, and every refusal the
console shows is the service's message, verbatim.

Appearance is governed by the approved wireframes (constitution
Article XIV): gate T534-WF passed 2026-10-12 with the owner's
ratified recommendation block (see
`docs/wireframes/console/README.md`, addendum). The markup mirrors
`docs/wireframes/console/*.html` screen for screen; the stylesheets
served are the wireframes' own — `docs/wireframes/style.css` (via
`tekmerion.ui`) plus a byte-identical copy of
`docs/wireframes/console/console.css`. Ratified readings that
differ from the specimen drawings: tenant-by-identifier sign-in
(Q8), inline event-detail expansion (Q4), and phase chips stripped
— state labels ship, task ids do not (Q5).

Served-artifact identity: every page carries the BUILD_ID stamp
(`tekmerion.console.build`); `/build-id` serves it machine-readably.
"""

from .build import BUILD_ID
from .server import create_server, serve

__all__ = ["BUILD_ID", "create_server", "serve"]
