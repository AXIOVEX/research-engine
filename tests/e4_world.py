"""Two-tenant OIDC world for the E4 tenancy batteries (T526–T533).

Extends the E1 world with a second tenant (uni-b) provisioned
through the platform plane, its own mock IdP issuer, its own tenant
admin (admin-b), a researcher (bob), and an adjudicator (bess).
Everything the E4 batteries attack crosses THIS boundary.
"""
from __future__ import annotations

from types import SimpleNamespace

import tekmerion.platform.authz as authz
from tekmerion.platform.directory import IdPConfig

from e1_world import TENANT_A, ISSUER_A, build_world, login_user, step_up_session

TENANT_B = "uni-b"
ISSUER_B = "https://idp-b.test"

USERS_B = {
    "admin-b": {"email": "admin@uni-b.test", "name": "Bea Admin", "affiliation": "Uni B"},
    "bob": {"email": "bob@uni-b.test", "name": "Bob Researcher", "affiliation": "Uni B"},
    "bess": {"email": "bess@uni-b.test", "name": "Bess Adjudicator", "affiliation": "Uni B"},
}


def build_two_tenant_world(tmp_path) -> SimpleNamespace:
    w = build_world(tmp_path)
    svc = w.service
    w.mock.add_issuer(ISSUER_B, USERS_B)
    svc.create_tenant(w.root_session, tenant_id=TENANT_B, name="University B")
    svc.provision_tenant_idp(w.root_session, IdPConfig(
        tenant_id=TENANT_B, issuer=ISSUER_B, client_id="tekmerion-uni-b",
        client_secret_ref="secret:uni-b-idp", redirect_uri="https://uni-b.test/callback"),
        client_secret="b-idp-secret")
    session, admin_b = login_b(w, "admin-b")
    svc.grant_role(w.root_session, identity_id=admin_b.identity_id,
                   role=authz.TENANT_ADMIN, tenant_id=TENANT_B)
    admin_b_session, admin_b = login_b(w, "admin-b")
    # Spec 013: tenant B's admin standing session is stepped up at
    # world build, like tenant A's (CLM-013-16/-17 gates).
    step_up_session(svc, w.mock, admin_b_session, TENANT_B, ISSUER_B,
                    "admin-b", USERS_B)
    w.tenant_b, w.issuer_b = TENANT_B, ISSUER_B
    w.admin_b, w.admin_b_session = admin_b, admin_b_session
    return w


def login_b(w, subject: str, role: str | None = None):
    """Log a uni-b user in through uni-b's own IdP door."""
    svc = w.service
    if role is not None:
        _, ident = _peek_login_b(w, subject)
        svc.grant_role(w.admin_b_session, identity_id=ident.identity_id,
                       role=role, tenant_id=TENANT_B)
    return _do_login_b(w, subject)


def _do_login_b(w, subject: str):
    svc = w.service
    url = svc.begin_login(TENANT_B, ISSUER_B)
    code, state = w.mock.authorize(url, subject)
    session = svc.complete_login(state, code)
    return session, svc.directory.find_identity(TENANT_B, ISSUER_B, subject)


def _peek_login_b(w, subject: str):
    return _do_login_b(w, subject)
