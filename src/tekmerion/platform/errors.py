"""Platform-plane error types. Denials are data, not crashes: the gate
raises these *after* recording the refusal in the audit ledger wherever
the attempt is attributable (Spec 005 §5, §13.4)."""

from __future__ import annotations


class PlatformError(Exception):
    """Base for all platform-plane refusals and configuration errors."""


class ConfigurationError(PlatformError):
    """A tenant/IdP/policy record is missing, malformed, or forbidden
    (e.g. an API key whose scopes exceed its role class — unrepresentable
    states raise here at construction, never at use)."""


class AuthenticationError(PlatformError):
    """Authentication failed: bad assertion, expired session, deactivated
    identity, bad API key. Messages deliberately do not distinguish
    unknown identity from failed authentication (§3.5.11)."""


class GateDenied(PlatformError):
    """The append gate refused an append: role, key state, signature,
    custody, step-up, or tenant-binding check failed. The refusal is
    recorded in the platform audit ledger before this is raised."""


class AuthorizationDenied(PlatformError):
    """The authorization service denied an action for an authenticated
    principal (admin-plane and service operations)."""
