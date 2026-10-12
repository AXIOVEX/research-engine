"""Spec 005 E4 — webhook egress (T531, F-005-21) + security events (T554).

Deliveries are signed (HMAC-SHA256 or Ed25519) over timestamp+body
with a replay window; the reference receiver rejects unsigned,
badly-signed, stale, and replayed deliveries BY NAME; transport
failures retry with backoff and exhaust honestly; every attempt is a
platform audit event. The T554 classes (auth-failure burst,
revocation storm, break-glass use, audit-verification failure) are
detected from real operations and egress signed.
"""

import axiomere
import pytest

from e1_world import login_user
from tekmerion.platform.service import PLATFORM_TENANT_ID
from e4_world import TENANT_B, build_two_tenant_world, login_b
from tekmerion.platform import authz
from tekmerion.platform.errors import (
    AuthenticationError, AuthorizationDenied, ConfigurationError,
)
from tekmerion.platform.keys import LocalKeySigner
from tekmerion.platform.webhooks import (
    EVENT_TEST, SEC_AUDIT_VERIFICATION_FAILURE, SEC_AUTH_FAILURE_BURST,
    SEC_BREAK_GLASS_USE, SEC_REVOCATION_STORM, ReferenceReceiver,
    WebhookRejection,
)


@pytest.fixture()
def world(tmp_path):
    return build_two_tenant_world(tmp_path)


def enroll_self(svc, session):
    seed_hex, _ = axiomere.generate_keypair()
    signer = LocalKeySigner(seed_hex)
    nonce = svc.begin_enrollment(session)
    rec = svc.enroll_self_key(
        session, public_key=signer.public_key,
        proof_signature=signer.sign(nonce.encode()), nonce=nonce)
    return signer, rec


class CapturingTransport:
    """Records calls; returns a scripted status (or raises)."""

    def __init__(self, statuses=(200,)):
        self.calls = []
        self.statuses = list(statuses)

    def __call__(self, url, body, headers):
        self.calls.append((url, body, dict(headers)))
        status = self.statuses.pop(0) if self.statuses else 200
        if isinstance(status, Exception):
            raise status
        return status


def register_security_sub(world, signing="hmac-sha256", tenant_id=None):
    svc = world.service
    tenant_id = tenant_id or world.tenant_id
    session = (world.root_session if tenant_id == PLATFORM_TENANT_ID
               else world.admin_session if tenant_id == world.tenant_id
               else world.admin_b_session)
    return svc.register_webhook(
        session, tenant_id=tenant_id, url="https://hooks.uni.test/egress",
        signing=signing, event_classes=["security.*"])


def test_registration_doors_and_secret_hygiene(world):
    svc = world.service
    alice_session, _ = login_user(world, "alice", role=authz.RESEARCHER)
    with pytest.raises(AuthorizationDenied):
        svc.register_webhook(alice_session, tenant_id=world.tenant_id,
                             url="https://hooks.uni.test/x",
                             signing="hmac-sha256", event_classes=["*"])
    with pytest.raises(ConfigurationError):
        svc.register_webhook(world.admin_session, tenant_id=world.tenant_id,
                             url="http://hooks.uni.test/x",
                             signing="hmac-sha256", event_classes=["*"])
    sub, shown_once = register_security_sub(world)
    assert shown_once  # the secret is shown exactly once: here
    # The tenant ledger carries the fingerprint, never the secret —
    # sweep every ledger's full payload text for the secret value.
    import json
    tenant_blob = json.dumps(
        [e["payload"] for e in svc._tenant_ledger(world.tenant_id).events()],
        default=str)
    deployment_blob = json.dumps(
        [e["payload"] for e in svc.deployment_ledger.events()], default=str)
    assert shown_once not in tenant_blob and shown_once not in deployment_blob
    assert sub.secret_fingerprint in tenant_blob
    # Platform-plane subscriptions belong to the platform plane.
    psub, _ = svc.register_webhook(world.root_session,
                                   tenant_id=PLATFORM_TENANT_ID,
                                   url="https://hooks.platform.test/x",
                                   signing="hmac-sha256",
                                   event_classes=["security.*"])
    assert psub.tenant_id == PLATFORM_TENANT_ID
    with pytest.raises(AuthorizationDenied):
        svc.register_webhook(world.admin_session, tenant_id=PLATFORM_TENANT_ID,
                             url="https://hooks.platform.test/y",
                             signing="hmac-sha256", event_classes=["*"])
    svc.revoke_webhook(world.admin_session, tenant_id=world.tenant_id,
                       subscription_id=sub.subscription_id)
    assert not sub.active


def test_hmac_delivery_roundtrip_and_receiver_rejections(world):
    """F-005-21 against the reference receiver: a genuine delivery is
    accepted; unsigned, badly-signed, stale, and replayed deliveries
    are each rejected by name."""
    svc = world.service
    sub, secret = svc.register_webhook(
        world.admin_session, tenant_id=world.tenant_id,
        url="https://hooks.uni.test/egress", signing="hmac-sha256",
        event_classes=[EVENT_TEST])
    ids = svc.send_webhook_test(world.admin_session,
                                tenant_id=world.tenant_id,
                                subscription_id=sub.subscription_id)
    assert len(ids) == 1
    transport = CapturingTransport()
    attempted = svc.deliver_webhooks(transport)
    assert len(attempted) == 1 and attempted[0].state == "delivered"
    url, body, headers = transport.calls[0]
    assert url == "https://hooks.uni.test/egress"

    def fresh_receiver(secret_bytes):
        return ReferenceReceiver(
            signing="hmac-sha256", hmac_secret=secret_bytes,
            now=lambda: world.clock_box[0])

    receiver = fresh_receiver(secret.encode("utf-8"))
    event = receiver.accept(headers, body)
    assert event["type"] == EVENT_TEST

    # Replay of the same delivery id (the accepting receiver's
    # register is consulted before the signature — cheap checks
    # first — so the replay is named as a replay).
    with pytest.raises(WebhookRejection, match="replayed"):
        receiver.accept(headers, body)
    # Tampered body at a fresh receiver: the signature check fires.
    with pytest.raises(WebhookRejection, match="signature"):
        fresh_receiver(secret.encode("utf-8")).accept(headers, body + b" ")
    # Unsigned.
    bare = {k: v for k, v in headers.items() if k != "X-Tekmerion-Signature"}
    with pytest.raises(WebhookRejection, match="signature header"):
        receiver.accept(bare, body)
    # Wrong secret at the receiver.
    receiver2 = ReferenceReceiver(
        signing="hmac-sha256", hmac_secret=b"not-the-secret",
        now=lambda: world.clock_box[0])
    with pytest.raises(WebhookRejection, match="signature"):
        receiver2.accept(headers, body)
    # Stale: the same well-signed delivery after the window.
    receiver3 = ReferenceReceiver(
        signing="hmac-sha256", hmac_secret=secret.encode("utf-8"),
        now=lambda: world.clock_box[0] + 301)
    with pytest.raises(WebhookRejection, match="window"):
        receiver3.accept(headers, body)
    # Every attempt was a platform audit event.
    succeeded = [e for e in svc._tenant_ledger(world.tenant_id).events()
                 if e["type"] == "webhook.delivery_succeeded"]
    assert len(succeeded) == 1


def test_ed25519_delivery_roundtrip(world):
    svc = world.service
    sub, shown_once = svc.register_webhook(
        world.admin_session, tenant_id=world.tenant_id,
        url="https://hooks.uni.test/ed", signing="ed25519",
        event_classes=[EVENT_TEST])
    assert shown_once is None  # nothing to show: the key is public
    svc.send_webhook_test(world.admin_session, tenant_id=world.tenant_id,
                          subscription_id=sub.subscription_id)
    transport = CapturingTransport()
    svc.deliver_webhooks(transport)
    _, body, headers = transport.calls[0]
    receiver = ReferenceReceiver(
        signing="ed25519",
        ed25519_public_key=bytes.fromhex(sub.signing_public_key_hex),
        now=lambda: world.clock_box[0])
    assert receiver.accept(headers, body)["type"] == EVENT_TEST
    fresh = ReferenceReceiver(
        signing="ed25519",
        ed25519_public_key=bytes.fromhex(sub.signing_public_key_hex),
        now=lambda: world.clock_box[0])
    with pytest.raises(WebhookRejection, match="signature"):
        fresh.accept(headers, body.replace(b"probe", b"forged"))


def test_delivery_retries_backoff_and_exhaustion(world):
    svc = world.service
    sub, _ = svc.register_webhook(
        world.admin_session, tenant_id=world.tenant_id,
        url="https://hooks.uni.test/flaky", signing="hmac-sha256",
        event_classes=[EVENT_TEST])
    svc.send_webhook_test(world.admin_session, tenant_id=world.tenant_id,
                          subscription_id=sub.subscription_id)
    transport = CapturingTransport(statuses=[500, 500, 500, 500])
    svc.deliver_webhooks(transport)
    (delivery,) = svc.pending_deliveries()
    assert delivery.attempts == 1
    # Not due yet: an immediate second pass attempts nothing.
    svc.deliver_webhooks(transport)
    assert len(transport.calls) == 1
    world.clock_box[0] += 1
    svc.deliver_webhooks(transport)
    world.clock_box[0] += 5
    svc.deliver_webhooks(transport)
    world.clock_box[0] += 25
    svc.deliver_webhooks(transport)
    assert delivery.attempts == 4 and delivery.state == "failed"
    failures = [e for e in svc._tenant_ledger(world.tenant_id).events()
                if e["type"] == "webhook.delivery_failed"]
    assert len(failures) == 4
    assert failures[-1]["payload"]["exhausted"] is True

    # A transport exception is recorded as data, and a later retry
    # can still succeed.
    svc.send_webhook_test(world.admin_session, tenant_id=world.tenant_id,
                          subscription_id=sub.subscription_id)
    flaky = CapturingTransport(statuses=[ConnectionError("refused"), 200])
    svc.deliver_webhooks(flaky)
    world.clock_box[0] += 1
    attempted = svc.deliver_webhooks(flaky)
    assert attempted and attempted[0].state == "delivered"
    errors = [e for e in svc._tenant_ledger(world.tenant_id).events()
              if e["type"] == "webhook.delivery_failed"
              and "ConnectionError" in str(e["payload"].get("error"))]
    assert errors


def fail_login(world, subject="alice"):
    svc = world.service
    url = svc.begin_login(world.tenant_id, world.issuer_a)
    _, state = world.mock.authorize(url, subject)
    with pytest.raises(AuthenticationError):
        svc.complete_login(state, "bogus-code")


def test_security_event_auth_failure_burst(world):
    """T554: the burst fires ONCE per window at the threshold, is a
    platform audit event, and egresses signed to subscribers."""
    svc = world.service
    svc.directory.tenant(world.tenant_id).policy.auth_failure_burst_threshold = 3
    sub, secret = register_security_sub(world)
    fail_login(world)
    fail_login(world)
    assert not svc.pending_deliveries()
    fail_login(world)  # third: threshold reached
    pending = svc.pending_deliveries()
    assert len(pending) == 1
    assert pending[0].event_type == SEC_AUTH_FAILURE_BURST
    emitted = [e for e in svc._tenant_ledger(world.tenant_id).events()
               if e["type"] == "security.event_emitted"]
    assert len(emitted) == 1
    # Inside the same window, more failures do not re-fire.
    fail_login(world)
    fail_login(world)
    fail_login(world)
    assert len(svc.pending_deliveries()) == 1
    # The egress is verifiable end-to-end.
    transport = CapturingTransport()
    svc.deliver_webhooks(transport)
    _, body, headers = transport.calls[0]
    receiver = ReferenceReceiver(
        signing="hmac-sha256", hmac_secret=secret.encode("utf-8"),
        now=lambda: world.clock_box[0])
    assert receiver.accept(headers, body)["type"] == SEC_AUTH_FAILURE_BURST
    # A new window can fire again.
    world.clock_box[0] += 301
    for _ in range(3):
        fail_login(world)
    assert any(d.event_type == SEC_AUTH_FAILURE_BURST
               for d in svc.pending_deliveries())


def test_security_event_revocation_storm(world):
    svc = world.service
    svc.directory.tenant(world.tenant_id).policy.revocation_storm_threshold = 3
    register_security_sub(world)
    sessions = []
    for subject in ("alice", "ada", "ivy"):
        session, _ = login_user(world, subject)
        enroll_self(svc, session)
        sessions.append(session)
    # Three self-revocations inside the window: the storm fires.
    from tekmerion.platform.service import PlatformService  # noqa: F401
    directory = svc.directory
    for session in sessions:
        _, identity = svc._resolve_session(session)
        keys = svc.registry(world.tenant_id).keys_for_identity(identity.identity_id)
        svc.revoke_key(session, key_fingerprint=keys[0].fingerprint,
                       reason="storm battery")
    pending = [d for d in svc.pending_deliveries()
               if d.event_type == SEC_REVOCATION_STORM]
    assert len(pending) == 1


def test_security_event_break_glass_use_egress(world):
    svc = world.service
    sub, secret = register_security_sub(world)
    svc.declare_break_glass_policy(
        world.admin_session, tenant_id=world.tenant_id,
        invoker_roles=[authz.PLATFORM_ADMIN],
        second_authorizer_plane="tenant_admin",
        max_duration_seconds=600, scopes=[authz.TENANT_AUDIT_EXPORT])
    bg = svc.invoke_break_glass(world.root_session, tenant_id=world.tenant_id,
                                reason="egress drill", duration_seconds=300)
    svc.authorize_break_glass(world.admin_session, bg_session_id=bg.bg_session_id)
    pending = [d for d in svc.pending_deliveries()
               if d.event_type == SEC_BREAK_GLASS_USE]
    assert len(pending) == 1
    transport = CapturingTransport()
    svc.deliver_webhooks(transport)
    _, body, headers = transport.calls[0]
    receiver = ReferenceReceiver(
        signing="hmac-sha256", hmac_secret=secret.encode("utf-8"),
        now=lambda: world.clock_box[0])
    event = receiver.accept(headers, body)
    assert event["type"] == SEC_BREAK_GLASS_USE
    assert event["data"]["bg_session_id"] == bg.bg_session_id


def test_security_event_audit_verification_failure(world):
    """Tamper with the tenant ledger's bytes (one payload letter in
    the tenant-admin's role.granted event): verification reports the
    break honestly, the failure is a security event, and it egresses.

    Roles replay from the ledger (it is the record of truth), so the
    tampered grant itself stops working — the tenant admin's own
    door denies — and it is the platform plane's verification that
    names the break. Detection, not silent reinterpretation."""
    svc = world.service
    sub, secret = register_security_sub(world)
    path = svc.root / "tenant-uni-a.axmr"
    data = bytearray(path.read_bytes())
    marker = data.find(b"tenant_admin")
    assert marker > 0
    data[marker + 11] = ord("m")   # role "tenant_admin" -> "tenant_admim"
    path.write_bytes(bytes(data))
    with pytest.raises(AuthorizationDenied):
        svc.verify_tenant_audit(world.admin_session,
                                tenant_id=world.tenant_id)
    result = svc.verify_tenant_audit(world.root_session,
                                     tenant_id=world.tenant_id)
    assert result["ok"] is False
    assert result["reason"] == "hash-mismatch"
    pending = [d for d in svc.pending_deliveries()
               if d.event_type == SEC_AUDIT_VERIFICATION_FAILURE]
    assert len(pending) == 1


def test_event_class_matching(world):
    """Subscriptions receive only their classes: a revocation-storm
    subscription sees no auth bursts, and vice versa."""
    svc = world.service
    policy = svc.directory.tenant(world.tenant_id).policy
    policy.auth_failure_burst_threshold = 2
    policy.revocation_storm_threshold = 2
    storms, _s1 = svc.register_webhook(
        world.admin_session, tenant_id=world.tenant_id,
        url="https://hooks.uni.test/storms", signing="hmac-sha256",
        event_classes=[SEC_REVOCATION_STORM])
    bursts, _s2 = svc.register_webhook(
        world.admin_session, tenant_id=world.tenant_id,
        url="https://hooks.uni.test/bursts", signing="hmac-sha256",
        event_classes=[SEC_AUTH_FAILURE_BURST])
    fail_login(world)
    fail_login(world)
    by_sub = {}
    for d in svc.pending_deliveries():
        by_sub.setdefault(d.subscription_id, set()).add(d.event_type)
    assert by_sub.get(bursts.subscription_id) == {SEC_AUTH_FAILURE_BURST}
    assert storms.subscription_id not in by_sub
