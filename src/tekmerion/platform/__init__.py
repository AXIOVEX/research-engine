"""Tekmerion platform plane (Spec 005) — identity, authorization, tenancy,
administration. The study plane (Spec 002) is unchanged; this package is
the service layer that decides *whose append counts* before the record
layer (Axiomere) writes anything.

E1 scope: OIDC identity core, identity↔key binding with custody modes,
service-layer RBAC on the WS6 matrix, the platform audit ledger, and
scoped API keys. See specs/005-enterprise-platform/.
"""
