"""SCIM 2.0 provisioning surface (Spec 005 §4, E3, T518/T519).

The platform plane's other doors are browsers and IdPs; this one is
the tenant IdP's provisioning client (Entra ID, Okta, and peers speak
SCIM to *us* — SCIM provisions, IdPs authenticate; CLM-005-06's
boundary). There are no sockets in the platform package: like the
OIDC client behind its transport interface, the SCIM surface is a
service-layer mapping from SCIM operations (method + resource +
document) to platform lifecycle operations, returning
`(status, document)` pairs in RFC 7644 shapes. An HTTP adapter is a
deployment concern that translates to these calls unchanged.

Design rules, all load-bearing:

- **Tenant comes from the URL tenant, credential from the bearer.**
  A credential is issued per tenant by a tenant admin, stored only
  as a SHA-256 hash (the §9 API-key discipline), shown once. A
  credential presented against another tenant's endpoint is refused
  and the attempt is ledgered in the *addressed* tenant's ledger
  before the raise (E1/E2 refusal style).
- **SCIM delete is lifecycle, never record removal** (DN-005,
  Article IV): DELETE deactivates through the same core as SCIM
  `active=false` and tenant-admin deactivation, and drops the SCIM
  *directory record* (off-ledger state, like the identity directory)
  — the identity, its ledger history, and its attributions are
  untouched. The identity's stable key in SCIM membership payloads
  is its platform `identity_id`; the SCIM `id` is the provisioning
  record's own ID and is never reused.
- **A SCIM-provisioned identity is not an authenticated principal.**
  SCIM creates the identity in the provisioning namespace
  `(tenant, "scim", userName)` with no roles. Login identities are
  created by IdP assertions under the IdP's issuer (E1/E2 JIT); a
  person known to both doors holds two identities until an
  account-linking rule is specced — the E2 dual-door fact, unchanged.
- **Groups grant nothing by themselves.** A group membership becomes
  a study-role grant only through a tenant-admin-approved mapping
  record (T519), applied as `role.granted` / `role.revoked` events
  by the platform (`actor_id="system"`, `via="scim-group-mapping"`,
  naming the mapping) — replayable, revocable, and never silent.
- Every SCIM success and every attributable SCIM failure lands in
  the tenant's platform audit ledger as a `scim.sync_*` event
  (CLM-005-14's SCIM half); every failure is recorded *before* the
  raise, and a failed operation leaves directory state unchanged.

Compatibility posture (honesty): shapes follow RFC 7643/7644 and the
documented expectations of Entra ID / Okta provisioning clients
(PATCH-heavy updates, `emails[type eq "work"].value` paths, list
filters of the `attr op "value"` family). No live SCIM client has
been exercised against this surface — fixtures only.
"""

from __future__ import annotations

import re
import secrets as _secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .directory import Identity
from .errors import PlatformError

CORE_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
CORE_GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"
LIST_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"
PATCH_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
#: Platform extension block on User resources: the provisioning↔identity
#: link, explicit on the wire (random IDs only — never PII, §4).
IDENTITY_EXTENSION = "urn:tekmerion:params:scim:identity"

#: The provisioning namespace: SCIM-created identities live under
#: (tenant, SCIM_ISSUER, userName). See the module docstring.
SCIM_ISSUER = "scim"


# -- errors -------------------------------------------------------------------


class ScimError(PlatformError):
    """A SCIM refusal in RFC 7644 §3.12 error shape. The service
    records attributable failures in the tenant's audit ledger before
    this is raised, exactly as the gate records append refusals."""

    status = 400
    scim_type: Optional[str] = None

    def __init__(self, detail: str, *, scim_type: Optional[str] = None) -> None:
        super().__init__(detail)
        self.detail = detail
        if scim_type is not None:
            self.scim_type = scim_type

    def error_doc(self) -> dict:
        doc = {"schemas": [ERROR_SCHEMA], "detail": self.detail,
               "status": str(self.status)}
        if self.scim_type:
            doc["scimType"] = self.scim_type
        return doc


class ScimBadRequestError(ScimError):
    status = 400


class ScimAuthenticationError(ScimError):
    status = 401


class ScimForbiddenError(ScimError):
    status = 403


class ScimNotFoundError(ScimError):
    status = 404


class ScimUniquenessError(ScimError):
    status = 409
    scim_type = "uniqueness"


# -- records (off-ledger, like the identity directory) --------------------------


@dataclass
class ScimCredential:
    """A per-tenant SCIM bearer credential (T518). Only the SHA-256
    hash of the secret is stored; the plaintext is shown once at
    issuance, as with API keys (§9). Credential IDs are safe to
    record anywhere, including ledgers."""
    credential_id: str                       # public prefix, e.g. "scim_9f3ac2"
    tenant_id: str
    secret_hash: str
    created_by_actor_id: str
    created_at: float
    revoked: bool = False


@dataclass
class ProvisionedUser:
    """The SCIM directory record for one provisioned user. `scim_id`
    is this record's own ID (never reused, even after DELETE); the
    identity it provisions is `identity_id`."""
    scim_id: str
    identity_id: str
    user_name: str
    external_id: Optional[str] = None
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class ScimGroup:
    scim_id: str
    display_name: str
    external_id: Optional[str] = None
    member_identity_ids: set = field(default_factory=set)
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class GroupRoleMapping:
    """A tenant-admin-approved group→role mapping record (T519).
    The approval is a platform-ledger event; this record is its
    projection. `group_ref` names the group by SCIM id, externalId,
    or displayName — whichever the admin approved — so a mapping may
    be approved before the group is first provisioned."""
    mapping_id: str
    tenant_id: str
    group_ref: str
    role: str
    approved_by_actor_id: str
    active: bool = True


@dataclass
class TenantScimState:
    users: dict = field(default_factory=dict)            # scim_id -> ProvisionedUser
    users_by_identity: dict = field(default_factory=dict)  # identity_id -> scim_id
    groups: dict = field(default_factory=dict)           # scim_id -> ScimGroup
    credentials: dict = field(default_factory=dict)      # credential_id -> ScimCredential
    mappings: dict = field(default_factory=dict)         # mapping_id -> GroupRoleMapping


class ScimDirectory:
    """All off-ledger SCIM state, per tenant, next to the identity
    directory in spirit: provisioning records are operational state;
    the ledgers carry the lifecycle truth."""

    def __init__(self) -> None:
        self._tenants: dict[str, TenantScimState] = {}

    def tenant(self, tenant_id: str) -> TenantScimState:
        return self._tenants.setdefault(tenant_id, TenantScimState())

    def peek(self, tenant_id: str) -> Optional[TenantScimState]:
        return self._tenants.get(tenant_id)

    # -- credentials -----------------------------------------------------

    def add_credential(self, cred: ScimCredential) -> ScimCredential:
        self.tenant(cred.tenant_id).credentials[cred.credential_id] = cred
        return cred

    def find_credential(self, credential_id: str) -> Optional[tuple[str, ScimCredential]]:
        """Global lookup by credential ID: (owning tenant, record).
        Tenant scoping is enforced by the caller comparing the owner
        to the addressed tenant — a mismatch is the cross-tenant
        refusal, and it must be distinguishable from an unknown ID."""
        for tenant_id, state in self._tenants.items():
            cred = state.credentials.get(credential_id)
            if cred is not None:
                return tenant_id, cred
        return None

    # -- users -------------------------------------------------------------

    def user_by_external_id(self, tenant_id: str, external_id: str) -> Optional[ProvisionedUser]:
        for u in self.tenant(tenant_id).users.values():
            if u.external_id == external_id:
                return u
        return None

    def user_by_user_name(self, tenant_id: str, user_name: str) -> Optional[ProvisionedUser]:
        folded = user_name.casefold()
        for u in self.tenant(tenant_id).users.values():
            if u.user_name.casefold() == folded:
                return u
        return None

    def add_user(self, tenant_id: str, user: ProvisionedUser) -> ProvisionedUser:
        state = self.tenant(tenant_id)
        state.users[user.scim_id] = user
        state.users_by_identity[user.identity_id] = user.scim_id
        return user

    def remove_user(self, tenant_id: str, user: ProvisionedUser) -> None:
        state = self.tenant(tenant_id)
        state.users.pop(user.scim_id, None)
        state.users_by_identity.pop(user.identity_id, None)
        for g in state.groups.values():
            g.member_identity_ids.discard(user.identity_id)

    def forget_identity(self, tenant_id: str, identity_id: str) -> None:
        """Drop every SCIM directory trace of an identity (T523
        erasure path): the provisioning record and group memberships.
        Off-ledger state only — no chain is reachable from here."""
        state = self.peek(tenant_id)
        if state is None:
            return
        scim_id = state.users_by_identity.pop(identity_id, None)
        if scim_id is not None:
            state.users.pop(scim_id, None)
        for g in state.groups.values():
            g.member_identity_ids.discard(identity_id)

    # -- groups --------------------------------------------------------------

    def group_by_ref(self, tenant_id: str, ref: str) -> Optional[ScimGroup]:
        state = self.tenant(tenant_id)
        if ref in state.groups:
            return state.groups[ref]
        for g in state.groups.values():
            if g.external_id == ref or g.display_name == ref:
                return g
        return None

    def add_group(self, tenant_id: str, group: ScimGroup) -> ScimGroup:
        self.tenant(tenant_id).groups[group.scim_id] = group
        return group

    def remove_group(self, tenant_id: str, group: ScimGroup) -> None:
        self.tenant(tenant_id).groups.pop(group.scim_id, None)

    # -- mappings --------------------------------------------------------------

    def add_mapping(self, mapping: GroupRoleMapping) -> GroupRoleMapping:
        self.tenant(mapping.tenant_id).mappings[mapping.mapping_id] = mapping
        return mapping

    def mapping_for(self, tenant_id: str, group: ScimGroup,
                    role: Optional[str] = None) -> list[GroupRoleMapping]:
        """Active mappings naming this group (by id, externalId, or
        displayName) — optionally for one role."""
        refs = {group.scim_id, group.display_name}
        if group.external_id:
            refs.add(group.external_id)
        out = []
        for m in self.tenant(tenant_id).mappings.values():
            if m.active and m.group_ref in refs and (role is None or m.role == role):
                out.append(m)
        return out


def new_scim_id() -> str:
    return uuid.uuid4().hex


def new_prefixed_id(prefix: str) -> str:
    return prefix + _secrets.token_hex(4)


# -- document helpers -----------------------------------------------------------


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def primary_email(doc: dict) -> Optional[str]:
    """The primary (or first) email value of a SCIM user document —
    the Entra/Okta `emails[type eq "work"].value` shape included."""
    emails = doc.get("emails")
    if isinstance(emails, str):
        return emails
    if isinstance(emails, dict):
        return emails.get("value")
    if isinstance(emails, list):
        fallback = None
        for entry in emails:
            if isinstance(entry, str):
                fallback = fallback or entry
            elif isinstance(entry, dict) and entry.get("value"):
                if entry.get("primary"):
                    return entry["value"]
                fallback = fallback or entry["value"]
        return fallback
    return None


def display_name_of(doc: dict) -> str:
    if doc.get("displayName"):
        return str(doc["displayName"])
    name = doc.get("name") or {}
    if isinstance(name, dict):
        if name.get("formatted"):
            return str(name["formatted"])
        parts = [name.get("givenName", ""), name.get("familyName", "")]
        return " ".join(p for p in parts if p).strip()
    return ""


def user_resource(state: TenantScimState, user: ProvisionedUser,
                  identity: Identity) -> dict:
    """Render a User resource (RFC 7643 §4.1) from the records. The
    `active` flag is the identity's lifecycle state — the record of
    truth — not a copy kept in the SCIM directory."""
    doc: dict = {
        "schemas": [CORE_USER_SCHEMA],
        "id": user.scim_id,
        "userName": user.user_name,
        "displayName": identity.display_name,
        "name": {"formatted": identity.display_name},
        "active": identity.active,
        "groups": [
            {"value": g.scim_id, "display": g.display_name,
             "$ref": f"../Groups/{g.scim_id}"}
            for g in sorted(state.groups.values(), key=lambda g: g.scim_id)
            if user.identity_id in g.member_identity_ids
        ],
        "meta": {
            "resourceType": "User",
            "created": _iso(user.created_at),
            "lastModified": _iso(user.updated_at),
            "location": f"Users/{user.scim_id}",
        },
        IDENTITY_EXTENSION: {
            "identity_id": user.identity_id,
            "actor_id": identity.actor_id,
            "issuer": identity.issuer,
        },
    }
    if user.external_id:
        doc["externalId"] = user.external_id
    if identity.email:
        doc["emails"] = [{"value": identity.email, "primary": True, "type": "work"}]
    return doc


def group_resource(state: TenantScimState, group: ScimGroup,
                   identities: dict) -> dict:
    """Render a Group resource (RFC 7643 §4.2). Member `value`s are
    platform identity IDs — the stable key across the SCIM record's
    own lifetime (see the module docstring)."""
    members = []
    for iid in sorted(group.member_identity_ids):
        entry = {"value": iid}
        ident = identities.get(iid)
        if ident is not None:
            entry["display"] = ident.display_name
        scim_id = state.users_by_identity.get(iid)
        if scim_id is not None:
            entry["$ref"] = f"../Users/{scim_id}"
        members.append(entry)
    doc: dict = {
        "schemas": [CORE_GROUP_SCHEMA],
        "id": group.scim_id,
        "displayName": group.display_name,
        "members": members,
        "meta": {
            "resourceType": "Group",
            "created": _iso(group.created_at),
            "lastModified": _iso(group.updated_at),
            "location": f"Groups/{group.scim_id}",
        },
    }
    if group.external_id:
        doc["externalId"] = group.external_id
    return doc


def list_response(resources: list, *, total: int, start_index: int) -> dict:
    return {
        "schemas": [LIST_SCHEMA],
        "totalResults": total,
        "startIndex": start_index,
        "itemsPerPage": len(resources),
        "Resources": resources,
    }


# -- filters (RFC 7644 §3.4.2.2, the comparison family) -------------------------

_FILTER_RE = re.compile(
    r'^\s*([A-Za-z][A-Za-z0-9_.]*)\s+(eq|ne|co|pr)(?:\s+(?:"([^"]*)"|(\S+)))?\s*$',
    re.IGNORECASE)


def parse_filter(expression: str) -> tuple[str, str, Optional[str]]:
    """Parse `attr op "value"` / `attr pr`. Anything richer (value
    filters, boolean logic) is refused as a bad request rather than
    silently mis-served — an honest subset, named in the refusal."""
    m = _FILTER_RE.match(expression or "")
    if not m:
        raise ScimBadRequestError(
            f"unsupported filter: {expression!r} (comparison filters only)",
            scim_type="invalidFilter")
    attr, op = m.group(1), m.group(2).lower()
    value = m.group(3) if m.group(3) is not None else m.group(4)
    if op != "pr" and value is None:
        raise ScimBadRequestError(
            f"filter operator {op} requires a value", scim_type="invalidFilter")
    return attr, op, value


def _field(doc: dict, attr: str):
    if attr == "id":
        return doc.get("id")
    if attr == "userName":
        return doc.get("userName")
    if attr == "displayName":
        return doc.get("displayName")
    if attr == "externalId":
        return doc.get("externalId")
    if attr == "active":
        return doc.get("active")
    return None


def matches_filter(doc: dict, parsed: tuple[str, str, Optional[str]]) -> bool:
    attr, op, value = parsed
    actual = _field(doc, attr)
    if op == "pr":
        return actual is not None and actual != "" and actual is not False
    if actual is None:
        return op == "ne"
    if isinstance(actual, bool):
        wanted = str(value).lower() == "true"
        return (actual == wanted) if op == "eq" else (actual != wanted)
    actual_s, value_s = str(actual).casefold(), str(value).casefold()
    if op == "eq":
        return actual_s == value_s
    if op == "ne":
        return actual_s != value_s
    if op == "co":
        return value_s in actual_s
    return False


def paginate(items: list, *, start_index: int = 1,
             count: Optional[int] = None) -> tuple[list, int]:
    """RFC 7644 §3.4.2.4: 1-based startIndex; returns (page, start)."""
    start = max(1, start_index)
    sliced = items[start - 1:]
    if count is not None:
        sliced = sliced[:max(0, count)]
    return sliced, start
