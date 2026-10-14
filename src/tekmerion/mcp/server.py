"""Tekmerion MCP server — tools over the production services (Spec 009).

Structure: `Session` holds the instance configuration (one actor,
one WS6 role, one workspace) and implements every tool as a plain
function of its declared arguments (CLM-009-12 — no transport or
request context reaches a handler). `build_server` registers those
functions with the MCP SDK as a thin shell. Engine exceptions
propagate with their text unchanged (CLM-009-02); the SDK shell
converts them to MCP error results carrying `str(exc)` verbatim.

Identity: the actor is configured at launch (`TEKMERION_ACTOR`,
required) and the role via `TEKMERION_ROLE`; no tool accepts an
actor parameter (WS6 §1 — event actors are recorded from the
identity, never typed per action). Role enforcement applies the
shipped UI's permission matrix, imported from
`tekmerion.ui.server.PERMISSIONS` so the surfaces cannot drift
(CLM-009-03); tool families with no UI counterpart (adapters, math)
take the register family's tuple by reference.

Spec 013 (WS-5) hardens this surface: lane-2 appends
(`record_digestion` / `record_acceptance`) are adjudicator acts
whose references must resolve to records in the study; faithfulness
re-pinning is adjudicator-only and the pin history is projected;
`ingest_lean` fetches http/https only and adapter file paths are
confined to the workspace; second reviews are validated against
the queue; and an OS error inside a tool surfaces as a
`SurfaceRefusal` that names no absolute path (CLM-013-28…35).
"""

from __future__ import annotations

import functools
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from .. import deposit as deposit_mod
from .. import export as export_mod
from .. import mathclaims
from .. import verification as vf
from ..adapters import checkcif as checkcif_mod
from ..adapters import codecheck as codecheck_mod
from ..adapters import statconsistency as stat_mod
from ..adapters.core import adapter_runs
from ..claims import Claim, EvidenceItem
from ..connectors import CoreConnector, CrossrefConnector, OpenAlexConnector
from ..ui import state as st
from ..ui.server import PERMISSIONS

ROLES = st.ROLES

# Tool -> roles that may call it. Entries for actions the UI matrix
# names reference PERMISSIONS tuples directly; reads are open to
# every role (the UI shows them to all four views).
TOOL_ROLES: dict[str, Optional[tuple[str, ...]]] = {
    "create_study": PERMISSIONS["create_study"],
    "register_claim": PERMISSIONS["register_claim"],
    "withdraw_claim": PERMISSIONS["withdraw"],
    "attach_citation": PERMISSIONS["attach_citation"],
    "decide_adjudication": PERMISSIONS["decide"],
    "record_second_review": PERMISSIONS["second_review"],
    "freeze_study": PERMISSIONS["freeze"],
    "run_evaluation": PERMISSIONS["run"],
    "export_bundle": PERMISSIONS["export"],
    "deposit_bundle": PERMISSIONS["deposit"],
    "verify_bundle": PERMISSIONS["verify_bundle"],
    "run_checkcif": PERMISSIONS["register_claim"],
    "run_codecheck": PERMISSIONS["register_claim"],
    "run_grim": PERMISSIONS["register_claim"],
    "run_statcheck": PERMISSIONS["register_claim"],
    "register_theorem": PERMISSIONS["register_claim"],
    "pin_faithfulness": PERMISSIONS["register_claim"],
    "ingest_lean": PERMISSIONS["register_claim"],
    # Lane-2 appends are adjudicator acts (Spec 013 CLM-013-28): a
    # digestion or acceptance record states that a human explained
    # or accepted a result, so the role that may append one is the
    # adjudicator's — not the register family's.
    "record_digestion": ("adjudicator",),
    "record_acceptance": ("adjudicator",),
}


class ConfigError(RuntimeError):
    """The instance is misconfigured; the server does not start."""


class SurfaceRefusal(RuntimeError):
    """A refusal originated by this surface (role, transport, or
    workspace state) — its own text, like the UI's refusal banner.
    Engine refusals are never wrapped in this class."""


def _scrub_paths(text: str, root: str) -> str:
    """Take absolute filesystem paths out of an error's text. The
    workspace root becomes a label; any other absolute path becomes
    a placeholder. What remains is the plain reason (for example
    'File name too long'), which is the part a caller can act on."""
    if root:
        text = text.replace(root, "<workspace>")
    return re.sub(r"/(?:[\w.\-+@]+/)*[\w.\-+@]*", "<path>", text)


def _surface_guard(fn):
    """Spec 013 CLM-013-35: an `OSError` raised inside a tool (a file
    name too long, a missing file, a full disk) surfaces as a
    `SurfaceRefusal` naming no absolute path, instead of leaking the
    raw OS error — paths and all — to the client. Engine refusals
    are not `OSError`s and pass through with their text unchanged
    (CLM-009-02)."""
    @functools.wraps(fn)
    def wrapped(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except OSError as exc:
            detail = _scrub_paths(str(exc), str(self.ws.root))
            raise SurfaceRefusal(
                "the workspace could not carry out that operation: "
                f"{detail}") from exc
    return wrapped


@dataclass
class ServerConfig:
    workspace_root: str
    actor: str
    role: str = "researcher"
    deposit_root: Optional[str] = None

    @classmethod
    def from_env(cls, env: Optional[dict[str, str]] = None) -> "ServerConfig":
        env = os.environ if env is None else env
        actor = (env.get("TEKMERION_ACTOR") or "").strip()
        if not actor:
            raise ConfigError(
                "TEKMERION_ACTOR is not set: a Tekmerion MCP instance runs as "
                "one named actor (WS6 §1) and appends are signed with that "
                "identity — there is no anonymous mode. Set TEKMERION_ACTOR "
                "and TEKMERION_ROLE (researcher|reviewer|adjudicator|integrity)."
            )
        role = (env.get("TEKMERION_ROLE") or "researcher").strip()
        if role not in ROLES:
            raise ConfigError(
                f"TEKMERION_ROLE {role!r} is not a WS6 role; expected one of {ROLES}"
            )
        return cls(
            workspace_root=(env.get("TEKMERION_WORKSPACE") or "./tekmerion-workspace"),
            actor=actor,
            role=role,
            deposit_root=(env.get("TEKMERION_DEPOSIT_ROOT") or None),
        )


def _default_connectors() -> list:
    connectors = [CrossrefConnector()]
    if os.environ.get("OPENALEX_API_KEY"):
        connectors.append(OpenAlexConnector())
    if os.environ.get("CORE_API_KEY"):
        # Spec 012: CORE is the content channel — appended last, so
        # primary resolution order (Crossref, OpenAlex, CORE) holds
        # and a keyless deployment behaves exactly as before.
        connectors.append(CoreConnector())
    return connectors


class Session:
    """One configured instance: workspace + identity + session state.

    A fresh `StudyStore` and rebuilt register are loaded per tool
    call (the UI's per-request discipline), so appends by other
    instances against the same workspace are always visible. Adapter
    evidence is the one session-scoped state (spec §4): items an
    adapter attaches are kept per study and re-applied after each
    rebuild.
    """

    def __init__(self, config: ServerConfig, *,
                 connector_factory: Optional[Callable[[], list]] = None,
                 codecheck_fetcher: Optional[Callable[[str], bytes]] = None) -> None:
        self.config = config
        self.ws = st.Workspace(config.workspace_root)
        self._connector_factory = connector_factory or _default_connectors
        self._codecheck_fetcher = codecheck_fetcher
        self._adapter_items: dict[str, dict[str, list[EvidenceItem]]] = {}

    # ------------------------------------------------------------ plumbing

    @property
    def actor(self) -> str:
        return self.config.actor

    @property
    def role(self) -> str:
        return self.config.role

    def _require(self, tool: str) -> None:
        allowed = TOOL_ROLES.get(tool)
        if allowed is not None and self.role not in allowed:
            raise SurfaceRefusal(
                f"role {self.role!r} may not call {tool}: this action requires "
                f"one of {list(allowed)} (WS6 §1). This instance runs as "
                f"{self.actor!r} ({self.role}); start an instance configured "
                "with an authorised role for this action."
            )

    def _load(self, study_id: str):
        """Open the study and rebuild its register + derived evidence,
        re-applying this session's adapter-attached items."""
        try:
            store = self.ws.open(study_id)
        except st.WorkspaceError as exc:
            raise SurfaceRefusal(str(exc)) from exc
        register, info = st.rebuild_register(store)
        retrieved_sidecar = self.ws.read_sidecar(study_id, "retrieved.json", {}) or {}
        st.derive_evidence(store, register, retrieved_sidecar)
        for claim_id, items in self._adapter_items.get(study_id, {}).items():
            if claim_id in register.claims:
                for item in items:
                    register.add_evidence(claim_id, item)
        return store, register, info

    def _harvest_adapter_items(self, study_id: str, register,
                               claim_id: Optional[str], before: int) -> None:
        if claim_id is None:
            return
        items = register.evidence.get(claim_id, [])
        new = items[before:]
        if new:
            self._adapter_items.setdefault(study_id, {}).setdefault(
                claim_id, []).extend(new)

    def _transport(self):
        if self.config.deposit_root:
            return deposit_mod.LocalTransport(self.config.deposit_root)
        if os.environ.get("ZENODO_ACCESS_TOKEN"):
            return deposit_mod.ZenodoTransport()
        return None

    # ------------------------------------------- Spec 013 WS-5 gates

    def _ref_resolves(self, study_id: str, store, register,
                      ref: Optional[str]) -> bool:
        """Whether a lane-2 reference points at an existing record
        (CLM-013-28). Resolvable means the study's own record holds
        it: a claim id in the register; an ingested artifact's URL
        (named exactly, or appearing inside the reference's text);
        a citation id or DOI from a citation check; a queue id; an
        anchor receipt's locator, root, bundle hash, or DOI; or a
        file that exists inside the workspace. Anything else — an
        invented name, a bare token, an outside URL the study never
        ingested — does not resolve."""
        ref = (ref or "").strip()
        if not ref:
            return False
        if ref in register.claims:
            return True
        ingestion_urls = []
        for event in store.events():
            payload = event["payload"]
            etype = event["type"]
            if etype == "math.lean_ingested":
                url = (payload.get("artifact") or {}).get("url") or ""
                if url:
                    ingestion_urls.append(url)
                    if ref == url:
                        return True
            elif etype == "citation.checked":
                if ref in (payload.get("citation_id"), payload.get("doi")):
                    return True
            elif etype == "adjudication.enqueued":
                if ref == payload.get("queue_id"):
                    return True
            elif etype == "anchor.recorded":
                if ref in (payload.get("locator"), payload.get("root"),
                           payload.get("bundle_hash"), payload.get("doi")):
                    return True
        if any(url in ref for url in ingestion_urls):
            return True
        root = self.ws.root.resolve()
        for base in (self.ws.study_dir(study_id), self.ws.root):
            try:
                resolved = (base / ref).resolve()
            except OSError:
                continue
            if resolved.is_file() and resolved.is_relative_to(root):
                return True
        return False

    def _require_resolvable(self, study_id: str, store, register,
                            ref: Optional[str], field: str) -> None:
        if not self._ref_resolves(study_id, store, register, ref):
            raise SurfaceRefusal(
                f"{field} {ref!r} does not resolve to an existing record "
                "in this study: name a claim, an ingested artifact, a "
                "checked citation, an anchor receipt, or a file inside "
                "the workspace — a lane-2 stage cannot rest on a "
                "reference the record does not hold (Spec 013 CLM-013-28)")

    def _confine_adapter_path(self, raw: str, field: str) -> str:
        """Resolve an adapter file path and confine it to the
        workspace (CLM-013-33). Relative paths are read as relative
        to the workspace root. A path that lands outside the
        workspace is refused: the server is not a way to read, hash,
        or fingerprint the host's files."""
        root = self.ws.root.resolve()
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = root / candidate
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root):
            raise SurfaceRefusal(
                f"{field} must name a file inside the workspace: paths "
                "outside the workspace are refused, so the server cannot "
                "be used to read or fingerprint the host's files "
                "(Spec 013 CLM-013-33)")
        return str(resolved)

    @staticmethod
    def _ok(**payload: Any) -> dict[str, Any]:
        return {"ok": True, **payload}

    # ------------------------------------------------------------ studies

    @_surface_guard
    def list_studies(self) -> dict[str, Any]:
        studies = []
        for sid in self.ws.list_study_ids():
            meta = self.ws.meta(sid)
            studies.append({"study_id": sid, "title": meta["title"]})
        return self._ok(studies=studies, actor=self.actor, role=self.role)

    @_surface_guard
    def create_study(self, study_id: str, title: str = "") -> dict[str, Any]:
        self._require("create_study")
        try:
            meta = self.ws.create_study(study_id, title)
        except st.WorkspaceError as exc:
            raise SurfaceRefusal(str(exc)) from exc
        return self._ok(study=meta)

    @_surface_guard
    def get_study_status(self, study_id: str) -> dict[str, Any]:
        store, register, info = self._load(study_id)
        verification = store.verify()
        fe = st.frozen_event(store)
        run = st.run_projection(
            store, register, str(self.ws.ledger_path(study_id)),
            st.freeze_control_fields(self.ws, study_id, store))
        return self._ok(
            study=self.ws.meta(study_id),
            chain_ok=bool(verification.ok),
            chain_detail=str(verification),
            events=len(store.events()),
            claims=[c.as_dict() for c in register.claims.values()],
            dead=info.get("dead", {}),
            frozen=(fe["payload"] if fe else None),
            freeze_root=st.freeze_checkpoint_root(store),
            run={"state": run["state"], "issued": run["issued"],
                 "reasons": run["reasons"]},
            verdicts=st.verdicts_by_claim(store),
            anchors=st.anchor_receipts(store),
            adapter_runs=adapter_runs(store),
        )

    # ------------------------------------------------------------ claims

    @_surface_guard
    def register_claim(self, study_id: str, claim_id: str, statement: str,
                       falsifier: str, kind: str = "data",
                       dependencies: Optional[list[str]] = None,
                       margin: Optional[float] = None,
                       sufficiency_floor: Optional[int] = None,
                       supersedes: Optional[str] = None) -> dict[str, Any]:
        self._require("register_claim")
        store, register, _ = self._load(study_id)
        claim = Claim(
            claim_id=claim_id, statement=statement, falsifier=falsifier,
            kind=kind, dependencies=list(dependencies or []),
            margin=margin, sufficiency_floor=sufficiency_floor,
            supersedes=supersedes)
        # The engine validates first (RegistrationError propagates
        # verbatim, before anything is appended — CLM-009-02).
        st.action_register_claim(store, register, claim, self.actor)
        return self._ok(claim=claim.as_dict())

    @_surface_guard
    def list_claims(self, study_id: str) -> dict[str, Any]:
        store, register, info = self._load(study_id)
        verdicts = st.verdicts_by_claim(store)
        out = []
        for cid in info.get("order", list(register.claims)):
            claim = register.claims.get(cid)
            if claim is None:
                continue
            entry = claim.as_dict()
            entry["groups"] = register.group_masses(cid)
            entry["verdict"] = verdicts.get(cid)
            if cid in info.get("dead", {}):
                entry["dead"] = info["dead"][cid]
            out.append(entry)
        return self._ok(claims=out)

    @_surface_guard
    def get_claim(self, study_id: str, claim_id: str) -> dict[str, Any]:
        result = self.list_claims(study_id)
        for entry in result["claims"]:
            if entry["claim_id"] == claim_id:
                return self._ok(claim=entry)
        raise SurfaceRefusal(f"no such claim in study {study_id}: {claim_id}")

    @_surface_guard
    def withdraw_claim(self, study_id: str, claim_id: str,
                       reason: str) -> dict[str, Any]:
        self._require("withdraw_claim")
        if not reason or not reason.strip():
            raise SurfaceRefusal(
                "withdrawal requires a reason: a dead record without one is "
                "a deletion wearing a costume (DN-005)")
        store, _, _ = self._load(study_id)
        event = store.withdraw(claim_id, reason=reason, actor=self.actor)
        return self._ok(event=event)

    # ------------------------------------------------------------ citations

    @_surface_guard
    def attach_citation(self, study_id: str, citation_id: str, claim_id: str,
                        proposition: str, doi: Optional[str] = None,
                        title: str = "", authors: Optional[list[str]] = None,
                        year: Optional[int] = None,
                        venue: Optional[str] = None) -> dict[str, Any]:
        self._require("attach_citation")
        store, _, _ = self._load(study_id)
        citation = vf.Citation(
            citation_id=citation_id, claim_id=claim_id,
            proposition=proposition, doi=doi, title=title,
            authors=list(authors or []), year=year, venue=venue)
        result = st.action_attach_citation(
            store, self.ws, study_id, citation,
            self._connector_factory(), self.actor)
        queue = vf.queue_state(store)
        return self._ok(result=result.as_dict(),
                        pending_queue=[i["queue_id"] for i in queue["pending"]])

    # ------------------------------------------------------------ adjudication

    @_surface_guard
    def list_adjudication_queue(self, study_id: str) -> dict[str, Any]:
        store, _, _ = self._load(study_id)
        meta = self.ws.meta(study_id)
        view = st.queue_view(store, meta)
        return self._ok(**view)

    @_surface_guard
    def decide_adjudication(self, study_id: str, queue_id: str, decision: str,
                            rationale: str = "") -> dict[str, Any]:
        self._require("decide_adjudication")
        store, _, _ = self._load(study_id)
        event = vf.decide(store, queue_id, decision,
                          adjudicator=self.actor, rationale=rationale)
        return self._ok(event=event)

    @_surface_guard
    def record_second_review(self, study_id: str, queue_id: str,
                             agrees: bool) -> dict[str, Any]:
        self._require("record_second_review")
        # Strictly boolean (Spec 013 CLM-013-34): the JSON wire can
        # carry the string "yes"; coercing it to True would let a
        # malformed call agree on the reviewer's behalf. The store
        # then validates the target itself — the item must exist, be
        # decided, and have been decided by someone else.
        if not isinstance(agrees, bool):
            raise SurfaceRefusal(
                f"second review refused: agrees must be a boolean, got "
                f"{agrees!r} — a string such as 'yes' is rejected, not "
                "coerced (Spec 013 CLM-013-34)")
        store, _, _ = self._load(study_id)
        event = store.log_second_review(queue_id, reviewer=self.actor,
                                        agrees=agrees)
        return self._ok(event=event)

    # ------------------------------------------------------------ freeze / run

    @_surface_guard
    def freeze_study(self, study_id: str, mode: str = "confirmation",
                     linked_exploratory: Optional[list[str]] = None,
                     controls: Optional[list[dict[str, Any]]] = None,
                     deployment_shape: str = "hosted") -> dict[str, Any]:
        self._require("freeze_study")
        store, register, _ = self._load(study_id)
        fields = controls if controls is not None else _default_control_fields()
        # `linked_exploratory` passes through exactly as given
        # (Spec 013 CLM-013-35): in confirmation mode an omitted
        # disclosure is not the same as an explicit empty one, and
        # the freeze layer refuses the omission — converting None
        # to [] here would silently make that disclosure for the
        # caller.
        result = st.action_freeze(
            store, register, self.ws, study_id, self.actor, mode=mode,
            linked_exploratory=linked_exploratory,
            control_fields=fields, deployment_shape=deployment_shape)
        return self._ok(**result)

    @_surface_guard
    def run_evaluation(self, study_id: str) -> dict[str, Any]:
        self._require("run_evaluation")
        store, register, info = self._load(study_id)
        result = st.action_run(
            store, register, str(self.ws.ledger_path(study_id)),
            st.freeze_control_fields(self.ws, study_id, store), self.actor)
        # A dead claim's verdict is computed but never issued — the
        # issuance path skips it, so the ledger never receives it.
        # The result marks it as not issued (Spec 013 CLM-013-35),
        # so nobody quoting this result overstates what was issued.
        dead = set(info.get("dead", {})) | {
            cid for cid, claim in register.claims.items()
            if claim.status == "dead"}
        claim_verdicts = []
        for verdict in result.claim_verdicts:
            entry = verdict.as_dict()
            entry["issued"] = (result.run_verdict == "valid"
                               and verdict.claim_id not in dead)
            if verdict.claim_id in dead:
                entry["not_issued_reason"] = (
                    "the claim is dead (withdrawn): this verdict was "
                    "computed for the record and never issued")
            claim_verdicts.append(entry)
        return self._ok(
            run_verdict=result.run_verdict,
            invalid_reasons=list(result.invalid_reasons),
            claim_verdicts=claim_verdicts,
            mode=result.mode, disclosure=list(result.disclosure))

    @_surface_guard
    def get_verdicts(self, study_id: str) -> dict[str, Any]:
        store, register, _ = self._load(study_id)
        run = st.run_projection(
            store, register, str(self.ws.ledger_path(study_id)),
            st.freeze_control_fields(self.ws, study_id, store))
        return self._ok(state=run["state"], issued=run["issued"],
                        reasons=run["reasons"],
                        verdicts=st.verdicts_by_claim(store))

    # ------------------------------------------------------------ export / deposit

    @_surface_guard
    def export_bundle(self, study_id: str) -> dict[str, Any]:
        self._require("export_bundle")
        store, register, _ = self._load(study_id)
        manifest, verification, out = st.action_export(
            store, register, self.ws, study_id, self.actor)
        return self._ok(manifest=manifest, bundle_dir=str(out),
                        verification={"ok": bool(verification.ok),
                                      "failures": list(verification.failures),
                                      "checks": verification.checks})

    @_surface_guard
    def verify_bundle(self, bundle_dir: str) -> dict[str, Any]:
        self._require("verify_bundle")
        v = export_mod.verify_bundle(bundle_dir)
        return self._ok(ok=bool(v.ok), failures=list(v.failures),
                        checks=v.checks)

    @_surface_guard
    def verify_anchor(self, bundle_dir: str,
                      public_record: dict[str, Any]) -> dict[str, Any]:
        v = export_mod.verify_anchor(bundle_dir, public_record)
        return self._ok(ok=bool(v.ok), failures=list(v.failures),
                        details=v.details)

    @_surface_guard
    def deposit_bundle(self, study_id: str, approved_by: str = "") -> dict[str, Any]:
        self._require("deposit_bundle")
        transport = self._transport()
        if transport is None:
            raise SurfaceRefusal(
                "no deposit transport is configured for this server instance: "
                "set TEKMERION_DEPOSIT_ROOT (local transport) or "
                "ZENODO_ACCESS_TOKEN (Zenodo). Approval is never "
                "configuration — it is the approved_by argument, decided by "
                "the engine's gate on every call.")
        store, _, _ = self._load(study_id)
        held = st.held_bundles(self.ws, study_id)
        if not held:
            raise SurfaceRefusal(
                "no exported bundle is held in this workspace — export one first")
        latest = st.export_events(store)[-1]
        target = held[-1]
        for p in held:
            mpath = p / "manifest.json"
            if mpath.exists():
                m = json.loads(mpath.read_text(encoding="utf-8"))
                if m.get("bundle_hash") == latest.get("bundle_hash"):
                    target = p
                    break
        # deposit_bundle's mechanical gate decides (DepositError
        # propagates verbatim when approved_by is empty — CLM-009-04).
        receipt = st.action_deposit(store, self.ws, study_id, target,
                                    transport, approved_by=approved_by,
                                    actor=self.actor)
        return self._ok(receipt=receipt)

    # ------------------------------------------------------------ adapters (lane-1)

    def _adapter_pre(self, tool: str, study_id: str, claim_id: Optional[str]):
        self._require(tool)
        store, register, _ = self._load(study_id)
        before = len(register.evidence.get(claim_id, [])) if claim_id else 0
        return store, register, before

    @_surface_guard
    def run_checkcif(self, study_id: str, cif_path: Optional[str] = None,
                     recorded_output_path: Optional[str] = None,
                     claim_id: Optional[str] = None,
                     item_id: Optional[str] = None,
                     origin_group: Optional[str] = None) -> dict[str, Any]:
        store, register, before = self._adapter_pre(
            "run_checkcif", study_id, claim_id)
        cif_bytes = (Path(self._confine_adapter_path(cif_path, "cif_path"))
                     .read_bytes() if cif_path else None)
        recorded = (Path(self._confine_adapter_path(
            recorded_output_path, "recorded_output_path")).read_bytes()
            if recorded_output_path else None)
        run = checkcif_mod.run_checkcif(
            store, cif_bytes=cif_bytes,
            cif_label=Path(cif_path).name if cif_path else "",
            actor=self.actor, claim_id=claim_id, register=register,
            item_id=item_id, origin_group=origin_group,
            recorded_output=recorded,
            recorded_provenance=(f"recorded output file {recorded_output_path}"
                                 if recorded_output_path else None))
        self._harvest_adapter_items(study_id, register, claim_id, before)
        return self._ok(run=run.as_dict())

    @_surface_guard
    def run_codecheck(self, study_id: str, certificate_id: str,
                      claim_id: Optional[str] = None,
                      item_id: Optional[str] = None,
                      origin_group: Optional[str] = None,
                      work_outputs: Optional[list[str]] = None) -> dict[str, Any]:
        store, register, before = self._adapter_pre(
            "run_codecheck", study_id, claim_id)
        run = codecheck_mod.ingest_codecheck_certificate(
            store, certificate_id=certificate_id, actor=self.actor,
            claim_id=claim_id, register=register, item_id=item_id,
            origin_group=origin_group, work_outputs=work_outputs,
            fetcher=self._codecheck_fetcher)
        self._harvest_adapter_items(study_id, register, claim_id, before)
        return self._ok(run=run.as_dict())

    @_surface_guard
    def run_grim(self, study_id: str, cases: list[dict[str, Any]],
                 claim_id: Optional[str] = None,
                 item_id: Optional[str] = None,
                 origin_group: Optional[str] = None) -> dict[str, Any]:
        # An empty case list is refused (Spec 013 CLM-013-35): a run
        # over zero cases would still be recorded as a run, and a
        # recorded run that checked nothing reads as a check.
        if not isinstance(cases, list) or not cases:
            raise SurfaceRefusal(
                "run_grim refused: the case list is empty — a GRIM run "
                "over zero cases checks nothing and is not recorded "
                "(Spec 013 CLM-013-35)")
        store, register, before = self._adapter_pre(
            "run_grim", study_id, claim_id)
        run = stat_mod.run_grim_family(
            store, cases=cases, actor=self.actor, claim_id=claim_id,
            register=register, item_id=item_id, origin_group=origin_group)
        self._harvest_adapter_items(study_id, register, claim_id, before)
        return self._ok(run=run.as_dict())

    @_surface_guard
    def run_statcheck(self, study_id: str,
                      manuscript_path: Optional[str] = None,
                      recorded_output_path: Optional[str] = None,
                      claim_id: Optional[str] = None,
                      item_id: Optional[str] = None,
                      origin_group: Optional[str] = None) -> dict[str, Any]:
        store, register, before = self._adapter_pre(
            "run_statcheck", study_id, claim_id)
        text = (Path(self._confine_adapter_path(
            manuscript_path, "manuscript_path")).read_text(encoding="utf-8")
            if manuscript_path else None)
        recorded = (Path(self._confine_adapter_path(
            recorded_output_path, "recorded_output_path")).read_bytes()
            if recorded_output_path else None)
        run = stat_mod.run_statcheck(
            store, text=text, actor=self.actor, claim_id=claim_id,
            register=register, item_id=item_id, origin_group=origin_group,
            recorded_output=recorded,
            recorded_provenance=(f"recorded output file {recorded_output_path}"
                                 if recorded_output_path else None))
        self._harvest_adapter_items(study_id, register, claim_id, before)
        return self._ok(run=run.as_dict())

    @_surface_guard
    def list_adapter_runs(self, study_id: str,
                          adapter_id: Optional[str] = None) -> dict[str, Any]:
        store, _, _ = self._load(study_id)
        return self._ok(runs=adapter_runs(store, adapter_id))

    # ------------------------------------------------------------ math (Spec 003)

    @_surface_guard
    def register_theorem(self, study_id: str, parent_id: str, headline: str,
                         claimant: str, problem: str, margin: float = 0.1,
                         sufficiency_floor: int = 1,
                         statements: Optional[dict[str, str]] = None
                         ) -> dict[str, Any]:
        self._require("register_theorem")
        store, register, _ = self._load(study_id)
        claims = mathclaims.register_theorem(
            register, parent_id=parent_id, headline=headline,
            claimant=claimant, problem=problem, margin=margin,
            sufficiency_floor=sufficiency_floor, statements=statements)
        for claim in claims.values():
            store.register_claim(claim.claim_id, claim.as_dict(), actor=self.actor)
        return self._ok(claims={k: c.as_dict() for k, c in claims.items()})

    @_surface_guard
    def pin_faithfulness(self, study_id: str, claim_id: str,
                         formal_statement: str, original_statement: str,
                         original_source: str) -> dict[str, Any]:
        self._require("pin_faithfulness")
        store, register, _ = self._load(study_id)
        # Pinning is validated (Spec 013 CLM-013-29): the claim must
        # exist in the register (an empty pin for a claim whose
        # registration failed pinned seq 1 of a study in the red-team
        # probe), the fields must be non-empty (refused in
        # mathclaims itself), and replacing an existing pair is an
        # adjudicator act — a researcher cannot quietly re-pin a
        # weaker pair over a stronger one.
        if claim_id not in register.claims:
            raise SurfaceRefusal(
                f"faithfulness pin refused: no such claim in study "
                f"{study_id}: {claim_id} — a pin can only attach to a "
                "claim on the record (Spec 013 CLM-013-29)")
        if mathclaims.faithfulness_pair(store, claim_id) is not None \
                and self.role != "adjudicator":
            raise SurfaceRefusal(
                f"faithfulness re-pin refused: claim {claim_id} already "
                f"has a pinned pair, and replacing it requires the "
                f"adjudicator role — this instance runs as {self.actor!r} "
                f"({self.role}). The existing pair stands; the full pin "
                "history is on the record (Spec 013 CLM-013-29)")
        event = mathclaims.pin_faithfulness(
            store, claim_id=claim_id, formal_statement=formal_statement,
            original_statement=original_statement,
            original_source=original_source, actor=self.actor)
        return self._ok(event=event)

    @_surface_guard
    def ingest_lean(self, study_id: str, url: str,
                    theorem_name: Optional[str] = None,
                    source_compile_claim: Optional[dict[str, Any]] = None
                    ) -> dict[str, Any]:
        self._require("ingest_lean")
        # http/https only (Spec 013 CLM-013-33): a file:// URL turns
        # the ingestion record into a fingerprint of a local file —
        # its hash and length, on the record, for a file the study
        # has no business reading.
        scheme = urlparse(url or "").scheme.lower()
        if scheme not in ("http", "https"):
            raise SurfaceRefusal(
                f"ingest_lean refused: only http and https URLs are "
                f"ingested, got scheme {scheme!r} — local files and "
                "other schemes are not artifacts the server fetches "
                "(Spec 013 CLM-013-33)")
        store, _, _ = self._load(study_id)
        ingestion = mathclaims.ingest_lean_artifact(
            store, url=url, actor=self.actor, theorem_name=theorem_name,
            source_compile_claim=source_compile_claim)
        return self._ok(ingestion=ingestion.as_dict())

    @_surface_guard
    def record_digestion(self, study_id: str, claim_id: str, explainer: str,
                         artifact_ref: str,
                         claimant_explanation: bool = False) -> dict[str, Any]:
        # Adjudicator-only via TOOL_ROLES (Spec 013 CLM-013-28), and
        # the explanation artifact must resolve to a record the
        # study holds — an invented artifact reference would clear
        # the verified-but-unexplained risk flag on nothing.
        self._require("record_digestion")
        store, register, _ = self._load(study_id)
        if not explainer or not explainer.strip():
            raise SurfaceRefusal(
                "digestion refused: name the human who explained the "
                "result — digestion is a named human's work, and an "
                "unnamed explanation is not one (Spec 013 CLM-013-28)")
        self._require_resolvable(study_id, store, register,
                                  artifact_ref, "artifact_ref")
        event = mathclaims.record_digestion(
            store, claim_id=claim_id, explainer=explainer,
            artifact_ref=artifact_ref, actor=self.actor,
            claimant_explanation=bool(claimant_explanation))
        return self._ok(event=event)

    @_surface_guard
    def record_acceptance(self, study_id: str, claim_id: str, stage: str,
                          by: str, evidence_ref: str) -> dict[str, Any]:
        # Adjudicator-only via TOOL_ROLES (Spec 013 CLM-013-28), and
        # the evidence reference must resolve to a record the study
        # holds — an invented reference would advance the claim's
        # lane-2 stage on nothing.
        self._require("record_acceptance")
        store, register, _ = self._load(study_id)
        if not by or not by.strip():
            raise SurfaceRefusal(
                "acceptance refused: name the human the stage is "
                "credited to — lane-2 stages are human acts, and an "
                "unnamed one is not one (Spec 013 CLM-013-28)")
        self._require_resolvable(study_id, store, register,
                                  evidence_ref, "evidence_ref")
        event = mathclaims.record_acceptance(
            store, claim_id=claim_id, stage=stage, by=by,
            evidence_ref=evidence_ref, actor=self.actor)
        return self._ok(event=event)

    @_surface_guard
    def get_theorem_state(self, study_id: str, claim_id: str) -> dict[str, Any]:
        store, _, _ = self._load(study_id)
        verdicts = st.verdicts_by_claim(store)
        parent = claim_id
        proof_id = mathclaims.subclaim_id(parent, "proof_verified")
        # Pins are appended under the faithful sub-claim's id; the
        # projection resolves it from the parent so the pair — and
        # its history — is what the operator actually sees.
        try:
            faithful_id = mathclaims.subclaim_id(parent, mathclaims.FAITHFUL)
        except ValueError:
            faithful_id = claim_id
        proof_verdict = (verdicts.get(proof_id) or {}).get("verdict")
        return self._ok(
            claim_id=claim_id,
            lane1=mathclaims.lane1_summary(store, claim_id,
                                           proof_verdict=proof_verdict),
            lane2=mathclaims.lane2_state(store, claim_id),
            digestion=mathclaims.digestion_state(store, claim_id),
            acceptance=mathclaims.acceptance_state(store, claim_id),
            faithfulness_pair=mathclaims.faithfulness_pair(store, faithful_id),
            faithfulness_history=mathclaims.faithfulness_history(
                store, faithful_id),
            ingestions=mathclaims.ingestions_for(store, ""),
        )


def _default_control_fields() -> list[dict[str, Any]]:
    """The UI's default control set (ui.server._DEFAULT_CONTROL_FIELDS),
    mirrored: positive + negative + swap, failure modes named, no
    fixtures. A freeze with these registers the controls; a run
    executes the swap control and any fixture-carrying controls the
    caller froze with."""
    return [
        {"kind": "positive",
         "failure_mode": "retrieval broken: known-true claim not supported",
         "expected": "supported", "representative_rationale": "",
         "fixture": None},
        {"kind": "negative",
         "failure_mode": "verification decorative: fabricated citation accepted",
         "expected": "contradicted", "representative_rationale": "",
         "fixture": None},
        {"kind": "swap",
         "failure_mode": "integrity machinery decorative: provenance swap undetected",
         "expected": None, "representative_rationale": "", "fixture": None},
    ]


# ------------------------------------------------------------ MCP SDK shell

def build_server(session: Session):
    """Register the session's tool functions with the MCP SDK.

    Kept deliberately thin: each registration forwards the declared
    arguments to the handler and lets exceptions propagate — the SDK
    turns them into error results carrying str(exc), which for engine
    exceptions is the verbatim refusal text (CLM-009-02)."""
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as exc:  # pragma: no cover
        raise ConfigError(
            "the MCP SDK is not installed: the server is the optional extra "
            "— install with `pip install 'tekmerion[mcp]'` (spec 009 §2)"
        ) from exc

    server = MCPServer(
        "tekmerion",
        instructions=(
            "Tekmerion: defensible research records. Every claim needs a "
            "falsifier; verdicts come only from frozen registrations and "
            "valid runs; an INVALID run issues no verdicts and is reported "
            "as INVALID. Engine refusals are final — do not work around "
            "them. See the tekmerion skill for playbooks."
        ),
    )

    def reg(fn):
        # SDK 2.x masks non-ToolError exceptions ("Error executing
        # tool <name>" only). Engine refusals are deliberate,
        # client-facing messages, so the shell converts every handler
        # exception to a ToolError carrying str(exc) verbatim —
        # that conversion is what makes CLM-009-02 true on the wire.
        import functools

        from mcp.server.mcpserver.exceptions import ToolError

        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except ToolError:
                raise
            except Exception as exc:
                raise ToolError(str(exc)) from exc

        server.tool()(wrapped)
        return fn

    @reg
    def list_studies() -> dict:
        """List the studies in this instance's workspace."""
        return session.list_studies()

    @reg
    def create_study(study_id: str, title: str = "") -> dict:
        """Create a study (one append-only Axiomere ledger). Roles: researcher, adjudicator."""
        return session.create_study(study_id, title)

    @reg
    def get_study_status(study_id: str) -> dict:
        """Study projection: chain verification, claims, freeze state, run state, verdicts, anchors, adapter runs."""
        return session.get_study_status(study_id)

    @reg
    def register_claim(study_id: str, claim_id: str, statement: str,
                       falsifier: str, kind: str = "data",
                       dependencies: Optional[list[str]] = None,
                       margin: Optional[float] = None,
                       sufficiency_floor: Optional[int] = None,
                       supersedes: Optional[str] = None) -> dict:
        """Register a claim. The falsifier is mandatory — without one the engine refuses and nothing is appended."""
        return session.register_claim(
            study_id, claim_id, statement, falsifier, kind=kind,
            dependencies=dependencies, margin=margin,
            sufficiency_floor=sufficiency_floor, supersedes=supersedes)

    @reg
    def list_claims(study_id: str) -> dict:
        """All claims in registration order, with origin-group masses and any issued verdict."""
        return session.list_claims(study_id)

    @reg
    def get_claim(study_id: str, claim_id: str) -> dict:
        """One claim with its evidence groups and verdict."""
        return session.get_claim(study_id, claim_id)

    @reg
    def withdraw_claim(study_id: str, claim_id: str, reason: str) -> dict:
        """Withdraw a claim the only way that exists: a dead snapshot with the reason on the record (score 0.0). There is no delete."""
        return session.withdraw_claim(study_id, claim_id, reason)

    @reg
    def attach_citation(study_id: str, citation_id: str, claim_id: str,
                        proposition: str, doi: Optional[str] = None,
                        title: str = "", authors: Optional[list[str]] = None,
                        year: Optional[int] = None,
                        venue: Optional[str] = None) -> dict:
        """Attach a citation to a claim and run the verification pipeline (resolution, agreement, content check). Exactly one outcome is ledgered per citation; disagreements are quarantined to the adjudication queue."""
        return session.attach_citation(
            study_id, citation_id, claim_id, proposition, doi=doi,
            title=title, authors=authors, year=year, venue=venue)

    @reg
    def list_adjudication_queue(study_id: str) -> dict:
        """Pending and decided adjudication items, the RT-4 second-review sample, and the rubber-stamp report."""
        return session.list_adjudication_queue(study_id)

    @reg
    def decide_adjudication(study_id: str, queue_id: str, decision: str,
                            rationale: str = "") -> dict:
        """Record a named adjudication decision (adjudicator role only). Decisions are appends; a decided item cannot be re-decided."""
        return session.decide_adjudication(study_id, queue_id, decision,
                                           rationale)

    @reg
    def record_second_review(study_id: str, queue_id: str,
                             agrees: bool) -> dict:
        """Record an independent second review of an adjudication decision (reviewer or adjudicator)."""
        return session.record_second_review(study_id, queue_id, agrees)

    @reg
    def freeze_study(study_id: str, mode: str = "confirmation",
                     linked_exploratory: Optional[list[str]] = None,
                     controls: Optional[list[dict]] = None,
                     deployment_shape: str = "hosted") -> dict:
        """Freeze the registration (adjudicator only). Fails closed: the engine's FreezeError names every failed check. For confirmation mode, linked_exploratory must be disclosed — pass [] to state 'none'."""
        return session.freeze_study(
            study_id, mode=mode, linked_exploratory=linked_exploratory,
            controls=controls, deployment_shape=deployment_shape)

    @reg
    def run_evaluation(study_id: str) -> dict:
        """Run the evaluation against the frozen registration (adjudicator only). A valid run appends verdict.issued per claim; an INVALID run appends nothing and says why."""
        return session.run_evaluation(study_id)

    @reg
    def get_verdicts(study_id: str) -> dict:
        """Issued verdicts, or the run projection: an INVALID replay is returned as INVALID with the engine's reasons."""
        return session.get_verdicts(study_id)

    @reg
    def export_bundle(study_id: str) -> dict:
        """Export the audit bundle and re-verify it standalone. Refuses (ExportError) on a broken chain or an unfrozen study."""
        return session.export_bundle(study_id)

    @reg
    def verify_bundle(bundle_dir: str) -> dict:
        """Standalone bundle verification — consumes only the bundle directory."""
        return session.verify_bundle(bundle_dir)

    @reg
    def verify_anchor(bundle_dir: str, public_record: dict) -> dict:
        """Check a bundle against a public anchor record (e.g. its Zenodo record JSON)."""
        return session.verify_anchor(bundle_dir, public_record)

    @reg
    def deposit_bundle(study_id: str, approved_by: str = "") -> dict:
        """Deposit the latest exported bundle through the configured transport (adjudicator only). The adjudicator-approval gate is mechanical: with approved_by empty the engine refuses and nothing is appended, and an approver equal to the depositing actor is refused — approval is a second person's act."""
        return session.deposit_bundle(study_id, approved_by)

    @reg
    def run_checkcif(study_id: str, cif_path: Optional[str] = None,
                     recorded_output_path: Optional[str] = None,
                     claim_id: Optional[str] = None,
                     item_id: Optional[str] = None,
                     origin_group: Optional[str] = None) -> dict:
        """checkCIF/PLATON adapter (P2, lane-1): live PLATON where a binary exists, else a recorded output, else the run records not_runnable_here. A clean check is context, never support (CLM-006-02)."""
        return session.run_checkcif(
            study_id, cif_path=cif_path,
            recorded_output_path=recorded_output_path, claim_id=claim_id,
            item_id=item_id, origin_group=origin_group)

    @reg
    def run_codecheck(study_id: str, certificate_id: str,
                      claim_id: Optional[str] = None,
                      item_id: Optional[str] = None,
                      origin_group: Optional[str] = None,
                      work_outputs: Optional[list[str]] = None) -> dict:
        """CODECHECK adapter (P3, lane-1): ingest a certificate from the public register as scoped re-execution evidence. A certificate never certifies correctness (CLM-007-02)."""
        return session.run_codecheck(
            study_id, certificate_id, claim_id=claim_id, item_id=item_id,
            origin_group=origin_group, work_outputs=work_outputs)

    @reg
    def run_grim(study_id: str, cases: list[dict],
                 claim_id: Optional[str] = None,
                 item_id: Optional[str] = None,
                 origin_group: Optional[str] = None) -> dict:
        """GRIM/GRIMMER adapter (P7, lane-1): cases are {label, mean, sd?, n, items?} with mean/sd as strings (precision is data). An impossibility is a falsifier observation for a reporting-consistency claim."""
        return session.run_grim(
            study_id, cases, claim_id=claim_id, item_id=item_id,
            origin_group=origin_group)

    @reg
    def run_statcheck(study_id: str, manuscript_path: Optional[str] = None,
                      recorded_output_path: Optional[str] = None,
                      claim_id: Optional[str] = None,
                      item_id: Optional[str] = None,
                      origin_group: Optional[str] = None) -> dict:
        """statcheck adapter (P7, lane-1): live R seam where an R runtime exists, else recorded output, else not_runnable_here. Extraction coverage is part of every record — no flags is not a clean paper."""
        return session.run_statcheck(
            study_id, manuscript_path=manuscript_path,
            recorded_output_path=recorded_output_path, claim_id=claim_id,
            item_id=item_id, origin_group=origin_group)

    @reg
    def list_adapter_runs(study_id: str,
                          adapter_id: Optional[str] = None) -> dict:
        """Replay every adapter run record in the ledger, provenance intact."""
        return session.list_adapter_runs(study_id, adapter_id)

    @reg
    def register_theorem(study_id: str, parent_id: str, headline: str,
                         claimant: str, problem: str, margin: float = 0.1,
                         sufficiency_floor: int = 1,
                         statements: Optional[dict[str, str]] = None) -> dict:
        """Register a theorem claim as a parent plus its five Spec 003 sub-claims (faithful, proof, open, attribution, significance), each with its registered falsifier."""
        return session.register_theorem(
            study_id, parent_id, headline, claimant, problem, margin=margin,
            sufficiency_floor=sufficiency_floor, statements=statements)

    @reg
    def pin_faithfulness(study_id: str, claim_id: str, formal_statement: str,
                         original_statement: str,
                         original_source: str) -> dict:
        """Pin a formal statement beside the original problem statement, verbatim — the pair the faithful sub-claim is judged from. The claim must exist and every field must be non-empty; replacing an existing pair is adjudicator-only, and the pin history stays on the record."""
        return session.pin_faithfulness(
            study_id, claim_id, formal_statement, original_statement,
            original_source)

    @reg
    def ingest_lean(study_id: str, url: str,
                    theorem_name: Optional[str] = None,
                    source_compile_claim: Optional[dict] = None) -> dict:
        """Ingest a Lean artifact from an http/https URL: fetch, SHA-256, sorry/admit counts, axiom audit where a toolchain exists. Other schemes (file:// and the rest) are refused. The compile state is recorded as it is (not_attempted / claimed_by_source / run_by_us / not_runnable_here) — never upgraded."""
        return session.ingest_lean(
            study_id, url, theorem_name=theorem_name,
            source_compile_claim=source_compile_claim)

    @reg
    def record_digestion(study_id: str, claim_id: str, explainer: str,
                         artifact_ref: str,
                         claimant_explanation: bool = False) -> dict:
        """Lane-2 record (adjudicator only): a named human's explanation of a result. The artifact_ref must resolve to a record the study holds. Claimant self-explanation is recorded but labeled as the claimant's."""
        return session.record_digestion(
            study_id, claim_id, explainer, artifact_ref,
            claimant_explanation)

    @reg
    def record_acceptance(study_id: str, claim_id: str, stage: str, by: str,
                          evidence_ref: str) -> dict:
        """Lane-2 record (adjudicator only): stage advancement (accepted|digested) on named human evidence — the evidence_ref must resolve to a record the study holds. Lane-1 activity can never move lane 2."""
        return session.record_acceptance(study_id, claim_id, stage, by,
                                         evidence_ref)

    @reg
    def get_theorem_state(study_id: str, claim_id: str) -> dict:
        """Lane-1 summary and lane-2 state for a theorem claim, stated separately — lane 1 never displays as lane 2."""
        return session.get_theorem_state(study_id, claim_id)

    return server


def main(argv: Optional[list[str]] = None) -> int:
    try:
        config = ServerConfig.from_env()
    except ConfigError as exc:
        print(f"tekmerion-mcp: {exc}", flush=True)
        return 2
    session = Session(config)
    try:
        server = build_server(session)
    except ConfigError as exc:
        print(f"tekmerion-mcp: {exc}", flush=True)
        return 2
    server.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
