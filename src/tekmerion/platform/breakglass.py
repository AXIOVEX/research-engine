"""Break-glass (Spec 005 §5, T529) — emergency access as a named
mechanism, never a standing door.

The shapes live here; the operations live on `PlatformService`
(the `breakglass` section of `service.py`), following the package's
grain. The rules, from spec §5 and the T534-WF wireframe package
(`docs/wireframes/console/break-glass.html`, whose UNDECLARED state
is the requirement these mechanics make real):

- A tenant with **no declared policy cannot be invoked** — by
  construction, not by an administrator's restraint. Declaration is
  itself a ledgered tenant-admin act naming invoker roles, the
  second-authorizer plane, the action scopes, and the time box.
- The time box is capped in code: `MAX_DURATION_SECONDS` (4 h).
  A declaration may set a smaller box; nothing — no declaration, no
  parameter — sets a larger one. Extension of a live session does
  not exist; a longer need is a new declaration + a new session.
- Invocation mints a *pending* session, never a credential. A
  **second authorizer** — a different identity, holding the declared
  authorizer plane's role — activates it. The invoker can never
  authorize their own session, whatever roles they hold.
- Every action under an active session is exercised through the
  platform service, checked against the declared scopes, and
  recorded as a marked `breakglass.action` event in BOTH the
  tenant's ledger (the tenant's own record of what touched it) and
  the deployment ledger (the platform security log).
- Closing (explicit, on policy revocation, or at expiry) creates a
  **post-use review item** automatically; a tenant admin's review
  disposition is itself a recorded act.

In the self-hosted shape the institution's own operators hold
infrastructure access outside this mechanism (CLM-005-10's boundary
states that honestly); this machinery governs the platform plane.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

#: The hard ceiling on any break-glass time box (§5: "default ≤ 4h,
#: configurable down, never up silently" — the code makes the "never
#: up" half unrepresentable rather than procedural).
MAX_DURATION_SECONDS = 4 * 3600

AUTHORIZER_PLATFORM = "platform_admin"
AUTHORIZER_TENANT = "tenant_admin"
AUTHORIZER_PLANES = (AUTHORIZER_PLATFORM, AUTHORIZER_TENANT)

# Session states. A session is usable only in STATE_ACTIVE and only
# before its expires_at; every other state refuses, recorded.
STATE_PENDING = "pending"        # invoked, awaiting second authorization
STATE_ACTIVE = "active"          # authorized, inside the time box
STATE_DENIED = "denied"          # second authorizer refused
STATE_CLOSED = "closed"          # ended inside its box (explicit / policy revoked)
STATE_EXPIRED = "expired"        # the time box ran out


@dataclass
class BreakGlassPolicy:
    """One tenant's declared break-glass policy — the current
    projection of its declaration events."""
    tenant_id: str
    invoker_roles: tuple[str, ...]        # held roles whose holders may invoke
    second_authorizer_plane: str          # AUTHORIZER_PLATFORM | AUTHORIZER_TENANT
    max_duration_seconds: float           # <= MAX_DURATION_SECONDS, enforced at declaration
    scopes: tuple[str, ...]               # tenant-admin actions the session may exercise
    declared_by_actor_id: str
    declared_at: float
    active: bool = True


@dataclass
class BreakGlassSession:
    """One break-glass session: a minted, dual-authorized, time-boxed
    context — never a credential. Actions name the session; the
    session names the invoker, the authorizer, and the box."""
    bg_session_id: str
    tenant_id: str
    invoker_identity_id: str
    invoker_actor_id: str
    reason: str
    requested_duration_seconds: float
    state: str = STATE_PENDING
    invoked_at: float = 0.0
    authorized_by_actor_id: Optional[str] = None
    authorized_by_identity_id: Optional[str] = None
    authorized_at: Optional[float] = None
    expires_at: Optional[float] = None
    closed_at: Optional[float] = None
    close_reason: str = ""
    review_item_id: Optional[str] = None
    review_completed: bool = False
    actions_taken: int = 0
