"""Session & transport baseline (Spec 005 §9, T530) — the enumerable
contract CLM-005-19 claims, in one place so the battery can enumerate
it rather than admire it.

There is no HTTP transport in the platform package (E1–E3 scope fact:
the surfaces are service-layer APIs an adapter binds). What §9 binds
is therefore split honestly in two:

- **Enforced here, now:** session idle/absolute lifetimes (the
  directory's `TenantPolicy` defaults + `PlatformService`'s session
  resolution, which this module's constants mirror and the battery
  cross-checks), and per-tenant rate limits — `RateLimiter`, wired
  into every service endpoint class, answering with 429 semantics
  and recording the trip (§6: exhaustion is a recorded stop).
- **Contract for the adapter, asserted as data:** the security
  header set, the session-cookie attributes, and the TLS posture
  (serve / redirect / refuse). An HTTP adapter that does not emit
  exactly these fails this module's battery, not a code review.

Nothing here weakens a default: tenants configure session lifetimes
and rate limits down (TenantPolicy); the header/cookie contract has
no per-tenant loosening at all.
"""

from __future__ import annotations

from collections import deque

from .directory import TenantPolicy
from .errors import ConfigurationError, RateLimited

# -- session lifetimes (§9 defaults; TenantPolicy carries the live values)

SESSION_IDLE_SECONDS = 1800        # 30 min
SESSION_ABSOLUTE_SECONDS = 43200   # 12 h

# -- headers (§9: on every response) --------------------------------------

SECURITY_HEADERS: dict[str, str] = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}


def security_headers() -> dict[str, str]:
    """The header set every response carries, exactly. A copy — the
    caller may add response-specific headers, never remove these."""
    return dict(SECURITY_HEADERS)


# -- session cookie (§9: Secure + HttpOnly + SameSite) ----------------------

SESSION_COOKIE_NAME = "tekmerion_session"
SESSION_COOKIE_ATTRIBUTES: dict[str, object] = {
    "Secure": True,
    "HttpOnly": True,
    "SameSite": "Lax",
    "Path": "/",
}


def session_cookie_attributes() -> dict[str, object]:
    return dict(SESSION_COOKIE_ATTRIBUTES)


def render_session_cookie(value: str) -> str:
    """The Set-Cookie header for a session token, with exactly the
    §9 attributes — the artifact the battery parses."""
    parts = [f"{SESSION_COOKIE_NAME}={value}"]
    for name, attr in SESSION_COOKIE_ATTRIBUTES.items():
        parts.append(name if attr is True else f"{name}={attr}")
    return "; ".join(parts)


# -- TLS posture (§9: HTTP refused or redirected to TLS) -------------------

def tls_posture(url: str) -> tuple[str, str]:
    """Returns ("serve", url) for TLS URLs and ("redirect", https_url)
    for plain-HTTP URLs — an adapter serves the first and answers the
    second with a redirect, never content. Any other scheme is a
    configuration error, refused outright."""
    if url.startswith("https://"):
        return "serve", url
    if url.startswith("http://"):
        return "redirect", "https://" + url[len("http://"):]
    raise ConfigurationError(f"unsupported URL scheme (TLS required): {url!r}")


def policy_defaults_match_spec() -> bool:
    """The §9 defaults the battery cross-checks: TenantPolicy's live
    defaults must be this module's stated constants — a drift between
    the contract and the enforcement default fails the battery."""
    p = TenantPolicy()
    return (p.session_idle_seconds == SESSION_IDLE_SECONDS
            and p.session_absolute_seconds == SESSION_ABSOLUTE_SECONDS)


# -- rate limiting (§6 tenant budgets + §9 limits) ---------------------------

#: The service-layer endpoint classes the limiter guards. These are
#: the endpoint classes that exist (E1–E4 scope fact: service layer).
ENDPOINT_CLASSES = (
    "auth.login",        # OIDC begin/complete
    "auth.saml",         # SAML begin/complete/step-up completion
    "scim",              # every SCIM operation's authentication
    "append.session",    # session-authorized study appends
    "append.api",        # API-key study appends
    "breakglass",        # break-glass invocation / authorization / action
)


class RateLimiter:
    """Fixed-window per-(tenant, endpoint class) limiter. The window
    is the trailing 60 seconds; the limit is the tenant policy's
    `rate_limit_per_minute`. State is in-memory working state — the
    *trip* is what reaches the record (the service ledgers it)."""

    WINDOW_SECONDS = 60.0

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque] = {}

    def check(self, tenant_id: str, endpoint_class: str, *,
              limit_per_minute: int, now: float) -> None:
        """Admit one request or raise RateLimited (429 semantics).
        Every admitted request is counted — the limit is on load,
        not on failures."""
        key = (tenant_id, endpoint_class)
        hits = self._hits.setdefault(key, deque())
        cutoff = now - self.WINDOW_SECONDS
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= limit_per_minute:
            retry_after = max(1.0, hits[0] + self.WINDOW_SECONDS - now)
            raise RateLimited(
                f"rate limit exhausted for tenant {tenant_id} "
                f"endpoint class {endpoint_class}: "
                f"{limit_per_minute}/min (429)",
                retry_after_seconds=retry_after)
        hits.append(now)

    def count(self, tenant_id: str, endpoint_class: str, *, now: float) -> int:
        hits = self._hits.get((tenant_id, endpoint_class), deque())
        cutoff = now - self.WINDOW_SECONDS
        return sum(1 for t in hits if t > cutoff)
