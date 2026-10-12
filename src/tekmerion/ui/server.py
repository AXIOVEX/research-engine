"""HTTP surface for the register-first workspace (T219).

Stdlib only. Rendering is server-side; every mutation is a form POST
that lands on the production services (`tekmerion.ui.state` actions),
and every engine refusal is re-rendered on the originating screen
with the engine's message verbatim.

Identity (CLM-002-38): the event actor is the identity supplied to
the server, never a value typed per action. In deployment that is
the SSO layer, whose hook is the `X-Tekmerion-Actor` /
`X-Tekmerion-Role` header pair; for local use the same identity can
arrive as `?actor=` / `?role=` (a header always wins). Roles are the
WS6 §1 views: researcher, reviewer, adjudicator, integrity. The
integrity view is offered no mutating control, and any forged POST
under it is refused server-side as well.
"""

from __future__ import annotations

import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import parse_qs, quote, urlparse

from .. import deposit as deposit_mod
from .. import export as export_mod
from .. import verification as vf
from ..claims import Claim, ClaimRegister, RegistrationError
from ..connectors import CrossrefConnector
from ..freeze import FreezeError
from . import state as st
from . import views

STYLE_CSS = (Path(__file__).parent / "style.css").read_bytes()

ACTOR_NOTES = {
    "register": ("In production this identity arrives via SSO; event actors are "
                 "recorded from it, never typed per action (WS6 §1)."),
    "queue": ("Decisions record the adjudicator from this identity. A researcher "
              "or reviewer sees this queue read-only."),
    "freeze": ("Freezes, runs, and verdicts record the acting identity from SSO; "
               "event actors are never typed per action (WS6 §1)."),
    "export": ("Deposits record the approving adjudicator from this identity; "
               "event actors are never typed per action (WS6 §1)."),
    "default": ("In production this identity arrives via SSO; event actors are "
                "recorded from it, never typed per action (WS6 §1)."),
}

# Which roles may perform each mutation (WS6 §1, CLM-002-38).
PERMISSIONS: dict[str, tuple[str, ...]] = {
    "create_study": ("researcher", "adjudicator"),
    "register_claim": ("researcher", "adjudicator"),
    "attach_citation": ("researcher", "adjudicator"),
    "withdraw": ("researcher", "adjudicator"),
    "decide": ("adjudicator",),
    "second_review": ("reviewer", "adjudicator"),
    "freeze": ("adjudicator",),
    "run": ("adjudicator",),
    "export": ("researcher", "reviewer", "adjudicator"),
    "deposit": ("adjudicator",),
    "verify_bundle": st.ROLES,
}

_DEFAULT_CONTROL_FIELDS = [
    {"kind": "positive",
     "failure_mode": "retrieval broken: known-true claim not supported",
     "expected": "supported", "representative_rationale": "", "fixture": None},
    {"kind": "negative",
     "failure_mode": "verification decorative: fabricated citation accepted",
     "expected": "contradicted", "representative_rationale": "", "fixture": None},
    {"kind": "swap",
     "failure_mode": "integrity machinery decorative: provenance swap undetected",
     "expected": None, "representative_rationale": "", "fixture": None},
]


class Refused(Exception):
    """A request the workspace refuses before any engine call."""


class App:
    """One workspace + its injectable seams (connectors, transports).

    The seams exist for tests and for the deployment's token
    configuration; the defaults are the production ones (live
    Crossref; Zenodo iff a token is configured in the environment).
    """

    def __init__(self, root: str | Path, *,
                 connector_factory: Optional[Callable[[], list]] = None,
                 transport_factory: Optional[Callable[[], Any]] = None) -> None:
        self.ws = st.Workspace(root)
        self._connector_factory = connector_factory or (lambda: [CrossrefConnector()])
        self._transport_factory = transport_factory or self._default_transport

    @staticmethod
    def _default_transport() -> Any:
        import os
        if os.environ.get("ZENODO_ACCESS_TOKEN"):
            return deposit_mod.ZenodoTransport()
        return None

    # ------------------------------------------------------------ context

    def study_ctx(self, sid: str) -> dict[str, Any]:
        store = self.ws.open(sid)
        register, info = st.rebuild_register(store)
        retrieved_sidecar = self.ws.read_sidecar(sid, "retrieved.json", {}) or {}
        st.derive_evidence(store, register, retrieved_sidecar)
        meta = self.ws.meta(sid)
        fe = st.frozen_event(store)
        anchors = st.anchor_receipts(store)
        queue = st.queue_view(store, meta)
        run = st.run_projection(store, register, str(self.ws.ledger_path(sid)),
                                st.freeze_control_fields(self.ws, sid, store))
        return {
            "store": store, "register": register, "info": info, "meta": meta,
            "study": {
                "id": sid, "title": meta["title"],
                "frozen": fe is not None,
                "anchored_mechanism": (anchors[-1].get("mechanism")
                                       if anchors else None),
            },
            "frozen_event": fe, "anchors": anchors, "queue": queue, "run": run,
            "pending_count": len(queue["pending"]),
            "registration_hash": (fe["payload"].get("registration_hash")
                                  if fe else None),
            "freeze_root": st.freeze_checkpoint_root(store),
            "head_root": st.head_checkpoint_root(store),
            "frozen_claims": (fe["payload"].get("claims", []) if fe else []),
        }

    # ------------------------------------------------------------ screens

    def screen_register(self, sid: str, ident: dict) -> str:
        c = self.study_ctx(sid)
        store, register = c["store"], c["register"]
        results = st.citation_results(store)
        cov = st.coverage(register)
        claim_rows = []
        for cid in c["info"]["order"]:
            claim = register.claims.get(cid)
            if claim is None:
                continue
            verdicts = c["run"]["verdicts"].get(cid) if c["run"]["issued"] else None
            claim_rows.append({
                "claim": claim, "dead": c["info"]["dead"].get(cid),
                "groups": register.group_masses(cid),
                "verdict": verdicts,
            })
        total = cov["groups"]
        ctx = {
            **_base_ctx(c, ident, "register"),
            "rows": claim_rows,
            "stats": {
                "claims": len(c["info"]["order"]),
                "citations": len(results),
                "resolved": sum(1 for r in results.values()
                                if r.get("resolution") == "resolved"),
                "cov_pct": int(100 * cov["checked"] / total) if total else 0,
            },
            "ledger_ok": store.verify().ok,
            "can_register": ident["role"] in PERMISSIONS["register_claim"],
        }
        return views.render_register(ctx)

    def screen_register_form(self, sid: str, ident: dict, *,
                             values: Optional[dict] = None,
                             refusal: Optional[str] = None) -> str:
        c = self.study_ctx(sid)
        ctx = {**_base_ctx(c, ident, "register"), "values": values or {},
               "refusal": refusal,
               "can_register": ident["role"] in PERMISSIONS["register_claim"]}
        return views.render_register_form(ctx)

    def screen_claim(self, sid: str, cid: str, ident: dict, *,
                     refusal: Optional[str] = None) -> str:
        c = self.study_ctx(sid)
        store, register = c["store"], c["register"]
        claim = register.claims.get(cid)
        if claim is None:
            raise Refused(f"no such claim in this register: {cid}")
        dead = c["info"]["dead"].get(cid)
        queue = st.queue_view(store, c["meta"])
        decided_by_cit = {i.get("citation_id"): i for i in queue["decided"]
                          if i.get("citation_id")}
        pending_cits = {i.get("citation_id") for i in queue["pending"]}
        cited_inputs = self.ws.read_sidecar(sid, "citations.json", {}) or {}
        retrieved_sidecar = self.ws.read_sidecar(sid, "retrieved.json", {}) or {}
        cit_rows, retrieved_cards = [], []
        queue_by_seq = {i.get("citation_id"): i for i in
                        queue["pending"] + queue["decided"] if i.get("citation_id")}
        for cit_id, payload in st.citation_results(store).items():
            if payload.get("claim_id") != cid:
                continue
            item = queue_by_seq.get(cit_id)
            if item is not None and item in queue["decided"]:
                disp = (f'{views.chip("decision: " + item["decision"].replace("_", " "))} '
                        f'<a href="/studies/{sid}/queue">adjudicated · {item["queue_id"]}</a>')
            elif cit_id in pending_cits:
                disp = (f'<span class="chip invalid">quarantined · pending</span> '
                        f'<a href="/studies/{sid}/queue">queue</a>')
            else:
                disp = '<span class="muted">stands</span>'
            cit_rows.append({"payload": payload,
                             "cited": cited_inputs.get(cit_id), "disposition": disp})
            if cit_id in retrieved_sidecar:
                retrieved_cards.append({"payload": payload,
                                        "record": retrieved_sidecar[cit_id]})
        groups = []
        for g in register.group_masses(cid):
            items = [it for it in register.evidence.get(cid, [])
                     if it.origin_group == g["origin_group"]]
            groups.append({**g, "items": items})
        cov = st.coverage(register)["per_claim"].get(cid, {"groups": 0, "checked": 0})
        verdict = c["run"]["verdicts"].get(cid) if c["run"]["issued"] else None
        ctx = {
            **_base_ctx(c, ident, "register"), "claim": claim, "dead": dead,
            "groups": groups, "citations": cit_rows, "retrieved": retrieved_cards,
            "verdict": verdict, "run_state": c["run"]["state"],
            "cov_checked": cov["checked"], "cov_groups": cov["groups"],
            "can_mutate": ident["role"] in PERMISSIONS["register_claim"],
            "refusal": refusal,
            "registration_hash": c["registration_hash"],
        }
        return views.render_claim(ctx)

    def screen_queue(self, sid: str, ident: dict, *,
                     refusal: Optional[str] = None) -> str:
        c = self.study_ctx(sid)
        ctx = {**_base_ctx(c, ident, "queue"), "queue": c["queue"],
               "fraction": c["meta"]["second_review_fraction"],
               "sampled_unreviewed": set(c["queue"]["sampled_unreviewed"]),
               "can_decide": ident["role"] in PERMISSIONS["decide"],
               "can_review": ident["role"] in PERMISSIONS["second_review"],
               "refusal": refusal}
        return views.render_queue(ctx)

    def screen_freeze(self, sid: str, ident: dict, *,
                      refusal: Optional[str] = None) -> str:
        c = self.study_ctx(sid)
        store = c["store"]
        fields = st.freeze_control_fields(self.ws, sid, store)
        verdict_rows = []
        if c["run"]["issued"]:
            for cid in c["info"]["order"]:
                v = c["run"]["verdicts"].get(cid)
                if v:
                    verdict_rows.append(v)
        frozen = None
        if c["frozen_event"] is not None:
            p = c["frozen_event"]["payload"]
            frozen = {
                "registration_hash": p.get("registration_hash"),
                "mode": p.get("mode"), "actor": c["frozen_event"]["actor"],
                "claims": p.get("claims", []),
                "linked": p.get("linked_exploratory", []),
            }
        sidecar = self.ws.read_sidecar(sid, "freeze.json", {}) or {}
        ctx = {
            **_base_ctx(c, ident, "freeze"), "frozen": frozen,
            "deployment_shape": sidecar.get("deployment_shape"),
            "control_fields": fields, "control_defaults": _DEFAULT_CONTROL_FIELDS,
            "verdict_rows": verdict_rows,
            "can_freeze": ident["role"] in PERMISSIONS["freeze"],
            "can_run": ident["role"] in PERMISSIONS["run"],
            "refusal": refusal,
        }
        return views.render_freeze(ctx)

    def screen_export(self, sid: str, ident: dict, *,
                      refusal: Optional[str] = None,
                      verify_path: Optional[str] = None,
                      verify_html: Optional[str] = None) -> str:
        c = self.study_ctx(sid)
        exports = st.export_events(c["store"])
        held = {p.name: p for p in st.held_bundles(self.ws, sid)}
        current = None
        if exports:
            latest = exports[-1]
            name = None
            manifest = None
            for p in held.values():
                m = _read_manifest(p)
                if m and m.get("bundle_hash") == latest.get("bundle_hash"):
                    name, manifest = p.name, m
                    break
            verification = None
            if name is not None:
                v = export_mod.verify_bundle(str(held[name]))
                verification = {"ok": v.ok, "failures": v.failures}
            current = {
                "name": name or "bundle (exported)",
                "bundle_hash": latest.get("bundle_hash"),
                "event_count": latest.get("event_count"),
                "head_root": latest.get("checkpoint_root"),
                "actor": latest.get("_actor"), "seq": latest.get("_seq"),
                "verification": verification,
            }
        public_checks: dict[int, dict] = {}
        public_record = self.ws.read_sidecar(sid, "public-record.json")
        if public_record:
            for receipt in c["anchors"]:
                for p in held.values():
                    m = _read_manifest(p)
                    if m and m.get("bundle_hash") == receipt.get("bundle_hash"):
                        v = export_mod.verify_anchor(str(p), public_record)
                        public_checks[receipt["_seq"]] = {
                            "ok": v.ok, "failures": v.failures}
                        break
        transport = self._transport_factory()
        deposit_ctx = None
        if ident["role"] not in PERMISSIONS["deposit"]:
            deposit_ctx = {
                "request": True,
                "link": views.role_links(f"/studies/{sid}/export",
                                         ident["actor"])["adjudicator"],
            }
        if ident["role"] in PERMISSIONS["deposit"]:
            if not exports:
                deposit_ctx = {"available": False,
                               "reason": "Nothing to deposit yet — export a bundle first."}
            elif transport is None:
                deposit_ctx = {"available": False,
                               "reason": ("No deposit transport is configured on this "
                                          "workspace (a Zenodo token in the environment "
                                          "enables deposits). The deposit gate itself — "
                                          "an adjudicator's recorded approval — is "
                                          "unchanged; it simply has nowhere to go.")}
            else:
                deposit_ctx = {
                    "available": True,
                    "transport_label": getattr(transport, "mechanism",
                                               type(transport).__name__),
                    "transport_is_test": getattr(transport, "mechanism", "")
                    == "local-filesystem",
                }
        ctx = {
            **_base_ctx(c, ident, "export"), "anchors": c["anchors"],
            "current_export": current, "public_checks": public_checks,
            "can_export": ident["role"] in PERMISSIONS["export"],
            "deposit": deposit_ctx, "refusal": refusal,
            "verify_path": verify_path, "verify_result_html": verify_html,
        }
        return views.render_export(ctx)

    def screen_picker(self, ident: dict, *, refusal: Optional[str] = None) -> str:
        studies = []
        for sid in self.ws.list_study_ids():
            c = self.study_ctx(sid)
            studies.append({
                "id": sid, "title": c["meta"]["title"],
                "claims": len(c["info"]["order"]),
                "events": len(c["store"].events()),
                "frozen": c["frozen_event"] is not None,
                "anchored": bool(c["anchors"]),
            })
        ctx = {"actor": ident["actor"], "role": ident["role"],
               "links": views.role_links("/", ident["actor"]),
               "actor_note": ACTOR_NOTES["default"],
               "studies": studies,
               "can_create": ident["role"] in PERMISSIONS["create_study"],
               "refusal": refusal}
        return views.render_picker(ctx)

    def screen_specimens(self, ident: dict) -> str:
        demo = None
        for sid in self.ws.list_study_ids():
            if self.ws.read_sidecar(sid, "meta.json", {}):
                demo = sid
                break
        return views.render_specimens({
            "actor": ident["actor"], "role": ident["role"],
            "links": {"picker": "/"}, "demo_sid": demo})

    # ------------------------------------------------------------ actions

    def _require(self, ident: dict, action: str) -> None:
        if ident["role"] not in PERMISSIONS[action]:
            raise Refused(
                f"the {views.st.ROLE_LABELS[ident['role']]} view cannot do this "
                f"(WS6 §1): {action.replace('_', ' ')} is not among its appends")

    def act_create_study(self, form: dict, ident: dict) -> str:
        self._require(ident, "create_study")
        sid = (form.get("study_id") or "").strip()
        title = (form.get("title") or "").strip()
        self.ws.create_study(sid, title)
        return sid

    def act_register_claim(self, sid: str, form: dict, ident: dict) -> str:
        self._require(ident, "register_claim")
        c = self.study_ctx(sid)
        claim = Claim(
            claim_id=(form.get("claim_id") or "").strip(),
            statement=(form.get("statement") or "").strip(),
            falsifier=(form.get("falsifier") or "").strip(),
            kind=(form.get("kind") or "data").strip(),
            dependencies=_csv(form.get("dependencies")),
            margin=_float_or_none(form.get("margin")),
            sufficiency_floor=_int_or_none(form.get("sufficiency_floor")),
            supersedes=(form.get("supersedes") or "").strip() or None,
        )
        st.action_register_claim(c["store"], c["register"], claim, ident["actor"])
        return claim.claim_id

    def act_attach_citation(self, sid: str, cid: str, form: dict, ident: dict) -> None:
        self._require(ident, "attach_citation")
        c = self.study_ctx(sid)
        if cid not in c["register"].claims:
            raise Refused(f"no such claim in this register: {cid}")
        citation = vf.Citation(
            citation_id=(form.get("citation_id") or "").strip(),
            claim_id=cid,
            proposition=(form.get("proposition") or "").strip(),
            doi=(form.get("doi") or "").strip() or None,
            title=(form.get("title") or "").strip() or None,
            authors=_csv(form.get("authors")) or None,
            year=_int_or_none(form.get("year")),
            venue=(form.get("venue") or "").strip() or None,
            dataset_id=(form.get("dataset_id") or "").strip() or None,
            derived_from=(form.get("derived_from") or "").strip() or None,
        )
        if not citation.citation_id:
            raise Refused("a citation needs an ID — the ledger accounts for every check by ID (K1)")
        st.action_attach_citation(c["store"], self.ws, sid, citation,
                                   self._connector_factory(), ident["actor"])

    def act_withdraw(self, sid: str, cid: str, form: dict, ident: dict) -> None:
        self._require(ident, "withdraw")
        c = self.study_ctx(sid)
        reason = (form.get("reason") or "").strip()
        if not reason:
            raise Refused("withdrawal requires a reason (DN-005): the dead "
                          "snapshot records it verbatim")
        c["store"].withdraw(cid, reason=reason, actor=ident["actor"])

    def act_decide(self, sid: str, qid: str, form: dict, ident: dict) -> None:
        self._require(ident, "decide")
        c = self.study_ctx(sid)
        vf.decide(c["store"], qid, (form.get("decision") or "").strip(),
                  adjudicator=ident["actor"],
                  rationale=(form.get("rationale") or "").strip())

    def act_second_review(self, sid: str, qid: str, form: dict, ident: dict) -> None:
        self._require(ident, "second_review")
        c = self.study_ctx(sid)
        c["store"].log_second_review(
            qid, reviewer=ident["actor"],
            agrees=(form.get("agrees") or "") == "yes")

    def act_freeze(self, sid: str, form: dict, ident: dict) -> None:
        self._require(ident, "freeze")
        c = self.study_ctx(sid)
        fields = []
        for i in range(4):
            fm = form.get(f"ctl{i}_failure_mode")
            if fm is None:
                break
            expected = (form.get(f"ctl{i}_expected") or "").strip() or None
            fields.append({
                "kind": _DEFAULT_CONTROL_FIELDS[i]["kind"] if i < 3 else "positive",
                "failure_mode": fm.strip(),
                "expected": expected,
                "representative_rationale":
                    (form.get(f"ctl{i}_rationale") or "").strip(),
            })
        st.action_freeze(
            c["store"], c["register"], self.ws, sid, ident["actor"],
            mode=(form.get("mode") or "confirmation").strip(),
            linked_exploratory=_csv(form.get("linked_exploratory")),
            control_fields=fields,
            deployment_shape=(form.get("deployment_shape") or "hosted").strip())

    def act_run(self, sid: str, ident: dict) -> None:
        self._require(ident, "run")
        c = self.study_ctx(sid)
        st.action_run(c["store"], c["register"], str(self.ws.ledger_path(sid)),
                      st.freeze_control_fields(self.ws, sid, c["store"]),
                      ident["actor"])

    def act_export(self, sid: str, ident: dict) -> None:
        self._require(ident, "export")
        c = self.study_ctx(sid)
        st.action_export(c["store"], c["register"], self.ws, sid, ident["actor"])

    def act_verify_bundle(self, bundle_path: str) -> dict:
        v = export_mod.verify_bundle(bundle_path)
        return {"ok": v.ok, "failures": v.failures, "checks": v.checks}

    def act_deposit(self, sid: str, form: dict, ident: dict) -> None:
        self._require(ident, "deposit")
        c = self.study_ctx(sid)
        transport = self._transport_factory()
        if transport is None:
            raise Refused("no deposit transport is configured on this workspace")
        held = st.held_bundles(self.ws, sid)
        if not held:
            raise Refused("no exported bundle is held in this workspace — "
                          "export one first")
        latest = st.export_events(c["store"])[-1]
        target = None
        for p in held:
            m = _read_manifest(p)
            if m and m.get("bundle_hash") == latest.get("bundle_hash"):
                target = p
                break
        st.action_deposit(c["store"], self.ws, sid, target or held[-1], transport,
                          approved_by=(form.get("approved_by") or "").strip(),
                          actor=ident["actor"])


# ------------------------------------------------------------------ helpers

def _read_manifest(bundle_dir: Path) -> Optional[dict]:
    import json
    path = bundle_dir / "manifest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _base_ctx(c: dict, ident: dict, active: str) -> dict:
    base_path = f"/studies/{c['study']['id']}/" if active == "register" else \
        f"/studies/{c['study']['id']}/{active}"
    return {
        "study": c["study"], "actor": ident["actor"], "role": ident["role"],
        "links": views.role_links(base_path, ident["actor"]),
        "actor_note": ACTOR_NOTES.get(active, ACTOR_NOTES["default"]),
        "pending_count": c["pending_count"],
        "frozen_claims": c["frozen_claims"],
        "registration_hash": c["registration_hash"],
        "freeze_root": c["freeze_root"],
        "run": c["run"],
    }


def _csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _float_or_none(value: Optional[str]) -> Optional[float]:
    value = (value or "").strip()
    return float(value) if value else None


def _int_or_none(value: Optional[str]) -> Optional[int]:
    value = (value or "").strip()
    return int(value) if value else None


def resolve_identity(headers: Any, query: dict) -> dict:
    actor = (headers.get("X-Tekmerion-Actor")
             or _first(query.get("actor")) or "local-operator")
    role = (headers.get("X-Tekmerion-Role")
            or _first(query.get("role")) or "researcher").strip().lower()
    if role not in st.ROLES:
        role = "researcher"
    return {"actor": actor.strip(), "role": role}


def _first(values: Optional[list]) -> Optional[str]:
    return values[0] if values else None


# ------------------------------------------------------------------ HTTP

_LOCK = threading.Lock()


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        # -- plumbing ---------------------------------------------------
        def log_message(self, fmt, *args):  # keep local logs quiet
            pass

        def _send(self, status: int, body: bytes, *,
                  content_type: str = "text/html; charset=utf-8",
                  headers: Optional[dict] = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _html(self, text: str, status: int = 200) -> None:
            self._send(status, text.encode("utf-8"))

        def _redirect(self, location: str) -> None:
            self._send(303, b"", headers={"Location": location})

        def _form(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            return {k: v[0] for k, v in parse_qs(raw).items()}

        def _identity(self, query: dict) -> dict:
            return resolve_identity(self.headers, query)

        # -- dispatch ---------------------------------------------------
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            ident = self._identity(query)
            path = parsed.path
            try:
                if path == "/static/style.css":
                    self._send(200, STYLE_CSS, content_type="text/css; charset=utf-8")
                elif path == "/":
                    self._html(app.screen_picker(ident))
                elif path == "/specimens":
                    self._html(app.screen_specimens(ident))
                elif m := re.fullmatch(r"/studies/([^/]+)/?", path):
                    self._html(app.screen_register(m.group(1), ident))
                elif m := re.fullmatch(r"/studies/([^/]+)/register", path):
                    self._html(app.screen_register_form(m.group(1), ident))
                elif m := re.fullmatch(r"/studies/([^/]+)/claims/([^/]+)", path):
                    self._html(app.screen_claim(m.group(1), m.group(2), ident))
                elif m := re.fullmatch(r"/studies/([^/]+)/queue", path):
                    self._html(app.screen_queue(m.group(1), ident))
                elif m := re.fullmatch(r"/studies/([^/]+)/freeze", path):
                    self._html(app.screen_freeze(m.group(1), ident))
                elif m := re.fullmatch(r"/studies/([^/]+)/export", path):
                    self._html(app.screen_export(m.group(1), ident))
                else:
                    self._html("not found", status=404)
            except (Refused, st.WorkspaceError) as exc:
                self._html(f"refused: {views.e(exc)}", status=404)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            ident = self._identity(parse_qs(parsed.query))
            form = self._form()
            path = parsed.path
            with _LOCK:
                self._post(path, ident, form)

        def _post(self, path: str, ident: dict, form: dict) -> None:
            sid_m = re.fullmatch(r"/studies/([^/]+)(/.*)?", path)
            sid = sid_m.group(1) if sid_m else None
            try:
                if path == "/studies":
                    new_sid = app.act_create_study(form, ident)
                    self._redirect(f"/studies/{new_sid}/")
                    return
                if m := re.fullmatch(r"/studies/([^/]+)/claims", path):
                    cid = app.act_register_claim(m.group(1), form, ident)
                    self._redirect(f"/studies/{m.group(1)}/claims/{cid}")
                    return
                if m := re.fullmatch(r"/studies/([^/]+)/claims/([^/]+)/citations", path):
                    app.act_attach_citation(m.group(1), m.group(2), form, ident)
                    self._redirect(f"/studies/{m.group(1)}/claims/{m.group(2)}")
                    return
                if m := re.fullmatch(r"/studies/([^/]+)/claims/([^/]+)/withdraw", path):
                    app.act_withdraw(m.group(1), m.group(2), form, ident)
                    self._redirect(f"/studies/{m.group(1)}/claims/{m.group(2)}")
                    return
                if m := re.fullmatch(r"/studies/([^/]+)/queue/([^/]+)/decide", path):
                    app.act_decide(m.group(1), m.group(2), form, ident)
                    self._redirect(f"/studies/{m.group(1)}/queue")
                    return
                if m := re.fullmatch(r"/studies/([^/]+)/queue/([^/]+)/second-review", path):
                    app.act_second_review(m.group(1), m.group(2), form, ident)
                    self._redirect(f"/studies/{m.group(1)}/queue")
                    return
                if m := re.fullmatch(r"/studies/([^/]+)/freeze", path):
                    app.act_freeze(m.group(1), form, ident)
                    self._redirect(f"/studies/{m.group(1)}/freeze")
                    return
                if m := re.fullmatch(r"/studies/([^/]+)/run", path):
                    app.act_run(m.group(1), ident)
                    self._redirect(f"/studies/{m.group(1)}/freeze")
                    return
                if m := re.fullmatch(r"/studies/([^/]+)/export", path):
                    app.act_export(m.group(1), ident)
                    self._redirect(f"/studies/{m.group(1)}/export")
                    return
                if m := re.fullmatch(r"/studies/([^/]+)/deposit", path):
                    app.act_deposit(m.group(1), form, ident)
                    self._redirect(f"/studies/{m.group(1)}/export")
                    return
                if m := re.fullmatch(r"/studies/([^/]+)/verify-bundle", path):
                    result = app.act_verify_bundle(
                        (form.get("bundle_path") or "").strip())
                    if result["ok"]:
                        checks = ", ".join(
                            f"{k}: {'ok' if v else 'FAILED'}"
                            for k, v in result["checks"].items())
                        html = ('<div class="banner-valid" style="margin-top:14px">'
                                "<strong>Bundle verified.</strong> "
                                f'<span class="mono">{views.e(checks)}</span></div>')
                    else:
                        html = views.banner_refusal(
                            "Verification failed.",
                            "; ".join(result["failures"]))
                    self._html(app.screen_export(
                        m.group(1), ident,
                        verify_path=(form.get("bundle_path") or "").strip(),
                        verify_html=html))
                    return
                self._html("not found", status=404)
            except RegistrationError as exc:
                if sid and re.fullmatch(r"/studies/[^/]+/claims", path):
                    self._html(app.screen_register_form(
                        sid, ident, values=form, refusal=str(exc)))
                else:
                    self._html(f"refused: {views.e(exc)}", status=400)
            except FreezeError as exc:
                self._html(app.screen_freeze(sid, ident, refusal=str(exc)))
            except export_mod.ExportError as exc:
                self._html(app.screen_export(sid, ident, refusal=str(exc)))
            except deposit_mod.DepositError as exc:
                self._html(app.screen_export(sid, ident, refusal=str(exc)))
            except ValueError as exc:
                if sid and "/queue/" in path:
                    self._html(app.screen_queue(sid, ident, refusal=str(exc)))
                else:
                    self._html(f"refused: {views.e(exc)}", status=400)
            except Refused as exc:
                self._refusal_for(sid, path, ident, str(exc))
            except st.WorkspaceError as exc:
                self._html(f"refused: {views.e(exc)}", status=404)

        def _refusal_for(self, sid: Optional[str], path: str, ident: dict,
                         message: str) -> None:
            """Role/permission refusals re-render the screen they were
            attempted on, with the refusal shown."""
            if sid is None:
                self._html(app.screen_picker(ident, refusal=message))
            elif "/queue/" in path or path.endswith("/queue"):
                self._html(app.screen_queue(sid, ident, refusal=message))
            elif path.endswith("/freeze") or path.endswith("/run"):
                self._html(app.screen_freeze(sid, ident, refusal=message))
            elif path.endswith("/export") or path.endswith("/deposit") \
                    or path.endswith("/verify-bundle"):
                self._html(app.screen_export(sid, ident, refusal=message))
            elif "/claims/" in path:
                cid = path.split("/claims/")[1].split("/")[0]
                self._html(app.screen_claim(sid, cid, ident, refusal=message))
            elif path.endswith("/claims"):
                self._html(app.screen_register_form(sid, ident, values={},
                                                    refusal=message))
            else:
                self._html(app.screen_register(sid, ident))

    return Handler


def create_server(root: str | Path, *, host: str = "127.0.0.1", port: int = 8765,
                  connector_factory: Optional[Callable[[], list]] = None,
                  transport_factory: Optional[Callable[[], Any]] = None
                  ) -> ThreadingHTTPServer:
    app = App(root, connector_factory=connector_factory,
              transport_factory=transport_factory)
    return ThreadingHTTPServer((host, port), make_handler(app))


def serve(root: str | Path, *, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = create_server(root, host=host, port=port)
    print(f"Tekmerion workspace at http://{host}:{port}/  (root: {root})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
