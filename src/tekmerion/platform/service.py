"""PlatformService (Spec 005 E1) — the facade every E1 surface calls.

Responsibilities: tenant and IdP administration, the OIDC login
lifecycle, role grants, key enrollment/lifecycle (via the registry),
identity deactivation, API keys, and the authorization core for study
appends (consumed by `gate.GatedStudyWriter`).

Recording discipline (§5, §8, §13.4): every mutation and every
authentication outcome lands in a platform audit ledger — tenant-scope
events in the tenant's ledger, platform-plane events in the
deployment ledger. Denials of attributable attempts are recorded
*before* the refusal is raised. Platform-plane *actions* are
session+role authorized and ledgered; *study appends* additionally
require an enrolled-key signature (the gate, T507) — that split is
§3's: enrollment governs whose signature the record believes.

Time is injectable (`now=`) so expiry behavior is testable without
sleeping.
"""

from __future__ import annotations

import base64
import secrets as _secrets
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Optional

from . import authz, ed25519
from .authz import AuthorizationService
from .directory import (
    ApiKeyRecord, Directory, IdPConfig, Identity, InMemorySecrets,
    SamlIdPConfig, Session, Tenant, hash_api_secret,
)
from .errors import AuthenticationError, AuthorizationDenied, ConfigurationError, GateDenied
from .keys import DelegatedSigner, KeyRecord, KeyRegistry, fingerprint
from .ledger import (
    APIKEY_ISSUED, APIKEY_REVOKED, AUTH_APIKEY_FAILED, AUTH_LOGIN_FAILED,
    AUTH_LOGIN_SUCCEEDED, AUTH_LOGOUT, AUTH_STEPUP, AUTHZ_DENIED,
    IDENTITY_CREATED, IDENTITY_DEACTIVATED, IDENTITY_UPDATED, IDP_CONFIGURED,
    IDP_UPDATED, PLATFORM_BOOTSTRAPPED, ROLE_GRANTED, ROLE_REVOKED,
    SESSION_REVOKED, TENANT_CREATED, TENANT_UPDATED, PlatformLedger,
)
from .oidc import OIDCClient, pkce_pair
from .saml import (
    CLOCK_SKEW_SECONDS, SamlAssertion, SamlIdPSettings, build_authn_request,
    new_request_id, parse_metadata, redirect_binding_url, validate_response,
)
from .x509 import parse_certificate

#: Step-up requests ask the IdP for the REFEDS MFA profile context;
#: an IdP that cannot evidence MFA cannot step a session up (§2).
STEPUP_MFA_CONTEXT_REF = "https://refeds.org/profile/mfa"

PLATFORM_TENANT_ID = "__platform__"
SYSTEM_ACTOR = "system"


@dataclass
class AppendAuthorization:
    """What the gate established about an append, for the writer to
    embed as attribution: the record shows who acted, under which
    role, with which key, in which custody mode — never PII (§4)."""
    identity: Identity
    role_basis: str
    key_fingerprint: Optional[str]
    custody: Optional[str]           # "self" | "delegated" | "api_key"
    session_id: Optional[str]
    signature_hex: Optional[str] = None
    api_key_id: Optional[str] = None

    def attribution(self) -> dict:
        return {
            "actor_id": self.identity.actor_id,
            "role_basis": self.role_basis,
            "key_fingerprint": self.key_fingerprint,
            "custody": self.custody,
            "session_id": self.session_id,
            "intent_signature": self.signature_hex,
            "api_key_id": self.api_key_id,
        }


class PlatformService:
    def __init__(self, root: str | Path, *, now: Callable[[], float] = time.time,
                 oidc_client: Optional[OIDCClient] = None,
                 deployment_seed_hex: Optional[str] = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._now = now
        self.directory = Directory()
        self.secrets = InMemorySecrets()
        self.authz = AuthorizationService()
        self.oidc = oidc_client or OIDCClient(now=now)
        self.delegated_signer = DelegatedSigner()
        deployment_path = self.root / "deployment.axmr"
        if deployment_path.exists():
            self.deployment_ledger = PlatformLedger.open(str(deployment_path), scope="deployment")
        else:
            self.deployment_ledger = PlatformLedger.create(
                str(deployment_path), scope="deployment", seed_hex=deployment_seed_hex)
        self._tenant_ledgers: dict[str, PlatformLedger] = {}
        self._registries: dict[str, KeyRegistry] = {}
        self._pending_auth: dict[str, dict] = {}
        self._ensure_platform_tenant()

    # -- internal plumbing -------------------------------------------------

    def _ensure_platform_tenant(self) -> None:
        if PLATFORM_TENANT_ID not in self.directory.tenants:
            self.directory.add_tenant(Tenant(
                tenant_id=PLATFORM_TENANT_ID, name="Platform", shape="platform"))

    def _tenant_ledger(self, tenant_id: str) -> PlatformLedger:
        if tenant_id not in self._tenant_ledgers:
            path = self.root / f"tenant-{tenant_id}.axmr"
            if path.exists():
                led = PlatformLedger.open(str(path), scope="tenant", tenant_id=tenant_id)
            else:
                led = PlatformLedger.create(str(path), scope="tenant", tenant_id=tenant_id)
            self._tenant_ledgers[tenant_id] = led
        return self._tenant_ledgers[tenant_id]

    def registry(self, tenant_id: str) -> KeyRegistry:
        if tenant_id not in self._registries:
            self._registries[tenant_id] = KeyRegistry(
                self._tenant_ledger(tenant_id), now=self._now)
        return self._registries[tenant_id]

    def _ledger_for_scope(self, tenant_id: Optional[str]) -> PlatformLedger:
        return self.deployment_ledger if tenant_id is None else self._tenant_ledger(tenant_id)

    def _auth_ledger(self, tenant_id: str) -> PlatformLedger:
        """Authentication/identity events for platform-plane identities
        belong to the deployment ledger (§8); tenant identities' events
        belong to their tenant ledger."""
        return self.deployment_ledger if tenant_id == PLATFORM_TENANT_ID else self._tenant_ledger(tenant_id)

    # -- roles (projection over grant events) --------------------------------

    def roles_of(self, identity_id: str, tenant_id: Optional[str] = None) -> set[str]:
        """Effective roles: replay role.granted / role.revoked in order.
        With tenant_id=None, only platform-plane grants are considered;
        with a tenant, that tenant's grants. Callers union as needed."""
        roles: set[str] = set()
        ledgers = [self.deployment_ledger] if tenant_id is None else [self._tenant_ledger(tenant_id)]
        for led in ledgers:
            for ev in led.events():
                p = ev["payload"]
                if p.get("identity_id") != identity_id:
                    continue
                if ev["type"] == ROLE_GRANTED:
                    roles.add(p["role"])
                elif ev["type"] == ROLE_REVOKED:
                    roles.discard(p["role"])
        return roles

    def all_roles_of(self, identity: Identity) -> set[str]:
        return (self.roles_of(identity.identity_id, None)
                | self.roles_of(identity.identity_id, identity.tenant_id))

    # -- session resolution ----------------------------------------------------

    def _resolve_session(self, session_token: str) -> tuple[Session, Identity]:
        session = self.directory.session(session_token)
        if session is None or session.revoked:
            raise AuthenticationError("session unknown or revoked")
        identity = self.directory.identity(session.identity_id)
        policy = self.directory.tenant(session.tenant_id).policy
        now = self._now()
        idle_expired = (now - session.last_seen_at) > policy.session_idle_seconds
        absolute_expired = (now - session.created_at) > policy.session_absolute_seconds
        if idle_expired or absolute_expired:
            session.revoked = True
            raise AuthenticationError("session expired")
        if not identity.active:
            raise AuthenticationError("identity is deactivated")
        return session, identity

    def _require(self, session_token: str, action: str, *, tenant_id: Optional[str]) -> tuple[Session, Identity]:
        """Authorize an admin-plane action: session valid, role permits.
        Denials are recorded in the scope's ledger before raising."""
        session, identity = self._resolve_session(session_token)
        roles = (self.roles_of(identity.identity_id, None) if tenant_id is None
                 else self.roles_of(identity.identity_id, tenant_id))
        decision = self.authz.decide(roles, action)
        if not decision.allowed:
            self._ledger_for_scope(tenant_id).record(
                AUTHZ_DENIED, actor_id=identity.actor_id,
                target=f"action:{action}", outcome="denied",
                action=action, reason=decision.reason, at=self._now(),
            )
            raise AuthorizationDenied(decision.reason)
        return session, identity

    # -- bootstrap / tenants -----------------------------------------------------

    def bootstrap_platform_admin(self, *, issuer: str, subject: str,
                                 display_name: str = "") -> Identity:
        """Out-of-band genesis of the first platform admin (deployment
        act, performed by whoever provisions the deployment; recorded
        as such — there is no silent superuser)."""
        ident, created = self.directory.get_or_create_identity(
            PLATFORM_TENANT_ID, issuer, subject, created_via="bootstrap",
            display_name=display_name)
        if created:
            self.deployment_ledger.record(
                IDENTITY_CREATED, actor_id="bootstrap", target=f"identity:{ident.identity_id}",
                identity_id=ident.identity_id, subject_actor_id=ident.actor_id, at=self._now())
        self.deployment_ledger.record(
            PLATFORM_BOOTSTRAPPED, actor_id="bootstrap", target=f"identity:{ident.identity_id}",
            identity_id=ident.identity_id, subject_actor_id=ident.actor_id, at=self._now())
        self.deployment_ledger.record(
            ROLE_GRANTED, actor_id="bootstrap", target=f"identity:{ident.identity_id}",
            identity_id=ident.identity_id, subject_actor_id=ident.actor_id,
            role=authz.PLATFORM_ADMIN, tenant_id=None, at=self._now())
        return ident

    def create_tenant(self, session_token: str, *, tenant_id: str, name: str,
                      shape: str = "hosted", region: Optional[str] = None) -> Tenant:
        _, admin = self._require(session_token, authz.PLATFORM_TENANT_CREATE, tenant_id=None)
        tenant = self.directory.add_tenant(Tenant(
            tenant_id=tenant_id, name=name, shape=shape, region=region))
        self._tenant_ledger(tenant_id)  # create the tenant's audit ledger now
        self.deployment_ledger.record(
            TENANT_CREATED, actor_id=admin.actor_id, target=f"tenant:{tenant_id}",
            tenant_id=tenant_id, name=name, shape=shape, region=region, at=self._now())
        return tenant

    def update_tenant(self, session_token: str, *, tenant_id: str,
                      name: Optional[str] = None, region: Optional[str] = None) -> Tenant:
        _, admin = self._require(session_token, authz.PLATFORM_TENANT_MANAGE, tenant_id=None)
        tenant = self.directory.tenant(tenant_id)
        changed = {}
        if name is not None:
            tenant.name = name
            changed["name"] = name
        if region is not None:
            tenant.region = region
            changed["region"] = region
        self.deployment_ledger.record(
            TENANT_UPDATED, actor_id=admin.actor_id, target=f"tenant:{tenant_id}",
            tenant_id=tenant_id, fields=sorted(changed), at=self._now())
        return tenant

    # -- IdP configuration ---------------------------------------------------------

    def provision_tenant_idp(self, session_token: str, config: IdPConfig, *,
                             client_secret: str) -> IdPConfig:
        """Deployment provisioning of a tenant's FIRST IdP config —
        a platform act (tenant lifecycle), recorded in the tenant's
        ledger. After this, the tenant's own admin manages IdP
        configuration via configure_idp; the planes stay disjoint."""
        _, admin = self._require(session_token, authz.PLATFORM_TENANT_MANAGE, tenant_id=None)
        self.secrets.put(config.client_secret_ref, client_secret)
        self.directory.add_idp(config)
        self._tenant_ledger(config.tenant_id).record(
            IDP_CONFIGURED, actor_id=admin.actor_id, target=f"idp:{config.issuer}",
            issuer=config.issuer, client_id=config.client_id,
            client_secret_ref=config.client_secret_ref,
            required_amr=list(config.required_amr), via="provisioning", at=self._now())
        return config

    def configure_idp(self, session_token: str, config: IdPConfig, *,
                      client_secret: str) -> IdPConfig:
        _, admin = self._require(session_token, authz.TENANT_IDP_MANAGE, tenant_id=config.tenant_id)
        existing = (config.tenant_id, config.issuer) in self.directory.idps
        self.secrets.put(config.client_secret_ref, client_secret)
        self.directory.add_idp(config)
        self._tenant_ledger(config.tenant_id).record(
            IDP_UPDATED if existing else IDP_CONFIGURED,
            actor_id=admin.actor_id, target=f"idp:{config.issuer}",
            issuer=config.issuer, client_id=config.client_id,
            client_secret_ref=config.client_secret_ref,  # reference only — never the value (T502)
            required_amr=list(config.required_amr), at=self._now())
        return config

    # -- SAML IdP configuration (E2, T513) -------------------------------------

    def _register_saml_idp(self, admin: Identity, *, tenant_id: str,
                           sp_entity_id: str, acs_url: str, metadata_xml: str,
                           attribute_map: Optional[dict], subject_source: str,
                           allow_idp_initiated: bool, via: str) -> SamlIdPConfig:
        """Metadata import + validation, shared by provisioning and
        tenant self-service. The imported certificates are stored by
        reference (T502 discipline); the ledger event carries their
        fingerprints, never the material."""
        meta = parse_metadata(metadata_xml, now=self._now())
        if all(c.not_after <= self._now() for c in meta.signing_certs):
            raise ConfigurationError("every signing certificate in the metadata is expired")
        refs: list[str] = []
        fingerprints: list[str] = []
        for cert in meta.signing_certs:
            ref = f"saml-cert:{tenant_id}:{meta.entity_id}:{cert.fingerprint[:16]}"
            self.secrets.put(ref, base64.b64encode(cert.der).decode("ascii"))
            refs.append(ref)
            fingerprints.append(cert.fingerprint)
        kwargs: dict = {}
        if attribute_map is not None:
            kwargs["attribute_map"] = dict(attribute_map)
        config = SamlIdPConfig(
            tenant_id=tenant_id, idp_entity_id=meta.entity_id,
            sp_entity_id=sp_entity_id, acs_url=acs_url,
            sso_redirect_url=meta.sso_redirect_url, sso_post_url=meta.sso_post_url,
            signing_cert_refs=tuple(refs),
            signing_cert_fingerprints=tuple(fingerprints),
            subject_source=subject_source,
            allow_idp_initiated=allow_idp_initiated, **kwargs)
        existing = (tenant_id, meta.entity_id) in self.directory.saml_idps
        self.directory.add_saml_idp(config)
        self._tenant_ledger(tenant_id).record(
            IDP_UPDATED if existing else IDP_CONFIGURED,
            actor_id=admin.actor_id, target=f"idp:{meta.entity_id}",
            protocol="saml", idp_entity_id=meta.entity_id, sp_entity_id=sp_entity_id,
            signing_cert_refs=refs, signing_cert_fingerprints=fingerprints,
            subject_source=subject_source, allow_idp_initiated=allow_idp_initiated,
            via=via, at=self._now())
        return config

    def provision_tenant_saml_idp(self, session_token: str, *, tenant_id: str,
                                  sp_entity_id: str, acs_url: str, metadata_xml: str,
                                  attribute_map: Optional[dict] = None,
                                  subject_source: str = "nameid",
                                  allow_idp_initiated: bool = True) -> SamlIdPConfig:
        """Platform provisioning of a tenant's SAML IdP (tenant
        lifecycle act, like provision_tenant_idp)."""
        _, admin = self._require(session_token, authz.PLATFORM_TENANT_MANAGE, tenant_id=None)
        return self._register_saml_idp(
            admin, tenant_id=tenant_id, sp_entity_id=sp_entity_id, acs_url=acs_url,
            metadata_xml=metadata_xml, attribute_map=attribute_map,
            subject_source=subject_source, allow_idp_initiated=allow_idp_initiated,
            via="provisioning")

    def configure_saml_idp(self, session_token: str, *, tenant_id: str,
                           sp_entity_id: str, acs_url: str, metadata_xml: str,
                           attribute_map: Optional[dict] = None,
                           subject_source: str = "nameid",
                           allow_idp_initiated: bool = True) -> SamlIdPConfig:
        _, admin = self._require(session_token, authz.TENANT_IDP_MANAGE, tenant_id=tenant_id)
        return self._register_saml_idp(
            admin, tenant_id=tenant_id, sp_entity_id=sp_entity_id, acs_url=acs_url,
            metadata_xml=metadata_xml, attribute_map=attribute_map,
            subject_source=subject_source, allow_idp_initiated=allow_idp_initiated,
            via="tenant-admin")

    # -- role grants ------------------------------------------------------------------

    def grant_role(self, session_token: str, *, identity_id: str, role: str,
                   tenant_id: Optional[str]) -> None:
        # Grantor rules: platform_admin is granted by a platform admin
        # (deployment ledger). tenant_admin is ALSO granted by a
        # platform admin — the first tenant admin cannot be granted by
        # a tenant admin who does not exist yet — but is recorded in
        # the tenant's ledger, where the role has effect. Study roles
        # are granted by the tenant's own tenant admin.
        if role == authz.PLATFORM_ADMIN:
            _, grantor = self._require(session_token, authz.PLATFORM_ADMIN_GRANT, tenant_id=None)
            scope_ledger, scope_tenant = self.deployment_ledger, None
        elif role == authz.TENANT_ADMIN:
            if tenant_id is None:
                raise ConfigurationError("tenant_admin grants require tenant_id")
            _, grantor = self._require(session_token, authz.PLATFORM_ADMIN_GRANT, tenant_id=None)
            scope_ledger, scope_tenant = self._tenant_ledger(tenant_id), tenant_id
        else:
            if tenant_id is None:
                raise ConfigurationError("tenant-scoped role grants require tenant_id")
            _, grantor = self._require(session_token, authz.TENANT_MEMBER_MANAGE, tenant_id=tenant_id)
            scope_ledger, scope_tenant = self._tenant_ledger(tenant_id), tenant_id
        grantee = self.directory.identity(identity_id)
        if scope_tenant is not None and grantee.tenant_id != scope_tenant:
            raise ConfigurationError("cannot grant a tenant role to an identity of another tenant")
        scope_ledger.record(
            ROLE_GRANTED, actor_id=grantor.actor_id, target=f"identity:{identity_id}",
            identity_id=identity_id, subject_actor_id=grantee.actor_id, role=role,
            tenant_id=scope_tenant, at=self._now())

    def revoke_role(self, session_token: str, *, identity_id: str, role: str,
                    tenant_id: Optional[str]) -> None:
        if role == authz.PLATFORM_ADMIN:
            _, grantor = self._require(session_token, authz.PLATFORM_ADMIN_GRANT, tenant_id=None)
            scope_ledger, scope_tenant = self.deployment_ledger, None
        elif role == authz.TENANT_ADMIN:
            if tenant_id is None:
                raise ConfigurationError("tenant_admin revocations require tenant_id")
            _, grantor = self._require(session_token, authz.PLATFORM_ADMIN_GRANT, tenant_id=None)
            scope_ledger, scope_tenant = self._tenant_ledger(tenant_id), tenant_id
        else:
            if tenant_id is None:
                raise ConfigurationError("tenant-scoped role revocations require tenant_id")
            _, grantor = self._require(session_token, authz.TENANT_MEMBER_MANAGE, tenant_id=tenant_id)
            scope_ledger, scope_tenant = self._tenant_ledger(tenant_id), tenant_id
        grantee = self.directory.identity(identity_id)
        scope_ledger.record(
            ROLE_REVOKED, actor_id=grantor.actor_id, target=f"identity:{identity_id}",
            identity_id=identity_id, subject_actor_id=grantee.actor_id, role=role,
            tenant_id=scope_tenant, at=self._now())

    # -- login lifecycle -----------------------------------------------------------------

    def begin_login(self, tenant_id: str, issuer: str) -> str:
        config = self.directory.idp(tenant_id, issuer)
        state = _secrets.token_urlsafe(24)
        nonce = _secrets.token_urlsafe(24)
        verifier, challenge = pkce_pair()
        self._pending_auth[state] = {
            "tenant_id": tenant_id, "issuer": issuer, "nonce": nonce,
            "verifier": verifier, "expires": self._now() + 600,
        }
        return self.oidc.authorization_url(
            issuer=issuer, client_id=config.client_id,
            redirect_uri=config.redirect_uri, state=state, nonce=nonce,
            code_challenge=challenge)

    def complete_login(self, state: str, code: str) -> str:
        pending = self._pending_auth.pop(state, None)
        if (pending is None or pending["expires"] < self._now()
                or pending.get("protocol", "oidc") != "oidc"):
            raise AuthenticationError("login state unknown or expired")
        tenant_id, issuer = pending["tenant_id"], pending["issuer"]
        config = self.directory.idp(tenant_id, issuer)
        ledger = self._auth_ledger(tenant_id)

        def fail(reason: str) -> AuthenticationError:
            ledger.record(AUTH_LOGIN_FAILED, actor_id="unknown",
                          target=f"tenant:{tenant_id}", outcome="failed",
                          reason=reason, issuer=issuer, at=self._now())
            return AuthenticationError("authentication failed")

        try:
            tokens = self.oidc.exchange_code(
                issuer=issuer, client_id=config.client_id,
                client_secret=self.secrets.get(config.client_secret_ref),
                redirect_uri=config.redirect_uri, code=code,
                code_verifier=pending["verifier"])
            claims = self.oidc.validate_id_token(
                tokens["id_token"], issuer=issuer, client_id=config.client_id,
                nonce=pending["nonce"], attribute_map=config.attribute_map)
        except AuthenticationError:
            raise fail("assertion rejected")
        except Exception:
            raise fail("token exchange failed")

        identity, created = self.directory.get_or_create_identity(
            tenant_id, issuer, claims.subject,
            display_name=claims.attributes.get("display_name", ""),
            email=claims.attributes.get("email", ""),
            affiliation=claims.attributes.get("affiliation", ""))
        if not identity.active:
            raise fail("identity deactivated")
        if created:
            ledger.record(IDENTITY_CREATED, actor_id=identity.actor_id,
                          target=f"identity:{identity.identity_id}",
                          identity_id=identity.identity_id, subject_actor_id=identity.actor_id,
                          via="oidc", at=self._now())
        session = self.directory.new_session(
            identity, amr=claims.amr, acr=claims.acr, mfa=claims.mfa, now=self._now())
        policy = self.directory.tenant(tenant_id).policy
        ledger.record(AUTH_LOGIN_SUCCEEDED, actor_id=identity.actor_id,
                      target=f"identity:{identity.identity_id}",
                      identity_id=identity.identity_id, subject_actor_id=identity.actor_id,
                      session_id=session.session_id, mfa=claims.mfa,
                      mfa_required=policy.require_mfa, at=self._now())
        return session.session_id

    # -- SAML login lifecycle (E2, T513–T515, T517) ----------------------------

    def _saml_settings(self, config: SamlIdPConfig) -> SamlIdPSettings:
        certs = tuple(
            parse_certificate(base64.b64decode(self.secrets.get(ref)))
            for ref in config.signing_cert_refs)
        return SamlIdPSettings(
            idp_entity_id=config.idp_entity_id, sp_entity_id=config.sp_entity_id,
            acs_url=config.acs_url, signing_certs=certs,
            attribute_map=config.attribute_map, subject_source=config.subject_source)

    def _saml_redirect(self, config: SamlIdPConfig, *, purpose: str,
                       extra: Optional[dict] = None) -> str:
        if not config.sso_redirect_url:
            raise ConfigurationError("tenant's SAML IdP offers no redirect SSO endpoint")
        state = _secrets.token_urlsafe(24)
        request_id = new_request_id()
        pending = {
            "protocol": "saml", "purpose": purpose,
            "tenant_id": config.tenant_id, "idp_entity_id": config.idp_entity_id,
            "request_id": request_id, "expires": self._now() + 600,
        }
        if extra:
            pending.update(extra)
        self._pending_auth[state] = pending
        xml = build_authn_request(
            request_id=request_id, sp_entity_id=config.sp_entity_id,
            acs_url=config.acs_url, destination=config.sso_redirect_url,
            issue_instant=self._now(),
            force_authn=(purpose == "stepup"),
            mfa_context_ref=STEPUP_MFA_CONTEXT_REF if purpose == "stepup" else None)
        return redirect_binding_url(xml, endpoint=config.sso_redirect_url,
                                    relay_state=state)

    def begin_saml_login(self, tenant_id: str, idp_entity_id: str) -> str:
        config = self.directory.saml_idp(tenant_id, idp_entity_id)
        return self._saml_redirect(config, purpose="login")

    def begin_saml_step_up(self, session_token: str) -> str:
        """Step-up for a SAML-born session (T517 parity): a fresh,
        ForceAuthn request to the same IdP that made the identity."""
        session, identity = self._resolve_session(session_token)
        config = self.directory.saml_idp(identity.tenant_id, identity.issuer)
        return self._saml_redirect(
            config, purpose="stepup",
            extra={"session_id": session.session_id, "identity_id": identity.identity_id})

    def _validate_saml(self, tenant_id: str, idp_entity_id: str,
                       relay_state: Optional[str], saml_response_b64: str,
                       *, purpose: str) -> tuple[SamlIdPConfig, SamlAssertion, Optional[dict]]:
        """The validation half of both SAML completions. Raises
        AuthenticationError with the specific refusal; callers record
        it as an authentication failure, then raise the generic
        message (the E1 complete_login pattern)."""
        try:
            config = self.directory.saml_idp(tenant_id, idp_entity_id)
        except ConfigurationError:
            raise AuthenticationError("no SAML IdP configured for tenant")
        pending: Optional[dict] = None
        if relay_state:
            pending = self._pending_auth.pop(relay_state, None)
            if (pending is None or pending.get("protocol") != "saml"
                    or pending.get("purpose") != purpose
                    or pending["expires"] < self._now()
                    or pending["tenant_id"] != tenant_id
                    or pending["idp_entity_id"] != idp_entity_id):
                raise AuthenticationError("login state unknown, expired, or mismatched")
        elif purpose == "stepup":
            raise AuthenticationError("step-up requires a RelayState")
        elif not config.allow_idp_initiated:
            raise AuthenticationError("IdP-initiated login is not enabled for this tenant")
        settings = self._saml_settings(config)
        now = self._now()
        live = tuple(c for c in settings.signing_certs
                     if c.not_before - CLOCK_SKEW_SECONDS <= now <= c.not_after + CLOCK_SKEW_SECONDS)
        if not live:
            raise AuthenticationError("IdP signing certificate is expired")
        settings = replace(settings, signing_certs=live)
        claims = validate_response(
            saml_response_b64, settings=settings,
            pending_request_id=pending["request_id"] if pending else None, now=now)
        hold_until = claims.expires_at + CLOCK_SKEW_SECONDS
        if not self.directory.consume_saml_id(claims.assertion_id, hold_until, now):
            raise AuthenticationError("assertion replay detected")
        if not self.directory.consume_saml_id(claims.response_id, hold_until, now):
            raise AuthenticationError("response replay detected")
        return config, claims, pending

    def complete_saml_login(self, tenant_id: str, idp_entity_id: str,
                            relay_state: Optional[str], saml_response_b64: str) -> str:
        """The tenant's ACS, as a service method. SP-initiated when a
        RelayState is carried; IdP-initiated (unsolicited) when not —
        and only where the tenant's configuration allows it."""
        ledger = self._auth_ledger(tenant_id)

        def fail(reason: str) -> AuthenticationError:
            ledger.record(AUTH_LOGIN_FAILED, actor_id="unknown",
                          target=f"tenant:{tenant_id}", outcome="failed",
                          reason=f"saml: {reason}", issuer=idp_entity_id,
                          protocol="saml", at=self._now())
            return AuthenticationError("authentication failed")

        try:
            _, claims, _ = self._validate_saml(
                tenant_id, idp_entity_id, relay_state, saml_response_b64,
                purpose="login")
        except AuthenticationError as exc:
            raise fail(str(exc))
        identity, created = self.directory.get_or_create_identity(
            tenant_id, idp_entity_id, claims.subject, created_via="saml",
            display_name=claims.attributes.get("display_name", ""),
            email=claims.attributes.get("email", ""),
            affiliation=claims.attributes.get("affiliation", ""))
        if not identity.active:
            raise fail("identity deactivated")
        if created:
            ledger.record(IDENTITY_CREATED, actor_id=identity.actor_id,
                          target=f"identity:{identity.identity_id}",
                          identity_id=identity.identity_id,
                          subject_actor_id=identity.actor_id,
                          via="saml", at=self._now())
        session = self.directory.new_session(
            identity, amr=claims.amr, acr=claims.acr, mfa=claims.mfa, now=self._now())
        policy = self.directory.tenant(tenant_id).policy
        ledger.record(AUTH_LOGIN_SUCCEEDED, actor_id=identity.actor_id,
                      target=f"identity:{identity.identity_id}",
                      identity_id=identity.identity_id,
                      subject_actor_id=identity.actor_id,
                      session_id=session.session_id, mfa=claims.mfa,
                      mfa_required=policy.require_mfa, protocol="saml",
                      at=self._now())
        return session.session_id

    def complete_saml_step_up(self, relay_state: str, saml_response_b64: str) -> str:
        """Consume a step-up response: the pending record names the
        tenant, IdP, and session; the assertion must be for the same
        identity and must evidence MFA (T517 — the SAML door reaches
        the same §2 step-up state as the OIDC door)."""
        peek = self._pending_auth.get(relay_state)
        if peek is None or peek.get("protocol") != "saml" or peek.get("purpose") != "stepup":
            raise AuthenticationError("step-up state unknown")
        tenant_id, idp_entity_id = peek["tenant_id"], peek["idp_entity_id"]
        ledger = self._auth_ledger(tenant_id)

        def fail(reason: str) -> AuthenticationError:
            ledger.record(AUTH_LOGIN_FAILED, actor_id="unknown",
                          target=f"tenant:{tenant_id}", outcome="failed",
                          reason=f"saml step-up: {reason}", issuer=idp_entity_id,
                          protocol="saml", at=self._now())
            return AuthenticationError("step-up failed")

        try:
            _, claims, pending = self._validate_saml(
                tenant_id, idp_entity_id, relay_state, saml_response_b64,
                purpose="stepup")
        except AuthenticationError as exc:
            raise fail(str(exc))
        assert pending is not None  # step-up always carries a pending record
        session = self.directory.session(pending["session_id"])
        identity = self.directory.identity(pending["identity_id"])
        if session is None or session.revoked:
            raise fail("step-up session is gone")
        if claims.subject != identity.subject or claims.issuer != identity.issuer:
            raise fail("step-up assertion is for a different identity")
        if not claims.mfa:
            raise fail("step-up requires MFA evidence")
        session.stepped_up_at = self._now()
        session.amr = claims.amr
        session.mfa = True
        ledger.record(AUTH_STEPUP, actor_id=identity.actor_id,
                      target=f"session:{session.session_id}",
                      identity_id=identity.identity_id,
                      subject_actor_id=identity.actor_id,
                      session_id=session.session_id, protocol="saml",
                      at=self._now())
        return session.session_id

    def logout(self, session_token: str) -> None:
        session = self.directory.session(session_token)
        if session is None or session.revoked:
            raise AuthenticationError("session unknown or revoked")
        session.revoked = True
        identity = self.directory.identity(session.identity_id)
        self._auth_ledger(session.tenant_id).record(
            AUTH_LOGOUT, actor_id=identity.actor_id, target=f"session:{session.session_id}",
            identity_id=identity.identity_id, subject_actor_id=identity.actor_id, at=self._now())

    def step_up(self, session_token: str, *, id_token: str, nonce: str) -> None:
        """Record a fresh step-up authentication for the session
        (fresh assertion for the same identity, MFA-evidencing);
        verdict-class and admin actions consult its freshness (§2)."""
        session, identity = self._resolve_session(session_token)
        config = self.directory.idp(identity.tenant_id, identity.issuer)
        claims = self.oidc.validate_id_token(
            id_token, issuer=identity.issuer, client_id=config.client_id,
            nonce=nonce, attribute_map=config.attribute_map)
        if claims.subject != identity.subject or claims.issuer != identity.issuer:
            raise AuthenticationError("step-up assertion is for a different identity")
        if not claims.mfa:
            raise AuthenticationError("step-up requires MFA evidence")
        session.stepped_up_at = self._now()
        session.amr = claims.amr
        session.mfa = True
        self._auth_ledger(identity.tenant_id).record(
            AUTH_STEPUP, actor_id=identity.actor_id, target=f"session:{session.session_id}",
            identity_id=identity.identity_id, subject_actor_id=identity.actor_id,
            session_id=session.session_id, at=self._now())

    # -- identity administration ----------------------------------------------------------

    def create_service_identity(self, session_token: str, *, tenant_id: str,
                                name: str) -> Identity:
        _, admin = self._require(session_token, authz.TENANT_MEMBER_MANAGE, tenant_id=tenant_id)
        ident, _ = self.directory.get_or_create_identity(
            tenant_id, "service", f"svc:{name}", created_via="admin", display_name=name)
        self._tenant_ledger(tenant_id).record(
            IDENTITY_CREATED, actor_id=admin.actor_id, target=f"identity:{ident.identity_id}",
            identity_id=ident.identity_id, subject_actor_id=ident.actor_id, via="admin",
            principal_class="service", at=self._now())
        return ident

    def deactivate_identity(self, session_token: str, *, identity_id: str,
                            reason: str = "") -> None:
        """The E1 mechanism of deprovisioning (§4; SCIM wires to this
        in E3): deactivation event, sessions revoked, keys closed —
        effective at the next request. History is untouched."""
        identity = self.directory.identity(identity_id)
        tenant_id = identity.tenant_id
        _, admin = self._require(session_token, authz.TENANT_MEMBER_MANAGE, tenant_id=tenant_id)
        ledger = self._tenant_ledger(tenant_id)
        identity.active = False
        ledger.record(IDENTITY_DEACTIVATED, actor_id=admin.actor_id,
                      target=f"identity:{identity_id}",
                      identity_id=identity_id, subject_actor_id=identity.actor_id,
                      reason=reason, at=self._now())
        n = self.directory.revoke_sessions_for(identity_id)
        if n:
            ledger.record(SESSION_REVOKED, actor_id=admin.actor_id,
                          target=f"identity:{identity_id}",
                          identity_id=identity_id, subject_actor_id=identity.actor_id,
                          sessions_revoked=n, reason="deactivation", at=self._now())
        self.registry(tenant_id).close_for_identity(
            identity_id=identity_id, recorded_by_actor_id=admin.actor_id,
            reason="deactivation")

    def update_identity(self, session_token: str, *, identity_id: str, **attrs) -> Identity:
        identity = self.directory.identity(identity_id)
        _, admin = self._require(session_token, authz.TENANT_MEMBER_MANAGE,
                                 tenant_id=identity.tenant_id)
        changed = {}
        for k, v in attrs.items():
            if k in ("display_name", "email", "affiliation") and v is not None:
                setattr(identity, k, v)
                changed[k] = v
        self._tenant_ledger(identity.tenant_id).record(
            IDENTITY_UPDATED, actor_id=admin.actor_id, target=f"identity:{identity_id}",
            identity_id=identity_id, subject_actor_id=identity.actor_id,
            fields=sorted(changed), at=self._now())
        return identity

    # -- key lifecycle (session-side entry points) -------------------------------------------

    def begin_enrollment(self, session_token: str) -> str:
        session, identity = self._resolve_session(session_token)
        return self.registry(identity.tenant_id).issue_nonce(identity.identity_id)

    def enroll_self_key(self, session_token: str, *, public_key: bytes,
                        proof_signature: bytes, nonce: str) -> KeyRecord:
        session, identity = self._resolve_session(session_token)
        self._require_stepup_if_adjudicator(identity, session)
        return self.registry(identity.tenant_id).enroll(
            identity_id=identity.identity_id, actor_id=identity.actor_id,
            public_key=public_key, custody="self",
            proof_signature=proof_signature, nonce=nonce,
            recorded_by_actor_id=identity.actor_id)

    def enroll_delegated_key(self, session_token: str, *, seed_hex: str) -> KeyRecord:
        """Delegated custody enrollment: the key is generated for the
        platform's signer (dev signer in E1 — see keys.DelegatedSigner)
        and proof of possession is the signer signing the nonce."""
        session, identity = self._resolve_session(session_token)
        self._require_stepup_if_adjudicator(identity, session)
        public_key = ed25519.publickey_from_seed(bytes.fromhex(seed_hex))
        fp = self.delegated_signer.hold(seed_hex)
        assert fp == fingerprint(public_key)
        nonce = self.registry(identity.tenant_id).issue_nonce(identity.identity_id)
        proof = self.delegated_signer.sign(fp, nonce.encode("utf-8"))
        return self.registry(identity.tenant_id).enroll(
            identity_id=identity.identity_id, actor_id=identity.actor_id,
            public_key=public_key, custody="delegated",
            proof_signature=proof, nonce=nonce,
            recorded_by_actor_id=identity.actor_id)

    def _require_stepup_if_adjudicator(self, identity: Identity, session: Session) -> None:
        """§3: adjudicator key enrollment happens in a stepped-up
        session — an adjudicator's key is a verdict instrument."""
        roles = self.roles_of(identity.identity_id, identity.tenant_id)
        if authz.ADJUDICATOR in roles:
            policy = self.directory.tenant(identity.tenant_id).policy
            if not session.has_fresh_stepup(policy, self._now()):
                raise GateDenied("adjudicator key enrollment requires a fresh step-up")

    def rotate_key(self, session_token: str, *, old_fingerprint: str,
                   new_public_key: bytes, proof_signature: bytes, nonce: str) -> KeyRecord:
        session, identity = self._resolve_session(session_token)
        self._require_stepup_if_adjudicator(identity, session)  # rotation enrolls a new key (§3)
        registry = self.registry(identity.tenant_id)
        rec = registry.get(old_fingerprint)
        if rec is None or rec.identity_id != identity.identity_id:
            raise GateDenied("only the key's owner can rotate it")
        if rec.custody != "self":
            raise GateDenied("delegated keys rotate through the custody provider, not self-service")
        return registry.rotate(
            old_fingerprint=old_fingerprint, new_public_key=new_public_key,
            proof_signature=proof_signature, nonce=nonce,
            recorded_by_actor_id=identity.actor_id)

    def revoke_key(self, session_token: str, *, key_fingerprint: str, reason: str = "") -> None:
        session, identity = self._resolve_session(session_token)
        registry = self.registry(identity.tenant_id)
        rec = registry.get(key_fingerprint)
        if rec is None:
            raise GateDenied(f"unknown key: {key_fingerprint}")
        if rec.identity_id != identity.identity_id:
            # Someone else's key: tenant key management only.
            self._require(session_token, authz.TENANT_KEY_MANAGE, tenant_id=identity.tenant_id)
        registry.revoke(fp=key_fingerprint, recorded_by_actor_id=identity.actor_id,
                        reason=reason)

    # -- API keys -----------------------------------------------------------------------------

    def issue_api_key(self, session_token: str, *, tenant_id: str,
                      principal_identity_id: str, role_class: str,
                      scopes: list[str], lifetime_seconds: float) -> tuple[ApiKeyRecord, str]:
        _, admin = self._require(session_token, authz.TENANT_KEY_MANAGE, tenant_id=tenant_id)
        AuthorizationService.validate_key_scopes(role_class, scopes)
        principal = self.directory.identity(principal_identity_id)
        if principal.tenant_id != tenant_id:
            raise ConfigurationError("API key principal belongs to another tenant")
        now = self._now()
        secret = _secrets.token_urlsafe(32)
        record = ApiKeyRecord(
            key_id="tk_" + _secrets.token_hex(4),
            tenant_id=tenant_id, principal_identity_id=principal_identity_id,
            role_class=role_class, scopes=frozenset(scopes),
            secret_hash=hash_api_secret(secret),
            created_at=now, expires_at=now + lifetime_seconds,
            created_by_actor_id=admin.actor_id)
        self.directory.add_api_key(record)  # enforces the ≤1y lifetime (§9)
        self._tenant_ledger(tenant_id).record(
            APIKEY_ISSUED, actor_id=admin.actor_id, target=f"apikey:{record.key_id}",
            key_id=record.key_id, principal_actor_id=principal.actor_id,
            role_class=role_class, scopes=sorted(scopes),
            expires_at=int(record.expires_at), at=now)  # int: ledger payload discipline (ledger.py)
        return record, secret

    def revoke_api_key(self, session_token: str, *, tenant_id: str, key_id: str) -> None:
        _, admin = self._require(session_token, authz.TENANT_KEY_MANAGE, tenant_id=tenant_id)
        record = self.directory.api_keys.get(key_id)
        if record is None or record.tenant_id != tenant_id:
            raise ConfigurationError(f"unknown API key: {key_id}")
        record.revoked = True
        self._tenant_ledger(tenant_id).record(
            APIKEY_REVOKED, actor_id=admin.actor_id, target=f"apikey:{key_id}",
            key_id=key_id, at=self._now())

    # -- append authorization (the gate core; consumed by gate.py) ------------------------------

    def _deny_append(self, tenant_id: str, actor_id: str, action: str, reason: str) -> GateDenied:
        self._tenant_ledger(tenant_id).record(
            AUTHZ_DENIED, actor_id=actor_id, target=f"action:{action}",
            outcome="denied", action=action, reason=reason, at=self._now())
        return GateDenied(reason)

    def authorize_study_append(self, session_token: str, *, tenant_id: str,
                               action: str, intent: bytes,
                               key_fingerprint: str,
                               signature: Optional[bytes]) -> AppendAuthorization:
        """T507: an append is authorized only under an enrolled,
        unrevoked key bound to the session identity, with the role,
        tenant binding, MFA, and step-up rules of §§2/5/13.5. Every
        refusal is recorded before it is raised."""
        try:
            session, identity = self._resolve_session(session_token)
        except AuthenticationError as exc:
            raise self._deny_append(tenant_id, "unknown", action, f"session: {exc}")
        if identity.tenant_id != tenant_id or session.tenant_id != tenant_id:
            raise self._deny_append(tenant_id, identity.actor_id, action,
                                    "tenant context comes from the session, not the request")
        roles = self.roles_of(identity.identity_id, tenant_id)
        decision = self.authz.decide(roles, action)
        if not decision.allowed:
            raise self._deny_append(tenant_id, identity.actor_id, action, decision.reason)
        policy = self.directory.tenant(tenant_id).policy
        if policy.require_mfa and not session.mfa:
            raise self._deny_append(tenant_id, identity.actor_id, action,
                                    "tenant policy requires MFA-evidenced session (§13.5)")
        if action in authz.VERDICT_CLASS_ACTIONS and not session.has_fresh_stepup(policy, self._now()):
            raise self._deny_append(tenant_id, identity.actor_id, action,
                                    "verdict-class signing requires a fresh step-up (§2/§3)")
        registry = self.registry(tenant_id)
        rec = registry.get(key_fingerprint)
        if rec is None or rec.identity_id != identity.identity_id:
            raise self._deny_append(tenant_id, identity.actor_id, action,
                                    "key is not enrolled for this identity")
        if not registry.is_accepted(key_fingerprint):
            raise self._deny_append(tenant_id, identity.actor_id, action,
                                    f"key is {registry.status(key_fingerprint)}, not enrolled")
        if rec.custody == "self":
            if signature is None:
                raise self._deny_append(tenant_id, identity.actor_id, action,
                                        "self-custody append requires the actor's signature")
            if not ed25519.verify(bytes.fromhex(rec.public_key_hex), intent, signature):
                raise self._deny_append(tenant_id, identity.actor_id, action,
                                        "intent signature does not verify")
            sig_hex = signature.hex()
        else:  # delegated: the platform signer signs inside this authorized session
            sig_hex = self.delegated_signer.sign(key_fingerprint, intent).hex()
        session.last_seen_at = self._now()
        return AppendAuthorization(
            identity=identity, role_basis=decision.role_basis or "",
            key_fingerprint=key_fingerprint, custody=rec.custody,
            session_id=session.session_id, signature_hex=sig_hex)

    def authorize_api_append(self, key_id: str, secret: str, *, tenant_id: str,
                             action: str) -> AppendAuthorization:
        """Service-account appends (CLM-005-18): the key authenticates;
        scope, expiry, revocation, and the principal's state decide.
        Actions are attributed to the principal in the record."""
        ledger = self._tenant_ledger(tenant_id)
        record = self.directory.find_api_key(key_id, secret)
        if record is None or record.tenant_id != tenant_id:
            ledger.record(AUTH_APIKEY_FAILED, actor_id="unknown", target=f"apikey:{key_id}",
                          outcome="failed", reason="unknown key or bad secret", at=self._now())
            raise GateDenied("API key authentication failed")
        if record.revoked:
            ledger.record(AUTH_APIKEY_FAILED, actor_id="unknown", target=f"apikey:{key_id}",
                          outcome="failed", reason="key revoked", at=self._now())
            raise GateDenied("API key is revoked")
        if record.expires_at <= self._now():
            ledger.record(AUTH_APIKEY_FAILED, actor_id="unknown", target=f"apikey:{key_id}",
                          outcome="failed", reason="key expired", at=self._now())
            raise GateDenied("API key is expired")
        principal = self.directory.identity(record.principal_identity_id)
        if not principal.active:
            raise self._deny_append(tenant_id, principal.actor_id, action,
                                    "API key principal is deactivated")
        if action not in record.scopes:
            raise self._deny_append(tenant_id, principal.actor_id, action,
                                    f"action {action} outside API key scopes")
        record.last_used_at = self._now()
        return AppendAuthorization(
            identity=principal, role_basis=record.role_class,
            key_fingerprint=None, custody="api_key",
            session_id=None, api_key_id=key_id)
