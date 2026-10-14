"""HTTP server for the admin console (Spec 005, E5).

Stdlib `http.server`, server-side rendering, the Phase 6 discipline:
the console is a thin adapter over `PlatformService` — every read is
the service's own read model (directory, registries, ledgers, the E6
compliance machinery) and every mutation is a service method call.
There are no console-only mutation paths (Spec 005 §7), and every
refusal the console renders is the service's exception message,
verbatim, in the wireframes' refusal treatment.

Plane separation is structural (CLM-005-09): the route trees are
disjoint — `/platform/*` resolves only for a session whose identity
holds `platform_admin` at deployment scope; `/tenant/*` resolves
only for a session holding `tenant_admin` in the session's own
tenant, and the tenant of every tenant-plane read and write is the
session's tenant, never a request parameter. A session from the
other plane gets the sign-in screen (unauthenticated treatment),
not the other plane's shell with disabled controls: the controls
do not exist for it.

Sign-in is the platform's own machinery: the console calls
`begin_login` / `begin_saml_login` and the completion endpoints are
the service's `complete_login` / `complete_saml_login` (ACS). There
is no password field anywhere in the console (CLM-005-01).

State-changing POSTs carry a per-session CSRF token (Spec 013
CLM-013-32): a hidden field in every form the console renders for a
session, keyed to the session token and a per-process secret, and
verified before any service call — the console's defense does not
rest on the session cookie's SameSite attribute alone. The login
endpoints and the SAML ACS are exempt: they are how a session is
created, and the ACS is posted by the identity provider and
validated by its signature.

Every response carries the §9 baseline headers
(`tekmerion.platform.baseline.security_headers` — this console is
the contract's first HTTP adapter) and the session cookie is the
baseline's rendering. Every page carries the BUILD_ID stamp.
"""

from __future__ import annotations



import hashlib
import hmac
import json
import re
import secrets
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional

from ..platform import baseline
from ..platform.authz import ALL_GRANTABLE_ROLES, STUDY_ROLES
from ..platform.directory import IdPConfig
from ..platform.errors import PlatformError
from ..platform.matrix_data import MATRIX_CLASSES
from ..platform.service import PLATFORM_TENANT_ID, PlatformService
from . import views
from .build import BUILD_ID

_LOCK = threading.Lock()
_SESSION_COOKIE = baseline.SESSION_COOKIE_NAME

#: The §9 baseline CSP is `default-src 'self'` — correct for an API
#: adapter, but the approved wireframe design system (like the Phase
#: 6 study UI before it) carries data-driven INLINE styles: meter
#: widths, stat-grid column counts, the sidebar actor chip, the
#: standalone pages' brand color. Served under the unmodified
#: baseline CSP those attributes are inert and the console does NOT
#: render as approved (verified by screenshot: the sign-in brand
#: rendered white-on-paper). The console therefore serves the
#: baseline headers with one bounded adjustment: style-src gains
#: 'unsafe-inline'. Script posture is unchanged — default-src
#: 'self' still governs script-src, and the console emits no inline
#: script anywhere. baseline.py itself is untouched; this is a
#: console-local serving decision, recorded in the E5 exit record.
CONSOLE_CSP = ("default-src 'self'; style-src 'self' 'unsafe-inline'; "
               "frame-ancestors 'none'")


# ------------------------------------------------------------ data helpers

def _tenants(directory) -> list:
    return list(directory.tenants.values())


def _identities(directory, tenant_id: str) -> list:
    return [i for i in directory.identities.values()
            if i.tenant_id == tenant_id]



def _saml_idps(directory, tenant_id: str) -> list:
    return [c for c in directory.saml_idps.values()
            if c.tenant_id == tenant_id]

def _api_keys(directory, tenant_id: str) -> list:
    return [k for k in directory.api_keys.values()
            if k.tenant_id == tenant_id]


def _name_of(directory, tenant_id: str, identity_id: Optional[str]) -> str:
    if not identity_id:
        return "—"
    ident = directory.identity(identity_id)
    if ident is None:
        return "—"
    return ident.display_name or ident.subject


def _actor_names(directory, tenant_id: str) -> dict[str, str]:
    return {i.actor_id: (i.display_name or i.subject)
            for i in _identities(directory, tenant_id)}


def _latest_checkpoint(events: list[dict]) -> Optional[str]:
    for ev in reversed(events):
        if ev.get("type") == "checkpoint":
            return (ev.get("payload") or {}).get("merkle_root")
    return None


def _latest_anchor(events: list[dict]) -> Optional[dict]:
    for ev in reversed(events):
        if ev.get("type") == "audit.export_anchored":
            return ev.get("payload") or {}
    return None


def _tenant_events(service: PlatformService, tenant_id: str) -> list[dict]:
    ledger = (service.deployment_ledger if tenant_id == PLATFORM_TENANT_ID
              else service._tenant_ledger(tenant_id))
    return ledger.events()


def _event_ts(ev: dict) -> Any:
    p = ev.get("payload") or {}
    return p.get("ts") or p.get("ts_utc") or p.get("at") or 0


def _first_seen(service: PlatformService, tenant_id: str) -> dict[str, Any]:
    """identity_id -> created ts, from the identity.created events."""
    out: dict[str, Any] = {}
    for ev in _tenant_events(service, tenant_id):
        if ev.get("type") == "identity.created":
            p = ev.get("payload") or {}
            if p.get("identity_id"):
                out[p["identity_id"]] = _event_ts(ev)
    return out


#: POST endpoints that run before a session exists (login starts),
#: or that are posted by the identity provider rather than by a
#: console form (the SAML ACS). Every other POST requires the
#: session's CSRF token (Spec 013 CLM-013-32).
_CSRF_EXEMPT_POSTS = frozenset({
    "/auth/platform/oidc", "/auth/tenant/start", "/auth/saml/acs",
    "/fixture/idp/authorize",
})


def _inject_csrf_fields(body: str, token: str) -> str:
    """Embed the session's CSRF token in a rendered page: a hidden
    field in every POST form, and a meta tag in the head for
    programmatic clients. Neither changes anything the page looks
    like."""
    if "<head>" in body:
        body = body.replace(
            "<head>", f'<head><meta name="csrf-token" content="{token}">', 1)
    return re.sub(
        r'(<form\s+method="post"[^>]*>)',
        rf'\1<input type="hidden" name="csrf_token" value="{token}">',
        body)


class ConsoleApp:
    """Binds a PlatformService to the console's routes."""

    def __init__(self, service: PlatformService, *, fixture=None,
                 exports_dir: Optional[Path] = None) -> None:
        self.service = service
        self.fixture = fixture  # FixtureWorld | None (tests/screenshots only)
        self.exports_dir = Path(exports_dir) if exports_dir else \
            Path(service.root) / "console-exports"
        self._stepup_pending: dict[str, dict] = {}
        self._csrf_secret = secrets.token_bytes(32)
        # The token for the session whose page is being rendered.
        # `handle` runs under the module lock, so one value at a
        # time is exact, never racy.
        self._active_csrf: Optional[str] = None

    # ------------------------------------------------------------ CSRF

    def csrf_token_for(self, session_token: str) -> str:
        """The per-session CSRF token: keyed to the session token
        and to this process's secret, so a page that does not hold
        the session cannot compute it (Spec 013 CLM-013-32)."""
        msg = f"csrf:{session_token}".encode("utf-8")
        return hmac.new(self._csrf_secret, msg, hashlib.sha256).hexdigest()

    def _csrf_ok(self, session_token: Optional[str], form: dict) -> bool:
        if not session_token:
            return False
        supplied = form.get("csrf_token") or ""
        if not isinstance(supplied, str):
            return False
        return hmac.compare_digest(
            supplied.encode("utf-8"),
            self.csrf_token_for(session_token).encode("utf-8"))

    @staticmethod
    def _csrf_refusal():
        raise PlatformError(
            "this submission did not carry the session's CSRF token, "
            "so it was refused and nothing was changed (Spec 013 "
            "CLM-013-32) — reload the page and submit the form as "
            "rendered")

    # ------------------------------------------------------ session/plane

    def session_identity(self, token: Optional[str]):
        """(session, identity) or (None, None). Read-only peek: the
        console never resolves (and thereby never mutates) a session
        it is about to refuse at the routing layer."""
        if not token:
            return None, None
        session = self.service.directory.session(token)
        if session is None or session.revoked:
            return None, None
        identity = self.service.directory.identity(session.identity_id)
        if identity is None or not identity.active:
            return None, None
        return session, identity

    def planes_for(self, token: str, identity) -> dict[str, bool]:
        svc = self.service
        platform = "platform_admin" in svc.roles_of(identity.identity_id, None)
        tenant = bool(identity.tenant_id != PLATFORM_TENANT_ID
                      and "tenant_admin" in svc.roles_of(
                          identity.identity_id, identity.tenant_id))
        return {"platform": platform, "tenant": tenant}

    def _ctx(self, token: str, identity, session) -> dict:
        directory = self.service.directory
        stepped = bool(session and session.stepped_up_at and
                       (time.time() - session.stepped_up_at) <=
                       directory.tenant(identity.tenant_id).policy.stepup_freshness_seconds)
        return {"build_id": BUILD_ID,
                "actor_name": identity.display_name or identity.subject,
                "tenant_count": len([t for t in _tenants(directory)
                                     if t.tenant_id != PLATFORM_TENANT_ID]),
                "stepped_up": stepped}

    def _tenant_ctx(self, token: str, identity, session) -> dict:
        ctx = self._ctx(token, identity, session)
        tenant = self.service.directory.tenant(identity.tenant_id)
        ctx.update({"tenant_name": tenant.name, "tenant_id": tenant.tenant_id,
                    "user_count": len(_identities(self.service.directory,
                                                  tenant.tenant_id))})
        return ctx

    # ------------------------------------------------------------ routing

    def handle(self, method: str, path: str, query: dict, form: dict,
               cookies: dict) -> tuple[int, list[tuple[str, str]], bytes]:
        try:
            with _LOCK:
                return self._dispatch(method, path, query, form, cookies)
        except PlatformError as exc:
            return self._refusal_page(cookies, str(exc))
        except Exception as exc:  # noqa: BLE001 — a console 500 states itself
            return 500, [("Content-Type", "text/plain; charset=utf-8")], \
                f"console error: {type(exc).__name__}: {exc}".encode("utf-8")

    def _dispatch(self, method, path, query, form, cookies):
        self._active_csrf = None
        token = cookies.get(_SESSION_COOKIE)
        # Public + identity surfaces.
        if path == "/build-id":
            return self._json({"app": "tekmerion-console", "build_id": BUILD_ID})
        if path == "/static/style.css" or path == "/static/console.css":
            return self._static(path)
        if path == "/favicon.ico":
            return 204, [], b""
        if self.fixture is not None and path == "/fixture/idp/authorize":
            return self._fixture_authorize(method, query, form)
        if path.startswith("/auth/"):
            return self._auth(method, path, query, form, cookies)
        session, identity = self.session_identity(token)
        if session is not None:
            self._active_csrf = self.csrf_token_for(token)
        if path == "/":
            if session is None:
                return self._html(views.render_signin(self._signin_ctx()))
            planes = self.planes_for(token, identity)
            if planes["platform"] and planes["tenant"]:
                return self._html(views.render_plane_choice(
                    {**self._ctx(token, identity, session)}))
            if planes["platform"]:
                return self._redirect("/platform/tenants")
            if planes["tenant"]:
                return self._redirect("/tenant/users")
            return self._html(views.render_no_plane(
                {**self._ctx(token, identity, session)}))
        if session is None:
            return self._html(views.render_signin(self._signin_ctx()))
        if method == "POST" and path not in _CSRF_EXEMPT_POSTS \
                and not self._csrf_ok(token, form):
            self._csrf_refusal()
        planes = self.planes_for(token, identity)
        if path.startswith("/platform/"):
            if not planes["platform"]:
                return self._html(views.render_signin(self._signin_ctx()))
            try:
                return self._platform(method, path, query, form, token,
                                      identity, session)
            except PlatformError as exc:
                return self._platform("GET", self._screen_path(path),
                                      {**query, "refusal": str(exc)}, {},
                                      token, identity, session)
        if path.startswith("/tenant/"):
            if not planes["tenant"]:
                return self._html(views.render_signin(self._signin_ctx()))
            try:
                return self._tenant(method, path, query, form, token,
                                    identity, session)
            except PlatformError as exc:
                return self._tenant("GET", self._screen_path(path),
                                    {**query, "refusal": str(exc)}, {},
                                    token, identity, session)
        return self._html(views.render_signin(self._signin_ctx()))

    @staticmethod
    def _screen_path(path: str) -> str:
        """The screen a POST action belongs to — refusals re-render
        on the originating screen (the Phase 6 discipline)."""
        parts = [p for p in path.split("/") if p]
        if parts[:1] == ["platform"] and len(parts) >= 3 and parts[1] == "tenants":
            return f"/platform/tenants/{parts[2]}"
        if parts[:1] == ["platform"] and len(parts) >= 2:
            return f"/platform/{parts[1]}"
        if parts[:1] == ["tenant"] and len(parts) >= 2:
            return f"/tenant/{parts[1]}"
        return path

    # ------------------------------------------------------------ helpers

    def _html(self, body: str, status: int = 200):
        if self._active_csrf:
            body = _inject_csrf_fields(body, self._active_csrf)
        return status, [("Content-Type", "text/html; charset=utf-8")], \
            body.encode("utf-8")

    def _json(self, obj: dict, status: int = 200):
        return status, [("Content-Type", "application/json")], \
            json.dumps(obj).encode("utf-8")

    def _redirect(self, location: str, cookie: Optional[str] = None):
        headers = [("Location", location)]
        if cookie is not None:
            headers.append(("Set-Cookie",
                            baseline.render_session_cookie(cookie)))
        return 303, headers, b""

    def _static(self, path: str):
        from .. import ui as _ui_pkg  # console ships the Phase 6 base sheet
        if path.endswith("console.css"):
            data = (Path(__file__).parent / "console.css").read_bytes()
        else:
            data = (Path(_ui_pkg.__file__).parent / "style.css").read_bytes()
        return 200, [("Content-Type", "text/css; charset=utf-8")], data

    def _refusal_page(self, cookies, message: str):
        """A service refusal outside a screen's own rendering (auth
        completions): the sign-in screen carries it, in the
        wireframes' refusal treatment."""
        ctx = self._signin_ctx()
        ctx["refusal"] = f"auth.login_failed — {message}"
        return self._html(views.render_signin(ctx), status=200)

    def _signin_ctx(self) -> dict:
        directory = self.service.directory
        idps = [{"issuer": c.issuer}
                for c in directory.idps_for_tenant(PLATFORM_TENANT_ID)]
        return {"build_id": BUILD_ID, "platform_idps": idps, "refusal": None}

    # --------------------------------------------------------------- auth

    def _auth(self, method, path, query, form, cookies):
        svc = self.service
        if path == "/auth/logout" and method == "POST":
            token = cookies.get(_SESSION_COOKIE)
            if token and self.session_identity(token)[0] is not None \
                    and not self._csrf_ok(token, form):
                self._csrf_refusal()
            if token:
                try:
                    svc.logout(token)
                except PlatformError:
                    pass
            headers = [("Location", "/"),
                       ("Set-Cookie", baseline.render_session_cookie(""))]
            return 303, headers, b""
        if path == "/auth/platform/oidc" and method == "POST":
            issuer = form.get("issuer", "")
            url = svc.begin_login(PLATFORM_TENANT_ID, issuer)
            return self._redirect(self._idp_location(url))
        if path == "/auth/tenant/start" and method == "POST":
            tenant_id = (form.get("tenant_id") or "").strip()
            protocol = form.get("protocol", "oidc")
            tenant = svc.directory.tenant(tenant_id)  # raises, verbatim
            if protocol == "saml":
                samls = _saml_idps(svc.directory, tenant_id)
                if not samls:
                    raise PlatformError(
                        f"no SAML IdP is configured for tenant {tenant_id}")
                url = svc.begin_saml_login(tenant_id, samls[0].idp_entity_id)
                return self._redirect(url)
            idps = svc.directory.idps_for_tenant(tenant_id)
            if not idps:
                raise PlatformError(
                    f"no OIDC IdP is configured for tenant {tenant_id}")
            url = svc.begin_login(tenant_id, idps[0].issuer)
            return self._redirect(self._idp_location(url))
        if path == "/auth/oidc/callback" and method == "GET":
            state = query.get("state", "")
            if state in self._stepup_pending:
                return self._step_up_oidc_callback(query, cookies)
            token = svc.complete_login(state, query.get("code", ""))
            return self._redirect("/", cookie=token)
        if path == "/auth/saml/acs" and method == "POST":
            # The tenant (and the flow's purpose) is bound by the
            # RelayState's pending record, never by a form field:
            # the service resolves them from state it minted.
            relay = form.get("RelayState", "")
            pending = svc._pending_auth.get(relay)
            if pending is None or pending.get("protocol") != "saml":
                raise PlatformError("SAML response carries no pending state")
            if pending.get("purpose") == "stepup":
                token = svc.complete_saml_step_up(
                    relay, form.get("SAMLResponse", ""))
                return self._redirect("/", cookie=token)
            token = svc.complete_saml_login(
                pending["tenant_id"], pending["idp_entity_id"], relay,
                form.get("SAMLResponse", ""))
            return self._redirect("/", cookie=token)
        if path == "/auth/step-up" and method == "GET":
            return self._step_up_start(cookies)
        return self._html(views.render_signin(self._signin_ctx()))

    def _idp_location(self, url: str) -> str:
        if self.fixture is not None:
            rewritten = self.fixture.rewrite(url)
            if rewritten is not None:
                return rewritten
        return url

    def _step_up_start(self, cookies):
        svc = self.service
        token = cookies.get(_SESSION_COOKIE)
        session, identity = self.session_identity(token)
        if session is None:
            return self._html(views.render_signin(self._signin_ctx()))
        try:
            idp = svc.directory.idp(identity.tenant_id, identity.issuer)
        except PlatformError:
            idp = None
        if idp is not None:
            # OIDC: a fresh authorization round-trip for a fresh
            # id_token, at the IdP config's registered redirect URI;
            # the nonce is bound server-side to this session and the
            # callback discriminates step-up states from logins.
            from ..platform.oidc import pkce_pair
            nonce = svc.begin_step_up(token)  # Spec 013: server-issued challenge
            verifier, challenge = pkce_pair()
            state = secrets.token_urlsafe(24)
            self._stepup_pending[state] = {
                "session_token": token, "nonce": nonce, "verifier": verifier,
                "issuer": identity.issuer, "tenant_id": identity.tenant_id}
            url = svc.oidc.authorization_url(
                issuer=identity.issuer, client_id=idp.client_id,
                redirect_uri=idp.redirect_uri,
                state=state, nonce=nonce, code_challenge=challenge,
                acr_values="https://refeds.org/profile/mfa")
            return self._redirect(self._idp_location(url))
        # SAML session: the service's own step-up flow; its response
        # lands on the tenant's ACS, where the pending record's
        # purpose routes it to complete_saml_step_up.
        return self._redirect(svc.begin_saml_step_up(token))

    def _step_up_oidc_callback(self, query, cookies):
        svc = self.service
        pending = self._stepup_pending.pop(query.get("state", ""), None)
        if pending is None:
            raise PlatformError("step-up state unknown or already consumed")
        idp = svc.directory.idp(pending["tenant_id"], pending["issuer"])
        secret = svc.secrets.get(idp.client_secret_ref) if idp else None
        tokens = svc.oidc.exchange_code(
            issuer=pending["issuer"], client_id=idp.client_id,
            client_secret=secret or "", redirect_uri=idp.redirect_uri,
            code=query.get("code", ""), code_verifier=pending["verifier"])
        id_token = tokens.get("id_token")
        if not id_token:
            raise PlatformError("step-up token response carried no ID token")
        svc.step_up(pending["session_token"], id_token=id_token,
                    nonce=pending["nonce"])
        return self._redirect("/")

    # ------------------------------------------------------- fixture IdP

    def _fixture_authorize(self, method, query, form):
        """The fixture IdP's authorization endpoint, served locally:
        a labeled interstitial whose ceremony is choosing the
        specimen user (see fixture.py's docstring)."""
        idp = self.fixture.idp
        if method == "GET":
            issuer = query.get("issuer", "")
            users = idp.users_for(issuer)
            options = "".join(
                f'<option value="{views.e(s)}">{views.e(label)}</option>'
                for s, label in users)
            hidden = "".join(
                f'<input type="hidden" name="{views.e(k)}" value="{views.e(v)}">'
                for k, v in query.items())
            body = f"""<div class="signin-wrap">
  <div class="signin-head">
    <div class="brand-name" style="color:var(--brand)">FIXTURE IDENTITY PROVIDER</div>
    <div class="brand-tag" style="color:var(--ink-3)">Specimen — not a real IdP</div>
    <h1 style="margin-top:14px">Authenticate at {views.e(issuer)}</h1>
    <p class="page-sub">This console is running in <strong>fixture mode</strong>. In a
      deployment you would now be at your institution's identity provider, proving
      your identity (with MFA, where the tenant's policy requires it). The fixture
      IdP's ceremony is choosing the specimen user; the service still validates the
      resulting token — signature, PKCE, nonce, MFA claims — exactly as in production.</p>
  </div>
  <div class="card">
    <form method="post" action="/fixture/idp/authorize">
      {hidden}
      <div class="field"><label>Specimen user</label>
        <select name="subject">{options}</select></div>
      <div class="row-actions" style="margin-bottom:0">
        <button class="btn primary" type="submit">Continue as this user</button>
      </div>
    </form>
  </div>
  {views.build_footer(BUILD_ID)}
</div>"""
            return self._html(views.page("Fixture identity provider", body))
        issuer = form.get("issuer", "")
        code = idp.issue_code(issuer, form.get("subject", ""),
                              challenge=form.get("code_challenge", ""),
                              nonce=form.get("nonce", ""))
        redirect_uri = form.get("redirect_uri", "/")
        sep = "&" if "?" in redirect_uri else "?"
        location = (f"{redirect_uri}{sep}code={urllib.parse.quote(code)}"
                    f"&state={urllib.parse.quote(form.get('state', ''))}")
        return self._redirect(location)

    # ------------------------------------------------------ platform plane

    def _platform(self, method, path, query, form, token, identity, session):
        svc = self.service
        ctx = self._ctx(token, identity, session)
        parts = [p for p in path.split("/") if p]
        if parts == ["platform", "tenants"] and method == "GET":
            return self._html(views.render_tenants(
                self._tenants_ctx(ctx, query)))
        if parts == ["platform", "tenants"] and method == "POST":
            svc.create_tenant(token, tenant_id=form.get("tenant_id", ""),
                              name=form.get("name", ""),
                              shape=form.get("shape", "hosted"),
                              region=form.get("region", ""))
            return self._html(views.render_tenants(self._tenants_ctx(
                ctx, query, notice=f"tenant.created — {form.get('tenant_id', '')}")))
        if len(parts) >= 3 and parts[:2] == ["platform", "tenants"]:
            tenant_id = parts[2]
            sub = "/".join(parts[3:])
            return self._tenant_admin(method, sub, query, form, token,
                                      tenant_id, ctx, variant="platform")
        if parts == ["platform", "audit"]:
            return self._html(views.render_audit(
                self._audit_ctx(ctx, token, query)))
        if parts == ["platform", "audit", "export"] and method == "POST":
            return self._audit_export(form, token, ctx, query)
        if parts == ["platform", "compliance"]:
            return self._html(views.render_compliance(
                self._compliance_ctx(ctx, token, query)))
        if parts == ["platform", "compliance", "sprs-seed"] and method == "POST":
            svc.seed_control_states(token)
            return self._html(views.render_compliance(self._compliance_ctx(
                ctx, token, query, notice="compliance.states_seeded")))
        if parts == ["platform", "compliance", "poam-create"] and method == "POST":
            svc.poam_create_item(
                token, title=form.get("title", ""),
                weakness=form.get("weakness", ""),
                affected_requirements=[r.strip() for r in
                                       form.get("requirements", "").split(",")
                                       if r.strip()],
                source_ref=form.get("source_ref", ""),
                owner=form.get("owner", ""), tenant_id=None)
            return self._html(views.render_compliance(self._compliance_ctx(
                ctx, token, query, notice="poam.item_created")))
        if parts == ["platform", "compliance", "poam-status"] and method == "POST":
            svc.poam_set_status(token, item_id=form.get("item_id", ""),
                                status=form.get("status", ""), tenant_id=None)
            return self._html(views.render_compliance(self._compliance_ctx(
                ctx, token, query, notice="poam.status_changed")))
        if parts == ["platform", "compliance", "poam-milestone"] and method == "POST":
            svc.poam_add_milestone(token, item_id=form.get("item_id", ""),
                                   text=form.get("text", ""), tenant_id=None)
            return self._html(views.render_compliance(self._compliance_ctx(
                ctx, token, query, notice="poam.milestone_added")))
        if parts == ["platform", "status"]:
            return self._html(views.render_status(self._status_ctx(ctx, token)))
        if parts == ["platform", "break-glass"]:
            return self._html(views.render_break_glass_platform(
                self._bg_platform_ctx(ctx, token, query)))
        if parts == ["platform", "break-glass", "authorize"] and method == "POST":
            svc.authorize_break_glass(
                token, bg_session_id=form.get("bg_session_id", ""))
            return self._html(views.render_break_glass_platform(
                self._bg_platform_ctx(ctx, token, query,
                                      notice="breakglass.authorized")))
        if parts == ["platform", "break-glass", "deny"] and method == "POST":
            svc.deny_break_glass(
                token, bg_session_id=form.get("bg_session_id", ""))
            return self._html(views.render_break_glass_platform(
                self._bg_platform_ctx(ctx, token, query,
                                      notice="breakglass.authorization_denied")))
        return self._html(views.render_tenants(self._tenants_ctx(ctx, query)))

    def _tenants_ctx(self, ctx, query, refusal=None, notice=None):
        svc = self.service
        directory = svc.directory
        tenants = []
        total_identities = 0
        total_keys = 0
        for t in _tenants(directory):
            ids = _identities(directory, t.tenant_id)
            n_keys = len(svc.registry(t.tenant_id).keys)
            total_identities += len(ids)
            total_keys += n_keys
            if t.tenant_id == PLATFORM_TENANT_ID:
                continue
            scim_state = svc.scim.peek(t.tenant_id)
            tenants.append({
                "tenant_id": t.tenant_id, "name": t.name, "shape": t.shape,
                "region": t.region, "active": t.active,
                "oidc": directory.idps_for_tenant(t.tenant_id),
                "saml": _saml_idps(directory, t.tenant_id),
                "identities": len(ids), "keys": n_keys,
                "scim": bool(scim_state) and any(
                    not c.revoked for c in scim_state.credentials.values()),
            })
        platform = [t for t in _tenants(directory)
                    if t.tenant_id == PLATFORM_TENANT_ID][0]
        return {**ctx, "tenants": tenants,
                "platform_tenant": {
                    "tenant_id": platform.tenant_id,
                    "identities": len(_identities(directory, PLATFORM_TENANT_ID))},
                "stats": {"tenants": len(tenants),
                          "identities": total_identities, "keys": total_keys,
                          "deployment_events": len(_tenant_events(svc, PLATFORM_TENANT_ID))},
                "refusal": refusal or query.get("refusal"),
                "notice": notice or query.get("notice")}

    # ------------------------------------------- tenant administration
    # (platform variant: /platform/tenants/<id>/...; tenant variant:
    #  /tenant/idp — same sections, the session's own tenant)

    def _tenant_admin(self, method, sub, query, form, token, tenant_id, ctx,
                      variant):
        svc = self.service
        if method == "GET" and sub in ("", "idp"):
            return self._html(views.render_tenant_detail(
                self._tenant_detail_ctx(ctx, token, tenant_id, variant, query)))
        if method == "POST" and sub == "residency":
            svc.change_residency_pin(token, tenant_id=tenant_id,
                                     shape=form.get("shape", ""),
                                     region=form.get("region", ""))
            return self._html(views.render_tenant_detail(self._tenant_detail_ctx(
                ctx, token, tenant_id, variant, query,
                notice="tenant.residency_migrated")))
        if method == "POST" and len(sub.split("/")) == 2 and sub.startswith("idp/"):
            kind = sub.split("/")[1]
            if variant == "platform":
                if kind == "oidc":
                    secret = form.get("client_secret", "")
                    if not secret:
                        try:
                            existing = svc.directory.idp(
                                tenant_id, form.get("issuer", ""))
                            secret = svc.secrets.get(existing.client_secret_ref)
                        except PlatformError:
                            secret = ""
                    svc.provision_tenant_idp(token, IdPConfig(
                        tenant_id=tenant_id, issuer=form.get("issuer", ""),
                        client_id=form.get("client_id", ""),
                        client_secret_ref=form.get("client_secret_ref", ""),
                        redirect_uri=form.get("redirect_uri", "")),
                        client_secret=secret or "")
                else:
                    svc.provision_tenant_saml_idp(
                        token, tenant_id=tenant_id, sp_entity_id=form.get("sp_entity_id", ""),
                        acs_url=form.get("acs_url", ""),
                        metadata_xml=form.get("metadata_xml", ""),
                        subject_source=form.get("subject_source", "nameid"))
            else:
                if kind == "oidc":
                    secret = form.get("client_secret", "")
                    if not secret:
                        try:
                            existing = svc.directory.idp(
                                tenant_id, form.get("issuer", ""))
                            secret = svc.secrets.get(existing.client_secret_ref)
                        except PlatformError:
                            secret = ""
                    svc.configure_idp(token, IdPConfig(
                        tenant_id=tenant_id, issuer=form.get("issuer", ""),
                        client_id=form.get("client_id", ""),
                        client_secret_ref=form.get("client_secret_ref", ""),
                        redirect_uri=form.get("redirect_uri", "")),
                        client_secret=secret or "")
                else:
                    svc.configure_saml_idp(
                        token, tenant_id=tenant_id,
                        sp_entity_id=form.get("sp_entity_id", ""),
                        acs_url=form.get("acs_url", ""),
                        metadata_xml=form.get("metadata_xml", ""),
                        subject_source=form.get("subject_source", "nameid"))
            return self._html(views.render_tenant_detail(self._tenant_detail_ctx(
                ctx, token, tenant_id, variant, query, notice="idp.updated")))
        if method == "POST" and sub == "scim/issue":
            cred, secret = svc.issue_scim_token(token, tenant_id=tenant_id)
            dctx = self._tenant_detail_ctx(ctx, token, tenant_id, variant, query,
                                           notice="scim.credential_issued")
            dctx["scim_secret"] = {"credential_id": cred.credential_id,
                                   "secret": secret}
            return self._html(views.render_tenant_detail(dctx))
        if method == "POST" and sub == "scim/revoke":
            svc.revoke_scim_token(token, tenant_id=tenant_id,
                                  credential_id=form.get("credential_id", ""))
            return self._html(views.render_tenant_detail(self._tenant_detail_ctx(
                ctx, token, tenant_id, variant, query,
                notice="scim.credential_revoked")))
        return self._html(views.render_tenant_detail(
            self._tenant_detail_ctx(ctx, token, tenant_id, variant, query)))

    def _tenant_detail_ctx(self, ctx, token, tenant_id, variant, query,
                           refusal=None, notice=None, ):
        svc = self.service
        directory = svc.directory
        t = directory.tenant(tenant_id)
        events = _tenant_events(svc, tenant_id)
        created = "—"
        for ev in events:
            if ev.get("type") == "tenant.created":
                created = (f"{views.fmt_ts(_event_ts(ev))} · deployment ledger seq "
                           f"{ev.get('seq')} (<span class='mono'>tenant.created</span>)")
                break
        if tenant_id == PLATFORM_TENANT_ID:
            created = "system tenant — present from deployment bootstrap"
        oidc = None
        idps = directory.idps_for_tenant(tenant_id)
        if idps:
            c = idps[0]
            oidc = {"issuer": c.issuer, "client_id": c.client_id,
                    "client_secret_ref": c.client_secret_ref,
                    "redirect_uri": c.redirect_uri,
                    "required_amr": list(c.required_amr)}
        saml = None
        samls = _saml_idps(directory, tenant_id)
        if samls:
            s0 = samls[0]
            saml = {"idp_entity_id": s0.idp_entity_id,
                    "sp_entity_id": s0.sp_entity_id, "acs_url": s0.acs_url,
                    "sso_redirect_url": s0.sso_redirect_url,
                    "sso_post_url": s0.sso_post_url,
                    "signing_cert_fingerprints": list(s0.signing_cert_fingerprints),
                    "subject_source": s0.subject_source}
        scim_state = svc.scim.peek(tenant_id)
        last_sync = "no sync events recorded"
        for ev in reversed(events):
            if ev.get("type", "").startswith("scim.sync"):
                last_sync = f"{ev.get('type')} · seq {ev.get('seq')} · {views.fmt_ts(_event_ts(ev))}"
                break
        mappings = 0
        for ev in events:
            if ev.get("type") == "scim.group_mapping_approved":
                mappings += 1
            if ev.get("type") == "scim.group_mapping_revoked":
                mappings -= 1
        identities = _identities(directory, tenant_id)
        assertion_created = [i for i in identities
                             if i.created_via in ("oidc", "saml")]
        roleless = [i for i in assertion_created
                    if not svc.roles_of(i.identity_id, tenant_id)
                    and not svc.roles_of(i.identity_id, None)]
        holds = svc.active_holds(token, tenant_id=tenant_id)
        return {**ctx, "variant": variant,
                "tenant": {"tenant_id": t.tenant_id, "name": t.name,
                           "shape": t.shape, "region": t.region,
                           "active": t.active},
                "pin": svc.residency_pin(token, tenant_id) if variant == "platform"
                       else {"region": t.region, "migrations": 0},
                "created": created, "oidc": oidc, "saml": saml,
                "scim": {"configured": bool(scim_state) and any(
                             not c.revoked for c in
                             scim_state.credentials.values()),
                         "credentials": [{"credential_id": cid,
                                          "revoked": c.revoked}
                                         for cid, c in
                                         (scim_state.credentials.items()
                                          if scim_state else [])],
                         "mappings": mappings, "last_sync": last_sync},
                "jit": {"created": len(assertion_created),
                        "roleless": len(roleless)},
                "policy": {"require_mfa": t.policy.require_mfa,
                           "stepup_freshness_seconds": t.policy.stepup_freshness_seconds,
                           "session_idle_seconds": t.policy.session_idle_seconds,
                           "session_absolute_seconds": t.policy.session_absolute_seconds,
                           "allowed_custody": list(t.policy.allowed_custody),
                           "rate_limit_per_minute": t.policy.rate_limit_per_minute},
                "hold": holds[0] if holds else None,
                "refusal": refusal or query.get("refusal"),
                "notice": notice or query.get("notice")}


    # ------------------------------------------------------------- audit

    def _ledger_keys(self) -> list[dict]:
        directory = self.service.directory
        keys = [{"key": PLATFORM_TENANT_ID, "label": "Deployment ledger"}]
        for t in _tenants(directory):
            if t.tenant_id != PLATFORM_TENANT_ID:
                keys.append({"key": t.tenant_id,
                             "label": f"Tenant · {t.name}"})
        return keys

    def _audit_ctx(self, ctx, token, query, refusal=None, notice=None):
        svc = self.service
        selected = query.get("ledger", PLATFORM_TENANT_ID)
        valid = {k["key"] for k in self._ledger_keys()}
        if selected not in valid:
            selected = PLATFORM_TENANT_ID
        if selected == PLATFORM_TENANT_ID:
            result = svc.verify_deployment_audit(token)
            events = _tenant_events(svc, PLATFORM_TENANT_ID)
        else:
            result = svc.verify_tenant_audit(token, tenant_id=selected)
            events = _tenant_events(svc, selected)
        anchor = _latest_anchor(events)
        if anchor:
            anchor_text = (f"anchored — {anchor.get('mechanism')} · "
                           f"ref <span class='mono'>{anchor.get('ref')}</span>"
                           + (f" · <span class='mono'>{anchor.get('uri')}</span>"
                              if anchor.get("uri") else "")
                           + " (audit.export_anchored)")
        else:
            anchor_text = ("none recorded — the latest anchor for this ledger is an "
                           "internal checkpoint, not an external anchor; an external "
                           "anchor is a separate, recorded act")
        expand = query.get("expand")
        return {**ctx, "ledgers": self._ledger_keys(), "selected": selected,
                "selected_label": {k["key"]: k["label"]
                                     for k in self._ledger_keys()}[selected],
                "verify": result, "verified_at": views.fmt_ts(time.time()),
                "checkpoint_root": _latest_checkpoint(events),
                "anchor_text": anchor_text,
                "events": list(reversed(events))[:25],
                "expand": int(expand) if expand and expand.isdigit() else None,
                "refusal": refusal or query.get("refusal"),
                "notice": notice or query.get("notice")}

    def _audit_export(self, form, token, ctx, query):
        svc = self.service
        selected = form.get("ledger", PLATFORM_TENANT_ID)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        if selected == PLATFORM_TENANT_ID:
            manifest = svc.export_deployment_audit(token, self.exports_dir)
            notice = (f"audit.exported — {manifest['export_id']} · bundle "
                      f"{views.short(manifest['bundle_hash'], 12, 6)}")
        else:
            manifest = svc.export_tenant_audit(token, selected, self.exports_dir)
            notice = (f"audit.exported — {manifest['export_id']} · tenant {selected} "
                      f"· bundle {views.short(manifest['bundle_hash'], 12, 6)}")
        q = {"ledger": selected}
        return self._html(views.render_audit(
            self._audit_ctx(ctx, token, q, notice=notice)))

    # -------------------------------------------------------- compliance

    def _compliance_ctx(self, ctx, token, query, refusal=None, notice=None):
        svc = self.service
        families: dict[str, dict[str, int]] = {}
        totals = {"Platform": 0, "Supports": 0, "Organizational": 0}
        for req, cls in MATRIX_CLASSES.items():
            fam = ".".join(req.split(".")[:2])
            families.setdefault(fam, {"Platform": 0, "Supports": 0,
                                      "Organizational": 0})
            families[fam][cls] += 1
            totals[cls] += 1
        try:
            report = svc.sprs_report(token)
            inputs = report["inputs"]
            deductions = [{"requirement": i["requirement"],
                           "state": i["state"],
                           "deduction": i["deduction_applied"],
                           "evidence": i.get("evidence_link") or "",
                           "gap_reason": i.get("gap_marker") or ""}
                          for i in inputs if i.get("deduction_applied")]
            sprs = {**report, "deductions": deductions,
                    "inputs": len(inputs)}
        except PlatformError:
            sprs = None
        register = svc.poam_register_document(token)
        markings = []
        for t in _tenants(svc.directory):
            if t.tenant_id == PLATFORM_TENANT_ID:
                continue
            m = t.cui_marking or {}
            text = (f"{m.get('category')} · authority: {m.get('authority')}"
                    f" · {m.get('dissemination')}" if m else
                    "not recorded — no customer designation on file")
            markings.append({"tenant": f"{t.name} ({t.tenant_id})", "text": text})
        inventory = Path(__file__).parents[3] / "specs" / "005-enterprise-platform" \
            / "crypto-inventory.md"
        operations = validated = 0
        if inventory.exists():
            for line in inventory.read_text().splitlines():
                cells = [c.strip() for c in line.split("|")]
                if len(cells) >= 5 and cells[1].isdigit():
                    operations += 1
                    if "validated module in path" in line:
                        validated += 1
        return {**ctx, "families": sorted(families.items()),
                "class_totals": totals, "sprs": sprs, "poam": register,
                "markings": markings,
                "fips": {"operations": operations, "validated": validated,
                         "path": "specs/005-enterprise-platform/crypto-inventory.md"},
                "refusal": refusal or query.get("refusal"),
                "notice": notice or query.get("notice")}

    # ------------------------------------------------------------ status

    def _status_ctx(self, ctx, token):
        svc = self.service
        directory = svc.directory
        ledgers = []
        for key in self._ledger_keys():
            tid = key["key"]
            if tid == PLATFORM_TENANT_ID:
                result = svc.verify_deployment_audit(token)
            else:
                result = svc.verify_tenant_audit(token, tenant_id=tid)
            events = _tenant_events(svc, tid)
            anchor = _latest_anchor(events)
            ledgers.append({
                "label": key["label"], "ref": f"tenant-{tid}.axmr" if tid != PLATFORM_TENANT_ID else "deployment.axmr",
                "ok": result["ok"], "break_seq": result["break_seq"],
                "reason": result["reason"], "events": result["events"],
                "checkpoint": views.short(_latest_checkpoint(events), 12, 6) or "—",
                "anchor": (f"{anchor.get('mechanism')} · {anchor.get('ref')}"
                           if anchor else "none recorded")})
        tenants = [t for t in _tenants(directory)
                   if t.tenant_id != PLATFORM_TENANT_ID]
        open_bg = 0
        for t in tenants:
            state = svc.break_glass_state(token, tenant_id=t.tenant_id)
            open_bg += len([s for s in state["sessions"]
                            if s.state in ("pending", "active")])
        defaults = directory.tenant(PLATFORM_TENANT_ID).policy
        return {**ctx, "ledgers": ledgers,
                "policy_defaults": {
                    "rate_limit_per_minute": defaults.rate_limit_per_minute,
                    "stepup_freshness_seconds": defaults.stepup_freshness_seconds},
                "breakglass_open": open_bg,
                "idp_tenants": len([t for t in tenants
                                    if directory.idps_for_tenant(t.tenant_id)
                                    or _saml_idps(directory, t.tenant_id)]),
                "oidc_tenants": len([t for t in tenants
                                     if directory.idps_for_tenant(t.tenant_id)]),
                "saml_tenants": len([t for t in tenants
                                     if _saml_idps(directory, t.tenant_id)]),
                "mfa_tenants": len([t for t in tenants if t.policy.require_mfa]),
                "tenant_total": len(tenants),
                "webhook_subscriptions": len(directory.webhook_subscriptions),
                "pending_deliveries": len(svc.pending_deliveries(token))}

    # ------------------------------------------------------- break-glass

    def _bg_session_dict(self, svc, tenant_id, s) -> dict:
        directory = svc.directory
        return {
            "bg_session_id": s.bg_session_id, "state": s.state,
            "invoker_name": _name_of(directory, tenant_id, s.invoker_identity_id),
            "invoker_actor_id": s.invoker_actor_id,
            "authorized_by_name": _name_of(directory, tenant_id,
                                           s.authorized_by_identity_id),
            "reason": s.reason,
            "requested_duration_seconds": s.requested_duration_seconds,
            "invoked_at": s.invoked_at, "authorized_at": s.authorized_at,
            "expires_at": s.expires_at, "closed_at": s.closed_at,
            "close_reason": s.close_reason,
            "review_item_id": s.review_item_id,
            "review_completed": s.review_completed,
            "actions_taken": s.actions_taken, "actions": [],
            "viewer_can_authorize": False}

    def _bg_state_for(self, svc, token, tenant_id, viewer_identity, viewer_plane):
        state = svc.break_glass_state(token, tenant_id=tenant_id)
        policy = state["policy"]
        marked: dict[str, list[dict]] = {}
        for ev in _tenant_events(svc, tenant_id):
            if ev.get("type") == "breakglass.action":
                p = ev.get("payload") or {}
                marked.setdefault(p.get("bg_session_id"), []).append(
                    {"action": p.get("action", ""),
                     "target": p.get("target", ""), "ts": _event_ts(ev)})
        sessions = []
        for s in state["sessions"]:
            d = self._bg_session_dict(svc, tenant_id, s)
            d["actions"] = marked.get(s.bg_session_id, [])
            if policy is not None and s.state == "pending":
                d["viewer_can_authorize"] = bool(
                    policy.second_authorizer_plane == viewer_plane
                    and viewer_identity is not None
                    and viewer_identity.actor_id != s.invoker_actor_id)
            sessions.append(d)
        policy_dict = None
        if policy is not None:
            policy_dict = {
                "invoker_roles": list(policy.invoker_roles),
                "second_authorizer_plane": policy.second_authorizer_plane,
                "max_duration_seconds": policy.max_duration_seconds,
                "scopes": sorted(policy.scopes),
                "declared_by_actor_id": policy.declared_by_actor_id,
                "declared_at": policy.declared_at}
        return {"policy": policy_dict, "sessions": sessions}

    def _bg_platform_ctx(self, ctx, token, query, refusal=None, notice=None):
        svc = self.service
        session, identity = self.session_identity(token)
        tenants = []
        for t in _tenants(svc.directory):
            if t.tenant_id == PLATFORM_TENANT_ID:
                continue
            state = self._bg_state_for(svc, token, t.tenant_id, identity, "platform_admin")
            tenants.append({"tenant_id": t.tenant_id, "tenant_name": t.name,
                            "state": state,
                            "viewer_can_authorize": bool(
                                state["policy"] and
                                state["policy"]["second_authorizer_plane"] == "platform_admin")})
        return {**ctx, "tenants": tenants,
                "refusal": refusal or query.get("refusal"),
                "notice": notice or query.get("notice")}

    # -------------------------------------------------------- tenant plane

    def _tenant(self, method, path, query, form, token, identity, session):
        svc = self.service
        tenant_id = identity.tenant_id
        ctx = self._tenant_ctx(token, identity, session)
        parts = [p for p in path.split("/") if p]
        rest = parts[1] if len(parts) > 1 else ""
        sub = parts[2] if len(parts) > 2 else ""
        if rest == "idp":
            return self._tenant_admin(method, "/".join(parts[1:]), query,
                                      form, token, tenant_id, ctx,
                                      variant="tenant")
        if rest == "users":
            if method == "POST" and sub == "grant":
                svc.grant_role(token, tenant_id=tenant_id,
                               identity_id=form.get("identity_id", ""),
                               role=form.get("role", ""))
                return self._html(views.render_users(self._users_ctx(
                    ctx, query, notice="role.granted")))
            if method == "POST" and sub == "revoke":
                svc.revoke_role(token, tenant_id=tenant_id,
                                identity_id=form.get("identity_id", ""),
                                role=form.get("role", ""))
                return self._html(views.render_users(self._users_ctx(
                    ctx, query, notice="role.revoked")))
            if method == "POST" and sub == "deactivate":
                svc.deactivate_identity(
                    token, identity_id=form.get("identity_id", ""))
                return self._html(views.render_users(self._users_ctx(
                    ctx, query, notice="identity.deactivated")))
            if method == "POST" and sub == "reactivate":
                svc.reactivate_identity(
                    token, identity_id=form.get("identity_id", ""))
                return self._html(views.render_users(self._users_ctx(
                    ctx, query, notice="identity.reactivated")))
            if method == "POST" and sub == "create":
                svc.admin_create_identity(
                    token, tenant_id=tenant_id, issuer=form.get("issuer", ""),
                    subject=form.get("subject", ""),
                    display_name=form.get("display_name", ""),
                    email=form.get("email", ""),
                    affiliation=form.get("affiliation", ""))
                return self._html(views.render_users(self._users_ctx(
                    ctx, query, notice="identity.created")))
            return self._html(views.render_users(self._users_ctx(ctx, query)))
        if rest == "keys":
            return self._keys(method, sub, query, form, token, identity, ctx)
        if rest == "events":
            return self._html(views.render_events(
                self._events_ctx(ctx, token, tenant_id, query)))
        if rest == "break-glass":
            return self._break_glass(method, sub, query, form, token,
                                     identity, ctx)
        return self._html(views.render_users(self._users_ctx(ctx, query)))

    def _users_ctx(self, ctx, query, refusal=None, notice=None):
        svc = self.service
        directory = svc.directory
        tenant_id = ctx["tenant_id"]
        events = _tenant_events(svc, tenant_id)
        first_seen = _first_seen(svc, tenant_id)
        users = []
        for ident in _identities(directory, tenant_id):
            roles = sorted(svc.roles_of(ident.identity_id, tenant_id))
            users.append({
                "identity_id": ident.identity_id,
                "display_name": ident.display_name, "email": ident.email,
                "affiliation": ident.affiliation, "subject": ident.subject,
                "issuer": ident.issuer, "actor_id": ident.actor_id,
                "active": ident.active, "created_via": ident.created_via,
                "first_seen": first_seen.get(ident.identity_id),
                "roles": roles})
        names = _actor_names(directory, tenant_id)
        # Grantors may sit in another scope (a platform admin's grants
        # land in this tenant's ledger): resolve names directory-wide,
        # falling back to the tenant-scoped map.
        for ident in directory.identities.values():
            names.setdefault(ident.actor_id,
                             ident.display_name or ident.subject)
        grant_events = []
        for ev in reversed(events):
            if ev.get("type") in ("role.granted", "role.revoked"):
                p = ev.get("payload") or {}
                grant_events.append({
                    "grantor": names.get(p.get("actor_id"), "—"),
                    "grantee": names.get(p.get("subject_actor_id"), "—"),
                    "role": p.get("role", ""), "ts": _event_ts(ev),
                    "seq": ev.get("seq"), "event_type": ev.get("type")})
            if len(grant_events) >= 12:
                break
        issuers = [c.issuer for c in directory.idps_for_tenant(tenant_id)] + \
                  [c.idp_entity_id for c in _saml_idps(directory, tenant_id)]
        return {**ctx, "tenant": {"tenant_id": tenant_id,
                                  "name": ctx["tenant_name"]},
                "users": users, "grant_events": grant_events,
                "grantable": [r for r in ALL_GRANTABLE_ROLES
                              if r != "platform_admin"],
                "issuers": issuers,
                "stats": {"identities": len(users),
                          "with_roles": len([u for u in users if u["roles"]]),
                          "deactivated": len([u for u in users if not u["active"]])},
                "refusal": refusal or query.get("refusal"),
                "notice": notice or query.get("notice")}

    def _keys(self, method, sub, query, form, token, identity, ctx):
        svc = self.service
        tenant_id = identity.tenant_id
        if method == "POST" and sub == "begin-enrollment":
            nonce = svc.begin_enrollment(token)
            return self._html(views.render_keys(self._keys_ctx(
                ctx, identity, query, nonce=nonce)))
        if method == "POST" and sub == "enroll-self":
            svc.enroll_self_key(
                token, public_key=bytes.fromhex(form.get("public_key", "")),
                proof_signature=bytes.fromhex(form.get("proof_signature", "")),
                nonce=form.get("nonce", ""))
            return self._html(views.render_keys(self._keys_ctx(
                ctx, identity, query, notice="key.enrolled (self custody)")))
        if method == "POST" and sub == "enroll-delegated":
            rec = svc.enroll_delegated_key(
                token, seed_hex=secrets.token_hex(32))
            return self._html(views.render_keys(self._keys_ctx(
                ctx, identity, query,
                notice=f"key.enrolled (delegated) — {views.short(rec.fingerprint)}")))
        if method == "POST" and sub == "enroll-countersigned":
            rec = svc.enroll_key_countersigned(
                token, identity_id=form.get("identity_id", ""),
                public_key=bytes.fromhex(form.get("public_key", "")),
                proof_signature=bytes.fromhex(form.get("proof_signature", "")),
                nonce=form.get("nonce", ""))
            return self._html(views.render_keys(self._keys_ctx(
                ctx, identity, query,
                notice=f"key.enrolled (countersigned) — {views.short(rec.fingerprint)}")))
        if method == "POST" and sub == "rotate":
            rec = svc.rotate_key(
                token, old_fingerprint=form.get("old_fingerprint", ""),
                new_public_key=bytes.fromhex(form.get("new_public_key", "")),
                proof_signature=bytes.fromhex(form.get("proof_signature", "")),
                nonce=form.get("nonce", ""))
            return self._html(views.render_keys(self._keys_ctx(
                ctx, identity, query,
                notice=f"key.rotated — {views.short(rec.fingerprint)}")))
        if method == "POST" and sub == "revoke":
            svc.revoke_key(token, key_fingerprint=form.get("fingerprint", ""),
                           reason=form.get("reason", ""))
            return self._html(views.render_keys(self._keys_ctx(
                ctx, identity, query, notice="key.revoked")))
        if method == "POST" and sub == "apikey-issue":
            principal_id = form.get("principal_id", "")
            if not principal_id:
                created = svc.create_service_identity(
                    token, tenant_id=tenant_id,
                    name=form.get("service_name", ""))
                principal_id = created.identity_id
            scopes = [s.strip() for s in form.get("scopes", "").split(",")
                      if s.strip()]
            record, secret = svc.issue_api_key(
                token, tenant_id=tenant_id,
                principal_identity_id=principal_id,
                role_class=form.get("role_class", "researcher"),
                scopes=scopes,
                lifetime_seconds=int(form.get("expires_days", "90") or 90)
                * 86400)
            kctx = self._keys_ctx(ctx, identity, query)
            kctx["issued_key"] = {
                "key_id": record.key_id, "secret": secret,
                "principal_name": _name_of(svc.directory, tenant_id, principal_id)}
            return self._html(views.render_keys(kctx))
        if method == "POST" and sub == "apikey-revoke":
            svc.revoke_api_key(token, key_id=form.get("key_id", ""))
            return self._html(views.render_keys(self._keys_ctx(
                ctx, identity, query, notice="apikey.revoked")))
        return self._html(views.render_keys(self._keys_ctx(ctx, identity, query)))

    def _keys_ctx(self, ctx, identity, query, refusal=None, notice=None,
                  nonce=None):
        svc = self.service
        directory = svc.directory
        tenant_id = identity.tenant_id
        registry = svc.registry(tenant_id)
        keys = []
        for rec in registry.keys.values():
            owner = directory.identity(rec.identity_id)
            keys.append({
                "fingerprint": rec.fingerprint, "custody": rec.custody,
                "status": rec.status, "enrolled_seq": rec.enrolled_seq,
                "replaced_by": rec.replaced_by,
                "identity_name": (owner.display_name or owner.subject)
                if owner else "—",
                "actor_id": rec.actor_id})
        keys.sort(key=lambda k: k["enrolled_seq"])
        now = time.time()
        api_keys = []
        for k in _api_keys(directory, tenant_id):
            state = ("revoked" if k.revoked else
                     "expired" if k.expires_at <= now else "active")
            principal = directory.identity(k.principal_identity_id)
            api_keys.append({
                "key_id": k.key_id, "state": state, "role_class": k.role_class,
                "scopes": list(k.scopes), "expires_at": k.expires_at,
                "last_used_at": k.last_used_at,
                "principal": (principal.display_name or principal.subject)
                if principal else "—"})
        principals = [{"identity_id": i.identity_id,
                       "name": i.display_name or i.subject,
                       "kind": "service" if i.issuer == "service" else "identity"}
                      for i in _identities(directory, tenant_id)]
        adjudicators = [p for p in principals
                        if "adjudicator" in svc.roles_of(p["identity_id"],
                                                         tenant_id)]
        my_keys = [k for k in keys if k["actor_id"] == identity.actor_id]
        custody_note = views._CUSTODY_NOTE if any(
            k["custody"] == "delegated" for k in keys) else ""
        return {**ctx, "tenant": {"tenant_id": tenant_id,
                                  "name": ctx["tenant_name"]},
                "keys": keys, "api_keys": api_keys, "principals": principals,
                "adjudicators": adjudicators, "my_keys": my_keys,
                "role_classes": sorted(STUDY_ROLES),
                "custody_note": custody_note, "nonce": nonce,
                "refusal": refusal or query.get("refusal"),
                "notice": notice or query.get("notice")}

    def _events_ctx(self, ctx, token, tenant_id, query):
        svc = self.service
        events = svc.read_tenant_audit(token, tenant_id=tenant_id)
        cls = query.get("class", "all")
        if cls != "all":
            events = [ev for ev in events
                      if ev.get("type", "").startswith(cls)]
        expand = query.get("expand")
        verify = svc.verify_tenant_audit(token, tenant_id=tenant_id)
        return {**ctx, "tenant": {"tenant_id": tenant_id,
                                  "name": ctx["tenant_name"]},
                "events": list(reversed(events))[:50],
                "filter": cls, "verify": verify,
                "expand": int(expand) if expand and expand.isdigit() else None}

    def _break_glass(self, method, sub, query, form, token, identity, ctx):
        svc = self.service
        tenant_id = identity.tenant_id
        base_ctx = self._bg_tenant_ctx(ctx, token, identity, query)
        if method == "POST" and sub == "declare":
            svc.declare_break_glass_policy(
                token, tenant_id=tenant_id,
                invoker_roles=form.get("invoker_roles", []),
                second_authorizer_plane=form.get("second_authorizer_plane",
                                                 "platform_admin"),
                scopes=form.get("scopes", []),
                max_duration_seconds=int(form.get("max_duration_minutes", "60")
                                         or 60) * 60)
            return self._html(views.render_break_glass_tenant(self._bg_tenant_ctx(
                ctx, token, identity, query, notice="breakglass.policy_declared")))
        if method == "POST" and sub == "revoke-policy":
            svc.revoke_break_glass_policy(token, tenant_id=tenant_id)
            return self._html(views.render_break_glass_tenant(self._bg_tenant_ctx(
                ctx, token, identity, query, notice="breakglass.policy_revoked")))
        if method == "POST" and sub == "invoke":
            svc.invoke_break_glass(
                token, tenant_id=tenant_id, reason=form.get("reason", ""),
                duration_seconds=int(
                    form.get("duration_minutes", "60") or 60) * 60)
            return self._html(views.render_break_glass_tenant(self._bg_tenant_ctx(
                ctx, token, identity, query, notice="breakglass.invoked")))
        if method == "POST" and sub == "authorize":
            svc.authorize_break_glass(
                token, bg_session_id=form.get("bg_session_id", ""))
            return self._html(views.render_break_glass_tenant(self._bg_tenant_ctx(
                ctx, token, identity, query, notice="breakglass.authorized")))
        if method == "POST" and sub == "deny":
            svc.deny_break_glass(
                token, bg_session_id=form.get("bg_session_id", ""))
            return self._html(views.render_break_glass_tenant(self._bg_tenant_ctx(
                ctx, token, identity, query,
                notice="breakglass.authorization_denied")))
        if method == "POST" and sub == "close":
            svc.close_break_glass(
                token, bg_session_id=form.get("bg_session_id", ""))
            return self._html(views.render_break_glass_tenant(self._bg_tenant_ctx(
                ctx, token, identity, query, notice="breakglass.session_closed")))
        if method == "POST" and sub == "act":
            bg_id = form.get("bg_session_id", "")
            state = svc.break_glass_state(token, tenant_id=tenant_id)
            bg = next((s for s in state["sessions"]
                       if s.bg_session_id == bg_id), None)
            if bg is None or bg.invoker_actor_id != identity.actor_id:
                raise PlatformError(
                    "break-glass actions are exercised by the session's "
                    "invoker, under their own sign-in")
            result = svc.break_glass_act(
                bg_id, session_token=token, action=form.get("action", ""),
                key_fingerprint=form.get("fingerprint") or "",
                identity_id=form.get("identity_id") or "")
            note = "breakglass.action recorded"
            if form.get("action") == "tenant.audit_export" \
                    and isinstance(result, list):
                note = (f"breakglass.action — tenant audit read under the "
                        f"session ({len(result)} events)")
            return self._html(views.render_break_glass_tenant(self._bg_tenant_ctx(
                ctx, token, identity, query, notice=note)))
        if method == "POST" and sub == "review":
            item_id = form.get("review_item_id", "")
            state = svc.break_glass_state(token, tenant_id=tenant_id)
            bg = next((s for s in state["sessions"]
                       if s.review_item_id == item_id), None)
            if bg is None:
                raise PlatformError(
                    f"no break-glass review item {item_id} for this tenant")
            svc.record_break_glass_review(
                token, tenant_id=tenant_id, bg_session_id=bg.bg_session_id,
                disposition=form.get("disposition", ""),
                note=form.get("note", ""))
            return self._html(views.render_break_glass_tenant(self._bg_tenant_ctx(
                ctx, token, identity, query, notice="breakglass.review_completed")))
        return self._html(views.render_break_glass_tenant(base_ctx))

    def _bg_tenant_ctx(self, ctx, token, identity, query, refusal=None, notice=None):
        svc = self.service
        tenant_id = identity.tenant_id
        state = self._bg_state_for(svc, token, tenant_id, identity, "tenant_admin")
        identities = [{"identity_id": i.identity_id,
                       "name": i.display_name or i.subject}
                      for i in _identities(svc.directory, tenant_id)
                      if i.active]
        names = {i.actor_id: (i.display_name or i.subject)
                 for i in svc.directory.identities.values()}
        return {**ctx, "tenant": {"tenant_id": tenant_id,
                                  "name": ctx["tenant_name"]},
                "bg_state": state, "identities": identities,
                "names": names,
                "all_roles": [r for r in ALL_GRANTABLE_ROLES
                              if r != "platform_admin"],
                "bg_scopes": sorted(PlatformService.BREAKGLASS_SCOPES),
                "refusal": refusal or query.get("refusal"),
                "notice": notice or query.get("notice")}


# ----------------------------------------------------------------- serving

def create_server(app: Optional[ConsoleApp], host: str = "127.0.0.1",
                  port: int = 0) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):  # keep test output clean
            pass

        def _run(self, method: str) -> None:
            parsed = urllib.parse.urlparse(self.path)
            query = {k: v[0] for k, v in
                     urllib.parse.parse_qs(parsed.query).items()}
            form: dict[str, Any] = {}
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                raw = self.rfile.read(length).decode("utf-8")
                ctype = self.headers.get("Content-Type", "")
                if "application/x-www-form-urlencoded" in ctype:
                    parsed_form = urllib.parse.parse_qs(raw, keep_blank_values=True)
                    form = {k: (v[0] if len(v) == 1 else v)
                            for k, v in parsed_form.items()}
            cookies: dict[str, str] = {}
            for part in (self.headers.get("Cookie") or "").split(";"):
                if "=" in part:
                    k, v = part.strip().split("=", 1)
                    cookies[k] = v
            status, headers, body = self.server.app.handle(
                method, parsed.path, query, form, cookies)  # type: ignore[attr-defined]
            self.send_response(status)
            for k, v in baseline.security_headers().items():
                if k == "Content-Security-Policy":
                    v = CONSOLE_CSP  # see the note at CONSOLE_CSP
                self.send_header(k, v)
            for k, v in headers:
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def do_GET(self):
            self._run("GET")

        def do_POST(self):
            self._run("POST")

    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.app = app  # type: ignore[attr-defined]
    return httpd


def serve(root: Optional[str] = None, *, host: str = "127.0.0.1",
          port: int = 8770, fixture: bool = False) -> None:
    """Blocking serve. In fixture mode the specimen world is built
    against the actual bound port (IdP redirect URIs name it)."""
    if fixture:
        httpd = create_server(None, host, port)
        actual_port = httpd.server_address[1]
        import tempfile
        fixture_root = root or tempfile.mkdtemp(prefix="tekmerion-console-fixture-")
        from .fixture import build_fixture_world
        world = build_fixture_world(
            fixture_root, f"http://{host}:{actual_port}")
        httpd.app = ConsoleApp(world.service, fixture=world)  # type: ignore[attr-defined]
        print(f"FIXTURE console on http://{host}:{actual_port}/ "
              f"(specimen world at {fixture_root}; BUILD_ID {BUILD_ID})")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        return
    if not root:
        raise SystemExit("--root is required unless --fixture is given")
    service = PlatformService(root)
    httpd = create_server(ConsoleApp(service), host, port)
    actual_port = httpd.server_address[1]
    print(f"Tekmerion admin console on http://{host}:{actual_port}/ "
          f"(BUILD_ID {BUILD_ID})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
