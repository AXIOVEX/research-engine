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
from .baseline import ENDPOINT_CLASSES, RateLimiter, tls_posture
from .compliance import ControlStateStore
from .exports import export_platform_audit
from .breakglass import (
    AUTHORIZER_PLANES, AUTHORIZER_PLATFORM, AUTHORIZER_TENANT,
    MAX_DURATION_SECONDS as BREAKGLASS_MAX_DURATION_SECONDS,
    STATE_ACTIVE, STATE_CLOSED, STATE_DENIED, STATE_EXPIRED, STATE_PENDING,
    BreakGlassPolicy, BreakGlassSession,
)
from .directory import (
    ApiKeyRecord, Directory, IdPConfig, Identity, InMemorySecrets,
    SamlIdPConfig, Session, Tenant, hash_api_secret,
)
from .errors import (
    AuthenticationError, AuthorizationDenied, ConfigurationError, GateDenied,
    RateLimited,
)
from .keys import (
    STATUS_CLOSED, STATUS_REVOKED, DelegatedSigner, KeyRecord, KeyRegistry,
    fingerprint,
)
from .ledger import (
    APIKEY_ISSUED, APIKEY_REVOKED, AUDIT_EXPORT_ANCHORED, AUDIT_EXPORTED,
    AUTH_APIKEY_FAILED, AUTH_LOGIN_FAILED,
    AUTH_LOGIN_SUCCEEDED, AUTH_LOGOUT, AUTH_STEPUP, AUTHZ_DENIED,
    BREAKGLASS_ACTION, BREAKGLASS_ACTION_REFUSED, BREAKGLASS_AUTHORIZATION_DENIED,
    BREAKGLASS_AUTHORIZED, BREAKGLASS_INVOCATION_REFUSED, BREAKGLASS_INVOKED,
    BREAKGLASS_POLICY_DECLARED, BREAKGLASS_POLICY_REVOKED,
    BREAKGLASS_REVIEW_COMPLETED, BREAKGLASS_REVIEW_CREATED,
    BREAKGLASS_SESSION_CLOSED, COMPLIANCE_STATE_SET_REFUSED,
    DIRECTORY_PII_ERASED, GROUP_MAPPING_APPROVED,
    GROUP_MAPPING_REVOKED, GROUP_MEMBERSHIP_GRANTED, GROUP_MEMBERSHIP_REVOKED,
    IDENTITY_CREATED, IDENTITY_DEACTIVATED, IDENTITY_REACTIVATED,
    IDENTITY_UPDATED, IDP_CONFIGURED, IDP_UPDATED, LEGAL_HOLD_ENFORCED,
    LEGAL_HOLD_PLACED, LEGAL_HOLD_RELEASED, PLATFORM_BOOTSTRAPPED,
    RATE_LIMIT_EXCEEDED, ROLE_GRANTED, ROLE_REVOKED, SCIM_SYNC_FAILED,
    SCIM_SYNC_SUCCEEDED, SCIM_TOKEN_ISSUED, SCIM_TOKEN_REVOKED,
    SECURITY_EVENT_EMITTED, SESSION_REVOKED, TENANT_CREATED,
    TENANT_MARKING_UPDATED, TENANT_RESIDENCY_CHANGE_REFUSED,
    TENANT_RESIDENCY_MIGRATED, TENANT_UPDATED,
    WEBHOOK_DELIVERY_FAILED, WEBHOOK_DELIVERY_SUCCEEDED,
    WEBHOOK_SUBSCRIPTION_CREATED, WEBHOOK_SUBSCRIPTION_REVOKED,
    PlatformLedger,
)
from .oidc import OIDCClient, pkce_pair
from .poam import PoamRegister
from .saml import (
    CLOCK_SKEW_SECONDS, SamlAssertion, SamlIdPSettings, build_authn_request,
    new_request_id, parse_metadata, redirect_binding_url, validate_response,
)
from .scim import (
    SCIM_ISSUER, GroupRoleMapping, ProvisionedUser, ScimCredential,
    ScimDirectory, ScimError, ScimAuthenticationError, ScimBadRequestError,
    ScimGroup, ScimNotFoundError, ScimUniquenessError, display_name_of,
    group_resource, list_response, matches_filter, new_prefixed_id,
    new_scim_id, paginate, parse_filter, primary_email, user_resource,
)
from .webhooks import (
    BACKOFF_SECONDS, EVENT_TEST, MAX_ATTEMPTS, SIGNING_ED25519,
    SIGNING_HMAC_SHA256, SIGNING_MODES, SEC_AUDIT_VERIFICATION_FAILURE,
    SEC_AUTH_FAILURE_BURST, SEC_BREAK_GLASS_USE, SEC_REVOCATION_STORM,
    Delivery, SecurityMonitor, WebhookSubscription, build_delivery,
)
from .x509 import parse_certificate

#: Step-up requests ask the IdP for the REFEDS MFA profile context;
#: an IdP that cannot evidence MFA cannot step a session up (§2).
STEPUP_MFA_CONTEXT_REF = "https://refeds.org/profile/mfa"

PLATFORM_TENANT_ID = "__platform__"
SYSTEM_ACTOR = "system"

#: Spec 013 CLM-013-27 (red-team probe p17): SCIM failures against
#: tenant ids that do not exist are ledgered in the deployment
#: ledger, which an unauthenticated caller could otherwise grow
#: without bound by rotating tenant ids. Failure recording for
#: unknown tenants is capped deployment-wide at this many per
#: minute; beyond it the request is rate-limited BEFORE anything
#: is appended.
UNKNOWN_TENANT_SCIM_LIMIT_PER_MINUTE = 10
_UNKNOWN_TENANT_BUCKET = "__unknown_tenant__"

#: How long a step-up challenge (begin_step_up) stays redeemable.
STEPUP_CHALLENGE_SECONDS = 300


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
        self.scim = ScimDirectory()
        # E4 state: the rate limiter, the T554 security-event
        # detectors, and the egress delivery queue. Working state —
        # every trip, emission, and delivery outcome is ledgered.
        self.rate_limiter = RateLimiter()
        self.security_monitor = SecurityMonitor()
        self._deliveries: dict[str, Delivery] = {}
        deployment_path = self.root / "deployment.axmr"
        if deployment_path.exists():
            self.deployment_ledger = PlatformLedger.open(str(deployment_path), scope="deployment")
        else:
            self.deployment_ledger = PlatformLedger.create(
                str(deployment_path), scope="deployment", seed_hex=deployment_seed_hex)
        self._tenant_ledgers: dict[str, PlatformLedger] = {}
        self._registries: dict[str, KeyRegistry] = {}
        self._pending_auth: dict[str, dict] = {}
        # Spec 013 CLM-013-18: step-up challenges the service itself
        # issued, keyed by session id — {nonce, expires}. Single-use:
        # presenting a challenge consumes it, success or failure.
        self._pending_stepup: dict[str, dict] = {}
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

    def _require_admin_stepup(self, session: Session, identity: Identity,
                              *, action: str,
                              tenant_id: Optional[str]) -> None:
        """Spec 013 CLM-013-16/-17 (Spec 005 §2; red-team probes
        p01/p02): the sensitive admin-plane mutations — role grants
        and revocations, IdP configuration (tenant and provisioning
        paths, OIDC and SAML), API-key issuance, break-glass policy
        declaration and revocation — require, at the SERVICE layer
        (not merely in a UI):

        - MFA evidence on the session, whenever the actor's tenant
          policy requires MFA (a password-only session cannot
          perform them, whatever its roles); and
        - a fresh step-up on the session, within the same policy's
          freshness window.

        Denials are recorded in the action's scope ledger before
        the raise, like every other authorization denial here."""
        policy = self.directory.tenant(session.tenant_id).policy
        reason: Optional[str] = None
        if policy.require_mfa and not session.mfa:
            reason = ("admin-plane mutations require MFA evidence "
                      "under this tenant's policy (CLM-013-17): the "
                      "session authenticated without MFA")
        elif not session.has_fresh_stepup(policy, self._now()):
            reason = ("admin-plane mutations require a fresh step-up "
                      "at the service layer (CLM-013-16): step the "
                      "session up and retry")
        if reason is not None:
            self._ledger_for_scope(tenant_id).record(
                AUTHZ_DENIED, actor_id=identity.actor_id,
                target=f"action:{action}", outcome="denied",
                action=action, reason=reason, at=self._now(),
            )
            raise AuthorizationDenied(reason)

    # -- E4 plumbing: rate limits (T530) + security events (T554) -------------

    def _rate_guard(self, tenant_id: str, endpoint_class: str) -> None:
        """Per-tenant rate limit for one endpoint class (§6/§9). A
        trip is recorded in the tenant's ledger before the 429 is
        raised — exhaustion is a recorded stop, never a surprise.
        The platform tenant's trips land in the deployment ledger."""
        assert endpoint_class in ENDPOINT_CLASSES, endpoint_class
        policy = (self.directory.tenant(tenant_id).policy
                  if tenant_id in self.directory.tenants else None)
        limit = policy.rate_limit_per_minute if policy else 600
        try:
            self.rate_limiter.check(tenant_id, endpoint_class,
                                    limit_per_minute=limit, now=self._now())
        except RateLimited as exc:
            if tenant_id in self.directory.tenants:
                self._auth_ledger(tenant_id).record(
                    RATE_LIMIT_EXCEEDED, actor_id="system",
                    target=f"endpoint:{endpoint_class}", outcome="limited",
                    endpoint_class=endpoint_class, limit_per_minute=limit,
                    retry_after_seconds=int(exc.retry_after_seconds) + 1,
                    at=self._now())
            raise

    def _egress(self, tenant_id: str, event_type: str, data: dict) -> list[str]:
        """Queue signed deliveries for every subscription of the
        tenant matching this event type. Delivery itself (and its
        ledger records) happens in deliver_webhooks — egress is
        queued, never fired inline into a transport from inside an
        unrelated operation."""
        created: list[str] = []
        for sub in self.directory.webhook_subscriptions.values():
            if sub.tenant_id != tenant_id or not sub.matches(event_type):
                continue
            hmac_secret = ed_seed = None
            if sub.signing == SIGNING_HMAC_SHA256:
                hmac_secret = self.secrets.get(sub.secret_ref).encode("utf-8")
            else:
                ed_seed = bytes.fromhex(self.secrets.get(sub.signing_key_ref))
            delivery = build_delivery(
                sub, event_type=event_type, data=data, now=self._now(),
                hmac_secret=hmac_secret, ed25519_seed=ed_seed)
            self._deliveries[delivery.delivery_id] = delivery
            created.append(delivery.delivery_id)
        return created

    def _emit_security_event(self, tenant_id: str, event_type: str,
                             data: dict) -> None:
        """A T554 security event: the emission is itself a platform
        audit record (in the tenant's ledger; the deployment ledger
        for platform-plane context), then the event egresses signed
        over the webhook channel."""
        self._auth_ledger(tenant_id).record(
            SECURITY_EVENT_EMITTED, actor_id="system",
            target=f"security:{event_type}", outcome="emitted",
            event_class=event_type, at=self._now())
        self._egress(tenant_id, event_type, data)

    def _note_auth_failure(self, tenant_id: str) -> None:
        """Feed the T554 burst detector after an authentication
        failure has been recorded for this tenant."""
        if tenant_id not in self.directory.tenants:
            return
        policy = self.directory.tenant(tenant_id).policy
        if self.security_monitor.observe_auth_failure(
                tenant_id, now=self._now(),
                threshold=policy.auth_failure_burst_threshold,
                window=policy.security_window_seconds):
            self._emit_security_event(tenant_id, SEC_AUTH_FAILURE_BURST, {
                "tenant_id": tenant_id,
                "threshold": policy.auth_failure_burst_threshold,
                "window_seconds": int(policy.security_window_seconds),
            })

    def _note_revocations(self, tenant_id: str, count: int) -> None:
        """Feed the T554 revocation-storm detector after revocations
        have been recorded for this tenant."""
        if count <= 0 or tenant_id not in self.directory.tenants:
            return
        policy = self.directory.tenant(tenant_id).policy
        if self.security_monitor.observe_revocations(
                tenant_id, now=self._now(), count=count,
                threshold=policy.revocation_storm_threshold,
                window=policy.security_window_seconds):
            self._emit_security_event(tenant_id, SEC_REVOCATION_STORM, {
                "tenant_id": tenant_id,
                "threshold": policy.revocation_storm_threshold,
                "window_seconds": int(policy.security_window_seconds),
            })

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
        if tenant_id in self.directory.tenants:
            # Spec 013 CLM-013-26 (red-team probe p16; first recorded
            # by the E5 console pass): tenant ids are unique for the
            # life of the deployment. Re-creating an existing id used
            # to silently REPLACE the directory record — name, shape,
            # region/residency pin, marking default, and tenant
            # policy all reset under a live ledger whose legal holds,
            # break-glass policy, and exports still name the tenant.
            # The refusal is typed and ledgered; nothing is reset.
            self.deployment_ledger.record(
                AUTHZ_DENIED, actor_id=admin.actor_id,
                target=f"tenant:{tenant_id}", outcome="denied",
                action=authz.PLATFORM_TENANT_CREATE,
                reason=f"tenant already exists: {tenant_id} — "
                       "re-creation refused (CLM-013-26)",
                at=self._now())
            raise ConfigurationError(
                f"tenant already exists: {tenant_id} — tenant ids "
                "are unique for the life of the deployment; "
                "re-creating one would silently reset its residency "
                "pin, marking default, and policy under its ledger")
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
        if region is not None and region != tenant.region:
            # E6 (T541): the region IS the residency pin, and a pin
            # changes only through the export + anchor + migration
            # flow — never as a silent field update. The refusal is
            # ledgered before it is raised, like every refusal here.
            self.deployment_ledger.record(
                TENANT_RESIDENCY_CHANGE_REFUSED, actor_id=admin.actor_id,
                target=f"tenant:{tenant_id}", tenant_id=tenant_id,
                outcome="refused",
                reason="region is the residency pin; change it via "
                       "change_residency_pin (export + anchor + migration, T541)",
                at=self._now())
            raise ConfigurationError(
                "region is the tenant's residency pin — change it via "
                "change_residency_pin (anchored export + migration event), "
                "not update_tenant")
        changed = {}
        if name is not None:
            tenant.name = name
            changed["name"] = name
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
        session, admin = self._require(session_token, authz.PLATFORM_TENANT_MANAGE, tenant_id=None)
        self._require_admin_stepup(session, admin,
                                   action=authz.PLATFORM_TENANT_MANAGE,
                                   tenant_id=None)
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
        session, admin = self._require(session_token, authz.TENANT_IDP_MANAGE, tenant_id=config.tenant_id)
        self._require_admin_stepup(session, admin,
                                   action=authz.TENANT_IDP_MANAGE,
                                   tenant_id=config.tenant_id)
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
        session, admin = self._require(session_token, authz.PLATFORM_TENANT_MANAGE, tenant_id=None)
        self._require_admin_stepup(session, admin,
                                   action=authz.PLATFORM_TENANT_MANAGE,
                                   tenant_id=None)
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
        session, admin = self._require(session_token, authz.TENANT_IDP_MANAGE, tenant_id=tenant_id)
        self._require_admin_stepup(session, admin,
                                   action=authz.TENANT_IDP_MANAGE,
                                   tenant_id=tenant_id)
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
            session, grantor = self._require(session_token, authz.PLATFORM_ADMIN_GRANT, tenant_id=None)
            scope_ledger, scope_tenant = self.deployment_ledger, None
            grant_action = authz.PLATFORM_ADMIN_GRANT
        elif role == authz.TENANT_ADMIN:
            if tenant_id is None:
                raise ConfigurationError("tenant_admin grants require tenant_id")
            session, grantor = self._require(session_token, authz.PLATFORM_ADMIN_GRANT, tenant_id=None)
            scope_ledger, scope_tenant = self._tenant_ledger(tenant_id), tenant_id
            grant_action = authz.PLATFORM_ADMIN_GRANT
        else:
            if tenant_id is None:
                raise ConfigurationError("tenant-scoped role grants require tenant_id")
            session, grantor = self._require(session_token, authz.TENANT_MEMBER_MANAGE, tenant_id=tenant_id)
            scope_ledger, scope_tenant = self._tenant_ledger(tenant_id), tenant_id
            grant_action = authz.TENANT_MEMBER_MANAGE
        # Spec 013 CLM-013-16/-17: a role grant is a sensitive
        # admin-plane mutation — fresh step-up + MFA evidence.
        self._require_admin_stepup(session, grantor, action=grant_action,
                                   tenant_id=scope_tenant)
        grantee = self.directory.identity(identity_id)
        if scope_tenant is not None and grantee.tenant_id != scope_tenant:
            raise ConfigurationError("cannot grant a tenant role to an identity of another tenant")
        if identity_id == grantor.identity_id and \
                role not in self.roles_of(identity_id, scope_tenant):
            # Spec 013 CLM-013-19 (red-team probe p05): no identity
            # may grant ITSELF a role it does not already hold — the
            # adjudicator case by name, and plane separation with
            # self as counterparty everywhere else (a platform admin
            # may not hand themselves a tenant-plane role either).
            # Re-granting a role already held stays the recorded
            # no-op it has always been. The refusal is ledgered.
            reason = (
                "an identity cannot grant itself the adjudicator role"
                if role == authz.ADJUDICATOR else
                "an identity cannot grant itself a role it does not "
                "already hold") + " — grants require a second party (CLM-013-19)"
            scope_ledger.record(
                AUTHZ_DENIED, actor_id=grantor.actor_id,
                target=f"identity:{identity_id}", outcome="denied",
                action=grant_action, reason=reason, at=self._now())
            raise AuthorizationDenied(reason)
        scope_ledger.record(
            ROLE_GRANTED, actor_id=grantor.actor_id, target=f"identity:{identity_id}",
            identity_id=identity_id, subject_actor_id=grantee.actor_id, role=role,
            tenant_id=scope_tenant, at=self._now())

    def revoke_role(self, session_token: str, *, identity_id: str, role: str,
                    tenant_id: Optional[str]) -> None:
        if role == authz.PLATFORM_ADMIN:
            session, grantor = self._require(session_token, authz.PLATFORM_ADMIN_GRANT, tenant_id=None)
            scope_ledger, scope_tenant = self.deployment_ledger, None
            grant_action = authz.PLATFORM_ADMIN_GRANT
        elif role == authz.TENANT_ADMIN:
            if tenant_id is None:
                raise ConfigurationError("tenant_admin revocations require tenant_id")
            session, grantor = self._require(session_token, authz.PLATFORM_ADMIN_GRANT, tenant_id=None)
            scope_ledger, scope_tenant = self._tenant_ledger(tenant_id), tenant_id
            grant_action = authz.PLATFORM_ADMIN_GRANT
        else:
            if tenant_id is None:
                raise ConfigurationError("tenant-scoped role revocations require tenant_id")
            session, grantor = self._require(session_token, authz.TENANT_MEMBER_MANAGE, tenant_id=tenant_id)
            scope_ledger, scope_tenant = self._tenant_ledger(tenant_id), tenant_id
            grant_action = authz.TENANT_MEMBER_MANAGE
        # Revocations carry the same step-up + MFA requirement as
        # grants (CLM-013-16/-17): stripping roles is an admin-plane
        # mutation of the same sensitivity.
        self._require_admin_stepup(session, grantor, action=grant_action,
                                   tenant_id=scope_tenant)
        grantee = self.directory.identity(identity_id)
        scope_ledger.record(
            ROLE_REVOKED, actor_id=grantor.actor_id, target=f"identity:{identity_id}",
            identity_id=identity_id, subject_actor_id=grantee.actor_id, role=role,
            tenant_id=scope_tenant, at=self._now())

    # -- login lifecycle -----------------------------------------------------------------

    def begin_login(self, tenant_id: str, issuer: str) -> str:
        config = self.directory.idp(tenant_id, issuer)
        self._rate_guard(tenant_id, "auth.login")
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
        self._rate_guard(tenant_id, "auth.login")
        config = self.directory.idp(tenant_id, issuer)
        ledger = self._auth_ledger(tenant_id)

        def fail(reason: str) -> AuthenticationError:
            ledger.record(AUTH_LOGIN_FAILED, actor_id="unknown",
                          target=f"tenant:{tenant_id}", outcome="failed",
                          reason=reason, issuer=issuer, at=self._now())
            self._note_auth_failure(tenant_id)
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
                          via="oidc", provisioning="jit", at=self._now())
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
        self._rate_guard(tenant_id, "auth.saml")
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
        self._rate_guard(tenant_id, "auth.saml")
        ledger = self._auth_ledger(tenant_id)

        def fail(reason: str) -> AuthenticationError:
            ledger.record(AUTH_LOGIN_FAILED, actor_id="unknown",
                          target=f"tenant:{tenant_id}", outcome="failed",
                          reason=f"saml: {reason}", issuer=idp_entity_id,
                          protocol="saml", at=self._now())
            self._note_auth_failure(tenant_id)
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
                          via="saml", provisioning="jit", at=self._now())
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
            self._note_auth_failure(tenant_id)
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

    def begin_step_up(self, session_token: str) -> str:
        """Issue the step-up challenge for a session (Spec 013
        CLM-013-18; the OIDC sibling of begin_saml_step_up): the
        service mints a single-use nonce bound to this session and
        returns it; the caller presents it to the IdP as the
        authorization request's nonce, and step_up() accepts only a
        token carrying the nonce of a live, unconsumed challenge.
        A caller-asserted nonce — one the service never issued for
        this session — is not accepted."""
        session, identity = self._resolve_session(session_token)
        nonce = _secrets.token_urlsafe(24)
        self._pending_stepup[session.session_id] = {
            "nonce": nonce, "expires": self._now() + STEPUP_CHALLENGE_SECONDS}
        return nonce

    def step_up(self, session_token: str, *, id_token: str, nonce: str) -> None:
        """Record a fresh step-up authentication for the session
        (fresh assertion for the same identity, MFA-evidencing);
        verdict-class and admin actions consult its freshness (§2).

        Spec 013 CLM-013-18 (red-team probe p03): the nonce must be
        a live challenge this service issued via begin_step_up for
        THIS session — it is consumed by the presentation, success
        or failure, so a captured ID token cannot be replayed — and
        the assertion's auth_time must fall inside the tenant's
        step-up freshness window, so a token minted for an earlier
        ceremony cannot step a session up later in its lifetime."""
        session, identity = self._resolve_session(session_token)
        challenge = self._pending_stepup.pop(session.session_id, None)
        if challenge is None or challenge["expires"] < self._now() \
                or challenge["nonce"] != nonce:
            raise AuthenticationError(
                "step-up requires a live server-issued challenge "
                "(begin_step_up): caller-asserted or consumed nonces "
                "are not accepted")
        config = self.directory.idp(identity.tenant_id, identity.issuer)
        claims = self.oidc.validate_id_token(
            id_token, issuer=identity.issuer, client_id=config.client_id,
            nonce=nonce, attribute_map=config.attribute_map)
        if claims.subject != identity.subject or claims.issuer != identity.issuer:
            raise AuthenticationError("step-up assertion is for a different identity")
        if not claims.mfa:
            raise AuthenticationError("step-up requires MFA evidence")
        policy = self.directory.tenant(identity.tenant_id).policy
        if self._now() - claims.auth_time > policy.stepup_freshness_seconds:
            raise AuthenticationError(
                "step-up assertion is stale: its auth_time is outside "
                "the tenant's step-up freshness window")
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

    def _deactivate_identity_core(self, identity: Identity, *, actor_id: str,
                                  reason: str, via: str) -> None:
        """The one deprovisioning mechanism (§4), whatever door drives
        it — tenant admin (E1), SCIM deactivate/delete (E3), the
        lifecycle API (E3): deactivation event, sessions revoked, keys
        closed — effective at the next request. History is untouched:
        nothing here (or anywhere) rewrites an earlier event."""
        tenant_id = identity.tenant_id
        ledger = self._tenant_ledger(tenant_id)
        identity.active = False
        ledger.record(IDENTITY_DEACTIVATED, actor_id=actor_id,
                      target=f"identity:{identity.identity_id}",
                      identity_id=identity.identity_id,
                      subject_actor_id=identity.actor_id,
                      reason=reason, via=via, at=self._now())
        n = self.directory.revoke_sessions_for(identity.identity_id)
        if n:
            ledger.record(SESSION_REVOKED, actor_id=actor_id,
                          target=f"identity:{identity.identity_id}",
                          identity_id=identity.identity_id,
                          subject_actor_id=identity.actor_id,
                          sessions_revoked=n, reason="deactivation", via=via,
                          at=self._now())
        closed = self.registry(tenant_id).close_for_identity(
            identity_id=identity.identity_id, recorded_by_actor_id=actor_id,
            reason="deactivation")
        self._note_revocations(tenant_id, closed)

    def _reactivate_identity_core(self, identity: Identity, *, actor_id: str,
                                  via: str) -> None:
        """Reactivation restores append ability PROSPECTIVELY only:
        it is its own event; sessions are not restored (the identity
        signs in again); keys stay closed (re-enrollment is the only
        way back, §3); role grants were never revoked by deactivation
        — they are separate events — so they resume as the ledger
        projects them."""
        identity.active = True
        self._tenant_ledger(identity.tenant_id).record(
            IDENTITY_REACTIVATED, actor_id=actor_id,
            target=f"identity:{identity.identity_id}",
            identity_id=identity.identity_id,
            subject_actor_id=identity.actor_id, via=via, at=self._now())

    def deactivate_identity(self, session_token: str, *, identity_id: str,
                            reason: str = "") -> None:
        """Tenant-admin deprovisioning (§4): the E1 mechanism; SCIM
        deactivate/delete (E3) drive the same core."""
        identity = self.directory.identity(identity_id)
        _, admin = self._require(session_token, authz.TENANT_MEMBER_MANAGE,
                                 tenant_id=identity.tenant_id)
        self._deactivate_identity_core(
            identity, actor_id=admin.actor_id, reason=reason, via="admin")

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
        self._guard_adjudicator_reenrollment(identity)
        self._guard_revoked_key_reenrollment(identity, public_key)
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
        self._guard_adjudicator_reenrollment(identity)
        public_key = ed25519.publickey_from_seed(bytes.fromhex(seed_hex))
        self._guard_revoked_key_reenrollment(identity, public_key)
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

    def _guard_adjudicator_reenrollment(self, identity: Identity) -> None:
        """§3 recovery rule (T522): an adjudicator whose key was
        revoked or closed re-enrolls ONLY with a tenant-admin
        countersign — self-service refuses and names the countersigned
        path. First enrollments, and enrollments while a prior key is
        merely superseded by rotation, are unaffected."""
        roles = self.roles_of(identity.identity_id, identity.tenant_id)
        if authz.ADJUDICATOR not in roles:
            return
        registry = self.registry(identity.tenant_id)
        terminal = [k for k in registry.keys_for_identity(identity.identity_id)
                    if k.status in (STATUS_REVOKED, STATUS_CLOSED)]
        if terminal:
            raise GateDenied(
                "adjudicator re-enrollment after key revocation/closure "
                "requires a tenant-admin countersign (T522)")

    def _guard_revoked_key_reenrollment(self, identity: Identity,
                                        public_key: bytes) -> None:
        """Spec 013 CLM-013-20 (red-team probe p06): a key that was
        REVOKED or CLOSED is burned — for EVERY role, not only
        adjudicators. The holder cannot quietly undo an incident-
        response revocation by re-enrolling the same public key
        through the self-service door; the way back for that exact
        key is a tenant-admin countersign (enroll_key_countersigned),
        which records the admin's judgment on the event. Enrolling
        a NEW key is unaffected: reactivation after a revocation
        proceeds with fresh key material, as §4 describes."""
        fp = fingerprint(public_key)
        existing = self.registry(identity.tenant_id).get(fp)
        if existing is not None and existing.status in (STATUS_REVOKED, STATUS_CLOSED):
            raise GateDenied(
                "this public key was revoked or closed; re-enrolling "
                "it requires a tenant-admin countersign "
                "(enroll_key_countersigned) — for every role "
                "(CLM-013-20)")

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
        # Rotation enrolls a key: the burned-key rule applies to the
        # presented key exactly as at enrollment (CLM-013-20).
        self._guard_revoked_key_reenrollment(identity, new_public_key)
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
        self._note_revocations(identity.tenant_id, 1)

    # -- API keys -----------------------------------------------------------------------------

    def issue_api_key(self, session_token: str, *, tenant_id: str,
                      principal_identity_id: str, role_class: str,
                      scopes: list[str], lifetime_seconds: float) -> tuple[ApiKeyRecord, str]:
        session, admin = self._require(session_token, authz.TENANT_KEY_MANAGE, tenant_id=tenant_id)
        # API-key issuance is a sensitive admin-plane mutation
        # (CLM-013-16/-17): fresh step-up + MFA evidence.
        self._require_admin_stepup(session, admin,
                                   action=authz.TENANT_KEY_MANAGE,
                                   tenant_id=tenant_id)
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
        self._note_revocations(tenant_id, 1)

    # -- provisioning & lifecycle (E3: T518–T524) --------------------------------
    #
    # SCIM provisions; the lifecycle core deprovisions. The SCIM
    # operations take (tenant_id, credential_id, secret) — the tenant
    # from the endpoint path, the credential from the bearer header an
    # HTTP adapter would strip — and return (status, document) in
    # RFC 7644 shapes. Refusals raise ScimError subclasses AFTER the
    # failure is ledgered (the E1/E2 refusal discipline).

    def issue_scim_token(self, session_token: str, *, tenant_id: str) -> tuple[ScimCredential, str]:
        """Issue a tenant's SCIM provisioning credential (T518). The
        secret is shown once; only its SHA-256 hash is stored (§9)."""
        _, admin = self._require(session_token, authz.TENANT_PROVISIONING_MANAGE,
                                 tenant_id=tenant_id)
        secret = _secrets.token_urlsafe(32)
        cred = ScimCredential(
            credential_id=new_prefixed_id("scim_"), tenant_id=tenant_id,
            secret_hash=hash_api_secret(secret),
            created_by_actor_id=admin.actor_id, created_at=self._now())
        self.scim.add_credential(cred)
        self._tenant_ledger(tenant_id).record(
            SCIM_TOKEN_ISSUED, actor_id=admin.actor_id,
            target=f"scim-token:{cred.credential_id}",
            credential_id=cred.credential_id, at=self._now())
        return cred, secret

    def revoke_scim_token(self, session_token: str, *, tenant_id: str,
                          credential_id: str) -> None:
        _, admin = self._require(session_token, authz.TENANT_PROVISIONING_MANAGE,
                                 tenant_id=tenant_id)
        found = self.scim.find_credential(credential_id)
        if found is None or found[0] != tenant_id:
            raise ConfigurationError(
                f"unknown SCIM credential for tenant: {credential_id}")
        found[1].revoked = True
        self._tenant_ledger(tenant_id).record(
            SCIM_TOKEN_REVOKED, actor_id=admin.actor_id,
            target=f"scim-token:{credential_id}",
            credential_id=credential_id, at=self._now())
        self._note_revocations(tenant_id, 1)

    # -- SCIM plumbing -----------------------------------------------------------

    def _record_scim_failure(self, tenant_id: str, *, actor_id: str, op: str,
                             target: str, reason: str) -> None:
        """A SCIM refusal is a record before it is a response: tenant-
        scope failures land in the addressed tenant's ledger; a
        failure addressed to a tenant that does not exist lands in
        the deployment ledger, the only scope that can carry it."""
        ledger = (self._tenant_ledger(tenant_id)
                  if tenant_id in self.directory.tenants else self.deployment_ledger)
        ledger.record(SCIM_SYNC_FAILED, actor_id=actor_id, target=target,
                      outcome="failed", op=op, reason=reason, via="scim",
                      tenant_id=tenant_id, at=self._now())

    def _scim_auth(self, tenant_id: str, credential_id: str, secret: str,
                   *, op: str) -> ScimCredential:
        actor = f"scim:{credential_id}"
        target = f"tenant:{tenant_id}"
        if tenant_id not in self.directory.tenants:
            # Spec 013 CLM-013-27 (red-team probe p17): recording the
            # failure is right; recording it WITHOUT LIMIT is a
            # ledger-growth attack — the deployment ledger is the
            # scope these records land in, and rotating tenant ids
            # or credentials must not mint unbounded history. One
            # deployment-wide bucket caps the recording rate BEFORE
            # anything is appended; past the cap the request is
            # rate-limited and nothing is recorded.
            self.rate_limiter.check(
                _UNKNOWN_TENANT_BUCKET, "scim",
                limit_per_minute=UNKNOWN_TENANT_SCIM_LIMIT_PER_MINUTE,
                now=self._now())
            self._record_scim_failure(tenant_id, actor_id=actor, op=op,
                                      target=target, reason="unknown tenant")
            raise ScimNotFoundError(f"unknown tenant: {tenant_id}")
        self._rate_guard(tenant_id, "scim")
        found = self.scim.find_credential(credential_id)
        if found is None or not _secrets.compare_digest(
                found[1].secret_hash, hash_api_secret(secret)):
            self._record_scim_failure(
                tenant_id, actor_id=actor, op=op, target=target,
                reason="unknown credential or bad secret")
            raise ScimAuthenticationError("SCIM credential authentication failed")
        owner, cred = found
        if owner != tenant_id:
            self._record_scim_failure(
                tenant_id, actor_id=actor, op=op, target=target,
                reason="credential belongs to another tenant")
            raise ScimAuthenticationError(
                "SCIM credential is not valid for this tenant")
        if cred.revoked:
            self._record_scim_failure(
                tenant_id, actor_id=actor, op=op, target=target,
                reason="credential revoked")
            raise ScimAuthenticationError("SCIM credential is revoked")
        return cred

    def _scim_ok(self, tenant_id: str, cred: ScimCredential, *, op: str,
                 target: str, identity: Optional[Identity] = None, **fields) -> None:
        extra = {}
        if identity is not None:
            extra = {"identity_id": identity.identity_id,
                     "subject_actor_id": identity.actor_id}
        self._tenant_ledger(tenant_id).record(
            SCIM_SYNC_SUCCEEDED, actor_id=f"scim:{cred.credential_id}",
            target=target, op=op, via="scim", **extra, **fields, at=self._now())

    def _scim_write(self, tenant_id: str, credential_id: str, secret: str,
                    *, op: str, target: str, fn):
        """Authenticate + run one mutating SCIM operation. Operation
        refusals are ledgered before the raise; the operations
        validate before they mutate, so a refused operation leaves
        directory state unchanged."""
        cred = self._scim_auth(tenant_id, credential_id, secret, op=op)
        try:
            return fn(cred)
        except ScimError as exc:
            self._record_scim_failure(
                tenant_id, actor_id=f"scim:{credential_id}", op=op,
                target=target, reason=exc.detail)
            raise

    # -- mapping-driven grants (T519) ----------------------------------------------

    def _scim_grant_role(self, tenant_id: str, identity: Identity, role: str,
                         *, group_ref: str, mapping_id: str) -> None:
        """A mapping-driven grant: recorded as the platform's act
        (actor "system"), naming the approved mapping that authorized
        it — never silent, always replayable."""
        self._tenant_ledger(tenant_id).record(
            ROLE_GRANTED, actor_id=SYSTEM_ACTOR,
            target=f"identity:{identity.identity_id}",
            identity_id=identity.identity_id,
            subject_actor_id=identity.actor_id, role=role, tenant_id=tenant_id,
            via="scim-group-mapping", group_ref=group_ref,
            mapping_id=mapping_id, at=self._now())

    def _scim_role_sources(self, tenant_id: str, identity: Identity,
                           role: str) -> set:
        """The sources CURRENTLY justifying (identity, role): "grant"
        when a direct (non-mapping) grant is in force per the ledger,
        plus the group_ref of each active mapping whose group the
        identity currently belongs to. Computed from present state —
        callers apply their withdrawal (member removed, mapping
        deactivated) BEFORE consulting this, so a withdrawn source
        never counts itself."""
        sources: set = set()
        direct = False
        for ev in self._tenant_ledger(tenant_id).events():
            p = ev["payload"]
            if p.get("identity_id") != identity.identity_id or p.get("role") != role:
                continue
            if ev["type"] == ROLE_GRANTED and p.get("via") != "scim-group-mapping":
                direct = True
            elif ev["type"] == ROLE_REVOKED and p.get("via") != "scim-group-mapping":
                direct = False
        if direct:
            sources.add("grant")
        state = self.scim.tenant(tenant_id)
        for m in state.mappings.values():
            if not m.active or m.role != role:
                continue
            group = self.scim.group_by_ref(tenant_id, m.group_ref)
            if group is not None and identity.identity_id in group.member_identity_ids:
                sources.add(m.group_ref)
        return sources

    def _scim_revoke_role(self, tenant_id: str, identity: Identity, role: str,
                          *, group_ref: str, reason: str) -> None:
        """Complete a mapping-source withdrawal (membership removed
        or mapping revoked — the caller has already applied it): if
        no other source still justifies the role, record the
        role.revoked event naming the mapping. Otherwise the
        membership/mapping event alone carries the change and the
        role correctly survives on its remaining source."""
        if self._scim_role_sources(tenant_id, identity, role):
            return
        self._tenant_ledger(tenant_id).record(
            ROLE_REVOKED, actor_id=SYSTEM_ACTOR,
            target=f"identity:{identity.identity_id}",
            identity_id=identity.identity_id,
            subject_actor_id=identity.actor_id, role=role, tenant_id=tenant_id,
            via="scim-group-mapping", group_ref=group_ref, reason=reason,
            at=self._now())

    def _scim_add_member(self, tenant_id: str, cred: ScimCredential,
                         group: ScimGroup, identity: Identity) -> None:
        """Add an identity to a SCIM group (directory state), record
        the membership, and apply every approved mapping as a grant."""
        group.member_identity_ids.add(identity.identity_id)
        group.updated_at = self._now()
        self._tenant_ledger(tenant_id).record(
            GROUP_MEMBERSHIP_GRANTED, actor_id=f"scim:{cred.credential_id}",
            target=f"scim-group:{group.scim_id}",
            identity_id=identity.identity_id,
            subject_actor_id=identity.actor_id, group_id=group.scim_id,
            via="scim", at=self._now())
        for mapping in self.scim.mapping_for(tenant_id, group):
            self._scim_grant_role(tenant_id, identity, mapping.role,
                                  group_ref=mapping.group_ref,
                                  mapping_id=mapping.mapping_id)

    def _scim_remove_member(self, tenant_id: str, group: ScimGroup,
                            identity: Identity, *, actor_id: str) -> None:
        group.member_identity_ids.discard(identity.identity_id)
        group.updated_at = self._now()
        self._tenant_ledger(tenant_id).record(
            GROUP_MEMBERSHIP_REVOKED, actor_id=actor_id,
            target=f"scim-group:{group.scim_id}",
            identity_id=identity.identity_id,
            subject_actor_id=identity.actor_id, group_id=group.scim_id,
            via="scim", at=self._now())
        for mapping in self.scim.mapping_for(tenant_id, group):
            self._scim_revoke_role(tenant_id, identity, mapping.role,
                                   group_ref=mapping.group_ref,
                                   reason="group membership removed")

    def _identities_of(self, tenant_id: str) -> dict:
        state = self.scim.tenant(tenant_id)
        return {u.identity_id: self.directory.identity(u.identity_id)
                for u in state.users.values()}

    def _group_or_bad_request(self, tenant_id: str, entry) -> ScimGroup:
        ref = entry.get("value") if isinstance(entry, dict) else entry
        group = self.scim.group_by_ref(tenant_id, ref) if ref else None
        if group is None:
            raise ScimBadRequestError(f"unknown group: {ref}",
                                      scim_type="invalidValue")
        return group

    # -- SCIM Users (T518) ---------------------------------------------------------

    def _scim_user_or_404(self, tenant_id: str, scim_id: str):
        state = self.scim.tenant(tenant_id)
        user = state.users.get(scim_id)
        if user is None:
            raise ScimNotFoundError(f"no such user: {scim_id}")
        return state, user, self.directory.identity(user.identity_id)

    def scim_get_user(self, tenant_id: str, credential_id: str, secret: str,
                      scim_id: str) -> tuple[int, dict]:
        self._scim_auth(tenant_id, credential_id, secret, op="user.get")
        state, user, identity = self._scim_user_or_404(tenant_id, scim_id)
        return 200, user_resource(state, user, identity)

    def scim_list_users(self, tenant_id: str, credential_id: str, secret: str,
                        *, filter_expr: Optional[str] = None, start_index: int = 1,
                        count: Optional[int] = None) -> tuple[int, dict]:
        self._scim_auth(tenant_id, credential_id, secret, op="user.list")
        state = self.scim.tenant(tenant_id)
        docs = [user_resource(state, u, self.directory.identity(u.identity_id))
                for u in sorted(state.users.values(), key=lambda u: u.scim_id)]
        if filter_expr:
            parsed = parse_filter(filter_expr)
            docs = [d for d in docs if matches_filter(d, parsed)]
        page, start = paginate(docs, start_index=start_index, count=count)
        return 200, list_response(page, total=len(docs), start_index=start)

    def scim_create_user(self, tenant_id: str, credential_id: str, secret: str,
                         doc: dict) -> tuple[int, dict]:
        return self._scim_write(
            tenant_id, credential_id, secret, op="user.create",
            target=f"tenant:{tenant_id}",
            fn=lambda cred: self._scim_create_user(tenant_id, cred, doc))

    def _scim_create_user(self, tenant_id: str, cred: ScimCredential,
                          doc: dict) -> tuple[int, dict]:
        state = self.scim.tenant(tenant_id)
        user_name = doc.get("userName")
        if not isinstance(user_name, str) or not user_name.strip():
            raise ScimBadRequestError("userName is required",
                                      scim_type="invalidValue")
        external_id = doc.get("externalId") or None
        if external_id and self.scim.user_by_external_id(tenant_id, external_id):
            raise ScimUniquenessError(f"externalId already exists: {external_id}")
        if self.scim.user_by_user_name(tenant_id, user_name):
            raise ScimUniquenessError(f"userName already exists: {user_name}")
        groups = [self._group_or_bad_request(tenant_id, g)
                  for g in doc.get("groups") or []]
        identity, created = self.directory.get_or_create_identity(
            tenant_id, SCIM_ISSUER, user_name, created_via="scim",
            display_name=display_name_of(doc), email=primary_email(doc) or "")
        reactivated = False
        if not created and not identity.active:
            # A create naming a deprovisioned identity (its SCIM
            # record was deleted) reactivates THAT identity — same
            # actor ID, same history; keys stay closed (§3).
            self._reactivate_identity_core(identity, actor_id=SYSTEM_ACTOR,
                                           via="scim")
            reactivated = True
        now = self._now()
        user = ProvisionedUser(scim_id=new_scim_id(),
                               identity_id=identity.identity_id,
                               user_name=user_name, external_id=external_id,
                               created_at=now, updated_at=now)
        self.scim.add_user(tenant_id, user)
        if created:
            self._tenant_ledger(tenant_id).record(
                IDENTITY_CREATED, actor_id=f"scim:{cred.credential_id}",
                target=f"identity:{identity.identity_id}",
                identity_id=identity.identity_id,
                subject_actor_id=identity.actor_id,
                via="scim", provisioning="scim", at=now)
        self._scim_ok(tenant_id, cred, op="user.create",
                      target=f"scim-user:{user.scim_id}", identity=identity,
                      reactivated=reactivated)
        for g in groups:
            self._scim_add_member(tenant_id, cred, g, identity)
        if doc.get("active") is False:
            self._deactivate_identity_core(
                identity, actor_id=SYSTEM_ACTOR,
                reason="scim create with active=false", via="scim")
        return 201, user_resource(state, user, identity)

    def _scim_set_user_active(self, tenant_id: str, user: ProvisionedUser,
                              identity: Identity, active: bool) -> None:
        """active transitions ride the lifecycle cores — the same
        events whatever door (SCIM PATCH/PUT/DELETE, admin) drives
        them (T521)."""
        if active and not identity.active:
            self._reactivate_identity_core(identity, actor_id=SYSTEM_ACTOR,
                                           via="scim")
        elif not active and identity.active:
            self._deactivate_identity_core(
                identity, actor_id=SYSTEM_ACTOR,
                reason="scim deactivate", via="scim")

    def _scim_apply_user_doc(self, tenant_id: str, cred: ScimCredential,
                             user: ProvisionedUser, identity: Identity,
                             doc: dict) -> None:
        """Replace semantics for the mutable profile fields. All
        collision checks run before any mutation of this user."""
        new_name = doc.get("userName", user.user_name)
        if not isinstance(new_name, str) or not new_name.strip():
            raise ScimBadRequestError("userName is required",
                                      scim_type="invalidValue")
        new_ext = doc.get("externalId") or None
        if new_ext and new_ext != user.external_id:
            holder = self.scim.user_by_external_id(tenant_id, new_ext)
            if holder is not None and holder.scim_id != user.scim_id:
                raise ScimUniquenessError(f"externalId already exists: {new_ext}")
        if (new_name.casefold() != user.user_name.casefold()
                and self.scim.user_by_user_name(tenant_id, new_name)):
            raise ScimUniquenessError(f"userName already exists: {new_name}")
        changed = []
        if new_name != user.user_name:
            self.directory.change_subject(identity, new_name)
            user.user_name = new_name
            changed.append("userName")
        if "externalId" in doc and new_ext != user.external_id:
            user.external_id = new_ext
            changed.append("externalId")
        if "displayName" in doc or "name" in doc:
            display = display_name_of(doc)
            if display != identity.display_name:
                identity.display_name = display
                changed.append("displayName")
        if "emails" in doc:
            email = primary_email(doc) or ""
            if email != identity.email:
                identity.email = email
                changed.append("emails")
        if changed:
            self._tenant_ledger(tenant_id).record(
                IDENTITY_UPDATED, actor_id=f"scim:{cred.credential_id}",
                target=f"identity:{identity.identity_id}",
                identity_id=identity.identity_id,
                subject_actor_id=identity.actor_id,
                fields=sorted(changed), via="scim", at=self._now())
        user.updated_at = self._now()

    @staticmethod
    def _profile_doc(user: ProvisionedUser, identity: Identity) -> dict:
        """The user's current profile as a SCIM document — the base a
        single-field PATCH merges into before replace semantics run."""
        doc: dict = {"userName": user.user_name,
                     "displayName": identity.display_name,
                     "emails": ([{"value": identity.email, "primary": True}]
                                if identity.email else [])}
        if user.external_id:
            doc["externalId"] = user.external_id
        return doc

    def scim_replace_user(self, tenant_id: str, credential_id: str, secret: str,
                          scim_id: str, doc: dict) -> tuple[int, dict]:
        def op(cred):
            state, user, identity = self._scim_user_or_404(tenant_id, scim_id)
            wanted = None
            if "groups" in doc:
                wanted = [self._group_or_bad_request(tenant_id, g)
                          for g in doc.get("groups") or []]
            self._scim_apply_user_doc(tenant_id, cred, user, identity, doc)
            if "active" in doc:
                self._scim_set_user_active(tenant_id, user, identity,
                                           bool(doc["active"]))
            if wanted is not None:
                wanted_ids = {g.scim_id for g in wanted}
                for g in list(state.groups.values()):
                    member = user.identity_id in g.member_identity_ids
                    if member and g.scim_id not in wanted_ids:
                        self._scim_remove_member(
                            tenant_id, g, identity,
                            actor_id=f"scim:{cred.credential_id}")
                    elif not member and g.scim_id in wanted_ids:
                        self._scim_add_member(tenant_id, cred, g, identity)
            self._scim_ok(tenant_id, cred, op="user.replace",
                          target=f"scim-user:{scim_id}", identity=identity)
            return 200, user_resource(state, user, identity)
        return self._scim_write(tenant_id, credential_id, secret,
                                op="user.replace", target=f"scim-user:{scim_id}",
                                fn=op)

    def scim_patch_user(self, tenant_id: str, credential_id: str, secret: str,
                        scim_id: str, doc: dict) -> tuple[int, dict]:
        def op(cred):
            state, user, identity = self._scim_user_or_404(tenant_id, scim_id)
            operations = doc.get("Operations")
            if not isinstance(operations, list) or not operations:
                raise ScimBadRequestError(
                    "PatchOp requires a non-empty Operations list",
                    scim_type="invalidValue")
            for operation in operations:
                self._scim_patch_user_op(tenant_id, cred, user, identity, operation)
            self._scim_ok(tenant_id, cred, op="user.patch",
                          target=f"scim-user:{scim_id}", identity=identity)
            return 200, user_resource(state, user, identity)
        return self._scim_write(tenant_id, credential_id, secret,
                                op="user.patch", target=f"scim-user:{scim_id}",
                                fn=op)

    def _scim_patch_user_op(self, tenant_id: str, cred: ScimCredential,
                            user: ProvisionedUser, identity: Identity,
                            operation) -> None:
        if not isinstance(operation, dict):
            raise ScimBadRequestError("patch operation must be an object",
                                      scim_type="invalidValue")
        action = str(operation.get("op", "")).lower()
        if action not in ("add", "remove", "replace"):
            raise ScimBadRequestError(
                f"unsupported patch op: {operation.get('op')!r}",
                scim_type="invalidValue")
        path = operation.get("path")
        value = operation.get("value")
        profile = self._profile_doc(user, identity)
        if path is None:
            if not isinstance(value, dict):
                raise ScimBadRequestError(
                    "pathless patch requires an object value",
                    scim_type="invalidValue")
            merged = {**profile, **value}
            if "active" in merged:
                self._scim_set_user_active(tenant_id, user, identity,
                                           bool(merged.pop("active")))
            self._scim_apply_user_doc(tenant_id, cred, user, identity, merged)
            return
        low = str(path).strip().casefold()
        if low == "active":
            if action == "remove":
                raise ScimBadRequestError("active cannot be removed",
                                          scim_type="invalidPath")
            self._scim_set_user_active(tenant_id, user, identity, bool(value))
        elif low == "groups":
            refs = value if isinstance(value, list) else [value]
            groups = [self._group_or_bad_request(tenant_id, e) for e in refs]
            for g in groups:
                member = user.identity_id in g.member_identity_ids
                if action == "remove":
                    if member:
                        self._scim_remove_member(
                            tenant_id, g, identity,
                            actor_id=f"scim:{cred.credential_id}")
                elif not member:
                    self._scim_add_member(tenant_id, cred, g, identity)
        elif low in ("displayname", "externalid", "username"):
            key = {"displayname": "displayName", "externalid": "externalId",
                   "username": "userName"}[low]
            if action == "remove":
                if key == "userName":
                    raise ScimBadRequestError("userName cannot be removed",
                                              scim_type="invalidPath")
                profile[key] = "" if key == "displayName" else None
            else:
                profile[key] = value
            self._scim_apply_user_doc(tenant_id, cred, user, identity, profile)
        elif low == "emails" or low.startswith("emails[") or low.startswith("emails."):
            # emails[type eq "work"].value & friends: set the primary email.
            if action == "remove":
                profile["emails"] = []
            elif isinstance(value, str):
                profile["emails"] = [{"value": value, "primary": True}]
            elif isinstance(value, list):
                profile["emails"] = value
            elif isinstance(value, dict) and value.get("value"):
                profile["emails"] = [{"value": value["value"], "primary": True}]
            else:
                raise ScimBadRequestError(f"unsupported email patch: {path}",
                                          scim_type="invalidPath")
            self._scim_apply_user_doc(tenant_id, cred, user, identity, profile)
        elif low.startswith("name."):
            part = low.split(".", 1)[1]
            if part not in ("givenname", "familyname", "formatted"):
                raise ScimBadRequestError(f"unsupported path: {path}",
                                          scim_type="invalidPath")
            if part == "formatted":
                profile["displayName"] = value or ""
            else:
                # The directory tracks one display name; a given/family
                # patch rewrites its corresponding part.
                parts = identity.display_name.split(" ", 1)
                given = parts[0] if parts else ""
                family = parts[1] if len(parts) > 1 else ""
                if part == "givenname":
                    given = value or ""
                else:
                    family = value or ""
                profile["displayName"] = " ".join(
                    p for p in (given, family) if p)
            self._scim_apply_user_doc(tenant_id, cred, user, identity, profile)
        else:
            raise ScimBadRequestError(f"unsupported path: {path}",
                                      scim_type="invalidPath")
        user.updated_at = self._now()

    def scim_delete_user(self, tenant_id: str, credential_id: str, secret: str,
                         scim_id: str) -> tuple[int, None]:
        def op(cred):
            state, user, identity = self._scim_user_or_404(tenant_id, scim_id)
            if identity.active:
                self._deactivate_identity_core(
                    identity, actor_id=SYSTEM_ACTOR,
                    reason="scim delete", via="scim")
            for g in list(state.groups.values()):
                if user.identity_id in g.member_identity_ids:
                    self._scim_remove_member(
                        tenant_id, g, identity,
                        actor_id=f"scim:{cred.credential_id}")
            self.scim.remove_user(tenant_id, user)
            self._scim_ok(tenant_id, cred, op="user.delete",
                          target=f"scim-user:{scim_id}", identity=identity)
            return 204, None
        return self._scim_write(tenant_id, credential_id, secret,
                                op="user.delete", target=f"scim-user:{scim_id}",
                                fn=op)

    # -- SCIM Groups (T518) ---------------------------------------------------------

    def _scim_group_or_404(self, tenant_id: str, scim_id: str):
        state = self.scim.tenant(tenant_id)
        group = state.groups.get(scim_id)
        if group is None:
            raise ScimNotFoundError(f"no such group: {scim_id}")
        return state, group

    def _resolve_member_ids(self, tenant_id: str, member_docs) -> list:
        """Group member refs are platform identity IDs of users
        provisioned in THIS tenant; anything else is refused before
        any state change."""
        state = self.scim.tenant(tenant_id)
        ids = []
        for entry in member_docs or []:
            ref = entry.get("value") if isinstance(entry, dict) else entry
            if ref not in state.users_by_identity:
                raise ScimBadRequestError(
                    f"group member is not a provisioned user of this tenant: {ref}",
                    scim_type="invalidValue")
            ids.append(ref)
        return ids

    def _check_group_uniqueness(self, tenant_id: str, *, display_name: str,
                                external_id: Optional[str],
                                exclude_scim_id: Optional[str] = None) -> None:
        state = self.scim.tenant(tenant_id)
        for g in state.groups.values():
            if g.scim_id == exclude_scim_id:
                continue
            if g.display_name == display_name:
                raise ScimUniquenessError(
                    f"group displayName already exists: {display_name}")
            if external_id and g.external_id == external_id:
                raise ScimUniquenessError(
                    f"group externalId already exists: {external_id}")

    def scim_get_group(self, tenant_id: str, credential_id: str, secret: str,
                       scim_id: str) -> tuple[int, dict]:
        self._scim_auth(tenant_id, credential_id, secret, op="group.get")
        state, group = self._scim_group_or_404(tenant_id, scim_id)
        return 200, group_resource(state, group, self._identities_of(tenant_id))

    def scim_list_groups(self, tenant_id: str, credential_id: str, secret: str,
                         *, filter_expr: Optional[str] = None, start_index: int = 1,
                         count: Optional[int] = None) -> tuple[int, dict]:
        self._scim_auth(tenant_id, credential_id, secret, op="group.list")
        state = self.scim.tenant(tenant_id)
        identities = self._identities_of(tenant_id)
        docs = [group_resource(state, g, identities)
                for g in sorted(state.groups.values(), key=lambda g: g.scim_id)]
        if filter_expr:
            parsed = parse_filter(filter_expr)
            docs = [d for d in docs if matches_filter(d, parsed)]
        page, start = paginate(docs, start_index=start_index, count=count)
        return 200, list_response(page, total=len(docs), start_index=start)

    def scim_create_group(self, tenant_id: str, credential_id: str, secret: str,
                          doc: dict) -> tuple[int, dict]:
        def op(cred):
            state = self.scim.tenant(tenant_id)
            display = doc.get("displayName")
            if not isinstance(display, str) or not display.strip():
                raise ScimBadRequestError("displayName is required",
                                          scim_type="invalidValue")
            external_id = doc.get("externalId") or None
            self._check_group_uniqueness(tenant_id, display_name=display,
                                         external_id=external_id)
            member_ids = self._resolve_member_ids(tenant_id, doc.get("members"))
            now = self._now()
            group = ScimGroup(scim_id=new_scim_id(), display_name=display,
                              external_id=external_id,
                              created_at=now, updated_at=now)
            self.scim.add_group(tenant_id, group)
            self._scim_ok(tenant_id, cred, op="group.create",
                          target=f"scim-group:{group.scim_id}",
                          group_id=group.scim_id)
            for iid in member_ids:
                self._scim_add_member(tenant_id, cred, group,
                                      self.directory.identity(iid))
            return 201, group_resource(state, group,
                                       self._identities_of(tenant_id))
        return self._scim_write(tenant_id, credential_id, secret,
                                op="group.create", target=f"tenant:{tenant_id}",
                                fn=op)

    def scim_replace_group(self, tenant_id: str, credential_id: str, secret: str,
                           scim_id: str, doc: dict) -> tuple[int, dict]:
        def op(cred):
            state, group = self._scim_group_or_404(tenant_id, scim_id)
            display = doc.get("displayName")
            if not isinstance(display, str) or not display.strip():
                raise ScimBadRequestError("displayName is required",
                                          scim_type="invalidValue")
            external_id = doc.get("externalId") or None
            self._check_group_uniqueness(tenant_id, display_name=display,
                                         external_id=external_id,
                                         exclude_scim_id=scim_id)
            member_ids = (self._resolve_member_ids(tenant_id, doc.get("members"))
                          if "members" in doc else None)
            group.display_name = display
            group.external_id = external_id
            group.updated_at = self._now()
            if member_ids is not None:
                wanted = set(member_ids)
                for iid in sorted(wanted - group.member_identity_ids):
                    self._scim_add_member(tenant_id, cred, group,
                                          self.directory.identity(iid))
                for iid in sorted(group.member_identity_ids - wanted):
                    self._scim_remove_member(
                        tenant_id, group, self.directory.identity(iid),
                        actor_id=f"scim:{cred.credential_id}")
            self._scim_ok(tenant_id, cred, op="group.replace",
                          target=f"scim-group:{scim_id}", group_id=scim_id)
            return 200, group_resource(state, group,
                                       self._identities_of(tenant_id))
        return self._scim_write(tenant_id, credential_id, secret,
                                op="group.replace", target=f"scim-group:{scim_id}",
                                fn=op)

    def scim_patch_group(self, tenant_id: str, credential_id: str, secret: str,
                         scim_id: str, doc: dict) -> tuple[int, dict]:
        def op(cred):
            state, group = self._scim_group_or_404(tenant_id, scim_id)
            operations = doc.get("Operations")
            if not isinstance(operations, list) or not operations:
                raise ScimBadRequestError(
                    "PatchOp requires a non-empty Operations list",
                    scim_type="invalidValue")
            for operation in operations:
                if not isinstance(operation, dict):
                    raise ScimBadRequestError("patch operation must be an object",
                                              scim_type="invalidValue")
                action = str(operation.get("op", "")).lower()
                if action not in ("add", "remove", "replace"):
                    raise ScimBadRequestError(
                        f"unsupported patch op: {operation.get('op')!r}",
                        scim_type="invalidValue")
                path = operation.get("path")
                value = operation.get("value")
                low = str(path).strip().casefold() if path else ""
                if path is None or low in ("displayname", "externalid"):
                    merged = {"displayName": group.display_name,
                              "externalId": group.external_id}
                    if path is None:
                        if not isinstance(value, dict):
                            raise ScimBadRequestError(
                                "pathless patch requires an object value",
                                scim_type="invalidValue")
                        merged.update(value)
                    elif low == "displayname":
                        merged["displayName"] = value
                    else:
                        merged["externalId"] = value
                    display = merged.get("displayName")
                    if not isinstance(display, str) or not display.strip():
                        raise ScimBadRequestError("displayName is required",
                                                  scim_type="invalidValue")
                    self._check_group_uniqueness(
                        tenant_id, display_name=display,
                        external_id=merged.get("externalId") or None,
                        exclude_scim_id=scim_id)
                    group.display_name = display
                    group.external_id = merged.get("externalId") or None
                    group.updated_at = self._now()
                elif low == "members":
                    ids = self._resolve_member_ids(
                        tenant_id, value if isinstance(value, list) else [value])
                    for iid in ids:
                        member = iid in group.member_identity_ids
                        if action == "remove":
                            if member:
                                self._scim_remove_member(
                                    tenant_id, group,
                                    self.directory.identity(iid),
                                    actor_id=f"scim:{cred.credential_id}")
                        elif not member:
                            self._scim_add_member(
                                tenant_id, cred, group,
                                self.directory.identity(iid))
                else:
                    raise ScimBadRequestError(f"unsupported path: {path}",
                                              scim_type="invalidPath")
            self._scim_ok(tenant_id, cred, op="group.patch",
                          target=f"scim-group:{scim_id}", group_id=scim_id)
            return 200, group_resource(state, group,
                                       self._identities_of(tenant_id))
        return self._scim_write(tenant_id, credential_id, secret,
                                op="group.patch", target=f"scim-group:{scim_id}",
                                fn=op)

    def scim_delete_group(self, tenant_id: str, credential_id: str, secret: str,
                          scim_id: str) -> tuple[int, None]:
        def op(cred):
            state, group = self._scim_group_or_404(tenant_id, scim_id)
            for iid in sorted(group.member_identity_ids):
                self._scim_remove_member(
                    tenant_id, group, self.directory.identity(iid),
                    actor_id=f"scim:{cred.credential_id}")
            self.scim.remove_group(tenant_id, group)
            self._scim_ok(tenant_id, cred, op="group.delete",
                          target=f"scim-group:{scim_id}", group_id=scim_id)
            return 204, None
        return self._scim_write(tenant_id, credential_id, secret,
                                op="group.delete", target=f"scim-group:{scim_id}",
                                fn=op)

    # -- group→role mapping administration (T519) -----------------------------------

    def approve_group_mapping(self, session_token: str, *, tenant_id: str,
                              group_ref: str, role: str) -> GroupRoleMapping:
        """The ONLY door from group membership to a study role: a
        tenant admin approves the mapping as a ledger event, and the
        mapping applies to current and future members. Mapping to an
        admin-plane role is refused by construction — groups grant
        study roles, never plane powers."""
        _, admin = self._require(session_token, authz.TENANT_PROVISIONING_MANAGE,
                                 tenant_id=tenant_id)
        if role not in authz.STUDY_ROLES:
            raise ConfigurationError(
                f"group mappings grant study roles only, not {role!r}")
        state = self.scim.tenant(tenant_id)
        for m in state.mappings.values():
            if m.active and m.group_ref == group_ref and m.role == role:
                return m
        mapping = GroupRoleMapping(
            mapping_id=new_prefixed_id("map_"), tenant_id=tenant_id,
            group_ref=group_ref, role=role,
            approved_by_actor_id=admin.actor_id)
        self.scim.add_mapping(mapping)
        self._tenant_ledger(tenant_id).record(
            GROUP_MAPPING_APPROVED, actor_id=admin.actor_id,
            target=f"scim-group:{group_ref}", group_ref=group_ref, role=role,
            mapping_id=mapping.mapping_id, at=self._now())
        group = self.scim.group_by_ref(tenant_id, group_ref)
        if group is not None:
            for iid in sorted(group.member_identity_ids):
                self._scim_grant_role(
                    tenant_id, self.directory.identity(iid), role,
                    group_ref=group_ref, mapping_id=mapping.mapping_id)
        return mapping

    def revoke_group_mapping(self, session_token: str, *, tenant_id: str,
                             mapping_id: str) -> None:
        _, admin = self._require(session_token, authz.TENANT_PROVISIONING_MANAGE,
                                 tenant_id=tenant_id)
        state = self.scim.tenant(tenant_id)
        mapping = state.mappings.get(mapping_id)
        if mapping is None or not mapping.active:
            raise ConfigurationError(f"unknown or inactive mapping: {mapping_id}")
        mapping.active = False
        self._tenant_ledger(tenant_id).record(
            GROUP_MAPPING_REVOKED, actor_id=admin.actor_id,
            target=f"scim-group:{mapping.group_ref}",
            group_ref=mapping.group_ref, role=mapping.role,
            mapping_id=mapping_id, at=self._now())
        group = self.scim.group_by_ref(tenant_id, mapping.group_ref)
        if group is not None:
            for iid in sorted(group.member_identity_ids):
                self._scim_revoke_role(
                    tenant_id, self.directory.identity(iid), mapping.role,
                    group_ref=mapping.group_ref,
                    reason="group mapping revoked")

    # -- lifecycle admin API (T522/T523/T524 — service layer; console is E5) ---------

    def admin_create_identity(self, session_token: str, *, tenant_id: str,
                              issuer: str, subject: str, display_name: str = "",
                              email: str = "", affiliation: str = "") -> Identity:
        """Tenant-admin membership creation (T524): an identity with
        no roles, recorded as an admin act. Assertion-created (JIT)
        and SCIM-created identities are the other doors; all three
        converge on the same identity model and the same ledger."""
        _, admin = self._require(session_token, authz.TENANT_MEMBER_MANAGE,
                                 tenant_id=tenant_id)
        if self.directory.find_identity(tenant_id, issuer, subject) is not None:
            raise ConfigurationError(
                "identity already exists for (tenant, issuer, subject)")
        ident, _ = self.directory.get_or_create_identity(
            tenant_id, issuer, subject, created_via="admin",
            display_name=display_name, email=email, affiliation=affiliation)
        self._tenant_ledger(tenant_id).record(
            IDENTITY_CREATED, actor_id=admin.actor_id,
            target=f"identity:{ident.identity_id}",
            identity_id=ident.identity_id, subject_actor_id=ident.actor_id,
            via="admin-api", at=self._now())
        return ident

    def reactivate_identity(self, session_token: str, *,
                            identity_id: str) -> Identity:
        """Tenant-admin reactivation (T524): prospective only — see
        _reactivate_identity_core for what is NOT restored."""
        identity = self.directory.identity(identity_id)
        _, admin = self._require(session_token, authz.TENANT_MEMBER_MANAGE,
                                 tenant_id=identity.tenant_id)
        if identity.active:
            raise ConfigurationError("identity is already active")
        self._reactivate_identity_core(identity, actor_id=admin.actor_id,
                                       via="admin")
        return identity

    def enroll_key_countersigned(self, admin_session_token: str, *,
                                 identity_id: str, public_key: bytes,
                                 proof_signature: bytes, nonce: str,
                                 custody: str = "self") -> KeyRecord:
        """Countersigned re-enrollment: the subject proves
        possession of the key (nonce from their own
        begin_enrollment); a tenant admin countersigns — the
        enrollment event names both actors. This path exists for
        exactly the cases self-service refuses: an adjudicator
        re-enrolling after a revocation/closure (T522, §3), and —
        Spec 013 CLM-013-20 — ANY identity re-enrolling a public
        key that was itself revoked or closed, where an admin's
        recorded judgment is what un-burns the key. Ordinary
        first enrollments of fresh keys are not this path's
        business and are refused here, as before."""
        identity = self.directory.identity(identity_id)
        _, admin = self._require(admin_session_token, authz.TENANT_KEY_MANAGE,
                                 tenant_id=identity.tenant_id)
        if not identity.active:
            raise GateDenied("cannot enroll keys for a deactivated identity")
        registry = self.registry(identity.tenant_id)
        existing = registry.get(fingerprint(public_key))
        key_is_burned = existing is not None and \
            existing.status in (STATUS_REVOKED, STATUS_CLOSED)
        if authz.ADJUDICATOR not in self.roles_of(identity_id, identity.tenant_id) \
                and not key_is_burned:
            raise ConfigurationError(
                "countersigned enrollment is the re-enrollment path "
                "for adjudicators and for revoked/closed keys; other "
                "identities enroll fresh keys through their own session")
        return self.registry(identity.tenant_id).enroll(
            identity_id=identity_id, actor_id=identity.actor_id,
            public_key=public_key, custody=custody,
            proof_signature=proof_signature, nonce=nonce,
            recorded_by_actor_id=admin.actor_id,
            countersigned_by_actor_id=admin.actor_id)

    def sweep_identity_keys(self, session_token: str, *,
                            identity_id: str) -> int:
        """The deprovisioned-identity key sweep (T522): close any key
        a deactivation left accepted. Refuses for active identities —
        closing a live identity's keys is revocation, a different
        recorded act, not a sweep."""
        identity = self.directory.identity(identity_id)
        _, admin = self._require(session_token, authz.TENANT_KEY_MANAGE,
                                 tenant_id=identity.tenant_id)
        if identity.active:
            raise ConfigurationError(
                "key sweep applies to deprovisioned identities")
        closed = self.registry(identity.tenant_id).close_for_identity(
            identity_id=identity_id, recorded_by_actor_id=admin.actor_id,
            reason="deprovision-sweep")
        self._note_revocations(identity.tenant_id, closed)
        return closed

    def erase_directory_pii(self, session_token: str, *,
                            identity_id: str) -> bool:
        """Directory erasure under a legal duty (T523): the off-ledger
        directory forgets the identity (PII blanked, login lookup
        dropped, SCIM record dropped); the ledgers — which never
        carried PII — are untouched, and this erasure event is the
        only new record. Deprovisioned identities only: erasing a
        live identity's directory entry would orphan its sessions."""
        identity = self.directory.identity(identity_id)
        tenant_id = identity.tenant_id
        _, admin = self._require(session_token, authz.TENANT_MEMBER_MANAGE,
                                 tenant_id=tenant_id)
        if identity.active:
            raise ConfigurationError(
                "directory erasure applies to deactivated identities "
                "(deprovision first)")
        hold = self._active_hold(tenant_id)
        if hold is not None:
            # E6 (T545): a legal hold freezes the erasure path for
            # the held scope — preservation is the hold's whole
            # point. Recorded before the raise, like every refusal.
            self._tenant_ledger(tenant_id).record(
                LEGAL_HOLD_ENFORCED, actor_id=admin.actor_id,
                target=f"identity:{identity_id}", outcome="refused",
                action="identity.pii_erasure", hold_id=hold["hold_id"],
                reason="an active legal hold covers this tenant; "
                       "erasure is refused while the hold stands (T545)",
                at=self._now())
            raise ConfigurationError(
                f"directory erasure refused: legal hold {hold['hold_id']} "
                "is active for this tenant (T545)")
        self.scim.forget_identity(tenant_id, identity_id)
        erased = self.directory.erase_identity_pii(identity_id)
        self._tenant_ledger(tenant_id).record(
            DIRECTORY_PII_ERASED, actor_id=admin.actor_id,
            target=f"identity:{identity_id}",
            identity_id=identity_id, subject_actor_id=identity.actor_id,
            at=self._now())
        return erased

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
        self._rate_guard(tenant_id, "append.session")
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
        if not ed25519.is_prime_order_key(bytes.fromhex(rec.public_key_hex)):
            # Defense in depth for CLM-013-21: enrollment refuses
            # small-order keys, and an append under one — however it
            # reached the registry — is refused here too.
            raise self._deny_append(tenant_id, identity.actor_id, action,
                                    "enrolled key is not in the prime-order "
                                    "subgroup (small-order keys are refused)")
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
        self._rate_guard(tenant_id, "append.api")
        ledger = self._tenant_ledger(tenant_id)
        record = self.directory.find_api_key(key_id, secret)
        if record is None or record.tenant_id != tenant_id:
            ledger.record(AUTH_APIKEY_FAILED, actor_id="unknown", target=f"apikey:{key_id}",
                          outcome="failed", reason="unknown key or bad secret", at=self._now())
            self._note_auth_failure(tenant_id)
            raise GateDenied("API key authentication failed")
        if record.revoked:
            ledger.record(AUTH_APIKEY_FAILED, actor_id="unknown", target=f"apikey:{key_id}",
                          outcome="failed", reason="key revoked", at=self._now())
            self._note_auth_failure(tenant_id)
            raise GateDenied("API key is revoked")
        if record.expires_at <= self._now():
            ledger.record(AUTH_APIKEY_FAILED, actor_id="unknown", target=f"apikey:{key_id}",
                          outcome="failed", reason="key expired", at=self._now())
            self._note_auth_failure(tenant_id)
            raise GateDenied("API key is expired")
        principal = self.directory.identity(record.principal_identity_id)
        if not principal.active:
            raise self._deny_append(tenant_id, principal.actor_id, action,
                                    "API key principal is deactivated")
        if action not in record.scopes:
            raise self._deny_append(tenant_id, principal.actor_id, action,
                                    f"action {action} outside API key scopes")
        if action in authz.VERDICT_CLASS_ACTIONS:
            # Spec 013 CLM-013-15 (red-team probe p04): verdict-class
            # appends require an enrolled-key intent signature and a
            # fresh step-up on EVERY path (§2/§3). An API key has no
            # session, no step-up, and no enrolled key — a bearer key
            # alone can never issue a verdict, whatever scopes it was
            # issued with. Non-verdict appends are unaffected.
            raise self._deny_append(
                tenant_id, principal.actor_id, action,
                "verdict-class appends require an enrolled-key intent "
                "signature and a fresh step-up; a bearer API key alone "
                "cannot issue a verdict (CLM-013-15)")
        record.last_used_at = self._now()
        return AppendAuthorization(
            identity=principal, role_basis=record.role_class,
            key_fingerprint=None, custody="api_key",
            session_id=None, api_key_id=key_id)

    # -- break-glass (E4: T529) ----------------------------------------------------
    #
    # The mechanism of §5, per breakglass.py's rules. Declaration is a
    # tenant-admin act (tenant.policy_manage); invocation mints a
    # PENDING session; a second authorizer — never the invoker —
    # activates it; actions run only inside the declared scopes and
    # the time box; every step is a marked event in BOTH the tenant's
    # ledger and the deployment ledger (the platform security log).

    #: The scopes a declaration may name: tenant-admin actions for
    #: which a break-glass operation exists. Declaring a scope the
    #: mechanism cannot exercise is refused at declaration — the
    #: declaration never promises what the mechanism cannot do.
    BREAKGLASS_SCOPES = frozenset({
        authz.TENANT_AUDIT_EXPORT, authz.TENANT_MEMBER_MANAGE,
        authz.TENANT_KEY_MANAGE,
    })

    def _bg_record(self, tenant_id: str, event_type: str, *, actor_id: str,
                   bg: Optional[BreakGlassSession] = None,
                   outcome: str = "ok", **fields) -> None:
        """A break-glass event is recorded in the tenant's own ledger
        AND the deployment security log, marked as break-glass."""
        marked = {"break_glass": True, "tenant_id": tenant_id, **fields}
        if bg is not None:
            marked["bg_session_id"] = bg.bg_session_id
        # A caller may name the acted-on target (the break-glass
        # action event does); it is the record's target, not a field.
        target = marked.pop("target", None) or (
            f"breakglass:{bg.bg_session_id}" if bg is not None
            else f"tenant:{tenant_id}")
        self._tenant_ledger(tenant_id).record(
            event_type, actor_id=actor_id, target=target, outcome=outcome,
            at=self._now(), **marked)
        self.deployment_ledger.record(
            event_type, actor_id=actor_id, target=target, outcome=outcome,
            at=self._now(), **marked)

    def declare_break_glass_policy(self, session_token: str, *, tenant_id: str,
                                   invoker_roles: list, second_authorizer_plane: str,
                                   max_duration_seconds: float,
                                   scopes: list) -> BreakGlassPolicy:
        """Declare (or re-declare) a tenant's break-glass policy.
        Until this act exists, break-glass cannot be invoked for the
        tenant — by construction (the wireframe's undeclared state)."""
        session, admin = self._require(session_token, authz.TENANT_POLICY_MANAGE,
                                       tenant_id=tenant_id)
        # Policy declaration is a sensitive admin-plane mutation
        # (CLM-013-16/-17): fresh step-up + MFA evidence.
        self._require_admin_stepup(session, admin,
                                   action=authz.TENANT_POLICY_MANAGE,
                                   tenant_id=tenant_id)
        if second_authorizer_plane not in AUTHORIZER_PLANES:
            raise ConfigurationError(
                f"second authorizer must be one of {AUTHORIZER_PLANES}")
        if not (0 < max_duration_seconds <= BREAKGLASS_MAX_DURATION_SECONDS):
            raise ConfigurationError(
                f"break-glass time box must be within (0, {BREAKGLASS_MAX_DURATION_SECONDS}] "
                "seconds — the 4h ceiling is not configurable up")
        bad_scopes = set(scopes) - self.BREAKGLASS_SCOPES
        if bad_scopes or not scopes:
            raise ConfigurationError(
                f"break-glass scopes must be a non-empty subset of "
                f"{sorted(self.BREAKGLASS_SCOPES)}; refused: {sorted(bad_scopes)}")
        bad_roles = set(invoker_roles) - authz.ALL_GRANTABLE_ROLES
        if bad_roles or not invoker_roles:
            raise ConfigurationError(
                f"invoker roles must be grantable roles; refused: {sorted(bad_roles)}")
        policy = BreakGlassPolicy(
            tenant_id=tenant_id, invoker_roles=tuple(invoker_roles),
            second_authorizer_plane=second_authorizer_plane,
            max_duration_seconds=float(max_duration_seconds),
            scopes=tuple(scopes), declared_by_actor_id=admin.actor_id,
            declared_at=self._now())
        self.directory.break_glass_policies[tenant_id] = policy
        self._tenant_ledger(tenant_id).record(
            BREAKGLASS_POLICY_DECLARED, actor_id=admin.actor_id,
            target=f"tenant:{tenant_id}", tenant_id=tenant_id,
            invoker_roles=list(policy.invoker_roles),
            second_authorizer_plane=second_authorizer_plane,
            max_duration_seconds=int(max_duration_seconds),
            scopes=list(policy.scopes), at=self._now())
        return policy

    def revoke_break_glass_policy(self, session_token: str, *,
                                  tenant_id: str) -> None:
        """Withdraw a tenant's declaration. Pending sessions are
        denied and active sessions closed on the spot — revocation
        never leaves a live session behind."""
        session, admin = self._require(session_token, authz.TENANT_POLICY_MANAGE,
                                       tenant_id=tenant_id)
        self._require_admin_stepup(session, admin,
                                   action=authz.TENANT_POLICY_MANAGE,
                                   tenant_id=tenant_id)
        policy = self.directory.break_glass_policies.get(tenant_id)
        if policy is None or not policy.active:
            raise ConfigurationError(f"no active break-glass policy for {tenant_id}")
        policy.active = False
        self._tenant_ledger(tenant_id).record(
            BREAKGLASS_POLICY_REVOKED, actor_id=admin.actor_id,
            target=f"tenant:{tenant_id}", tenant_id=tenant_id, at=self._now())
        for bg in list(self.directory.break_glass_sessions.values()):
            if bg.tenant_id != tenant_id:
                continue
            self._touch_bg_session(bg)
            if bg.state == STATE_PENDING:
                bg.state = STATE_DENIED
                self._bg_record(tenant_id, BREAKGLASS_AUTHORIZATION_DENIED,
                                actor_id=admin.actor_id, bg=bg, outcome="denied",
                                reason="policy revoked")
            elif bg.state == STATE_ACTIVE:
                self._close_bg_session(bg, state=STATE_CLOSED,
                                       reason="policy revoked",
                                       actor_id=admin.actor_id)

    def invoke_break_glass(self, session_token: str, *, tenant_id: str,
                           reason: str, duration_seconds: float) -> BreakGlassSession:
        """Mint a PENDING break-glass session. Refusals — no policy,
        wrong invoker role, oversized box — are recorded before the
        raise, in the tenant's ledger and the deployment log."""
        self._rate_guard(tenant_id, "breakglass")
        _, invoker = self._resolve_session(session_token)

        def refuse(message: str) -> GateDenied:
            fields = {"reason": message, "break_glass": True, "tenant_id": tenant_id}
            ledger = (self._tenant_ledger(tenant_id)
                      if tenant_id in self.directory.tenants
                      else self.deployment_ledger)
            ledger.record(BREAKGLASS_INVOCATION_REFUSED, actor_id=invoker.actor_id,
                          target=f"tenant:{tenant_id}", outcome="denied",
                          at=self._now(), **fields)
            if tenant_id in self.directory.tenants:
                self.deployment_ledger.record(
                    BREAKGLASS_INVOCATION_REFUSED, actor_id=invoker.actor_id,
                    target=f"tenant:{tenant_id}", outcome="denied",
                    at=self._now(), **fields)
            return GateDenied(message)

        policy = self.directory.break_glass_policies.get(tenant_id)
        if policy is None or not policy.active:
            raise refuse(
                f"break-glass cannot be invoked for tenant {tenant_id}: "
                "no policy declared")
        # Spec 013 CLM-013-22 (red-team probe p09): each declared
        # invoker role is checked in ITS OWN scope — a tenant role
        # counts only as granted in the TARGET tenant's ledger, the
        # platform role only on the platform plane. A role held in
        # some OTHER tenant (the probe's cross-tenant union) counts
        # for nothing here. (The authorizer check below already
        # scoped its plane this way; invocation now matches.)
        def _holds_in_scope(role: str) -> bool:
            if role == authz.PLATFORM_ADMIN:
                return role in self.roles_of(invoker.identity_id, None)
            return role in self.roles_of(invoker.identity_id, tenant_id)
        if not any(_holds_in_scope(r) for r in policy.invoker_roles):
            raise refuse(
                f"invoker holds none of the declared invoker roles "
                f"{sorted(policy.invoker_roles)} in tenant {tenant_id}'s scope")
        if not (0 < duration_seconds <= policy.max_duration_seconds):
            raise refuse(
                f"requested time box {duration_seconds}s is outside the "
                f"declared maximum {policy.max_duration_seconds}s")
        bg = BreakGlassSession(
            bg_session_id="bg_" + _secrets.token_hex(8), tenant_id=tenant_id,
            invoker_identity_id=invoker.identity_id,
            invoker_actor_id=invoker.actor_id, reason=reason,
            requested_duration_seconds=float(duration_seconds),
            invoked_at=self._now())
        self.directory.break_glass_sessions[bg.bg_session_id] = bg
        self._bg_record(tenant_id, BREAKGLASS_INVOKED, actor_id=invoker.actor_id,
                        bg=bg, reason=reason,
                        requested_duration_seconds=int(duration_seconds))
        return bg

    def _bg_authorizer_check(self, session_token: str,
                             bg: BreakGlassSession) -> Identity:
        """Eligibility for authorizing/denying/closing: the caller
        holds the DECLARED authorizer plane's role and is not the
        invoker. Failures are recorded before the raise."""
        _, authorizer = self._resolve_session(session_token)
        policy = self.directory.break_glass_policies.get(bg.tenant_id)

        def deny(message: str) -> GateDenied:
            self._bg_record(bg.tenant_id, BREAKGLASS_AUTHORIZATION_DENIED,
                            actor_id=authorizer.actor_id, bg=bg,
                            outcome="denied", reason=message)
            return GateDenied(message)

        if policy is None or not policy.active:
            raise deny("the tenant's break-glass policy is no longer active")
        if authorizer.identity_id == bg.invoker_identity_id:
            raise deny("the invoker cannot authorize their own break-glass "
                       "session — a second authorizer is required")
        if policy.second_authorizer_plane == AUTHORIZER_PLATFORM:
            eligible = authz.PLATFORM_ADMIN in self.roles_of(
                authorizer.identity_id, None)
        else:
            eligible = authz.TENANT_ADMIN in self.roles_of(
                authorizer.identity_id, bg.tenant_id)
        if not eligible:
            raise deny(
                f"second authorizer must hold the declared plane's role "
                f"({policy.second_authorizer_plane})")
        return authorizer

    def authorize_break_glass(self, session_token: str, *,
                              bg_session_id: str) -> BreakGlassSession:
        """The second authorization: activates the session and starts
        its time box. This act is the 'use' T554 egresses."""
        bg = self.directory.break_glass_sessions.get(bg_session_id)
        if bg is None:
            raise ConfigurationError(f"unknown break-glass session: {bg_session_id}")
        authorizer = self._bg_authorizer_check(session_token, bg)
        if bg.state != STATE_PENDING:
            self._bg_record(bg.tenant_id, BREAKGLASS_AUTHORIZATION_DENIED,
                            actor_id=authorizer.actor_id, bg=bg,
                            outcome="denied",
                            reason=f"session is {bg.state}, not pending")
            raise GateDenied(f"break-glass session is {bg.state}, not pending")
        policy = self.directory.break_glass_policies[bg.tenant_id]
        now = self._now()
        bg.state = STATE_ACTIVE
        bg.authorized_by_actor_id = authorizer.actor_id
        bg.authorized_by_identity_id = authorizer.identity_id
        bg.authorized_at = now
        bg.expires_at = now + min(bg.requested_duration_seconds,
                                  policy.max_duration_seconds)
        self._bg_record(bg.tenant_id, BREAKGLASS_AUTHORIZED,
                        actor_id=authorizer.actor_id, bg=bg,
                        invoker_actor_id=bg.invoker_actor_id,
                        expires_at=int(bg.expires_at))
        self._emit_security_event(bg.tenant_id, SEC_BREAK_GLASS_USE, {
            "tenant_id": bg.tenant_id, "bg_session_id": bg.bg_session_id,
            "invoker_actor_id": bg.invoker_actor_id,
            "authorized_by_actor_id": authorizer.actor_id,
            "expires_at": int(bg.expires_at),
        })
        return bg

    def deny_break_glass(self, session_token: str, *, bg_session_id: str,
                         note: str = "") -> BreakGlassSession:
        bg = self.directory.break_glass_sessions.get(bg_session_id)
        if bg is None:
            raise ConfigurationError(f"unknown break-glass session: {bg_session_id}")
        authorizer = self._bg_authorizer_check(session_token, bg)
        if bg.state != STATE_PENDING:
            raise GateDenied(f"break-glass session is {bg.state}, not pending")
        bg.state = STATE_DENIED
        self._bg_record(bg.tenant_id, BREAKGLASS_AUTHORIZATION_DENIED,
                        actor_id=authorizer.actor_id, bg=bg, outcome="denied",
                        reason=note or "second authorizer refused")
        return bg

    def _touch_bg_session(self, bg: BreakGlassSession) -> None:
        """Expiry is lazy and total: the first touch after the box
        runs out closes the session (with its review item) before
        anything else can use it."""
        if (bg.state == STATE_ACTIVE and bg.expires_at is not None
                and self._now() >= bg.expires_at):
            self._close_bg_session(bg, state=STATE_EXPIRED,
                                   reason="time box exhausted",
                                   actor_id=bg.invoker_actor_id)

    def _close_bg_session(self, bg: BreakGlassSession, *, state: str,
                          reason: str, actor_id: str) -> None:
        bg.state = state
        bg.closed_at = self._now()
        bg.close_reason = reason
        self._bg_record(bg.tenant_id, BREAKGLASS_SESSION_CLOSED,
                        actor_id=actor_id, bg=bg, close_reason=reason,
                        actions_taken=bg.actions_taken)
        # The post-use review item is created automatically (§5) —
        # an appended record naming the session and its action count;
        # its disposition is a tenant admin's recorded act.
        bg.review_item_id = "bgr_" + _secrets.token_hex(6)
        self._bg_record(bg.tenant_id, BREAKGLASS_REVIEW_CREATED,
                        actor_id=actor_id, bg=bg,
                        review_item_id=bg.review_item_id,
                        actions_taken=bg.actions_taken)

    def close_break_glass(self, session_token: str, *,
                          bg_session_id: str) -> BreakGlassSession:
        """End an active session early: the invoker, or an eligible
        second authorizer. No silent extension exists anywhere in
        this mechanism — a longer need is a new session."""
        bg = self.directory.break_glass_sessions.get(bg_session_id)
        if bg is None:
            raise ConfigurationError(f"unknown break-glass session: {bg_session_id}")
        self._touch_bg_session(bg)
        _, caller = self._resolve_session(session_token)
        if caller.identity_id == bg.invoker_identity_id:
            actor_id = caller.actor_id
        else:
            self._bg_authorizer_check(session_token, bg)
            actor_id = caller.actor_id
        if bg.state != STATE_ACTIVE:
            raise GateDenied(f"break-glass session is {bg.state}, not active")
        self._close_bg_session(bg, state=STATE_CLOSED,
                               reason="closed by invoker or authorizer",
                               actor_id=actor_id)
        return bg

    def break_glass_act(self, bg_session_id: str, *, session_token: str,
                        action: str, **kwargs):
        """Exercise one declared-scope action under an active
        break-glass session. The tenant comes from the session —
        never from a parameter (T526 discipline) — and every act,
        granted or refused, is a marked event in both ledgers.

        Spec 013 CLM-013-22 (red-team probe p09): acting requires
        presenting a session credential AT ACT TIME, and it must be
        the INVOKER's — a bare break-glass session id (a uuid in two
        ledgers) is a bearer token for tenant-admin powers no
        longer. A credential belonging to anyone else is refused
        and recorded under the caller's own actor id."""
        bg = self.directory.break_glass_sessions.get(bg_session_id)
        if bg is None:
            self.deployment_ledger.record(
                BREAKGLASS_ACTION_REFUSED, actor_id="unknown",
                target=f"breakglass:{bg_session_id}", outcome="denied",
                break_glass=True, reason="unknown break-glass session",
                at=self._now())
            raise GateDenied(f"unknown break-glass session: {bg_session_id}")
        self._rate_guard(bg.tenant_id, "breakglass")
        self._touch_bg_session(bg)
        _, actor = self._resolve_session(session_token)
        if actor.identity_id != bg.invoker_identity_id:
            self._bg_record(
                bg.tenant_id, BREAKGLASS_ACTION_REFUSED,
                actor_id=actor.actor_id, bg=bg, outcome="denied",
                action=action,
                reason="the act-time session credential does not "
                       "belong to the break-glass invoker (CLM-013-22)")
            raise GateDenied(
                "break-glass actions require the invoker's own "
                "session credential at act time (CLM-013-22)")

        def refuse(message: str) -> GateDenied:
            self._bg_record(bg.tenant_id, BREAKGLASS_ACTION_REFUSED,
                            actor_id=bg.invoker_actor_id, bg=bg,
                            outcome="denied", action=action, reason=message)
            return GateDenied(message)

        if bg.state != STATE_ACTIVE:
            raise refuse(f"break-glass session is {bg.state}, not active")
        policy = self.directory.break_glass_policies.get(bg.tenant_id)
        if policy is None or not policy.active:
            raise refuse("the tenant's break-glass policy is no longer active")
        if action not in policy.scopes:
            raise refuse(
                f"action {action} is outside the declared break-glass "
                f"scopes {sorted(policy.scopes)}")
        result = None
        if action == authz.TENANT_AUDIT_EXPORT:
            # Spec 013 CLM-013-24 (red-team probe p11): the legal
            # hold's access restriction binds EVERY export path —
            # break-glass is an emergency door into the same records,
            # not an exemption from a preservation order. The
            # platform-plane exception in export_tenant_audit does
            # not extend here: this act is exercised in the tenant's
            # name, under the tenant's own declaration.
            hold = self._active_hold(bg.tenant_id)
            if hold is not None:
                raise refuse(
                    f"legal hold {hold['hold_id']} covers tenant "
                    "audit export; the hold binds the break-glass "
                    "path too (CLM-013-24)")
            result = self._tenant_ledger(bg.tenant_id).events()
            target = f"tenant:{bg.tenant_id}"
        elif action == authz.TENANT_MEMBER_MANAGE:
            identity = self.directory.identity(kwargs["identity_id"])
            if identity.tenant_id != bg.tenant_id:
                raise refuse("target identity belongs to another tenant")
            self._deactivate_identity_core(
                identity, actor_id=bg.invoker_actor_id,
                reason=kwargs.get("reason", "break-glass"), via="break-glass")
            target = f"identity:{identity.identity_id}"
        elif action == authz.TENANT_KEY_MANAGE:
            fp = kwargs["key_fingerprint"]
            registry = self.registry(bg.tenant_id)
            if registry.get(fp) is None:
                raise refuse(f"unknown key for this tenant: {fp}")
            registry.revoke(fp=fp, recorded_by_actor_id=bg.invoker_actor_id,
                            reason=kwargs.get("reason", "break-glass"))
            self._note_revocations(bg.tenant_id, 1)
            target = f"key:{fp}"
        else:  # pragma: no cover — declaration validation keeps scopes implementable
            raise refuse(f"no break-glass operation implements {action}")
        bg.actions_taken += 1
        self._bg_record(bg.tenant_id, BREAKGLASS_ACTION,
                        actor_id=bg.invoker_actor_id, bg=bg,
                        action=action, target=target)
        return result

    def break_glass_state(self, session_token: str, *, tenant_id: str) -> dict:
        """The tenant's break-glass posture: current policy (or the
        honest undeclared state) + its sessions. This is the data the
        console's break-glass screen (E5) renders.

        Spec 013 CLM-013-23 (red-team probe p10): like every
        service-layer read, this requires an authenticated identity
        with audit access to the tenant — it is not callable
        credential-free."""
        self._require_audit_access(session_token, tenant_id)
        for bg in self.directory.break_glass_sessions.values():
            if bg.tenant_id == tenant_id:
                self._touch_bg_session(bg)
        policy = self.directory.break_glass_policies.get(tenant_id)
        return {
            "tenant_id": tenant_id,
            "policy": policy if (policy is not None and policy.active) else None,
            "sessions": [bg for bg in self.directory.break_glass_sessions.values()
                         if bg.tenant_id == tenant_id],
        }

    def record_break_glass_review(self, session_token: str, *, tenant_id: str,
                                  bg_session_id: str, disposition: str,
                                  note: str = "") -> None:
        """The post-use review's disposition: a tenant admin records
        it against the automatically created review item. The item is
        completable exactly once."""
        _, admin = self._require(session_token, authz.TENANT_AUDIT_EXPORT,
                                 tenant_id=tenant_id)
        bg = self.directory.break_glass_sessions.get(bg_session_id)
        if bg is None or bg.tenant_id != tenant_id or bg.review_item_id is None:
            raise ConfigurationError(
                f"no break-glass review item for session {bg_session_id}")
        if bg.review_completed:
            raise ConfigurationError("break-glass review already completed")
        bg.review_completed = True
        self._bg_record(tenant_id, BREAKGLASS_REVIEW_COMPLETED,
                        actor_id=admin.actor_id, bg=bg,
                        review_item_id=bg.review_item_id,
                        disposition=disposition, note=note)

    # -- webhook egress (E4: T531) ------------------------------------------------
    #
    # Subscription administration is a policy act: tenant admins
    # manage their tenant's egress under tenant.policy_manage;
    # platform-plane subscriptions (keyed to the platform tenant) are
    # platform.config_manage. Secrets are shown exactly once (HMAC)
    # or published as a public key (Ed25519); ledgers carry
    # fingerprints only (T502 discipline).

    def _webhook_door(self, session_token: str, tenant_id: str) -> Identity:
        if tenant_id == PLATFORM_TENANT_ID:
            _, admin = self._require(session_token, authz.PLATFORM_CONFIG_MANAGE,
                                     tenant_id=None)
            return admin
        _, admin = self._require(session_token, authz.TENANT_POLICY_MANAGE,
                                 tenant_id=tenant_id)
        return admin

    def _webhook_scope_ledger(self, tenant_id: str) -> PlatformLedger:
        return (self.deployment_ledger if tenant_id == PLATFORM_TENANT_ID
                else self._tenant_ledger(tenant_id))

    def register_webhook(self, session_token: str, *, tenant_id: str, url: str,
                         signing: str, event_classes: list) -> tuple[WebhookSubscription, Optional[str]]:
        """Register an egress endpoint. Returns (subscription,
        shown_once_secret) — the secret only in HMAC mode, only here."""
        admin = self._webhook_door(session_token, tenant_id)
        if signing not in SIGNING_MODES:
            raise ConfigurationError(f"unknown webhook signing mode: {signing}")
        posture, _ = tls_posture(url)
        if posture != "serve":
            raise ConfigurationError(
                "webhook URL must be https — signed payloads do not egress "
                "over plain HTTP (§9)")
        if not event_classes:
            raise ConfigurationError("a webhook subscription names at least one event class")
        sub_id = "wh_" + _secrets.token_hex(6)
        shown_once: Optional[str] = None
        fields: dict = {}
        if signing == SIGNING_HMAC_SHA256:
            secret = _secrets.token_urlsafe(32)
            ref = f"webhook-secret:{tenant_id}:{sub_id}"
            self.secrets.put(ref, secret)
            sub = WebhookSubscription(
                subscription_id=sub_id, tenant_id=tenant_id, url=url,
                signing=signing, event_classes=tuple(event_classes),
                secret_ref=ref, secret_fingerprint=hash_api_secret(secret),
                created_by_actor_id=admin.actor_id)
            fields["secret_fingerprint"] = sub.secret_fingerprint
            shown_once = secret
        else:
            seed = _secrets.token_bytes(32)
            ref = f"webhook-key:{tenant_id}:{sub_id}"
            self.secrets.put(ref, seed.hex())
            public_hex = ed25519.publickey_from_seed(seed).hex()
            sub = WebhookSubscription(
                subscription_id=sub_id, tenant_id=tenant_id, url=url,
                signing=signing, event_classes=tuple(event_classes),
                signing_key_ref=ref, signing_public_key_hex=public_hex,
                created_by_actor_id=admin.actor_id)
            fields["signing_public_key"] = public_hex
        self.directory.webhook_subscriptions[sub_id] = sub
        self._webhook_scope_ledger(tenant_id).record(
            WEBHOOK_SUBSCRIPTION_CREATED, actor_id=admin.actor_id,
            target=f"webhook:{sub_id}", subscription_id=sub_id, url=url,
            signing=signing, event_classes=list(event_classes),
            at=self._now(), **fields)
        return sub, shown_once

    def revoke_webhook(self, session_token: str, *, tenant_id: str,
                       subscription_id: str) -> None:
        admin = self._webhook_door(session_token, tenant_id)
        sub = self.directory.webhook_subscriptions.get(subscription_id)
        if sub is None or sub.tenant_id != tenant_id:
            raise ConfigurationError(
                f"unknown webhook subscription for tenant: {subscription_id}")
        sub.active = False
        self._webhook_scope_ledger(tenant_id).record(
            WEBHOOK_SUBSCRIPTION_REVOKED, actor_id=admin.actor_id,
            target=f"webhook:{subscription_id}", subscription_id=subscription_id,
            at=self._now())

    def send_webhook_test(self, session_token: str, *, tenant_id: str,
                          subscription_id: str) -> list[str]:
        """The operational probe: queue a signed test delivery to one
        subscription. Returns the queued delivery ids."""
        admin = self._webhook_door(session_token, tenant_id)
        sub = self.directory.webhook_subscriptions.get(subscription_id)
        if sub is None or sub.tenant_id != tenant_id or not sub.active:
            raise ConfigurationError(
                f"unknown or inactive webhook subscription: {subscription_id}")
        before = set(self._deliveries)
        self._egress(tenant_id, EVENT_TEST, {
            "probe": True, "subscription_id": subscription_id,
            "by_actor_id": admin.actor_id,
        })
        return [d for d in self._deliveries if d not in before
                and self._deliveries[d].subscription_id == subscription_id]

    def pending_deliveries(self, session_token: str, *,
                           tenant_id: Optional[str] = None) -> list[Delivery]:
        """The egress queue's pending deliveries (Spec 013
        CLM-013-23: an authenticated read, like every other). The
        platform plane sees the whole queue (or one tenant's slice);
        a tenant-plane caller sees only their own tenant's
        deliveries — the queue is operational data about other
        tenants' egress otherwise."""
        _, identity = self._resolve_session(session_token)
        try:
            self._require(session_token, authz.PLATFORM_CONFIG_MANAGE,
                          tenant_id=None)
            scope = tenant_id  # platform plane: any tenant, or all
        except AuthorizationDenied:
            if tenant_id is not None and tenant_id != identity.tenant_id:
                raise AuthorizationDenied(
                    "pending deliveries of another tenant are not "
                    "visible from this session")
            scope = identity.tenant_id
        return [d for d in self._deliveries.values()
                if d.state == "pending"
                and (scope is None or d.tenant_id == scope)]

    def deliver_webhooks(self, transport) -> list[Delivery]:
        """Attempt every due delivery once. `transport(url, body,
        headers) -> int` is injected (no sockets here — the HTTP
        adapter supplies the real one). Every attempt's outcome is a
        platform audit event in the subscription tenant's scope."""
        attempted: list[Delivery] = []
        now = self._now()
        for delivery in list(self._deliveries.values()):
            if delivery.state != "pending" or delivery.next_attempt_at > now:
                continue
            delivery.attempts += 1
            status: Optional[int] = None
            error = ""
            try:
                status = transport(self._subscription_url(delivery),
                                   delivery.body, delivery.headers)
            except Exception as exc:  # transport failure is data, not a crash
                error = f"{type(exc).__name__}: {exc}"
            ledger = self._webhook_scope_ledger(delivery.tenant_id)
            if status is not None and 200 <= status < 300:
                delivery.state = "delivered"
                delivery.last_status = status
                ledger.record(WEBHOOK_DELIVERY_SUCCEEDED,
                              actor_id="system",
                              target=f"webhook:{delivery.subscription_id}",
                              outcome="ok", delivery_id=delivery.delivery_id,
                              delivery_event_type=delivery.event_type,
                              attempt=delivery.attempts, status=status,
                              at=self._now())
            else:
                delivery.last_status = status
                delivery.last_error = error
                exhausted = delivery.attempts >= MAX_ATTEMPTS
                if exhausted:
                    delivery.state = "failed"
                else:
                    delivery.next_attempt_at = (
                        self._now() + BACKOFF_SECONDS[delivery.attempts - 1])
                ledger.record(WEBHOOK_DELIVERY_FAILED,
                              actor_id="system",
                              target=f"webhook:{delivery.subscription_id}",
                              outcome="failed", delivery_id=delivery.delivery_id,
                              delivery_event_type=delivery.event_type,
                              attempt=delivery.attempts, status=status,
                              error=error, exhausted=exhausted,
                              at=self._now())
            attempted.append(delivery)
        return attempted

    def _subscription_url(self, delivery: Delivery) -> str:
        sub = self.directory.webhook_subscriptions.get(delivery.subscription_id)
        return sub.url if sub is not None else ""

    # -- audit reads, verification, reconciliation (E4: T526/T532) ----------------
    #
    # The review half of CLM-005-26 + the join of CLM-005-22. Reads
    # are plane-checked like every other surface: a tenant's audit
    # record is readable by that tenant's audit-export role (and its
    # verification walkable by the platform plane) — never by another
    # tenant, never by a study role.

    def _require_audit_access(self, session_token: str, tenant_id: str) -> Identity:
        try:
            _, admin = self._require(session_token, authz.TENANT_AUDIT_EXPORT,
                                     tenant_id=tenant_id)
            return admin
        except AuthorizationDenied:
            _, admin = self._require(session_token, authz.PLATFORM_CONFIG_MANAGE,
                                     tenant_id=None)
            return admin

    def read_tenant_audit(self, session_token: str, *, tenant_id: str,
                          event_type: Optional[str] = None) -> list:
        """The tenant's complete platform audit record — its own
        ledger, nothing of any other tenant's (the §8 split)."""
        self._require_audit_access(session_token, tenant_id)
        events = self._tenant_ledger(tenant_id).events()
        if event_type is not None:
            events = [e for e in events if e["type"] == event_type]
        return events

    def read_deployment_audit(self, session_token: str, *,
                              event_type: Optional[str] = None) -> list:
        _, admin = self._require(session_token, authz.PLATFORM_CONFIG_MANAGE,
                                 tenant_id=None)
        events = self.deployment_ledger.events()
        if event_type is not None:
            events = [e for e in events if e["type"] == event_type]
        return events

    @staticmethod
    def _verification_dict(verification) -> dict:
        return {
            "ok": bool(getattr(verification, "ok", False)),
            "events": getattr(verification, "events", None),
            "break_seq": getattr(verification, "break_seq", None),
            "reason": getattr(verification, "reason", None),
            # The signature state rides along (Axiomere Spec 003):
            # how many signatures were checked, and which events
            # carry none — an unsigned stretch of the record is a
            # visible state in this result, never a silent pass.
            "signatures_checked": getattr(verification, "signatures_checked", None),
            "signatures_failed": getattr(verification, "signatures_failed", None),
            "unsigned_events": list(getattr(verification, "unsigned_events", ()) or ()),
            "untrusted_actors": list(getattr(verification, "untrusted_actors", ()) or ()),
        }

    def _verify_honestly(self, ledger: PlatformLedger) -> dict:
        """A chain result, or — for a ledger too damaged to read — an
        honest failure dict. Verification never raises on damage:
        damage IS the finding."""
        try:
            return self._verification_dict(ledger.verify())
        except Exception as exc:  # noqa: BLE001 — reported, not hidden
            return {"ok": False, "events": None, "break_seq": None,
                    "reason": f"ledger unreadable: {type(exc).__name__}: {exc}",
                    "signatures_checked": None, "signatures_failed": None,
                    "unsigned_events": [], "untrusted_actors": []}

    def verify_tenant_audit(self, session_token: str, *,
                            tenant_id: str) -> dict:
        """Chain-verify a tenant's platform ledger. The result is
        returned honestly either way (a broken chain is a finding,
        not an exception) — and a failure is a T554 security event."""
        self._require_audit_access(session_token, tenant_id)
        result = self._verify_honestly(self._tenant_ledger(tenant_id))
        if not result["ok"]:
            data = {
                "scope": "tenant", "tenant_id": tenant_id,
                "break_seq": result["break_seq"], "reason": result["reason"],
            }
            try:
                self._emit_security_event(
                    tenant_id, SEC_AUDIT_VERIFICATION_FAILURE, data)
            except Exception:  # noqa: BLE001 — the tenant ledger itself is damaged
                # The finding still lands — in the deployment log,
                # which is intact and is the platform security record.
                self.deployment_ledger.record(
                    SECURITY_EVENT_EMITTED, actor_id="system",
                    target="security:audit_verification_failure",
                    outcome="emitted",
                    event_class=SEC_AUDIT_VERIFICATION_FAILURE,
                    at=self._now())
                self._egress(tenant_id, SEC_AUDIT_VERIFICATION_FAILURE, data)
        return result

    def verify_deployment_audit(self, session_token: str) -> dict:
        _, admin = self._require(session_token, authz.PLATFORM_CONFIG_MANAGE,
                                 tenant_id=None)
        result = self._verify_honestly(self.deployment_ledger)
        if not result["ok"]:
            self._emit_security_event(PLATFORM_TENANT_ID,
                                      SEC_AUDIT_VERIFICATION_FAILURE, {
                                          "scope": "deployment",
                                          "break_seq": result["break_seq"],
                                          "reason": result["reason"],
                                      })
        return result

    def reconcile_actor(self, session_token: str, *, tenant_id: str,
                        actor_id: str, study_events: list) -> dict:
        """The CLM-005-22 walk: join one actor's platform-plane events
        to their study-ledger appends on the identity↔key binding.

        A study append pairs only if its attribution names this actor
        AND its signing key is (or was) enrolled to this identity —
        historical keys pair; another identity's key NEVER pairs, and
        an append claiming this actor under a foreign key is reported
        as a key mismatch, not silently dropped. Appends with no
        attribution pair on the ledger envelope actor (checkpoint
        class). `study_events` are the study ledger's event dicts,
        supplied by the caller — the platform↔study seam is data,
        exactly as the export pattern carries it (E6 anchors it)."""
        self._require_audit_access(session_token, tenant_id)
        identity = None
        for ident in self.directory.identities.values():
            if ident.actor_id == actor_id and ident.tenant_id == tenant_id:
                identity = ident
                break
        registry = self.registry(tenant_id)
        bindings = []
        own_fps: dict[str, str] = {}     # fingerprint -> owning identity_id
        if identity is not None:
            for rec in registry.keys_for_identity(identity.identity_id):
                bindings.append({
                    "key_fingerprint": rec.fingerprint, "status": rec.status,
                    "custody": rec.custody,
                })
                own_fps[rec.fingerprint] = identity.identity_id
        platform_events = []
        for ev in self._tenant_ledger(tenant_id).events():
            p = ev["payload"]
            if p.get("actor_id") == actor_id or p.get("subject_actor_id") == actor_id:
                platform_events.append(ev)
        paired, mismatches, unpaired = [], [], []
        for ev in study_events:
            payload = ev.get("payload") or {}
            attribution = payload.get("attribution")
            if not isinstance(attribution, dict):
                content = payload.get("content")
                if isinstance(content, dict):
                    attribution = content.get("attribution")
            attribution = attribution if isinstance(attribution, dict) else {}
            ev_actor = attribution.get("actor_id") or ev.get("actor")
            fp = attribution.get("key_fingerprint")
            if ev_actor != actor_id:
                unpaired.append({"event": ev, "why": "another actor"})
                continue
            if fp is not None and identity is not None and fp not in own_fps:
                holder = registry.get(fp)
                if holder is not None:
                    mismatches.append({
                        "event": ev,
                        "why": "key enrolled to a different identity",
                        "key_fingerprint": fp,
                    })
                    continue
                unpaired.append({"event": ev, "why": "key not enrolled in this tenant"})
                continue
            if fp is not None and identity is None:
                unpaired.append({"event": ev, "why": "actor has no identity in this tenant"})
                continue
            paired.append(ev)
        return {
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "identity": ({"identity_id": identity.identity_id,
                          "tenant_id": identity.tenant_id}
                         if identity is not None else None),
            "bindings": bindings,
            "platform_events": platform_events,
            "paired_appends": paired,
            "key_mismatches": mismatches,
            "unpaired_appends": unpaired,
        }

    # -- compliance evidence (E6: T541–T545, T551–T553) --------------------
    #
    # The evidence machinery the compliance wireframe depicts:
    # residency pin (T541), audit export + anchor (T542/T543),
    # legal hold (T545), CUI marking (T551), SPRS-input control
    # states (T552), and the POA&M register (T553). Scope discipline
    # matches the rest of the platform: tenant-scope compliance is
    # the tenant admin's plane (tenant.compliance_manage), the
    # deployment scope is the platform plane's; reads ride the
    # audit-access rule. Every write is a ledger event; every
    # attributable refusal is ledgered before it is raised.

    def _scope_ledger(self, tenant_id: Optional[str]) -> PlatformLedger:
        return self.deployment_ledger if tenant_id is None \
            else self._tenant_ledger(tenant_id)

    def _scope_ledger_path(self, tenant_id: Optional[str]) -> Path:
        return self.root / "deployment.axmr" if tenant_id is None \
            else self.root / f"tenant-{tenant_id}.axmr"

    def _require_compliance_write(self, session_token: str,
                                  tenant_id: Optional[str]) -> Identity:
        if tenant_id is None:
            _, admin = self._require(
                session_token, authz.PLATFORM_CONFIG_MANAGE, tenant_id=None)
            return admin
        try:
            _, admin = self._require(
                session_token, authz.TENANT_COMPLIANCE_MANAGE, tenant_id=tenant_id)
            return admin
        except AuthorizationDenied:
            _, admin = self._require(
                session_token, authz.PLATFORM_CONFIG_MANAGE, tenant_id=None)
            return admin

    # -- CUI marking (T551) ----------------------------------------------

    def set_tenant_marking(self, session_token: str, tenant_id: str, *,
                           category: Optional[str],
                           authority: Optional[str] = None,
                           dissemination: Optional[str] = None) -> dict:
        """Record (or clear, with category=None) the tenant's CUI
        marking fields. The platform records markings; it does not
        adjudicate them — the recorded values are the tenant's."""
        admin = self._require_compliance_write(session_token, tenant_id)
        tenant = self.directory.tenant(tenant_id)
        tenant.cui_marking = (
            {"category": category, "authority": authority,
             "dissemination": dissemination}
            if category else None)
        self.deployment_ledger.record(
            TENANT_MARKING_UPDATED, actor_id=admin.actor_id,
            target=f"tenant:{tenant_id}", tenant_id=tenant_id,
            category=category, authority=authority,
            dissemination=dissemination, at=self._now())
        return tenant.cui_marking or {"status": "unmarked"}

    # -- residency pin (T541) ----------------------------------------------

    def residency_pin(self, session_token: str, tenant_id: str) -> dict:
        """The tenant's recorded pin: shape + region as recorded at
        creation, plus the migration history (pin changes exist
        only as migration events — there is no other write path).
        An authenticated read (Spec 013 CLM-013-23): audit access
        to the tenant, as for the tenant's other record reads."""
        self._require_audit_access(session_token, tenant_id)
        tenant = self.directory.tenant(tenant_id)
        migrations = [
            e for e in self.deployment_ledger.events()
            if e["type"] == TENANT_RESIDENCY_MIGRATED
            and e["payload"].get("tenant_id") == tenant_id
        ]
        return {
            "tenant_id": tenant_id, "shape": tenant.shape,
            "region": tenant.region, "migrations": len(migrations),
            "last_migration_seq": migrations[-1]["seq"] if migrations else None,
        }

    def change_residency_pin(self, session_token: str, *, tenant_id: str,
                             shape: str, region: Optional[str]) -> dict:
        """The T541 flow, enforced: an anchored audit export of the
        tenant's own ledger must exist before the pin moves; the
        move itself is a migration event in both ledgers, carrying
        the export that authorized it. A held tenant's pin does not
        move at all."""
        _, admin = self._require(session_token, authz.PLATFORM_TENANT_MANAGE,
                                 tenant_id=None)
        tenant = self.directory.tenant(tenant_id)

        def refuse(reason: str) -> ConfigurationError:
            self.deployment_ledger.record(
                TENANT_RESIDENCY_CHANGE_REFUSED, actor_id=admin.actor_id,
                target=f"tenant:{tenant_id}", tenant_id=tenant_id,
                outcome="refused", reason=reason, at=self._now())
            return ConfigurationError(reason)

        if self._active_hold(tenant_id) is not None:
            raise refuse("a legal hold is active for this tenant; the "
                         "residency pin does not move under a hold (T545)")
        tenant_events = self._tenant_ledger(tenant_id).events()
        exported = {e["payload"].get("export_id") for e in tenant_events
                    if e["type"] == AUDIT_EXPORTED}
        anchored = {e["payload"].get("export_id") for e in tenant_events
                    if e["type"] == AUDIT_EXPORT_ANCHORED}
        ready = exported & anchored
        if not ready:
            raise refuse("residency pin change requires an anchored audit "
                         "export of the tenant's ledger first "
                         "(export + anchor + migration, T541)")
        export_id = sorted(ready)[-1]
        fields = dict(
            tenant_id=tenant_id, old_shape=tenant.shape,
            old_region=tenant.region, new_shape=shape, new_region=region,
            export_id=export_id)
        tenant.shape, tenant.region = shape, region
        self.deployment_ledger.record(
            TENANT_RESIDENCY_MIGRATED, actor_id=admin.actor_id,
            target=f"tenant:{tenant_id}", at=self._now(), **fields)
        self._tenant_ledger(tenant_id).record(
            TENANT_RESIDENCY_MIGRATED, actor_id=admin.actor_id,
            target=f"tenant:{tenant_id}", at=self._now(), **fields)
        return self.residency_pin(session_token, tenant_id)

    # -- audit export + anchor (T542/T543) ---------------------------------

    def _export_scope_audit(self, admin: Identity, tenant_id: Optional[str],
                            out_dir: str) -> dict:
        ledger = self._scope_ledger(tenant_id)
        ledger.checkpoint(actor_id=admin.actor_id)
        store = ControlStateStore(ledger)
        sprs = store.sprs_report() if store.is_seeded() else None
        marking = None
        if tenant_id is not None:
            marking = self.directory.tenant(tenant_id).cui_marking
        try:
            manifest = export_platform_audit(
                ledger, str(self._scope_ledger_path(tenant_id)), out_dir,
                marking=marking,
                poam_document=PoamRegister(ledger).register_document(),
                sprs_report=sprs)
        except ValueError as exc:
            raise ConfigurationError(str(exc)) from exc
        export_id = f"exp-{manifest['bundle_hash'][:12]}"
        ledger.record(
            AUDIT_EXPORTED, actor_id=admin.actor_id, target=f"export:{export_id}",
            export_id=export_id, bundle_hash=manifest["bundle_hash"],
            event_count=manifest["ledger"]["event_count"],
            marking_status=manifest["cui_marking"]["status"], at=self._now())
        return {**manifest, "export_id": export_id}

    def export_tenant_audit(self, session_token: str, tenant_id: str,
                            out_dir: str) -> dict:
        """Export one tenant's audit ledger in the Phase 5 bundle
        pattern (T542). While a legal hold covers the tenant, the
        tenant plane may not export — the platform plane may (the
        hold restricts access; it does not strand the record)."""
        try:
            _, admin = self._require(
                session_token, authz.TENANT_AUDIT_EXPORT, tenant_id=tenant_id)
            tenant_plane = True
        except AuthorizationDenied:
            _, admin = self._require(
                session_token, authz.PLATFORM_CONFIG_MANAGE, tenant_id=None)
            tenant_plane = False
        hold = self._active_hold(tenant_id)
        if hold is not None and tenant_plane:
            self._tenant_ledger(tenant_id).record(
                LEGAL_HOLD_ENFORCED, actor_id=admin.actor_id,
                target=f"tenant:{tenant_id}", outcome="refused",
                action="audit.export", hold_id=hold["hold_id"],
                reason="an active legal hold restricts tenant-plane "
                       "audit export; the platform plane retains "
                       "export access (T545)",
                at=self._now())
            raise AuthorizationDenied(
                f"audit export refused: legal hold {hold['hold_id']} "
                "restricts tenant-plane export while it stands")
        return self._export_scope_audit(admin, tenant_id, out_dir)

    def export_deployment_audit(self, session_token: str, out_dir: str) -> dict:
        """Export the deployment (platform-plane) audit ledger —
        the platform's own record, POA&M register included."""
        _, admin = self._require(
            session_token, authz.PLATFORM_CONFIG_MANAGE, tenant_id=None)
        return self._export_scope_audit(admin, None, out_dir)

    def _record_anchor(self, admin: Identity, tenant_id: Optional[str], *,
                       export_id: str, mechanism: str, ref: str,
                       uri: str = "") -> dict:
        return self._scope_ledger(tenant_id).record(
            AUDIT_EXPORT_ANCHORED, actor_id=admin.actor_id,
            target=f"export:{export_id}", export_id=export_id,
            mechanism=mechanism, ref=ref, uri=uri, at=self._now())

    def record_export_anchor(self, session_token: str, *,
                             tenant_id: Optional[str] = None,
                             export_id: str, mechanism: str, ref: str,
                             uri: str = "") -> dict:
        """Record that an export was anchored — the receipt fields
        of wherever the export's hash now also lives (T543). The
        anchor record is what a later standalone verification is
        checked against; the platform records receipts, and the
        receipt's truth is the anchor target's, verifiable there."""
        admin = self._require_compliance_write(session_token, tenant_id)
        known = {e["payload"].get("export_id")
                 for e in self._scope_ledger(tenant_id).events()
                 if e["type"] == AUDIT_EXPORTED}
        if export_id not in known:
            raise ConfigurationError(
                f"no audit export {export_id!r} recorded for this scope")
        return self._record_anchor(
            admin, tenant_id, export_id=export_id, mechanism=mechanism,
            ref=ref, uri=uri)

    # -- retention & legal hold (T545) --------------------------------------

    def _active_hold(self, tenant_id: Optional[str]) -> Optional[dict]:
        """The scope's active hold, by replay: a hold stands from
        its placed event until its released event. Holds are
        markers — the replay is their only state."""
        active: dict[str, dict] = {}
        for event in self._scope_ledger(tenant_id).events():
            payload = event["payload"]
            if event["type"] == LEGAL_HOLD_PLACED:
                active[payload["hold_id"]] = {
                    "hold_id": payload["hold_id"],
                    "scope_ref": payload.get("scope_ref"),
                    "reason": payload.get("reason"),
                    "authority": payload.get("authority"),
                    "export_id": payload.get("export_id"),
                    "placed_seq": event["seq"],
                    "placed_by": payload.get("actor_id"),
                }
            elif event["type"] == LEGAL_HOLD_RELEASED:
                active.pop(payload["hold_id"], None)
        if not active:
            return None
        return next(iter(active.values()))

    def active_holds(self, session_token: str, *,
                     tenant_id: Optional[str] = None) -> list[dict]:
        """The scope's active legal holds (Spec 013 CLM-013-23: an
        authenticated read — hold state is compliance data, not
        public posture). Tenant scope rides the audit-access rule;
        the deployment scope requires the platform plane."""
        if tenant_id is None:
            self._require(session_token, authz.PLATFORM_CONFIG_MANAGE,
                          tenant_id=None)
        else:
            self._require_audit_access(session_token, tenant_id)
        hold = self._active_hold(tenant_id)
        return [hold] if hold is not None else []

    def place_legal_hold(self, session_token: str, *,
                         tenant_id: Optional[str] = None, scope_ref: str,
                         reason: str, authority: str, out_dir: str) -> dict:
        """Place a hold: export the held scope, anchor the export
        record, and append the hold marker naming both (T545's
        flow — marker + export + anchor + access restriction; the
        restriction is enforced at the erasure, pin-change, and
        tenant-plane export surfaces). Nothing about a hold ever
        deletes or masks ledger content."""
        admin = self._require_compliance_write(session_token, tenant_id)
        if self._active_hold(tenant_id) is not None:
            raise ConfigurationError(
                "a legal hold is already active for this scope")
        manifest = self._export_scope_audit(admin, tenant_id, out_dir)
        self._record_anchor(
            admin, tenant_id, export_id=manifest["export_id"],
            mechanism="legal-hold-snapshot", ref=manifest["bundle_hash"])
        ledger = self._scope_ledger(tenant_id)
        number = sum(1 for e in ledger.events()
                     if e["type"] == LEGAL_HOLD_PLACED) + 1
        hold_id = f"HOLD-{number:04d}"
        ledger.record(
            LEGAL_HOLD_PLACED, actor_id=admin.actor_id,
            target=f"hold:{hold_id}", hold_id=hold_id, scope_ref=scope_ref,
            reason=reason, authority=authority,
            export_id=manifest["export_id"],
            bundle_hash=manifest["bundle_hash"], at=self._now())
        return {"hold_id": hold_id, "export_id": manifest["export_id"],
                "bundle_hash": manifest["bundle_hash"]}

    def release_legal_hold(self, session_token: str, *,
                           tenant_id: Optional[str] = None, hold_id: str,
                           note: str = "") -> dict:
        """Release a hold — itself an appended event; the hold's
        history (placed, enforced, released) stays in the record."""
        admin = self._require_compliance_write(session_token, tenant_id)
        hold = self._active_hold(tenant_id)
        if hold is None or hold["hold_id"] != hold_id:
            raise ConfigurationError(f"no active legal hold {hold_id!r} "
                                     "for this scope")
        return self._scope_ledger(tenant_id).record(
            LEGAL_HOLD_RELEASED, actor_id=admin.actor_id,
            target=f"hold:{hold_id}", hold_id=hold_id, note=note,
            at=self._now())

    # -- SPRS-input control states (T552) ------------------------------------

    def seed_control_states(self, session_token: str, *,
                            tenant_id: Optional[str] = None) -> bool:
        admin = self._require_compliance_write(session_token, tenant_id)
        return ControlStateStore(self._scope_ledger(tenant_id)).ensure_seeded(
            actor_id=admin.actor_id)

    def set_control_state(self, session_token: str, *,
                          tenant_id: Optional[str] = None,
                          requirement: str, state: str,
                          evidence_link: Optional[str] = None,
                          gap_marker: Optional[str] = None,
                          note: str = "") -> dict:
        admin = self._require_compliance_write(session_token, tenant_id)
        ledger = self._scope_ledger(tenant_id)
        store = ControlStateStore(ledger)
        if not store.is_seeded():
            raise ConfigurationError(
                "control states are not seeded for this scope — "
                "seed_control_states first (the seed is a recorded act)")
        try:
            return store.set_state(
                actor_id=admin.actor_id, requirement=requirement,
                state=state, evidence_link=evidence_link,
                gap_marker=gap_marker, note=note)
        except ValueError as exc:
            ledger.record(
                COMPLIANCE_STATE_SET_REFUSED, actor_id=admin.actor_id,
                target=f"requirement:{requirement}", outcome="refused",
                requirement=requirement, reason=str(exc), at=self._now())
            raise ConfigurationError(str(exc)) from exc

    def sprs_report(self, session_token: str, *,
                    tenant_id: Optional[str] = None) -> dict:
        """The scope's SPRS-input record + computed score. A report
        is computed from recorded inputs only; the platform never
        submits it — submission is the operator's act."""
        if tenant_id is None:
            self._require(session_token, authz.PLATFORM_CONFIG_MANAGE,
                          tenant_id=None)
        else:
            self._require_audit_access(session_token, tenant_id)
        store = ControlStateStore(self._scope_ledger(tenant_id))
        if not store.is_seeded():
            raise ConfigurationError(
                "control states are not seeded for this scope")
        return store.sprs_report()

    # -- POA&M register (T553) ------------------------------------------------

    def _poam(self, tenant_id: Optional[str]) -> PoamRegister:
        return PoamRegister(self._scope_ledger(tenant_id))

    def seed_poam_fips_item(self, session_token: str) -> Optional[str]:
        """Seed the deployment register with the §3.13.11 item
        exactly as the records carry it (T553)."""
        _, admin = self._require(
            session_token, authz.PLATFORM_CONFIG_MANAGE, tenant_id=None)
        return self._poam(None).seed_fips_item(actor_id=admin.actor_id)

    def poam_create_item(self, session_token: str, *,
                         tenant_id: Optional[str] = None, title: str,
                         weakness: str, affected_requirements: list,
                         source_ref: str, owner: str = "") -> str:
        admin = self._require_compliance_write(session_token, tenant_id)
        try:
            return self._poam(tenant_id).create_item(
                actor_id=admin.actor_id, title=title, weakness=weakness,
                affected_requirements=affected_requirements,
                source_ref=source_ref, owner=owner)
        except ValueError as exc:
            raise ConfigurationError(str(exc)) from exc

    def poam_add_milestone(self, session_token: str, *,
                           tenant_id: Optional[str] = None, item_id: str,
                           text: str, due: str = "") -> str:
        admin = self._require_compliance_write(session_token, tenant_id)
        try:
            return self._poam(tenant_id).add_milestone(
                actor_id=admin.actor_id, item_id=item_id, text=text, due=due)
        except ValueError as exc:
            raise ConfigurationError(str(exc)) from exc

    def poam_complete_milestone(self, session_token: str, *,
                                tenant_id: Optional[str] = None,
                                item_id: str, milestone_id: str,
                                note: str = "") -> dict:
        admin = self._require_compliance_write(session_token, tenant_id)
        try:
            return self._poam(tenant_id).complete_milestone(
                actor_id=admin.actor_id, item_id=item_id,
                milestone_id=milestone_id, note=note)
        except ValueError as exc:
            raise ConfigurationError(str(exc)) from exc

    def poam_set_status(self, session_token: str, *,
                        tenant_id: Optional[str] = None, item_id: str,
                        status: str, note: str = "") -> dict:
        admin = self._require_compliance_write(session_token, tenant_id)
        try:
            return self._poam(tenant_id).set_status(
                actor_id=admin.actor_id, item_id=item_id, status=status,
                note=note)
        except ValueError as exc:
            raise ConfigurationError(str(exc)) from exc

    def poam_register_document(self, session_token: str, *,
                               tenant_id: Optional[str] = None) -> dict:
        if tenant_id is None:
            self._require(session_token, authz.PLATFORM_CONFIG_MANAGE,
                          tenant_id=None)
        else:
            self._require_audit_access(session_token, tenant_id)
        return self._poam(tenant_id).register_document()
