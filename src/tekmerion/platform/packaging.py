"""Deployment shapes and self-hosted packaging (Spec 005 §6,
T546; CLM-005-12).

One codebase, one role model, two shapes — the claim is structural,
so the machinery here is a *descriptor + a fingerprint*, and the
parity battery (tests/test_e6_packaging.py) is what runs the same
scenario against both shapes and compares outcomes:

- **hosted**: the multi-tenant deployment Axiovex operates; tenant
  study data lives in tenant scopes of that deployment.
- **self-hosted**: a single-tenant deployment of the same codebase
  inside the institution's own boundary — the fully capable CUI
  path while the hosted shape's DFARS equivalency question stands
  open (CLM-005-31's recorded boundary). A self-hosted tenant's
  study data never transits or rests in the hosted plane: the
  shapes are separate roots, separate ledgers, separate processes;
  the battery asserts the absence, it is not a configuration hope.

Institution KMS option: custody is the E1 seam — a self-hosted
deployment records its custody choice as tenant configuration, and
the delegated-custody mode points the signer at an
institution-operated signer (recorded by reference, like every
secret in this platform). That is the integration surface a
institution KMS/HSM plugs into; no cloud KMS is built or claimed
here.

Upgrade path: a deployment upgrades by installing a newer signed
release of the same codebase; ledgers open in place (the Axiomere
format is versioned, `AXMR1`), tenant configuration is ledger
state and survives, and the release's claims bundle version is the
compatibility record. There is no migration tool because the format
discipline makes the data files forward-readable; a release that
ever broke that would be a claims event, not a silent upgrade.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Optional

from . import authz

SHAPES = frozenset({"hosted", "self-hosted"})


def role_model_fingerprint() -> str:
    """A hash of the authorization model (roles → actions). Two
    shapes run the same model iff their fingerprints match — the
    parity battery compares the fingerprint computed in each
    shape's process context against this one canonical value."""
    canonical = {
        role: sorted(actions) for role, actions in sorted(authz.ROLE_ACTIONS.items())
    }
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass
class DeploymentProfile:
    """One deployment's recorded shape facts — the descriptor the
    packaging story (and the residency pin, T541) reads."""

    shape: str                                  # "hosted" | "self-hosted"
    root: str                                   # this deployment's own data root
    region: Optional[str] = None                # residency pin region, where pinned
    custody: str = "self"                       # "self" | "delegated" (E1 modes)
    signer_ref: Optional[str] = None            # delegated signer, by reference only
    tenants: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.shape not in SHAPES:
            raise ValueError(f"unknown deployment shape {self.shape!r}")
        if self.shape == "self-hosted" and len(self.tenants) > 1:
            raise ValueError("a self-hosted deployment is single-tenant by shape")
        if self.custody == "delegated" and not self.signer_ref:
            raise ValueError("delegated custody names its signer by reference")

    def describe(self) -> dict[str, Any]:
        return {
            "shape": self.shape,
            "root": self.root,
            "region": self.region,
            "custody": self.custody,
            "signer_ref": self.signer_ref,
            "tenants": list(self.tenants),
            "role_model_fingerprint": role_model_fingerprint(),
            "codebase": "tekmerion (single codebase for both shapes)",
            "upgrade_path": "install a newer signed release; ledgers "
                            "open in place (Axiomere AXMR1); tenant "
                            "configuration is ledger state",
        }
