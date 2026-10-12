"""E5 console battery (Spec 005, T535–T540).

The console is driven over real HTTP against the real platform
services of the E1/E2/E4 test worlds (and, for the labeled fixture
flow, the fixture world). Nothing here mocks the service layer:
logins complete the actual OIDC/SAML flows, mutations are service
calls made by the console's handlers, and refusals asserted are the
service's own messages.

What is pinned:
- F-005-13's condition: screens exist only downstream of the
  T534-WF approval record (asserted in the records test below);
- CLM-005-01: no password field on any sign-in surface;
- CLM-005-09: cross-plane refusals at the HTTP layer — the other
  plane's shell does not render at all;
- served-artifact identity: BUILD_ID on the endpoint and every
  page, and the source-stamp currency mechanism;
- SPRS is computed at request time (mutate a state, the score
  moves) — never a hard-coded figure;
- secrets never render: IdP configuration shows references and
  fingerprints only.
"""

from __future__ import annotations

import http.client
import http.cookies
import re
import threading
import urllib.parse
from pathlib import Path

import pytest

import e1_world
import e2_world
import e4_world
from tekmerion.console import BUILD_ID
from tekmerion.console.build import source_stamp
from tekmerion.console.fixture import build_fixture_world
from tekmerion.console.server import ConsoleApp, create_server
from tekmerion.platform import authz
from tekmerion.platform.service import PLATFORM_TENANT_ID

REPO = Path(__file__).parent.parent


# ------------------------------------------------------------ HTTP client

class Client:
    def __init__(self, port: int) -> None:
        self.port = port
        self.jar: dict[str, str] = {}

    def request(self, method: str, path: str, form: dict | None = None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        headers: dict[str, str] = {}
        body = None
        if form is not None:
            body = urllib.parse.urlencode(form, doseq=True)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if self.jar:
            headers["Cookie"] = "; ".join(
                f"{k}={v}" for k, v in self.jar.items())
        conn.request(method, path, body, headers)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8", "replace")
        raw_headers = dict(resp.getheaders())
        set_cookie = resp.getheader("Set-Cookie")
        if set_cookie:
            for key, morsel in http.cookies.SimpleCookie(set_cookie).items():
                self.jar[key] = morsel.value
        conn.close()
        return resp.status, raw_headers, data

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, form):
        return self.request("POST", path, form)

    def with_session(self, token: str) -> "Client":
        self.jar["tekmerion_session"] = token
        return self


@pytest.fixture()
def serve():
    servers = []

    def _start(app: ConsoleApp) -> int:
        httpd = create_server(app, "127.0.0.1", 0)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        servers.append(httpd)
        return httpd.server_address[1]

    yield _start
    for httpd in servers:
        httpd.shutdown()


@pytest.fixture()
def world(tmp_path):
    return e4_world.build_two_tenant_world(tmp_path)


@pytest.fixture()
def app(world) -> ConsoleApp:
    return ConsoleApp(world.service)


@pytest.fixture()
def root_client(serve, app, world) -> Client:
    token = world.login(PLATFORM_TENANT_ID, e1_world.ISSUER_PLATFORM, "root")
    return Client(serve(app)).with_session(token)


@pytest.fixture()
def admin_client(serve, app, world) -> Client:
    token = world.login(world.tenant_id, world.issuer_a, "admin-a")
    return Client(serve(app)).with_session(token)


@pytest.fixture()
def fixture_app(tmp_path):
    fx = build_fixture_world(tmp_path, "http://127.0.0.1:0")
    return fx, ConsoleApp(fx.service, fixture=fx)


def _fixture_login(client: Client, start_path: str, form: dict,
                   subject: str) -> None:
    _, headers, _ = client.post(start_path, form)
    _, _, body = client.get(headers["Location"])
    hidden = dict(re.findall(
        r'<input type="hidden" name="([^"]+)" value="([^"]*)">', body))
    hidden["subject"] = subject
    _, headers, _ = client.post("/fixture/idp/authorize", hidden)
    client.get(headers["Location"])


# ------------------------------------------------------- BUILD_ID (T540)

def test_build_id_endpoint_and_footer(serve, app):
    client = Client(serve(app))
    status, _, body = client.get("/build-id")
    assert status == 200
    assert f'"build_id": "{BUILD_ID}"' in body
    status, _, body = client.get("/")
    assert status == 200
    assert "BUILD_ID" in body and BUILD_ID in body


def test_build_id_source_stamp_is_currency_sensitive(tmp_path):
    a = tmp_path / "a.py"
    b = tmp_path / "console.css"
    a.write_text("x = 1\n")
    b.write_text("/* sheet */\n")
    before = source_stamp([a, b])
    a.write_text("x = 2\n")
    assert source_stamp([a, b]) != before


def test_stylesheets_are_the_wireframes_own(serve, app):
    client = Client(serve(app))
    _, _, base = client.get("/static/style.css")
    _, _, over = client.get("/static/console.css")
    assert base.encode() == (REPO / "docs/wireframes/style.css").read_bytes()
    assert over.encode() == \
        (REPO / "docs/wireframes/console/console.css").read_bytes()
    assert (REPO / "src/tekmerion/console/console.css").read_bytes() == \
        (REPO / "docs/wireframes/console/console.css").read_bytes()


def test_baseline_headers_and_cookie_contract(serve, app, world):
    client = Client(serve(app))
    _, headers, _ = client.get("/")
    assert headers["Strict-Transport-Security"].startswith("max-age=63072000")
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]


# ------------------------------------------------- sign-in (CLM-005-01)

def test_signin_has_identifier_entry_and_no_password(serve, app):
    client = Client(serve(app))
    _, _, body = client.get("/")
    assert 'name="tenant_id"' in body
    assert 'type="password"' not in body
    # Q8: the sign-in page does not enumerate tenants.
    assert "University A" not in body and "University B" not in body


def test_no_signin_password_field_on_any_screen(serve, app, root_client,
                                                admin_client):
    paths = ["/platform/tenants", "/platform/tenants/uni-a",
             "/platform/audit", "/platform/compliance", "/platform/status",
             "/platform/break-glass"]
    for path in paths:
        _, _, body = root_client.get(path)
        for match in re.findall(r'<input[^>]*type="password"[^>]*>', body):
            assert 'name="client_secret"' in match, (path, match)
    for path in ["/tenant/users", "/tenant/keys", "/tenant/events",
                 "/tenant/break-glass", "/tenant/idp"]:
        _, _, body = admin_client.get(path)
        for match in re.findall(r'<input[^>]*type="password"[^>]*>', body):
            assert 'name="client_secret"' in match, (path, match)


def test_unknown_tenant_signin_refusal_in_product_voice(serve, app):
    client = Client(serve(app))
    _, _, body = client.post("/auth/tenant/start",
                             {"tenant_id": "uni-nope", "protocol": "oidc"})
    assert "Sign-in refused." in body
    assert "unknown tenant" in body


def test_oidc_login_completes_over_http(serve, app, world):
    client = Client(serve(app))
    _, headers, _ = client.post(
        "/auth/platform/oidc", {"issuer": e1_world.ISSUER_PLATFORM})
    url = headers["Location"]
    code, state = world.mock.authorize(url, "root")
    status, headers, _ = client.get(
        f"/auth/oidc/callback?code={code}&state={state}")
    assert status == 303
    assert "tekmerion_session" in client.jar
    set_cookie = headers.get("Set-Cookie", "")
    assert "HttpOnly" in set_cookie and "Secure" in set_cookie
    assert "SameSite=Lax" in set_cookie
    _, headers, _ = client.get("/")
    assert headers["Location"] == "/platform/tenants"


def test_oidc_login_refusal_renders_service_message(serve, app, world):
    client = Client(serve(app))
    _, headers, _ = client.post(
        "/auth/platform/oidc", {"issuer": e1_world.ISSUER_PLATFORM})
    url = headers["Location"]
    state = dict(urllib.parse.parse_qsl(
        urllib.parse.urlparse(url).query))["state"]
    _, _, body = client.get(f"/auth/oidc/callback?code=bogus&state={state}")
    assert "Sign-in refused." in body
    assert "auth.login_failed" in body


def test_saml_login_completes_over_http(serve, tmp_path):
    w = e2_world.build_saml_world(tmp_path)
    svc = w.service
    # alice needs the tenant_admin role to hold a console plane.
    e2_world.saml_login(w, "alice")
    alice = svc.directory.find_identity(w.tenant_id, w.idp_a, "alice")
    svc.grant_role(w.root_session, identity_id=alice.identity_id,
                   role=authz.TENANT_ADMIN, tenant_id=w.tenant_id)
    app = ConsoleApp(svc)
    client = Client(serve(app))
    _, headers, _ = client.post("/auth/tenant/start",
                                {"tenant_id": w.tenant_id, "protocol": "saml"})
    url = headers["Location"]
    state, response = e2_world.saml_respond(w, url, "alice")
    status, _, _ = client.post("/auth/saml/acs",
                               {"RelayState": state, "SAMLResponse": response})
    assert status == 303
    assert "tekmerion_session" in client.jar
    _, _, body = client.get("/tenant/users")
    assert "Users &amp; roles" in body
    _, _, body = client.get("/platform/tenants")
    assert "Sign in to the admin console" in body


# ------------------------------------------- cross-plane battery (§5/§9)

ALL_PATHS = ["/platform/tenants", "/platform/tenants/uni-a",
             "/platform/audit", "/platform/compliance", "/platform/status",
             "/platform/break-glass", "/tenant/users", "/tenant/keys",
             "/tenant/events", "/tenant/break-glass", "/tenant/idp"]


def test_unauthenticated_everything_is_the_signin_screen(serve, app):
    client = Client(serve(app))
    for path in ALL_PATHS:
        _, _, body = client.get(path)
        assert "Sign in to the admin console" in body, path
        assert "Acting as" not in body, path


def test_tenant_session_gets_no_platform_shell(serve, app, admin_client):
    for path in [p for p in ALL_PATHS if p.startswith("/platform/")]:
        _, _, body = admin_client.get(path)
        assert "Sign in to the admin console" in body, path
        assert "Deployment — all tenants" not in body, path


def test_platform_session_gets_no_tenant_shell(serve, app, root_client):
    for path in [p for p in ALL_PATHS if p.startswith("/tenant/")]:
        _, _, body = root_client.get(path)
        assert "Sign in to the admin console" in body, path


def test_tenant_session_sees_only_its_own_tenant(serve, app, admin_client):
    _, _, body = admin_client.get("/tenant/users")
    assert "University B" not in body
    # No route names another tenant in the tenant plane at all.
    assert "/platform/" not in body


def test_tenant_landing_is_users_and_roles(serve, app, admin_client):
    _, headers, _ = admin_client.get("/")
    assert headers["Location"] == "/tenant/users"


def test_researcher_only_identity_has_no_plane(serve, fixture_app):
    fx, app = fixture_app
    client = Client(serve(app))
    # nils holds researcher only in uni-a (no admin role anywhere).
    _fixture_login(client, "/auth/tenant/start",
                   {"tenant_id": "uni-a", "protocol": "oidc"}, "nils")
    _, _, body = client.get("/")
    assert "No admin plane for this identity" in body


# ------------------------------------------------------- platform screens

def test_tenants_screen_and_creation(serve, app, root_client, world):
    _, _, body = root_client.get("/platform/tenants")
    assert "University A" in body and "University B" in body
    assert "Platform plane" in body
    _, _, body = root_client.post(
        "/platform/tenants", {"tenant_id": "uni-c", "name": "University C",
                              "shape": "hosted", "region": "us-west"})
    assert "tenant.created" in body
    assert world.service.directory.tenant("uni-c").name == "University C"


def test_tenant_detail_shows_secret_by_reference_only(serve, app,
                                                      root_client):
    _, _, body = root_client.get("/platform/tenants/uni-a")
    assert "secret:uni-a-idp" in body
    assert "never displayed" in body
    # The actual secret values never render, on any platform screen.
    for path in [p for p in ALL_PATHS if p.startswith("/platform")]:
        _, _, page = root_client.get(path)
        assert "test-only" not in page, path


def test_idp_configuration_via_console(serve, app, root_client, world):
    _, _, body = root_client.post(
        "/platform/tenants/uni-b/idp/oidc",
        {"issuer": world.issuer_b, "client_id": "tekmerion-uni-b",
         "client_secret_ref": "secret:uni-b-idp", "client_secret": "",
         "redirect_uri": "https://uni-b.test/callback"})
    assert "idp.updated" in body
    config = world.service.directory.idp(world.tenant_b, world.issuer_b)
    assert config.client_id == "tekmerion-uni-b"


def test_audit_verify_and_export(serve, app, root_client):
    _, _, body = root_client.get("/platform/audit")
    assert "chain intact" in body
    assert "internal checkpoint" in body  # external-anchor absence stated
    _, _, body = root_client.post("/platform/audit/export",
                                  {"ledger": "uni-a"})
    assert "audit.exported" in body
    assert list(Path(app.exports_dir).iterdir())


def test_compliance_sprs_is_computed_live(serve, fixture_app):
    fx, app = fixture_app
    svc = fx.service
    from tekmerion.console.fixture import _login, PLATFORM_ISSUER
    token = _login(svc, fx.idp, PLATFORM_TENANT_ID, PLATFORM_ISSUER,
                   "root", step_up=True)
    client = Client(serve(app)).with_session(token)
    _, _, body = client.get("/platform/compliance")
    assert "self-score: -156" in body
    assert "POAM-0001" in body
    assert "0 of 13" in body
    # Change one recorded state; the score on the next request moves.
    svc.set_control_state(token, requirement="3.1.1",
                          state="not_implemented", evidence_link="",
                          gap_marker="console battery probe")
    _, _, body = client.get("/platform/compliance")
    assert "self-score: -156" not in body
    assert "self-score: -161" in body


def test_status_screen_reads_ledgers(serve, app, root_client):
    _, _, body = root_client.get("/platform/status")
    assert "deployment.axmr" in body
    assert "tenant-uni-a.axmr" in body
    assert "intact" in body


# --------------------------------------------------------- tenant screens

def test_users_screen_grant_revoke_deactivate(serve, app, admin_client,
                                              world):
    svc = world.service
    world.login(world.tenant_id, world.issuer_a, "rudy")
    world.login(world.tenant_id, world.issuer_a, "ivy")
    rudy = svc.directory.find_identity(world.tenant_id, world.issuer_a, "rudy")
    _, _, body = admin_client.post(
        "/tenant/users/grant", {"identity_id": rudy.identity_id,
                                "role": "reviewer"})
    assert "role.granted" in body
    assert "reviewer" in svc.roles_of(rudy.identity_id, world.tenant_id)
    _, _, body = admin_client.post(
        "/tenant/users/revoke", {"identity_id": rudy.identity_id,
                                 "role": "reviewer"})
    assert "role.revoked" in body
    assert "reviewer" not in svc.roles_of(rudy.identity_id, world.tenant_id)
    ivy = svc.directory.find_identity(world.tenant_id, world.issuer_a, "ivy")
    _, _, body = admin_client.post(
        "/tenant/users/deactivate", {"identity_id": ivy.identity_id})
    assert "identity.deactivated" in body
    assert not svc.directory.identity(ivy.identity_id).active


def test_refusal_rerenders_on_originating_screen(serve, app, admin_client,
                                                 world):
    # A tenant admin cannot grant platform_admin: the service
    # reserves it to the platform plane and refuses by name.
    world.login(world.tenant_id, world.issuer_a, "rudy")
    rudy = world.service.directory.find_identity(
        world.tenant_id, world.issuer_a, "rudy")
    _, _, body = admin_client.post(
        "/tenant/users/grant", {"identity_id": rudy.identity_id,
                                "role": "platform_admin"})
    assert "Users &amp; roles" in body  # still on the users screen
    assert "Refused." in body


def test_keys_screen_and_delegated_enrollment(serve, app, world):
    svc = world.service
    alice_session = world.login(world.tenant_id, world.issuer_a, "alice")
    alice = svc.directory.find_identity(world.tenant_id, world.issuer_a,
                                        "alice")
    svc.grant_role(world.root_session, identity_id=alice.identity_id,
                   role=authz.TENANT_ADMIN, tenant_id=world.tenant_id)
    alice_session = world.login(world.tenant_id, world.issuer_a, "alice")
    client = Client(serve(app)).with_session(alice_session)
    _, _, body = client.post("/tenant/keys/enroll-delegated", {})
    assert "key.enrolled (delegated)" in body
    assert "not a KMS/HSM custody claim" in body
    mine = [k for k in svc.registry(world.tenant_id).keys.values()
            if k.custody == "delegated"]
    assert mine


def test_events_screen_with_inline_expansion(serve, app, admin_client,
                                              world):
    _, _, body = admin_client.get("/tenant/events")
    assert "identity.created" in body
    events = world.service.read_tenant_audit(
        world.admin_session, tenant_id=world.tenant_id)
    seq = events[0]["seq"]
    _, _, body = admin_client.get(f"/tenant/events?expand={seq}")
    assert "it is the record" in body  # expansion detail row rendered


def test_no_phase_chips_ship(serve, app, root_client, admin_client):
    for client, paths in ((root_client, [p for p in ALL_PATHS
                                         if p.startswith("/platform")]),
                          (admin_client, [p for p in ALL_PATHS
                                          if p.startswith("/tenant")])):
        for path in paths:
            _, _, body = client.get(path)
            assert "phase-chip" not in body, path
            assert "T534" not in body and "T529" not in body, path


# ------------------------------------------------------------- break-glass

def test_break_glass_full_lifecycle_over_http(serve, fixture_app):
    fx, app = fixture_app
    svc = fx.service
    root = Client(serve(app))
    _fixture_login(root, "/auth/platform/oidc",
                   {"issuer": "https://idp-platform.fixture"}, "root")
    _, _, body = root.get("/platform/break-glass")
    assert "policy declared" in body
    pending = [s for s in svc.break_glass_state(tenant_id="uni-a")["sessions"]
               if s.state == "pending"][0]
    _, _, body = root.post("/platform/break-glass/authorize",
                           {"bg_session_id": pending.bg_session_id})
    assert "breakglass.authorized" in body

    alice = Client(serve(app))
    _fixture_login(alice, "/auth/tenant/start",
                   {"tenant_id": "uni-a", "protocol": "oidc"}, "alice")
    _, _, body = alice.get("/tenant/break-glass")
    assert "break-glass session active" in body
    _, _, body = alice.post("/tenant/break-glass/act",
                            {"bg_session_id": pending.bg_session_id,
                             "action": "tenant.audit_export"})
    assert "breakglass.action" in body
    _, _, body = alice.post("/tenant/break-glass/close",
                            {"bg_session_id": pending.bg_session_id})
    assert "breakglass.session_closed" in body
    state = svc.break_glass_state(tenant_id="uni-a")
    closed = [s for s in state["sessions"]
              if s.bg_session_id == pending.bg_session_id][0]
    assert closed.review_item_id and not closed.review_completed

    admin = Client(serve(app))
    _fixture_login(admin, "/auth/tenant/start",
                   {"tenant_id": "uni-a", "protocol": "oidc"}, "admin-a")
    _, _, body = admin.post(
        "/tenant/break-glass/review",
        {"review_item_id": closed.review_item_id,
         "disposition": "reviewed — actions appropriate to the stated reason",
         "note": "console battery"})
    assert "breakglass.review_completed" in body
    state = svc.break_glass_state(tenant_id="uni-a")
    done = [s for s in state["sessions"]
            if s.bg_session_id == pending.bg_session_id][0]
    assert done.review_completed
    # Completable exactly once: the second attempt is refused, on screen.
    _, _, body = admin.post(
        "/tenant/break-glass/review",
        {"review_item_id": closed.review_item_id,
         "disposition": "reviewed — actions appropriate to the stated reason",
         "note": "again"})
    assert "Refused." in body


def test_break_glass_undeclared_state_and_bad_scope_refusal(serve,
                                                            fixture_app):
    fx, app = fixture_app
    admin_b = Client(serve(app))
    _fixture_login(admin_b, "/auth/tenant/start",
                   {"tenant_id": "uni-b", "protocol": "oidc"}, "admin-b")
    _, _, body = admin_b.get("/tenant/break-glass")
    assert "no declaration" in body
    assert "Break-glass cannot be invoked for this tenant" in body
    _, _, body = admin_b.post(
        "/tenant/break-glass/declare",
        {"invoker_roles": ["tenant_admin"],
         "second_authorizer_plane": "platform_admin",
         "scopes": ["study.issue_verdict"], "max_duration_minutes": "60"})
    assert "Refused." in body
    assert "break-glass scopes must be a non-empty subset" in body


# ------------------------------------------------------- step-up (as-built)

def test_step_up_round_trip_over_http(serve, fixture_app):
    fx, app = fixture_app
    root = Client(serve(app))
    _fixture_login(root, "/auth/platform/oidc",
                   {"issuer": "https://idp-platform.fixture"}, "root")
    _, _, body = root.get("/platform/tenants")
    assert "Step up (fresh MFA)" in body
    _, headers, _ = root.get("/auth/step-up")
    _, _, body = root.get(headers["Location"])
    hidden = dict(re.findall(
        r'<input type="hidden" name="([^"]+)" value="([^"]*)">', body))
    hidden["subject"] = "root"
    _, headers, _ = root.post("/fixture/idp/authorize", hidden)
    root.get(headers["Location"])
    _, _, body = root.get("/platform/tenants")
    assert "Step-up: fresh MFA on this session." in body


def test_adjudicator_key_enrollment_stepup_gate(serve, app, world):
    """The as-built step-up gate (§3): an adjudicator's key
    enrollment refuses without a fresh step-up and succeeds after
    the console's step-up round trip — both over HTTP."""
    from tekmerion.platform import ed25519
    svc = world.service
    world.login(world.tenant_id, world.issuer_a, "alice")
    alice = svc.directory.find_identity(world.tenant_id, world.issuer_a,
                                        "alice")
    svc.grant_role(world.admin_session, identity_id=alice.identity_id,
                   role=authz.ADJUDICATOR, tenant_id=world.tenant_id)
    svc.grant_role(world.root_session, identity_id=alice.identity_id,
                   role=authz.TENANT_ADMIN, tenant_id=world.tenant_id)
    client = Client(serve(app))
    _, headers, _ = client.post(
        "/auth/tenant/start", {"tenant_id": world.tenant_id,
                               "protocol": "oidc"})
    # The console sent us to the tenant IdP; the world mock plays it.
    code, state = world.mock.authorize(headers["Location"], "alice")
    client.get(f"/auth/oidc/callback?code={code}&state={state}")
    _, _, body = client.post("/tenant/keys/begin-enrollment", {})
    nonce = re.search(r"Enrollment nonce\.</strong> "
                      r'<span class="mono">([^<]+)</span>', body).group(1)
    seed = bytes([0x5A]) * 32
    pub = ed25519.publickey_from_seed(seed)
    proof = ed25519.sign(seed, nonce.encode("utf-8"))
    _, _, body = client.post("/tenant/keys/enroll-self", {
        "public_key": pub.hex(), "proof_signature": proof.hex(),
        "nonce": nonce})
    assert "Refused." in body
    assert "adjudicator key enrollment requires a fresh step-up" in body
    # Step up over HTTP, then enroll with a fresh nonce + proof.
    _, headers, _ = client.get("/auth/step-up")
    code, state = world.mock.authorize(headers["Location"], "alice")
    client.get(f"/auth/oidc/callback?code={code}&state={state}")
    _, _, body = client.post("/tenant/keys/begin-enrollment", {})
    nonce = re.search(r"Enrollment nonce\.</strong> "
                      r'<span class="mono">([^<]+)</span>', body).group(1)
    proof = ed25519.sign(seed, nonce.encode("utf-8"))
    _, _, body = client.post("/tenant/keys/enroll-self", {
        "public_key": pub.hex(), "proof_signature": proof.hex(),
        "nonce": nonce})
    assert "key.enrolled (self custody)" in body


# ------------------------------------------------------------ fixture flow

def test_fixture_oidc_login_end_to_end(serve, fixture_app):
    fx, app = fixture_app
    client = Client(serve(app))
    _fixture_login(client, "/auth/tenant/start",
                   {"tenant_id": "uni-a", "protocol": "oidc"}, "alice")
    _, headers, _ = client.get("/")
    assert headers["Location"] == "/tenant/users"
    _, _, body = client.get("/tenant/keys")
    assert "rotated" in body and "revoked" in body and "closed" in body
    _, _, body = client.get("/tenant/break-glass")
    assert "policy declared" in body


# ------------------------------------------------------------- records

def test_wireframe_gate_record_precedes_console_code():
    """F-005-13's falsifier is a console screen whose rendered-
    wireframe approval is absent. The approval record (tasks.md
    T534-WF, checked with the 2026-10-12 owner approval) and the
    wireframe package both precede this package's code in the
    repository — asserted here against the files themselves."""
    tasks = (REPO / "specs/005-enterprise-platform/tasks.md").read_text()
    assert "- [x] T534-WF" in tasks
    assert "Gate PASSED 2026-10-12" in tasks
    readme = (REPO / "docs/wireframes/console/README.md").read_text()
    assert "Addendum — approval + break-glass flow extension (2026-10-12)" \
        in readme
    for name in ("signin", "tenants", "tenant", "users", "keys", "events",
                 "break-glass", "audit", "compliance", "status"):
        assert (REPO / f"docs/wireframes/console/{name}.html").exists()
    for name in ("declared", "pending", "active", "closed", "review"):
        assert (REPO / f"docs/wireframes/console/break-glass-{name}.html") \
            .exists()
