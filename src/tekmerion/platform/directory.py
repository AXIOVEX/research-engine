"""Identity directory — the platform's *mutable, off-ledger* state
(Spec 005 §4). Names, emails, session records, IdP configuration, and
API-key hashes live here under ordinary data controls; ledgers carry
only random actor IDs and key fingerprints, so erasing a directory
record under a legal duty never pressures a chain (DN-005 discipline).

E1 provides the in-memory directory. Persistence and the SCIM-driven
lifecycle (E3) build on these same records; nothing here is a record
of truth — the ledgers are.
"""

from __future__ import annotations

import hashlib
import secrets as _secrets
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .errors import ConfigurationError

CUSTODY_SELF = "self"
CUSTODY_DELEGATED = "delegated"
CUSTODY_MODES = (CUSTODY_SELF, CUSTODY_DELEGATED)

API_KEY_MAX_LIFETIME_SECONDS = 365 * 24 * 3600  # §9: expiry ≤ 1 year


@dataclass
class TenantPolicy:
    """Per-tenant security policy (recorded as platform-ledger events
    when set; the directory holds the current projection)."""
    allowed_custody: tuple[str, ...] = (CUSTODY_SELF, CUSTODY_DELEGATED)
    require_mfa: bool = True                # §13.5: MFA at the IdP, platform-enforced
    stepup_freshness_seconds: float = 600   # verdict/admin step-up must be this fresh
    session_idle_seconds: float = 1800      # §9 default 30 min
    session_absolute_seconds: float = 43200  # §9 default 12 h


@dataclass
class Tenant:
    tenant_id: str
    name: str
    shape: str = "hosted"                    # "hosted" | "self-hosted" (DN-003/DN-011)
    region: Optional[str] = None             # residency pin (§6)
    active: bool = True
    policy: TenantPolicy = field(default_factory=TenantPolicy)


@dataclass
class IdPConfig:
    """Per-tenant OIDC IdP configuration (T502). The client secret is
    NEVER in this record — only a reference into the secrets store."""
    tenant_id: str
    issuer: str
    client_id: str
    client_secret_ref: str
    redirect_uri: str
    attribute_map: dict = field(default_factory=lambda: {
        "display_name": "name", "email": "email", "affiliation": "affiliation",
    })
    required_amr: tuple[str, ...] = ("mfa",)  # §13.5: assertion must evidence MFA


@dataclass
class SamlIdPConfig:
    """Per-tenant SAML 2.0 IdP configuration (E2, T513). Built from
    imported IdP metadata. The signing certificates themselves live
    in the secrets store under `signing_cert_refs` (T502 discipline:
    references in config, material in the store); their SHA-256
    fingerprints are safe to record anywhere, including ledgers."""
    tenant_id: str
    idp_entity_id: str
    sp_entity_id: str                        # this tenant's SP entity ID
    acs_url: str                             # this tenant's assertion consumer URL
    sso_redirect_url: Optional[str] = None
    sso_post_url: Optional[str] = None
    signing_cert_refs: tuple[str, ...] = ()
    signing_cert_fingerprints: tuple[str, ...] = ()
    attribute_map: dict = field(default_factory=lambda: {
        "display_name": "displayName", "email": "mail",
        "affiliation": "eduPersonScopedAffiliation",
    })
    subject_source: str = "nameid"           # "nameid" | "eppn"
    allow_idp_initiated: bool = True


@dataclass
class Identity:
    """An internal identity: (tenant, issuer, subject) + mapped
    attributes (§2). Downstream of the protocol boundary, nothing
    speaks of OIDC or SAML — only of identities."""
    identity_id: str
    tenant_id: str
    issuer: str
    subject: str
    actor_id: str                            # stable random ID used in ledger payloads
    display_name: str = ""
    email: str = ""
    affiliation: str = ""
    active: bool = True
    created_via: str = "oidc"                # "oidc" | "saml" | "admin" | "bootstrap"


@dataclass
class Session:
    """Server-side session record (§9). The token is the bearer; the
    record is what the gate actually consults."""
    session_id: str                          # opaque token
    identity_id: str
    tenant_id: str
    created_at: float
    last_seen_at: float
    auth_time: float
    amr: tuple[str, ...] = ()
    acr: str = ""
    mfa: bool = False
    stepped_up_at: Optional[float] = None
    revoked: bool = False

    def has_fresh_stepup(self, policy: TenantPolicy, now: float) -> bool:
        return (
            self.stepped_up_at is not None
            and (now - self.stepped_up_at) <= policy.stepup_freshness_seconds
        )


@dataclass
class ApiKeyRecord:
    """A scoped API key (T511). Only the SHA-256 of the secret is
    stored; the plaintext is shown once at issuance."""
    key_id: str                              # public prefix, e.g. "tk_9f3ac2"
    tenant_id: str
    principal_identity_id: str               # the service identity it acts as
    role_class: str                          # the WS6 role its scopes are bounded by
    scopes: frozenset
    secret_hash: str
    created_at: float
    expires_at: float
    created_by_actor_id: str
    revoked: bool = False
    last_used_at: Optional[float] = None


class InMemorySecrets:
    """Development secrets store: a dict. Production shapes put IdP
    client secrets behind KMS-envelope or an institution KMS (§9);
    the interface — put/get by reference — is what the platform uses,
    so the store can be swapped without touching callers. Values are
    never written to config payloads or ledgers (T502)."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def put(self, ref: str, value: str) -> str:
        self._values[ref] = value
        return ref

    def get(self, ref: str) -> str:
        if ref not in self._values:
            raise ConfigurationError(f"secret reference not found: {ref}")
        return self._values[ref]


def hash_api_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


class Directory:
    """All off-ledger platform state, in one place so its boundary
    with the ledgers stays auditable."""

    def __init__(self) -> None:
        self.tenants: dict[str, Tenant] = {}
        self.idps: dict[tuple[str, str], IdPConfig] = {}       # (tenant_id, issuer)
        self.saml_idps: dict[tuple[str, str], SamlIdPConfig] = {}  # (tenant_id, IdP entity ID)
        self.identities: dict[str, Identity] = {}              # identity_id
        self._identity_by_triple: dict[tuple[str, str, str], str] = {}
        self.sessions: dict[str, Session] = {}
        self.api_keys: dict[str, ApiKeyRecord] = {}            # key_id
        self._saml_consumed: dict[str, float] = {}             # assertion/response ID -> expiry

    # -- tenants / IdPs ---------------------------------------------------

    def add_tenant(self, tenant: Tenant) -> Tenant:
        self.tenants[tenant.tenant_id] = tenant
        return tenant

    def tenant(self, tenant_id: str) -> Tenant:
        t = self.tenants.get(tenant_id)
        if t is None:
            raise ConfigurationError(f"unknown tenant: {tenant_id}")
        return t

    def add_idp(self, config: IdPConfig) -> IdPConfig:
        self.idps[(config.tenant_id, config.issuer)] = config
        return config

    def idp(self, tenant_id: str, issuer: str) -> IdPConfig:
        c = self.idps.get((tenant_id, issuer))
        if c is None:
            raise ConfigurationError(f"no IdP configured for tenant {tenant_id} issuer {issuer}")
        return c

    def idps_for_tenant(self, tenant_id: str) -> list[IdPConfig]:
        return [c for (t, _), c in self.idps.items() if t == tenant_id]

    # -- SAML IdPs -----------------------------------------------------------

    def add_saml_idp(self, config: SamlIdPConfig) -> SamlIdPConfig:
        self.saml_idps[(config.tenant_id, config.idp_entity_id)] = config
        return config

    def saml_idp(self, tenant_id: str, idp_entity_id: str) -> SamlIdPConfig:
        c = self.saml_idps.get((tenant_id, idp_entity_id))
        if c is None:
            raise ConfigurationError(
                f"no SAML IdP configured for tenant {tenant_id} entity {idp_entity_id}")
        return c

    def consume_saml_id(self, message_id: str, expires_at: float, now: float) -> bool:
        """Replay register (E2): returns True the first time an ID is
        presented, False on any re-presentation before its expiry.
        IDs are held until the assertion's own expiry (+skew handled
        by the caller folding it into `expires_at`)."""
        stale = [k for k, exp in self._saml_consumed.items() if exp <= now]
        for k in stale:
            del self._saml_consumed[k]
        if message_id in self._saml_consumed:
            return False
        self._saml_consumed[message_id] = expires_at
        return True

    # -- identities ---------------------------------------------------------

    def get_or_create_identity(self, tenant_id: str, issuer: str, subject: str,
                               *, created_via: str = "oidc", **attrs) -> tuple[Identity, bool]:
        key = (tenant_id, issuer, subject)
        existing = self._identity_by_triple.get(key)
        if existing is not None:
            ident = self.identities[existing]
            for k, v in attrs.items():
                if v:
                    setattr(ident, k, v)
            return ident, False
        ident = Identity(
            identity_id=uuid.uuid4().hex,
            tenant_id=tenant_id, issuer=issuer, subject=subject,
            actor_id=uuid.uuid4().hex, created_via=created_via, **attrs,
        )
        self.identities[ident.identity_id] = ident
        self._identity_by_triple[key] = ident.identity_id
        return ident, True

    def identity(self, identity_id: str) -> Identity:
        ident = self.identities.get(identity_id)
        if ident is None:
            raise ConfigurationError(f"unknown identity: {identity_id}")
        return ident

    def find_identity(self, tenant_id: str, issuer: str, subject: str) -> Optional[Identity]:
        iid = self._identity_by_triple.get((tenant_id, issuer, subject))
        return self.identities.get(iid) if iid else None

    def change_subject(self, identity: Identity, new_subject: str) -> None:
        """Rebind an identity to a new subject under the same issuer
        (a SCIM userName rename, E3). The (tenant, issuer, subject)
        triple is the login lookup; the identity — and its actor ID —
        is unchanged, so the ledger's attribution is untouched."""
        old_key = (identity.tenant_id, identity.issuer, identity.subject)
        new_key = (identity.tenant_id, identity.issuer, new_subject)
        holder = self._identity_by_triple.get(new_key)
        if holder is not None and holder != identity.identity_id:
            raise ConfigurationError(
                "subject already bound to another identity in this tenant")
        self._identity_by_triple.pop(old_key, None)
        self._identity_by_triple[new_key] = identity.identity_id
        identity.subject = new_subject

    def erase_identity_pii(self, identity_id: str) -> bool:
        """Off-ledger directory erasure under a legal duty (T523).
        Blanks the directory's PII for the identity and drops the
        (tenant, issuer, subject) lookup, so the same person arriving
        later is a NEW identity with a NEW actor ID — identifiers are
        never reused (matrix 3.5.5). The actor ID itself is random,
        not PII, and stays: chain attribution remains verifiable
        through the enrollment record (§4), while the directory
        forgets who it was. Nothing here can reach a ledger."""
        ident = self.identities.get(identity_id)
        if ident is None:
            return False
        ident.display_name = ""
        ident.email = ""
        ident.affiliation = ""
        self._identity_by_triple.pop(
            (ident.tenant_id, ident.issuer, ident.subject), None)
        ident.subject = ""
        return True

    # -- sessions -------------------------------------------------------------

    def new_session(self, identity: Identity, *, amr: tuple[str, ...] = (), acr: str = "",
                    mfa: bool = False, now: Optional[float] = None) -> Session:
        ts = now if now is not None else time.time()
        s = Session(
            session_id=_secrets.token_urlsafe(32),
            identity_id=identity.identity_id, tenant_id=identity.tenant_id,
            created_at=ts, last_seen_at=ts, auth_time=ts,
            amr=tuple(amr), acr=acr, mfa=mfa,
        )
        self.sessions[s.session_id] = s
        return s

    def session(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)

    def revoke_sessions_for(self, identity_id: str) -> int:
        n = 0
        for s in self.sessions.values():
            if s.identity_id == identity_id and not s.revoked:
                s.revoked = True
                n += 1
        return n

    # -- API keys ---------------------------------------------------------------

    def add_api_key(self, record: ApiKeyRecord) -> ApiKeyRecord:
        if record.expires_at - record.created_at > API_KEY_MAX_LIFETIME_SECONDS:
            raise ConfigurationError("API key lifetime exceeds 1 year (§9)")
        if record.expires_at <= record.created_at:
            raise ConfigurationError("API key must expire in the future at issuance")
        self.api_keys[record.key_id] = record
        return record

    def find_api_key(self, key_id: str, secret: str) -> Optional[ApiKeyRecord]:
        rec = self.api_keys.get(key_id)
        if rec is None:
            return None
        if not _secrets.compare_digest(rec.secret_hash, hash_api_secret(secret)):
            return None
        return rec
