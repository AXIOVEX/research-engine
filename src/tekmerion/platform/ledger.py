"""Platform audit ledger (Spec 005 §8, T510) — Axiomere, like every
other record in this program (DN-007). Two scopes, per the spec:

- the **deployment ledger** carries platform-plane events (tenant
  lifecycle, platform configuration, platform-admin grants);
- one **per-tenant ledger** carries that tenant's admin-plane and
  identity events, so a tenant's complete record exports without
  disclosing another tenant's (the AU/CMMC split, §13.2).

Event payloads carry the AU content set (§13.4): actor (random actor
ID, never PII — §4), event type, UTC timestamp, target, outcome.
Every E1 mutation and authentication path records its event *here*;
an action with no event is a defect (T550 sweep is the check).

Payload discipline (found in E1 testing, 2026-10-12): **no raw
high-precision floats in payloads.** Some f64 values (e.g.
1791810119.6349843) do not round-trip between Python's repr and the
record layer's serializer, and an event carrying one fails hash
verification on reopen — the chain reads as broken though nothing
tampered with it. Timestamps are therefore whole-second UTC here,
and callers must not put unrounded floats in payload fields either.
(Finding reported for the Axiomere side; the record layer itself is
out of this spec's scope to change.)
"""

from __future__ import annotations

import time
from typing import Any, Optional

try:
    import axiomere
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "tekmerion.platform requires the axiomere package (DN-007)"
    ) from exc


# -- event vocabulary (E1 core; E3/E4 extend, never rename) -------------

TENANT_CREATED = "tenant.created"
TENANT_UPDATED = "tenant.updated"
PLATFORM_BOOTSTRAPPED = "platform.bootstrapped"
IDP_CONFIGURED = "idp.configured"
IDP_UPDATED = "idp.updated"
IDENTITY_CREATED = "identity.created"
IDENTITY_UPDATED = "identity.updated"
IDENTITY_DEACTIVATED = "identity.deactivated"
IDENTITY_REACTIVATED = "identity.reactivated"
DIRECTORY_PII_ERASED = "identity.pii_erased"
SCIM_SYNC_SUCCEEDED = "scim.sync_succeeded"
SCIM_SYNC_FAILED = "scim.sync_failed"
SCIM_TOKEN_ISSUED = "scim.token_issued"
SCIM_TOKEN_REVOKED = "scim.token_revoked"
GROUP_MAPPING_APPROVED = "scim.group_mapping_approved"
GROUP_MAPPING_REVOKED = "scim.group_mapping_revoked"
GROUP_MEMBERSHIP_GRANTED = "scim.group_membership_granted"
GROUP_MEMBERSHIP_REVOKED = "scim.group_membership_revoked"
AUTH_LOGIN_SUCCEEDED = "auth.login_succeeded"
AUTH_LOGIN_FAILED = "auth.login_failed"
AUTH_LOGOUT = "auth.logout"
AUTH_STEPUP = "auth.stepup"
AUTH_APIKEY_FAILED = "auth.apikey_failed"
AUTHZ_DENIED = "authz.decision_denied"
ROLE_GRANTED = "role.granted"
ROLE_REVOKED = "role.revoked"
KEY_ENROLLED = "key.enrolled"
KEY_ROTATED = "key.rotated"
KEY_REVOKED = "key.revoked"
KEY_CLOSED = "key.closed"
APIKEY_ISSUED = "apikey.issued"
APIKEY_REVOKED = "apikey.revoked"
SESSION_REVOKED = "session.revoked"

# -- E4 vocabulary (T526–T533, T554): tenancy hardening ------------------
# Break-glass (T529): the mechanism's whole lifecycle. Every event of
# a break-glass session is *marked* — payloads carry break_glass=True
# plus the session id — and the tenant-scope events land in BOTH the
# tenant's ledger (the tenant's own record of what touched it) and
# the deployment ledger (the platform security log).
BREAKGLASS_POLICY_DECLARED = "breakglass.policy_declared"
BREAKGLASS_POLICY_REVOKED = "breakglass.policy_revoked"
BREAKGLASS_INVOKED = "breakglass.invoked"
BREAKGLASS_INVOCATION_REFUSED = "breakglass.invocation_refused"
BREAKGLASS_AUTHORIZED = "breakglass.authorized"
BREAKGLASS_AUTHORIZATION_DENIED = "breakglass.authorization_denied"
BREAKGLASS_ACTION = "breakglass.action"
BREAKGLASS_ACTION_REFUSED = "breakglass.action_refused"
BREAKGLASS_SESSION_CLOSED = "breakglass.session_closed"
BREAKGLASS_REVIEW_CREATED = "breakglass.review_created"
BREAKGLASS_REVIEW_COMPLETED = "breakglass.review_completed"
# Webhook egress (T531): subscription management + delivery outcomes.
WEBHOOK_SUBSCRIPTION_CREATED = "webhook.subscription_created"
WEBHOOK_SUBSCRIPTION_REVOKED = "webhook.subscription_revoked"
WEBHOOK_DELIVERY_SUCCEEDED = "webhook.delivery_succeeded"
WEBHOOK_DELIVERY_FAILED = "webhook.delivery_failed"
# Security-event emission (T554): a detector fired and the event was
# egressed over the webhook channel; the emission itself is a record.
SECURITY_EVENT_EMITTED = "security.event_emitted"
# Rate limiting (T530): a per-tenant limit tripped; §6's recorded stop.
RATE_LIMIT_EXCEEDED = "ratelimit.exceeded"

#: The §3.3.1/§3.3.2 event classes the CMMC amendment (T550) requires
#: the ledger to be able to evidence. The T550 sweep test asserts each
#: class is exercised by the E1 surface.
AU_EVENT_CLASSES = {
    "account_creation": {IDENTITY_CREATED},
    "account_modification": {
        IDENTITY_UPDATED, IDENTITY_DEACTIVATED, IDENTITY_REACTIVATED,
        ROLE_GRANTED, ROLE_REVOKED, SCIM_SYNC_SUCCEEDED, DIRECTORY_PII_ERASED,
    },
    "authentication_success": {AUTH_LOGIN_SUCCEEDED},
    "authentication_failure": {AUTH_LOGIN_FAILED, AUTH_APIKEY_FAILED},
    "authorization_decision_denial": {AUTHZ_DENIED},
    "administrative_action": {
        TENANT_CREATED, TENANT_UPDATED, IDP_CONFIGURED, IDP_UPDATED,
        PLATFORM_BOOTSTRAPPED, APIKEY_ISSUED, APIKEY_REVOKED, SESSION_REVOKED,
        IDENTITY_REACTIVATED, DIRECTORY_PII_ERASED,
        SCIM_SYNC_SUCCEEDED, SCIM_SYNC_FAILED, SCIM_TOKEN_ISSUED,
        SCIM_TOKEN_REVOKED, GROUP_MAPPING_APPROVED, GROUP_MAPPING_REVOKED,
        GROUP_MEMBERSHIP_GRANTED, GROUP_MEMBERSHIP_REVOKED,
        BREAKGLASS_POLICY_DECLARED, BREAKGLASS_POLICY_REVOKED,
        BREAKGLASS_INVOKED, BREAKGLASS_INVOCATION_REFUSED,
        BREAKGLASS_AUTHORIZED, BREAKGLASS_AUTHORIZATION_DENIED,
        BREAKGLASS_ACTION, BREAKGLASS_ACTION_REFUSED,
        BREAKGLASS_SESSION_CLOSED, BREAKGLASS_REVIEW_CREATED,
        BREAKGLASS_REVIEW_COMPLETED,
        WEBHOOK_SUBSCRIPTION_CREATED, WEBHOOK_SUBSCRIPTION_REVOKED,
        SECURITY_EVENT_EMITTED, RATE_LIMIT_EXCEEDED,
    },
    "key_lifecycle": {KEY_ENROLLED, KEY_ROTATED, KEY_REVOKED, KEY_CLOSED},
    "session_lifecycle": {AUTH_LOGIN_SUCCEEDED, AUTH_LOGOUT, AUTH_STEPUP, SESSION_REVOKED},
}


class PlatformLedger:
    """One Axiomere ledger used as an audit record, with the platform
    event vocabulary. Signed by the ledger's own key (the deployment
    or tenant-ledger key): the signature attests the platform recorded
    the event; the acting identity is the payload's `actor_id`."""

    def __init__(self, db: "axiomere.Database", *, scope: str, tenant_id: Optional[str] = None) -> None:
        self.db = db
        self.scope = scope            # "deployment" | "tenant"
        self.tenant_id = tenant_id

    @classmethod
    def create(cls, path: str, *, scope: str, tenant_id: Optional[str] = None,
               seed_hex: Optional[str] = None) -> "PlatformLedger":
        return cls(axiomere.Database.create(path, seed_hex=seed_hex), scope=scope, tenant_id=tenant_id)

    @classmethod
    def open(cls, path: str, *, scope: str, tenant_id: Optional[str] = None,
             seed_hex: Optional[str] = None) -> "PlatformLedger":
        return cls(axiomere.Database.open(path, seed_hex=seed_hex), scope=scope, tenant_id=tenant_id)

    def record(self, event_type: str, *, actor_id: str, target: str,
               outcome: str = "ok", at: Optional[float] = None, **fields: Any) -> dict:
        """Append one audit event with the AU content set. `actor_id` is
        the random actor ID of the acting identity (§4) or a plane
        marker ("system", "bootstrap") for pre-identity events."""
        payload = {
            "actor_id": actor_id,
            "target": target,
            "outcome": outcome,
            # Whole seconds — see the payload discipline note above.
            "ts_utc": int(at if at is not None else time.time()),
            **fields,
        }
        return self.db.append(event_type, payload, actor=actor_id)

    def events(self) -> list:
        return self.db.events()

    def event_types(self) -> list[str]:
        return [e["type"] for e in self.db.events()]

    def checkpoint(self, *, actor_id: str) -> dict:
        return self.db.checkpoint(actor=actor_id)

    def verify(self) -> "axiomere.Verification":
        return self.db.verify()
