"""Authorization service (Spec 005 §5, T508/T509) — the WS6 §1 role
matrix as policy, enforced in the service layer, deny-by-default.

Study roles are WS6's, unchanged: researcher / reviewer / adjudicator
/ integrity officer. Two admin planes are added — tenant admin and
platform admin — and are **disjoint** from study powers and from each
other: a tenant admin holds no study role by virtue of the plane, and
a platform admin cannot sign a study verdict. No plane implies
another (CLM-005-09; the E4 battery hardens what E1 models here).

An identity may hold several roles (grants are additive events); the
matrix says what each *role* permits, never what a person "usually"
does. `System` is a service-account principal class whose API-key
scopes must be a subset of one role's actions (CLM-005-18).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

# -- study-plane actions (the Spec 002 service surface) ----------------

REGISTER_CLAIM = "study.register_claim"
LOG_QUERY = "study.log_query"
RUN_CITATION_CHECK = "study.run_citation_check"
ENQUEUE_ADJUDICATION = "study.enqueue_adjudication"
DECIDE_ADJUDICATION = "study.decide_adjudication"
SECOND_REVIEW = "study.second_review"
ISSUE_VERDICT = "study.issue_verdict"
FREEZE = "study.freeze"
WITHDRAW_CLAIM = "study.withdraw_claim"
EXPORT_BUNDLE = "study.export_bundle"
ANCHOR = "study.anchor"
INSPECT = "study.inspect"

#: Actions whose signing requires a fresh step-up in both custody
#: modes (§2/§3): verdicts are the platform's load-bearing act.
VERDICT_CLASS_ACTIONS = frozenset({ISSUE_VERDICT})

STUDY_ACTIONS = frozenset({
    REGISTER_CLAIM, LOG_QUERY, RUN_CITATION_CHECK, ENQUEUE_ADJUDICATION,
    DECIDE_ADJUDICATION, SECOND_REVIEW, ISSUE_VERDICT, FREEZE,
    WITHDRAW_CLAIM, EXPORT_BUNDLE, ANCHOR, INSPECT,
})

# -- admin-plane actions --------------------------------------------------

TENANT_IDP_MANAGE = "tenant.idp_manage"
TENANT_MEMBER_MANAGE = "tenant.member_manage"      # grants, revocations, deactivation
TENANT_KEY_MANAGE = "tenant.key_manage"            # revoking/closing tenant members' keys
TENANT_AUDIT_EXPORT = "tenant.audit_export"
TENANT_POLICY_MANAGE = "tenant.policy_manage"

PLATFORM_TENANT_CREATE = "platform.tenant_create"
PLATFORM_TENANT_MANAGE = "platform.tenant_manage"
PLATFORM_CONFIG_MANAGE = "platform.config_manage"
PLATFORM_ADMIN_GRANT = "platform.admin_grant"

TENANT_ADMIN_ACTIONS = frozenset({
    TENANT_IDP_MANAGE, TENANT_MEMBER_MANAGE, TENANT_KEY_MANAGE,
    TENANT_AUDIT_EXPORT, TENANT_POLICY_MANAGE,
})
PLATFORM_ADMIN_ACTIONS = frozenset({
    PLATFORM_TENANT_CREATE, PLATFORM_TENANT_MANAGE, PLATFORM_CONFIG_MANAGE,
    PLATFORM_ADMIN_GRANT,
})

# -- roles ------------------------------------------------------------------

RESEARCHER = "researcher"
REVIEWER = "reviewer"
ADJUDICATOR = "adjudicator"
INTEGRITY_OFFICER = "integrity_officer"
TENANT_ADMIN = "tenant_admin"
PLATFORM_ADMIN = "platform_admin"
SYSTEM = "system"  # principal class for API keys, not a grantable human role

ROLE_ACTIONS: dict[str, frozenset] = {
    RESEARCHER: frozenset({
        REGISTER_CLAIM, LOG_QUERY, RUN_CITATION_CHECK, ENQUEUE_ADJUDICATION,
        FREEZE, INSPECT,
    }),
    REVIEWER: frozenset({SECOND_REVIEW, RUN_CITATION_CHECK, INSPECT}),
    ADJUDICATOR: frozenset({
        DECIDE_ADJUDICATION, ISSUE_VERDICT, WITHDRAW_CLAIM, FREEZE,
        EXPORT_BUNDLE, ANCHOR, INSPECT,
    }),
    INTEGRITY_OFFICER: frozenset({
        INSPECT, EXPORT_BUNDLE, ANCHOR, RUN_CITATION_CHECK, ENQUEUE_ADJUDICATION,
    }),
    TENANT_ADMIN: TENANT_ADMIN_ACTIONS,
    PLATFORM_ADMIN: PLATFORM_ADMIN_ACTIONS,
}

STUDY_ROLES = frozenset({RESEARCHER, REVIEWER, ADJUDICATOR, INTEGRITY_OFFICER})
ALL_GRANTABLE_ROLES = STUDY_ROLES | {TENANT_ADMIN, PLATFORM_ADMIN}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    action: str
    role_basis: Optional[str] = None     # the held role that permitted it
    reason: str = ""


class AuthorizationService:
    """Pure policy: roles in, decision out. Recording decisions is the
    caller's duty (§5: mutating decisions are recorded — the gate and
    the admin service do that in the platform ledger)."""

    def decide(self, roles: Iterable[str], action: str) -> Decision:
        held = set(roles)
        for role in held:
            if action in ROLE_ACTIONS.get(role, frozenset()):
                return Decision(True, action, role_basis=role)
        return Decision(
            False, action,
            reason=f"no held role permits {action} (held: {sorted(held) or 'none'})",
        )

    def permits(self, roles: Iterable[str], action: str) -> bool:
        return self.decide(roles, action).allowed

    @staticmethod
    def validate_key_scopes(role_class: str, scopes: Iterable[str]) -> None:
        """An API key's scopes must be a subset of its role class's
        actions — a key can never hold a power its class denies a
        human (CLM-005-18). Raises ConfigurationError via errors module
        to keep construction-time failures uniform."""
        from .errors import ConfigurationError

        allowed = ROLE_ACTIONS.get(role_class)
        if allowed is None:
            raise ConfigurationError(f"unknown role class for API key: {role_class}")
        extra = set(scopes) - set(allowed)
        if extra:
            raise ConfigurationError(
                f"API key scopes exceed role class {role_class}: {sorted(extra)}"
            )
        if not set(scopes):
            raise ConfigurationError("API key must carry at least one scope")
