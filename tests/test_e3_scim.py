"""Spec 005 E3 — SCIM 2.0 provisioning & lifecycle (T518–T524):
the conformance-style Users/Groups cycle (F-005-06), mapping-gated
group→role grants (T519), JIT least privilege for both doors
(F-005-07), the deprovisioning pipeline's both halves (F-005-05),
adjudicator re-enrollment with countersign + the key sweep (T522),
PII-off-ledger directory erasure (T523), and the lifecycle admin API
(T524). Refusals are ledgered before the raise, in the E1/E2 style.
"""

import json
from types import SimpleNamespace

import axiomere
import pytest

from e1_world import ISSUER_A, USERS_A, build_world, login_user
from tekmerion.platform import authz
from tekmerion.platform.directory import IdPConfig
from tekmerion.platform.errors import (
    AuthorizationDenied, ConfigurationError, GateDenied,
)
from tekmerion.platform.gate import (
    ApiKeyAuth, GatedStudyWriter, SessionAuth, canonical_intent,
)
from tekmerion.platform.keys import LocalKeySigner
from tekmerion.platform.ledger import (
    GROUP_MAPPING_APPROVED, GROUP_MAPPING_REVOKED, GROUP_MEMBERSHIP_GRANTED,
    GROUP_MEMBERSHIP_REVOKED, IDENTITY_CREATED, IDENTITY_DEACTIVATED,
    IDENTITY_REACTIVATED, IDENTITY_UPDATED, KEY_CLOSED, KEY_ENROLLED,
    ROLE_GRANTED, ROLE_REVOKED, SCIM_SYNC_FAILED, SCIM_SYNC_SUCCEEDED,
    SCIM_TOKEN_ISSUED, SCIM_TOKEN_REVOKED, DIRECTORY_PII_ERASED,
)
from tekmerion.platform.scim import (
    IDENTITY_EXTENSION, ScimAuthenticationError, ScimBadRequestError,
    ScimNotFoundError, ScimUniquenessError,
)
from tekmerion.store import StudyStore

STUDY_ID = "study-e3"
CLAIM = {"text": "Water boils at 100C at 1 atm.", "status": "contested"}
VERDICT = {"state": "SUPPORTED", "basis": "two independent checks"}


@pytest.fixture()
def world(tmp_path):
    return build_world(tmp_path)


@pytest.fixture()
def scim(world):
    cred, secret = world.service.issue_scim_token(
        world.admin_session, tenant_id=world.tenant_id)
    return cred.credential_id, secret


def ledger(w):
    return w.service._tenant_ledger(w.tenant_id)


def events(w, type_):
    return [e for e in ledger(w).events() if e["type"] == type_]


def create_user(w, cred, secret, user_name="carol", **over):
    doc = {"userName": user_name, "displayName": "Carol Provisioned",
           "emails": [{"value": "carol@uni-a.test", "primary": True, "type": "work"}],
           "externalId": f"ext-{user_name}"}
    doc.update(over)
    return w.service.scim_create_user(w.tenant_id, cred, secret, doc)


def ext_id(doc):
    return doc[IDENTITY_EXTENSION]["identity_id"]


def step_up(w, session, identity, nonce="stepup-nonce"):
    config = w.service.directory.idp(identity.tenant_id, identity.issuer)
    idtok = w.mock.issue_token(
        issuer=identity.issuer, subject=identity.subject,
        audience=config.client_id, nonce=nonce,
        profile=USERS_A[identity.subject])
    w.service.step_up(session, id_token=idtok, nonce=nonce)


def enroll_self(w, session):
    seed_hex, _ = axiomere.generate_keypair()
    signer = LocalKeySigner(seed_hex)
    nonce = w.service.begin_enrollment(session)
    rec = w.service.enroll_self_key(
        session, public_key=signer.public_key,
        proof_signature=signer.sign(nonce.encode()), nonce=nonce)
    return signer, rec


def make_writer(w, tmp_path):
    store = StudyStore.create(str(tmp_path / "study.axmr"))
    return GatedStudyWriter(w.service, store, tenant_id=w.tenant_id,
                            study_id=STUDY_ID), store


# -- credential issuance & authentication (T518) -------------------------------


def test_token_issuance_records_hash_only_and_requires_tenant_admin(world, scim):
    cred_id, secret = scim
    state = world.service.scim.tenant(world.tenant_id)
    record = state.credentials[cred_id]
    assert record.secret_hash != secret and secret not in record.secret_hash
    assert events(world, SCIM_TOKEN_ISSUED)
    # A study-role session cannot mint provisioning credentials.
    alice_session, _ = login_user(world, "alice", role=authz.RESEARCHER)
    with pytest.raises(AuthorizationDenied):
        world.service.issue_scim_token(alice_session, tenant_id=world.tenant_id)
    # Neither can the platform admin: the planes are disjoint (E1 model).
    with pytest.raises(AuthorizationDenied):
        world.service.issue_scim_token(world.root_session, tenant_id=world.tenant_id)


def test_bad_secret_and_unknown_credential_refused_and_ledgered(world, scim):
    cred_id, secret = scim
    before = len(events(world, SCIM_SYNC_FAILED))
    with pytest.raises(ScimAuthenticationError):
        world.service.scim_list_users(world.tenant_id, cred_id, "wrong-secret")
    with pytest.raises(ScimAuthenticationError):
        world.service.scim_list_users(world.tenant_id, "scim_deadbeef", secret)
    failures = events(world, SCIM_SYNC_FAILED)
    assert len(failures) == before + 2
    assert all(e["payload"]["outcome"] == "failed" for e in failures)
    assert world.service.scim.tenant(world.tenant_id).users == {}


def test_revoked_credential_refused(world, scim):
    cred_id, secret = scim
    world.service.revoke_scim_token(world.admin_session,
                                    tenant_id=world.tenant_id,
                                    credential_id=cred_id)
    assert events(world, SCIM_TOKEN_REVOKED)
    with pytest.raises(ScimAuthenticationError):
        world.service.scim_list_users(world.tenant_id, cred_id, secret)


def test_unknown_tenant_refused_and_recorded_on_deployment_ledger(world, scim):
    cred_id, secret = scim
    with pytest.raises(ScimNotFoundError):
        world.service.scim_list_users("uni-nope", cred_id, secret)
    dep_types = world.service.deployment_ledger.event_types()
    assert SCIM_SYNC_FAILED in dep_types


ISSUER_B = "https://idp-b.test"
USERS_B = {"admin-b": {"name": "Bea Admin", "email": "admin@uni-b.test"}}


def make_tenant_b(w):
    w.mock.add_issuer(ISSUER_B, USERS_B)
    w.service.create_tenant(w.root_session, tenant_id="uni-b", name="University B")
    w.service.provision_tenant_idp(w.root_session, IdPConfig(
        tenant_id="uni-b", issuer=ISSUER_B, client_id="tekmerion-uni-b",
        client_secret_ref="secret:uni-b-idp",
        redirect_uri="https://uni-b.test/callback"),
        client_secret="test-only-uni-b-secret")
    session_b = w.login("uni-b", ISSUER_B, "admin-b")
    ident_b = w.service.directory.find_identity("uni-b", ISSUER_B, "admin-b")
    w.service.grant_role(w.root_session, identity_id=ident_b.identity_id,
                         role=authz.TENANT_ADMIN, tenant_id="uni-b")
    session_b = w.login("uni-b", ISSUER_B, "admin-b")
    cred_b, secret_b = w.service.issue_scim_token(session_b, tenant_id="uni-b")
    return SimpleNamespace(session=session_b, admin=ident_b, cred=cred_b,
                           secret=secret_b, tenant_id="uni-b")


def test_cross_tenant_credential_refused_before_any_state_change(world, scim):
    cred_a, secret_a = scim
    b = make_tenant_b(world)
    users_before = dict(world.service.scim.tenant(world.tenant_id).users)
    with pytest.raises(ScimAuthenticationError):
        world.service.scim_create_user(
            world.tenant_id, b.cred.credential_id, b.secret,
            {"userName": "intruder", "displayName": "Intruder"})
    # The refusal is recorded in the ADDRESSED tenant's ledger, and
    # nothing was provisioned by it.
    failures = [e for e in events(world, SCIM_SYNC_FAILED)
                if e["payload"].get("reason") == "credential belongs to another tenant"]
    assert failures
    assert world.service.scim.tenant(world.tenant_id).users == users_before
    # Symmetric: A's credential at B's endpoint.
    with pytest.raises(ScimAuthenticationError):
        world.service.scim_create_user(
            b.tenant_id, cred_a, secret_a, {"userName": "intruder"})
    assert world.service.scim.tenant(b.tenant_id).users == {}


# -- Users cycle (T518, F-005-06) -----------------------------------------------


def test_create_user_full_cycle(world, scim):
    cred_id, secret = scim
    status, doc = create_user(world, cred_id, secret)
    assert status == 201
    assert doc["schemas"] == ["urn:ietf:params:scim:schemas:core:2.0:User"]
    assert doc["userName"] == "carol" and doc["active"] is True
    assert doc["displayName"] == "Carol Provisioned"
    assert doc["emails"][0]["value"] == "carol@uni-a.test"
    assert doc["externalId"] == "ext-carol"
    assert doc["meta"]["resourceType"] == "User"
    identity = world.service.directory.identity(ext_id(doc))
    assert identity.issuer == "scim" and identity.created_via == "scim"
    assert identity.active and identity.display_name == "Carol Provisioned"
    created = [e for e in events(world, IDENTITY_CREATED)
               if e["payload"].get("via") == "scim"]
    assert created and created[0]["payload"]["provisioning"] == "scim"
    syncs = [e for e in events(world, SCIM_SYNC_SUCCEEDED)
             if e["payload"].get("op") == "user.create"]
    assert syncs and syncs[0]["payload"]["identity_id"] == identity.identity_id
    # A SCIM-provisioned identity holds no study role (T519's premise).
    assert world.service.roles_of(identity.identity_id, world.tenant_id) == set()
    # Readable back, by id and by list.
    status, fetched = world.service.scim_get_user(world.tenant_id, cred_id, secret,
                                                  doc["id"])
    assert status == 200 and fetched["id"] == doc["id"]


def test_create_user_duplicate_conflicts_are_409_and_ledgered(world, scim):
    cred_id, secret = scim
    create_user(world, cred_id, secret)
    with pytest.raises(ScimUniquenessError) as exc:
        create_user(world, cred_id, secret, user_name="carol2",
                    externalId="ext-carol")  # duplicate externalId
    assert exc.value.status == 409 and exc.value.scim_type == "uniqueness"
    assert exc.value.error_doc()["status"] == "409"
    with pytest.raises(ScimUniquenessError):
        world.service.scim_create_user(
            world.tenant_id, cred_id, secret,
            {"userName": "CAROL", "externalId": "ext-other"})  # case-insensitive
    assert len(world.service.scim.tenant(world.tenant_id).users) == 1
    assert events(world, SCIM_SYNC_FAILED)


def test_create_user_without_username_refused_atomically(world, scim):
    cred_id, secret = scim
    identities_before = len(world.service.directory.identities)
    with pytest.raises(ScimBadRequestError) as exc:
        world.service.scim_create_user(world.tenant_id, cred_id, secret,
                                       {"displayName": "No Name"})
    assert exc.value.scim_type == "invalidValue"
    assert len(world.service.directory.identities) == identities_before


def test_create_user_with_unknown_group_refused_atomically(world, scim):
    cred_id, secret = scim
    identities_before = len(world.service.directory.identities)
    with pytest.raises(ScimBadRequestError):
        world.service.scim_create_user(
            world.tenant_id, cred_id, secret,
            {"userName": "dave", "groups": [{"value": "no-such-group"}]})
    assert len(world.service.directory.identities) == identities_before
    assert world.service.scim.tenant(world.tenant_id).users == {}


def test_list_users_filters_and_pagination(world, scim):
    cred_id, secret = scim
    for name in ("carol", "dave", "erin"):
        create_user(world, cred_id, secret, user_name=name,
                    displayName=f"{name.title()} Person")
    status, doc = world.service.scim_list_users(world.tenant_id, cred_id, secret)
    assert status == 200 and doc["totalResults"] == 3
    _, doc = world.service.scim_list_users(
        world.tenant_id, cred_id, secret, filter_expr='userName eq "dave"')
    assert doc["totalResults"] == 1
    assert doc["Resources"][0]["userName"] == "dave"
    _, doc = world.service.scim_list_users(
        world.tenant_id, cred_id, secret, filter_expr='displayName co "person"')
    assert doc["totalResults"] == 3
    _, doc = world.service.scim_list_users(
        world.tenant_id, cred_id, secret, filter_expr='active eq "true"')
    assert doc["totalResults"] == 3
    _, doc = world.service.scim_list_users(
        world.tenant_id, cred_id, secret, start_index=2, count=1)
    assert doc["totalResults"] == 3 and len(doc["Resources"]) == 1
    assert doc["startIndex"] == 2
    with pytest.raises(ScimBadRequestError) as exc:
        world.service.scim_list_users(
            world.tenant_id, cred_id, secret,
            filter_expr='userName eq "x" and active eq "true"')
    assert exc.value.scim_type == "invalidFilter"
    with pytest.raises(ScimNotFoundError):
        world.service.scim_get_user(world.tenant_id, cred_id, secret, "nope")


def test_replace_user_updates_profile_and_renames(world, scim):
    cred_id, secret = scim
    _, doc = create_user(world, cred_id, secret)
    identity_id = ext_id(doc)
    status, updated = world.service.scim_replace_user(
        world.tenant_id, cred_id, secret, doc["id"],
        {"userName": "carol-renamed", "displayName": "Carol R.",
         "emails": [{"value": "carol.r@uni-a.test", "primary": True}],
         "externalId": "ext-carol-2", "active": True})
    assert status == 200 and updated["userName"] == "carol-renamed"
    identity = world.service.directory.identity(identity_id)
    assert identity.subject == "carol-renamed"
    assert identity.display_name == "Carol R."
    assert identity.email == "carol.r@uni-a.test"
    assert world.service.directory.find_identity(
        world.tenant_id, "scim", "carol") is None
    assert world.service.directory.find_identity(
        world.tenant_id, "scim", "carol-renamed") is identity
    updated_events = events(world, IDENTITY_UPDATED)
    assert updated_events
    fields = updated_events[-1]["payload"]["fields"]
    assert "userName" in fields and "displayName" in fields


def test_replace_user_rename_collision_refused_before_mutation(world, scim):
    cred_id, secret = scim
    create_user(world, cred_id, secret, user_name="carol")
    _, d2 = create_user(world, cred_id, secret, user_name="dave")
    updates_before = len(events(world, IDENTITY_UPDATED))
    with pytest.raises(ScimUniquenessError):
        world.service.scim_replace_user(
            world.tenant_id, cred_id, secret, d2["id"],
            {"userName": "carol", "displayName": "Dave"})
    state = world.service.scim.tenant(world.tenant_id)
    assert state.users[d2["id"]].user_name == "dave"
    assert len(events(world, IDENTITY_UPDATED)) == updates_before


def test_patch_user_entra_style_paths(world, scim):
    cred_id, secret = scim
    _, doc = create_user(world, cred_id, secret)
    # Pathless replace (Entra's dominant PATCH shape).
    status, updated = world.service.scim_patch_user(
        world.tenant_id, cred_id, secret, doc["id"],
        {"Operations": [{"op": "Replace",
                         "value": {"displayName": "Carol Patched"}}]})
    assert status == 200 and updated["displayName"] == "Carol Patched"
    # emails[type eq "work"].value path.
    _, updated = world.service.scim_patch_user(
        world.tenant_id, cred_id, secret, doc["id"],
        {"Operations": [{"op": "replace",
                         "path": 'emails[type eq "work"].value',
                         "value": "carol.new@uni-a.test"}]})
    assert updated["emails"][0]["value"] == "carol.new@uni-a.test"
    # name.givenName rewrites the display name's first part.
    _, updated = world.service.scim_patch_user(
        world.tenant_id, cred_id, secret, doc["id"],
        {"Operations": [{"op": "replace", "path": "name.givenName",
                         "value": "Carolina"}]})
    assert updated["displayName"] == "Carolina Patched"


def test_patch_user_refusals(world, scim):
    cred_id, secret = scim
    _, doc = create_user(world, cred_id, secret)
    with pytest.raises(ScimBadRequestError) as exc:
        world.service.scim_patch_user(
            world.tenant_id, cred_id, secret, doc["id"],
            {"Operations": [{"op": "replace", "path": "manager", "value": "x"}]})
    assert exc.value.scim_type == "invalidPath"
    with pytest.raises(ScimBadRequestError):
        world.service.scim_patch_user(
            world.tenant_id, cred_id, secret, doc["id"],
            {"Operations": [{"op": "frobnicate", "path": "active", "value": False}]})
    with pytest.raises(ScimBadRequestError):
        world.service.scim_patch_user(world.tenant_id, cred_id, secret,
                                      doc["id"], {"Operations": []})
    with pytest.raises(ScimNotFoundError):
        world.service.scim_patch_user(
            world.tenant_id, cred_id, secret, "missing-id",
            {"Operations": [{"op": "replace", "path": "active", "value": False}]})


def test_patch_on_deactivated_user_still_updates_profile(world, scim):
    cred_id, secret = scim
    _, doc = create_user(world, cred_id, secret)
    world.service.scim_patch_user(
        world.tenant_id, cred_id, secret, doc["id"],
        {"Operations": [{"op": "replace", "path": "active", "value": False}]})
    status, updated = world.service.scim_patch_user(
        world.tenant_id, cred_id, secret, doc["id"],
        {"Operations": [{"op": "replace", "path": "displayName",
                         "value": "Carol Inactive"}]})
    assert status == 200 and updated["displayName"] == "Carol Inactive"
    assert updated["active"] is False


# -- Groups cycle (T518) ---------------------------------------------------------


def create_group(w, cred, secret, name="Researchers", members=()):
    return w.service.scim_create_group(
        w.tenant_id, cred, secret,
        {"displayName": name,
         "members": [{"value": m} for m in members]})


def test_group_crud_and_membership(world, scim):
    cred_id, secret = scim
    _, u1 = create_user(world, cred_id, secret, user_name="carol")
    _, u2 = create_user(world, cred_id, secret, user_name="dave")
    status, g = create_group(world, cred_id, secret,
                             members=[ext_id(u1)])
    assert status == 201
    assert g["members"][0]["value"] == ext_id(u1)
    assert g["members"][0]["display"] == "Carol Provisioned"
    _, fetched = world.service.scim_get_group(world.tenant_id, cred_id, secret,
                                              g["id"])
    assert fetched["displayName"] == "Researchers"
    _, listing = world.service.scim_list_groups(
        world.tenant_id, cred_id, secret, filter_expr='displayName eq "Researchers"')
    assert listing["totalResults"] == 1
    # PATCH add + remove members.
    _, g = world.service.scim_patch_group(
        world.tenant_id, cred_id, secret, g["id"],
        {"Operations": [{"op": "add", "path": "members",
                         "value": [{"value": ext_id(u2)}]}]})
    assert {m["value"] for m in g["members"]} == {ext_id(u1), ext_id(u2)}
    _, g = world.service.scim_patch_group(
        world.tenant_id, cred_id, secret, g["id"],
        {"Operations": [{"op": "remove", "path": "members",
                         "value": [{"value": ext_id(u1)}]}]})
    assert {m["value"] for m in g["members"]} == {ext_id(u2)}
    assert events(world, GROUP_MEMBERSHIP_GRANTED)
    assert events(world, GROUP_MEMBERSHIP_REVOKED)
    # Replace with an explicit member set, then delete.
    _, g = world.service.scim_replace_group(
        world.tenant_id, cred_id, secret, g["id"],
        {"displayName": "Researchers",
         "members": [{"value": ext_id(u1)}]})
    assert {m["value"] for m in g["members"]} == {ext_id(u1)}
    status, _ = world.service.scim_delete_group(world.tenant_id, cred_id, secret,
                                                g["id"])
    assert status == 204
    with pytest.raises(ScimNotFoundError):
        world.service.scim_get_group(world.tenant_id, cred_id, secret, g["id"])


def test_group_member_must_be_a_provisioned_user_of_the_tenant(world, scim):
    cred_id, secret = scim
    alice_session, alice = login_user(world, "alice")  # IdP-door identity
    with pytest.raises(ScimBadRequestError):
        create_group(world, cred_id, secret, members=[alice.identity_id])
    with pytest.raises(ScimBadRequestError):
        create_group(world, cred_id, secret, members=["totally-unknown"])
    assert world.service.scim.tenant(world.tenant_id).groups == {}


def test_group_display_name_uniqueness(world, scim):
    cred_id, secret = scim
    create_group(world, cred_id, secret)
    with pytest.raises(ScimUniquenessError):
        create_group(world, cred_id, secret)


# -- Group→role mappings (T519) ---------------------------------------------------


def test_membership_grants_nothing_without_a_mapping(world, scim):
    cred_id, secret = scim
    _, u1 = create_user(world, cred_id, secret)
    create_group(world, cred_id, secret, members=[ext_id(u1)])
    identity = world.service.directory.identity(ext_id(u1))
    assert world.service.roles_of(identity.identity_id, world.tenant_id) == set()
    grants = [e for e in events(world, ROLE_GRANTED)
              if e["payload"].get("identity_id") == identity.identity_id]
    assert grants == []


def test_mapping_grants_current_and_future_members(world, scim):
    cred_id, secret = scim
    _, u1 = create_user(world, cred_id, secret, user_name="carol")
    _, g = create_group(world, cred_id, secret, members=[ext_id(u1)])
    mapping = world.service.approve_group_mapping(
        world.admin_session, tenant_id=world.tenant_id,
        group_ref=g["id"], role=authz.RESEARCHER)
    assert events(world, GROUP_MAPPING_APPROVED)
    assert world.service.roles_of(ext_id(u1), world.tenant_id) == {authz.RESEARCHER}
    grant = [e for e in events(world, ROLE_GRANTED)
             if e["payload"].get("via") == "scim-group-mapping"]
    assert grant and grant[0]["payload"]["mapping_id"] == mapping.mapping_id
    assert grant[0]["payload"]["actor_id"] == "system"
    # A future member is granted on add.
    _, u2 = create_user(world, cred_id, secret, user_name="dave")
    world.service.scim_patch_group(
        world.tenant_id, cred_id, secret, g["id"],
        {"Operations": [{"op": "add", "path": "members",
                         "value": [{"value": ext_id(u2)}]}]})
    assert world.service.roles_of(ext_id(u2), world.tenant_id) == {authz.RESEARCHER}
    # Re-approving the same mapping is a no-op returning the record.
    again = world.service.approve_group_mapping(
        world.admin_session, tenant_id=world.tenant_id,
        group_ref=g["id"], role=authz.RESEARCHER)
    assert again.mapping_id == mapping.mapping_id


def test_mapping_requires_provisioning_admin_and_study_role(world, scim):
    cred_id, secret = scim
    create_group(world, cred_id, secret)
    alice_session, _ = login_user(world, "alice", role=authz.RESEARCHER)
    with pytest.raises(AuthorizationDenied):
        world.service.approve_group_mapping(
            alice_session, tenant_id=world.tenant_id,
            group_ref="Researchers", role=authz.RESEARCHER)
    with pytest.raises(ConfigurationError):
        world.service.approve_group_mapping(
            world.admin_session, tenant_id=world.tenant_id,
            group_ref="Researchers", role=authz.TENANT_ADMIN)
    with pytest.raises(ConfigurationError):
        world.service.approve_group_mapping(
            world.admin_session, tenant_id=world.tenant_id,
            group_ref="Researchers", role=authz.PLATFORM_ADMIN)
    assert world.service.scim.tenant(world.tenant_id).mappings == {}


def test_membership_removal_withdraws_role_when_last_source(world, scim):
    cred_id, secret = scim
    _, u1 = create_user(world, cred_id, secret)
    _, g = create_group(world, cred_id, secret, members=[ext_id(u1)])
    world.service.approve_group_mapping(
        world.admin_session, tenant_id=world.tenant_id,
        group_ref=g["id"], role=authz.RESEARCHER)
    world.service.scim_patch_group(
        world.tenant_id, cred_id, secret, g["id"],
        {"Operations": [{"op": "remove", "path": "members",
                         "value": [{"value": ext_id(u1)}]}]})
    assert world.service.roles_of(ext_id(u1), world.tenant_id) == set()
    revocations = [e for e in events(world, ROLE_REVOKED)
                   if e["payload"].get("via") == "scim-group-mapping"]
    assert revocations


def test_role_survives_on_second_mapped_group(world, scim):
    cred_id, secret = scim
    _, u1 = create_user(world, cred_id, secret)
    _, g1 = create_group(world, cred_id, secret, name="G1", members=[ext_id(u1)])
    _, g2 = create_group(world, cred_id, secret, name="G2", members=[ext_id(u1)])
    for g in (g1, g2):
        world.service.approve_group_mapping(
            world.admin_session, tenant_id=world.tenant_id,
            group_ref=g["id"], role=authz.RESEARCHER)
    revocations_before = len(events(world, ROLE_REVOKED))
    world.service.scim_patch_group(
        world.tenant_id, cred_id, secret, g1["id"],
        {"Operations": [{"op": "remove", "path": "members",
                         "value": [{"value": ext_id(u1)}]}]})
    # Still justified by G2: role survives, no revocation recorded.
    assert world.service.roles_of(ext_id(u1), world.tenant_id) == {authz.RESEARCHER}
    assert len(events(world, ROLE_REVOKED)) == revocations_before
    world.service.scim_patch_group(
        world.tenant_id, cred_id, secret, g2["id"],
        {"Operations": [{"op": "remove", "path": "members",
                         "value": [{"value": ext_id(u1)}]}]})
    assert world.service.roles_of(ext_id(u1), world.tenant_id) == set()


def test_direct_grant_survives_membership_removal(world, scim):
    cred_id, secret = scim
    _, u1 = create_user(world, cred_id, secret)
    _, g = create_group(world, cred_id, secret, members=[ext_id(u1)])
    world.service.approve_group_mapping(
        world.admin_session, tenant_id=world.tenant_id,
        group_ref=g["id"], role=authz.RESEARCHER)
    world.service.grant_role(world.admin_session, identity_id=ext_id(u1),
                             role=authz.RESEARCHER, tenant_id=world.tenant_id)
    world.service.scim_patch_group(
        world.tenant_id, cred_id, secret, g["id"],
        {"Operations": [{"op": "remove", "path": "members",
                         "value": [{"value": ext_id(u1)}]}]})
    assert world.service.roles_of(ext_id(u1), world.tenant_id) == {authz.RESEARCHER}


def test_mapping_revocation_withdraws_role(world, scim):
    cred_id, secret = scim
    _, u1 = create_user(world, cred_id, secret)
    _, g = create_group(world, cred_id, secret, members=[ext_id(u1)])
    mapping = world.service.approve_group_mapping(
        world.admin_session, tenant_id=world.tenant_id,
        group_ref=g["id"], role=authz.ADJUDICATOR)
    assert world.service.roles_of(ext_id(u1), world.tenant_id) == {authz.ADJUDICATOR}
    world.service.revoke_group_mapping(
        world.admin_session, tenant_id=world.tenant_id,
        mapping_id=mapping.mapping_id)
    assert events(world, GROUP_MAPPING_REVOKED)
    assert world.service.roles_of(ext_id(u1), world.tenant_id) == set()
    with pytest.raises(ConfigurationError):
        world.service.revoke_group_mapping(
            world.admin_session, tenant_id=world.tenant_id,
            mapping_id=mapping.mapping_id)


def test_mapping_may_precede_the_group(world, scim):
    cred_id, secret = scim
    world.service.approve_group_mapping(
        world.admin_session, tenant_id=world.tenant_id,
        group_ref="Future Group", role=authz.REVIEWER)
    _, u1 = create_user(world, cred_id, secret)
    create_group(world, cred_id, secret, name="Future Group",
                 members=[ext_id(u1)])
    assert world.service.roles_of(ext_id(u1), world.tenant_id) == {authz.REVIEWER}


# -- Deprovisioning pipeline (T521, F-005-05: both halves) -------------------------


def test_deprovisioning_ends_appends_and_preserves_history(world, tmp_path):
    writer, store = make_writer(world, tmp_path)
    session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    signer, rec = enroll_self(world, session)
    intent = canonical_intent(action=authz.REGISTER_CLAIM, tenant_id=world.tenant_id,
                              study_id=STUDY_ID, event="claim.registered",
                              payload=CLAIM)
    writer.register_claim(SessionAuth(session, rec.fingerprint, signer.sign(intent)),
                          "CLM-1", CLAIM)
    events_before = [dict(e) for e in store.events()]
    # Deprovision (tenant-admin door into the shared core).
    world.service.deactivate_identity(world.admin_session,
                                      identity_id=alice.identity_id,
                                      reason="left the institution")
    # Next request: the old session is dead and a fresh login refuses.
    with pytest.raises(GateDenied):
        writer.register_claim(
            SessionAuth(session, rec.fingerprint, signer.sign(intent)),
            "CLM-2", CLAIM)
    with pytest.raises(Exception):
        world.login(world.tenant_id, world.issuer_a, "alice")
    # Keys closed; the key's status is terminal for new appends.
    registry = world.service.registry(world.tenant_id)
    assert registry.status(rec.fingerprint) == "closed"
    # History intact: the study ledger verifies, the claim stands,
    # and the pre-deactivation signature still verifies against the
    # recorded public key (F-005-05's second half).
    assert store.verify().ok
    assert [dict(e) for e in store.events()] == events_before
    from tekmerion.platform import ed25519
    attribution = None
    for ev in store.events():
        if ev["type"] == "record.snapshot":
            attribution = ev["payload"]["content"]["attribution"]
    assert attribution is not None
    assert ed25519.verify(bytes.fromhex(rec.public_key_hex), intent,
                          bytes.fromhex(attribution["intent_signature"]))


def test_scim_deactivate_and_delete_use_the_same_core(world, scim):
    cred_id, secret = scim
    _, u1 = create_user(world, cred_id, secret, user_name="carol")
    _, g = create_group(world, cred_id, secret, members=[ext_id(u1)])
    world.service.approve_group_mapping(
        world.admin_session, tenant_id=world.tenant_id,
        group_ref=g["id"], role=authz.RESEARCHER)
    # PATCH active=false → SCIM deactivate (T521 via SCIM).
    world.service.scim_patch_user(
        world.tenant_id, cred_id, secret, u1["id"],
        {"Operations": [{"op": "replace", "path": "active", "value": False}]})
    identity = world.service.directory.identity(ext_id(u1))
    assert identity.active is False
    deactivations = [e for e in events(world, IDENTITY_DEACTIVATED)
                     if e["payload"].get("identity_id") == identity.identity_id]
    assert deactivations and deactivations[0]["payload"]["via"] == "scim"
    # Reactivation through the same surface is prospective and recorded.
    world.service.scim_patch_user(
        world.tenant_id, cred_id, secret, u1["id"],
        {"Operations": [{"op": "replace", "path": "active", "value": True}]})
    assert identity.active is True
    assert events(world, IDENTITY_REACTIVATED)
    # DELETE deactivates through the identical core and drops the
    # SCIM record; the identity and its history remain.
    _, u2 = create_user(world, cred_id, secret, user_name="dave")
    status, _ = world.service.scim_delete_user(world.tenant_id, cred_id, secret,
                                               u2["id"])
    assert status == 204
    gone = world.service.directory.identity(ext_id(u2))
    assert gone.active is False
    assert [e for e in events(world, IDENTITY_DEACTIVATED)
            if e["payload"].get("identity_id") == gone.identity_id]
    with pytest.raises(ScimNotFoundError):
        world.service.scim_get_user(world.tenant_id, cred_id, secret, u2["id"])
    assert ledger(world).verify().ok


def test_scim_recreate_after_delete_reactivates_the_same_identity(world, scim):
    cred_id, secret = scim
    _, u1 = create_user(world, cred_id, secret, user_name="carol")
    _, g = create_group(world, cred_id, secret, members=[ext_id(u1)])
    world.service.approve_group_mapping(
        world.admin_session, tenant_id=world.tenant_id,
        group_ref=g["id"], role=authz.RESEARCHER)
    world.service.scim_delete_user(world.tenant_id, cred_id, secret, u1["id"])
    status, u2 = create_user(world, cred_id, secret, user_name="carol")
    assert status == 201 and u2["id"] != u1["id"]  # SCIM ids are never reused
    assert ext_id(u2) == ext_id(u1)               # the identity is the same
    identity = world.service.directory.identity(ext_id(u1))
    assert identity.active is True
    syncs = [e for e in events(world, SCIM_SYNC_SUCCEEDED)
             if e["payload"].get("op") == "user.create"]
    assert syncs[-1]["payload"]["reactivated"] is True
    # Membership did not silently return with the identity.
    assert world.service.roles_of(identity.identity_id, world.tenant_id) == set()


def test_deprovisioned_api_key_principal_cannot_append(world, tmp_path):
    writer, store = make_writer(world, tmp_path)
    svc_ident = world.service.create_service_identity(
        world.admin_session, tenant_id=world.tenant_id, name="connector")
    record, secret = world.service.issue_api_key(
        world.admin_session, tenant_id=world.tenant_id,
        principal_identity_id=svc_ident.identity_id, role_class=authz.RESEARCHER,
        scopes=[authz.REGISTER_CLAIM], lifetime_seconds=3600)
    writer.register_claim(ApiKeyAuth(record.key_id, secret), "CLM-1", CLAIM)
    world.service.deactivate_identity(world.admin_session,
                                      identity_id=svc_ident.identity_id)
    with pytest.raises(GateDenied):
        writer.register_claim(ApiKeyAuth(record.key_id, secret), "CLM-2", CLAIM)


# -- JIT provisioning (T520, F-005-07) --------------------------------------------


def test_jit_oidc_identity_has_no_role_until_grant(world, tmp_path):
    session, mallory = login_user(world, "mallory")  # first assertion: JIT
    assert mallory.created_via == "oidc"
    created = [e for e in events(world, IDENTITY_CREATED)
               if e["payload"].get("identity_id") == mallory.identity_id]
    assert created and created[0]["payload"].get("provisioning") == "jit"
    assert world.service.roles_of(mallory.identity_id, world.tenant_id) == set()
    signer, rec = enroll_self(world, session)
    writer, store = make_writer(world, tmp_path)
    intent = canonical_intent(action=authz.REGISTER_CLAIM, tenant_id=world.tenant_id,
                              study_id=STUDY_ID, event="claim.registered",
                              payload=CLAIM)
    with pytest.raises(GateDenied):
        writer.register_claim(
            SessionAuth(session, rec.fingerprint, signer.sign(intent)),
            "CLM-1", CLAIM)
    # A recorded grant is the only door to a role.
    world.service.grant_role(world.admin_session, identity_id=mallory.identity_id,
                             role=authz.RESEARCHER, tenant_id=world.tenant_id)
    session = world.login(world.tenant_id, world.issuer_a, "mallory")
    writer.register_claim(SessionAuth(session, rec.fingerprint, signer.sign(intent)),
                          "CLM-1", CLAIM)


def test_jit_saml_identity_asserting_tenant_only(tmp_path):
    from e2_world import TENANT_B, build_saml_world, saml_login
    w = build_saml_world(tmp_path)
    session = saml_login(w, "alice")
    identity = w.service.directory.find_identity(
        w.tenant_id, w.idp_a, "alice")
    assert identity is not None and identity.created_via == "saml"
    created = [e for e in w.service._tenant_ledger(w.tenant_id).events()
               if e["type"] == IDENTITY_CREATED
               and e["payload"].get("identity_id") == identity.identity_id]
    assert created and created[0]["payload"].get("provisioning") == "jit"
    assert w.service.roles_of(identity.identity_id, w.tenant_id) == set()
    # Bob's assertion creates his identity in tenant B only.
    saml_login(w, "bob", tenant="uni-b", entity=w.idp_b)
    bob_b = w.service.directory.find_identity(TENANT_B, w.idp_b, "bob")
    assert bob_b is not None and bob_b.tenant_id == TENANT_B
    assert w.service.directory.find_identity(w.tenant_id, w.idp_b, "bob") is None
    assert all(i.subject != "bob"
               for i in w.service.directory.identities.values()
               if i.tenant_id == w.tenant_id)


# -- Key lifecycle completion (T522) ------------------------------------------------


def test_adjudicator_reenrollment_requires_countersign(world, tmp_path):
    session, ada = login_user(world, "ada", role=authz.ADJUDICATOR)
    step_up(world, session, ada)
    signer1, rec1 = enroll_self(world, session)
    # The key is revoked (lost device): recovery is re-enrollment,
    # and for an adjudicator it needs a countersign (§3).
    world.service.revoke_key(world.admin_session, key_fingerprint=rec1.fingerprint,
                             reason="lost device")
    session = world.login(world.tenant_id, world.issuer_a, "ada")
    step_up(world, session, ada)
    seed2, _ = axiomere.generate_keypair()
    signer2 = LocalKeySigner(seed2)
    nonce = world.service.begin_enrollment(session)
    with pytest.raises(GateDenied, match="countersign"):
        world.service.enroll_self_key(
            session, public_key=signer2.public_key,
            proof_signature=signer2.sign(nonce.encode()), nonce=nonce)
    # The countersigned path: subject's proof, admin's countersign.
    nonce = world.service.begin_enrollment(session)
    rec2 = world.service.enroll_key_countersigned(
        world.admin_session, identity_id=ada.identity_id,
        public_key=signer2.public_key,
        proof_signature=signer2.sign(nonce.encode()), nonce=nonce)
    enrolled = [e for e in events(world, KEY_ENROLLED)
                if e["payload"].get("key_fingerprint") == rec2.fingerprint]
    assert enrolled
    payload = enrolled[0]["payload"]
    assert payload["countersigned_by_actor_id"] == world.admin.actor_id
    assert payload["subject_actor_id"] == ada.actor_id
    # The re-enrolled key signs verdicts (stepped-up session).
    writer, store = make_writer(world, tmp_path)
    payload_doc = {"claim_id": "CLM-1", **VERDICT}
    intent = canonical_intent(action=authz.ISSUE_VERDICT, tenant_id=world.tenant_id,
                              study_id=STUDY_ID, event="verdict.issued",
                              payload=payload_doc)
    writer.issue_verdict(
        SessionAuth(session, rec2.fingerprint, signer2.sign(intent)),
        "CLM-1", VERDICT)


def test_countersign_refusals(world):
    alice_session, alice = login_user(world, "alice", role=authz.RESEARCHER)
    seed, _ = axiomere.generate_keypair()
    signer = LocalKeySigner(seed)
    nonce = world.service.begin_enrollment(alice_session)
    with pytest.raises(ConfigurationError):
        world.service.enroll_key_countersigned(
            world.admin_session, identity_id=alice.identity_id,
            public_key=signer.public_key,
            proof_signature=signer.sign(nonce.encode()), nonce=nonce)
    # A deactivated adjudicator cannot be countersigned back in —
    # reactivation is a separate recorded act that must come first.
    ada_session, ada = login_user(world, "ada", role=authz.ADJUDICATOR)
    world.service.deactivate_identity(world.admin_session,
                                      identity_id=ada.identity_id)
    nonce = world.service.registry(world.tenant_id).issue_nonce(ada.identity_id)
    with pytest.raises(GateDenied, match="deactivated"):
        world.service.enroll_key_countersigned(
            world.admin_session, identity_id=ada.identity_id,
            public_key=signer.public_key,
            proof_signature=signer.sign(nonce.encode()), nonce=nonce)


def test_key_sweep_closes_stragglers_of_deprovisioned_identities(world):
    session, mallory = login_user(world, "mallory")
    signer, rec = enroll_self(world, session)
    # Simulate a deactivation that predates the pipeline: the
    # identity is inactive but its key was never closed.
    world.service.directory.identity(mallory.identity_id).active = False
    registry = world.service.registry(world.tenant_id)
    assert registry.is_accepted(rec.fingerprint)
    n = world.service.sweep_identity_keys(world.admin_session,
                                          identity_id=mallory.identity_id)
    assert n == 1 and registry.status(rec.fingerprint) == "closed"
    closed = [e for e in events(world, KEY_CLOSED)
              if e["payload"].get("key_fingerprint") == rec.fingerprint]
    assert closed and closed[0]["payload"]["reason"] == "deprovision-sweep"
    assert world.service.sweep_identity_keys(
        world.admin_session, identity_id=mallory.identity_id) == 0
    with pytest.raises(ConfigurationError):
        world.service.sweep_identity_keys(world.admin_session,
                                          identity_id=world.admin.identity_id)


# -- Directory & erasure (T523) -----------------------------------------------------


def test_directory_erasure_never_touches_a_chain(world, scim):
    cred_id, secret = scim
    _, u1 = create_user(world, cred_id, secret, user_name="carol")
    identity_id = ext_id(u1)
    world.service.scim_patch_user(
        world.tenant_id, cred_id, secret, u1["id"],
        {"Operations": [{"op": "replace", "path": "active", "value": False}]})
    before = [dict(e) for e in ledger(world).events()]
    assert world.service.erase_directory_pii(world.admin_session,
                                             identity_id=identity_id) is True
    identity = world.service.directory.identity(identity_id)
    assert identity.display_name == "" and identity.email == ""
    assert identity.subject == ""
    # The login lookup is gone: the same person returning later is a
    # NEW identity (identifiers are never reused, matrix 3.5.5).
    assert world.service.directory.find_identity(
        world.tenant_id, "scim", "carol") is None
    assert world.service.scim.tenant(world.tenant_id).users == {}
    after = ledger(world).events()
    assert len(after) == len(before) + 1
    assert [dict(e) for e in after[:-1]] == before  # history byte-identical
    assert after[-1]["type"] == DIRECTORY_PII_ERASED
    assert ledger(world).verify().ok
    _, u2 = create_user(world, cred_id, secret, user_name="carol")
    assert ext_id(u2) != identity_id
    # Erasure refuses a live identity.
    _, u3 = create_user(world, cred_id, secret, user_name="erin")
    with pytest.raises(ConfigurationError):
        world.service.erase_directory_pii(world.admin_session,
                                          identity_id=ext_id(u3))


# -- Lifecycle admin API (T524) -------------------------------------------------------


def test_lifecycle_admin_api(world):
    ident = world.service.admin_create_identity(
        world.admin_session, tenant_id=world.tenant_id,
        issuer=ISSUER_A, subject="newbie", display_name="New Bie")
    assert ident.active and ident.created_via == "admin"
    assert world.service.roles_of(ident.identity_id, world.tenant_id) == set()
    created = [e for e in events(world, IDENTITY_CREATED)
               if e["payload"].get("identity_id") == ident.identity_id]
    assert created and created[0]["payload"]["via"] == "admin-api"
    with pytest.raises(ConfigurationError):
        world.service.admin_create_identity(
            world.admin_session, tenant_id=world.tenant_id,
            issuer=ISSUER_A, subject="newbie")
    alice_session, _ = login_user(world, "alice", role=authz.RESEARCHER)
    with pytest.raises(AuthorizationDenied):
        world.service.admin_create_identity(
            alice_session, tenant_id=world.tenant_id,
            issuer=ISSUER_A, subject="mallory2")
    # Deactivate / reactivate through the admin API.
    world.service.deactivate_identity(world.admin_session,
                                      identity_id=ident.identity_id)
    assert world.service.directory.identity(ident.identity_id).active is False
    world.service.reactivate_identity(world.admin_session,
                                      identity_id=ident.identity_id)
    assert world.service.directory.identity(ident.identity_id).active is True
    assert events(world, IDENTITY_REACTIVATED)
    with pytest.raises(ConfigurationError):
        world.service.reactivate_identity(world.admin_session,
                                          identity_id=ident.identity_id)


# -- Audit completeness for the E3 surface (CLM-005-14, E3 half) ---------------------


def test_e3_surface_events_and_chain_verification(world, scim):
    cred_id, secret = scim
    _, u1 = create_user(world, cred_id, secret, user_name="carol")
    _, g = create_group(world, cred_id, secret, members=[ext_id(u1)])
    mapping = world.service.approve_group_mapping(
        world.admin_session, tenant_id=world.tenant_id,
        group_ref=g["id"], role=authz.RESEARCHER)
    world.service.scim_patch_user(
        world.tenant_id, cred_id, secret, u1["id"],
        {"Operations": [{"op": "replace", "path": "displayName",
                         "value": "Carol C."}]})
    with pytest.raises(ScimAuthenticationError):
        world.service.scim_get_user(world.tenant_id, cred_id, "bad", u1["id"])
    world.service.scim_delete_user(world.tenant_id, cred_id, secret, u1["id"])
    world.service.revoke_group_mapping(
        world.admin_session, tenant_id=world.tenant_id,
        mapping_id=mapping.mapping_id)
    world.service.revoke_scim_token(world.admin_session,
                                    tenant_id=world.tenant_id,
                                    credential_id=cred_id)
    types = set(ledger(world).event_types())
    for expected in (SCIM_TOKEN_ISSUED, SCIM_TOKEN_REVOKED, SCIM_SYNC_SUCCEEDED,
                     SCIM_SYNC_FAILED, IDENTITY_CREATED, IDENTITY_UPDATED,
                     IDENTITY_DEACTIVATED, GROUP_MEMBERSHIP_GRANTED,
                     GROUP_MEMBERSHIP_REVOKED, GROUP_MAPPING_APPROVED,
                     GROUP_MAPPING_REVOKED, ROLE_GRANTED, ROLE_REVOKED):
        assert expected in types, f"missing audit event type: {expected}"
    assert ledger(world).verify().ok
    assert world.service.deployment_ledger.verify().ok


def test_scim_secret_never_appears_in_ledgers_or_resources(world, scim):
    cred_id, secret = scim
    _, u1 = create_user(world, cred_id, secret)
    create_group(world, cred_id, secret, members=[ext_id(u1)])
    blob = json.dumps(ledger(world).events()) + json.dumps(
        world.service.deployment_ledger.events())
    assert secret not in blob
    _, users = world.service.scim_list_users(world.tenant_id, cred_id, secret)
    _, groups = world.service.scim_list_groups(world.tenant_id, cred_id, secret)
    assert secret not in json.dumps(users) + json.dumps(groups)
    record = world.service.scim.tenant(world.tenant_id).credentials[cred_id]
    assert record.secret_hash not in blob
