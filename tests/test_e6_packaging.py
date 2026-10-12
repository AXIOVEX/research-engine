"""E6 self-hosted packaging battery (Spec 005 T546; CLM-005-12).

F-005-12's two checkable shapes: (1) *same battery, both shapes* —
one scenario (bootstrap → tenant → IdP → login → grant → compliance
seed → SPRS report → audit export → standalone verify) runs against
a hosted profile and a self-hosted profile and produces the same
outcomes, under a role model whose fingerprint matches across
shapes; (2) *payload absence* — the self-hosted tenant's record
(identifiers, POA&M content, events) never appears in the hosted
deployment's ledgers or files.
"""
from __future__ import annotations

import pytest

pytest.importorskip("axiomere")

from tekmerion.platform import authz  # noqa: E402
from tekmerion.platform.directory import IdPConfig  # noqa: E402
from tekmerion.platform.exports import verify_platform_audit_export  # noqa: E402
from tekmerion.platform.packaging import (  # noqa: E402
    DeploymentProfile, role_model_fingerprint,
)

from e1_world import USERS_A, build_world  # noqa: E402

ISSUER_SH = "https://idp-sh.test"
TENANT_SH = "selfhosted-uni"
MARKER = "self-hosted-only-weakness-7f3a"


def _self_hosted_world(tmp_path):
    """A second deployment whose tenant is created in the
    self-hosted shape, with its own IdP door."""
    w = build_world(tmp_path)
    svc = w.service
    w.mock.add_issuer(ISSUER_SH, USERS_A)
    svc.create_tenant(w.root_session, tenant_id=TENANT_SH,
                      name="Self-Hosted University", shape="self-hosted",
                      region="institution-dc")
    svc.provision_tenant_idp(w.root_session, IdPConfig(
        tenant_id=TENANT_SH, issuer=ISSUER_SH, client_id="tekmerion-sh",
        client_secret_ref="secret:sh-idp",
        redirect_uri="https://sh.test/callback"), client_secret="sh-secret")
    url = svc.begin_login(TENANT_SH, ISSUER_SH)
    code, state = w.mock.authorize(url, "admin-a")
    session = svc.complete_login(state, code)
    admin = svc.directory.find_identity(TENANT_SH, ISSUER_SH, "admin-a")
    svc.grant_role(w.root_session, identity_id=admin.identity_id,
                   role=authz.TENANT_ADMIN, tenant_id=TENANT_SH)
    url = svc.begin_login(TENANT_SH, ISSUER_SH)
    code, state = w.mock.authorize(url, "admin-a")
    w.sh_session = svc.complete_login(state, code)
    w.sh_tenant = TENANT_SH
    return w


def _scenario(svc, admin_session, tenant_id, out_dir, *, weakness="w"):
    """The parity scenario: identical calls, both shapes."""
    svc.seed_control_states(admin_session, tenant_id=tenant_id)
    svc.poam_create_item(
        admin_session, tenant_id=tenant_id, title="Scenario item",
        weakness=weakness, affected_requirements=["3.12.2"],
        source_ref="scenario/ssp")
    report = svc.sprs_report(admin_session, tenant_id=tenant_id)
    manifest = svc.export_tenant_audit(admin_session, tenant_id, out_dir)
    verification = verify_platform_audit_export(out_dir)
    return {
        "score": report["score"],
        "export_ok": verification.ok,
        "marking": manifest["cui_marking"]["status"],
        "pin": svc.residency_pin(tenant_id),
    }


def test_same_battery_both_shapes(tmp_path):
    hosted = build_world(tmp_path / "hosted")
    self_hosted = _self_hosted_world(tmp_path / "selfhosted")
    outcomes_hosted = _scenario(
        hosted.service, hosted.admin_session, hosted.tenant_id,
        str(tmp_path / "exp-hosted"))
    outcomes_sh = _scenario(
        self_hosted.service, self_hosted.sh_session, TENANT_SH,
        str(tmp_path / "exp-sh"), weakness=MARKER)
    # Same outcomes under both shapes (the pin differs in shape and
    # region — recorded facts, asserted separately below).
    assert outcomes_hosted["score"] == outcomes_sh["score"] == -156
    assert outcomes_hosted["export_ok"] is True
    assert outcomes_sh["export_ok"] is True
    assert outcomes_hosted["marking"] == outcomes_sh["marking"] == "unmarked"
    assert outcomes_sh["pin"]["shape"] == "self-hosted"
    assert outcomes_sh["pin"]["region"] == "institution-dc"
    assert outcomes_hosted["pin"]["shape"] == "hosted"


def test_role_model_fingerprint_is_shape_invariant():
    hosted = DeploymentProfile(shape="hosted", root="/srv/hosted",
                               tenants=["uni-a", "uni-b"])
    self_hosted = DeploymentProfile(
        shape="self-hosted", root="/srv/sh", region="institution-dc",
        custody="delegated", signer_ref="kms:institution-signer",
        tenants=[TENANT_SH])
    assert hosted.describe()["role_model_fingerprint"] == \
        self_hosted.describe()["role_model_fingerprint"] == \
        role_model_fingerprint()
    assert self_hosted.describe()["custody"] == "delegated"
    assert "AXMR1" in self_hosted.describe()["upgrade_path"]


def test_profile_validation():
    with pytest.raises(ValueError):
        DeploymentProfile(shape="self-hosted", root="/x",
                          tenants=["a", "b"])  # single-tenant by shape
    with pytest.raises(ValueError):
        DeploymentProfile(shape="hosted", root="/x",
                          custody="delegated")  # signer by reference only
    with pytest.raises(ValueError):
        DeploymentProfile(shape="sideways", root="/x")


def test_self_hosted_payloads_absent_from_hosted_plane(tmp_path):
    hosted = build_world(tmp_path / "hosted")
    self_hosted = _self_hosted_world(tmp_path / "selfhosted")
    _scenario(self_hosted.service, self_hosted.sh_session, TENANT_SH,
              str(tmp_path / "exp-sh"), weakness=MARKER)
    _scenario(hosted.service, hosted.admin_session, hosted.tenant_id,
              str(tmp_path / "exp-hosted"))
    hosted_root = tmp_path / "hosted" / "platform"
    sh_root = tmp_path / "selfhosted" / "platform"
    # The self-hosted tenant's record exists in its own deployment…
    sh_bytes = b"".join(p.read_bytes() for p in sh_root.glob("*.axmr"))
    assert TENANT_SH.encode() in sh_bytes and MARKER.encode() in sh_bytes
    # …and nowhere in the hosted deployment's files or ledgers.
    hosted_bytes = b"".join(p.read_bytes() for p in hosted_root.glob("*.axmr"))
    assert TENANT_SH.encode() not in hosted_bytes
    assert MARKER.encode() not in hosted_bytes
    assert not (hosted_root / f"tenant-{TENANT_SH}.axmr").exists()
    # The roots are disjoint deployments: the self-hosted tenant's
    # ledger file exists only under its own root.
    assert (sh_root / f"tenant-{TENANT_SH}.axmr").exists()
