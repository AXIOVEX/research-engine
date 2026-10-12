"""OSF deposit + registration anchor (Spec 010; pilot DESIGN §4, T-P1…T-P3).

The second anchor transport, alongside Zenodo (`tekmerion.deposit`).
From a verified audit bundle it creates an OSF project whose components
and files follow the `osf_metadata` component mapping — the mapping is
the contract — and takes an OSF registration (the registry snapshot) of
that project at the study's frozen state, with the bundle's anchor
values stated in the registration itself.

The discipline is the Zenodo path's, unchanged:

- Deposit is an explicit, adjudicator-approved action: no named
  approver, no deposit; a bundle that does not verify standalone, or
  carries no freeze binding, is refused before any OSF object exists.
- Requests are serial with >= 1 s spacing; an HTTP 429 is a stop,
  never a retry; provider errors surface verbatim (status + body) in
  `DepositError` — never swallowed, never retried blind into a
  duplicate.
- Partial progress is a recorded deposit state (a JSON the caller
  places), resumable by re-running; a repeat run checks for an existing
  registration binding the same study + schema before creating anything,
  and reports the existing registration instead of duplicating it.
- The deposit is complete when the receipt verifies — by an independent
  fetch of the registration record (`verify_osf_anchor`), not before.

Auth is the caller's, exactly as with `ZenodoTransport`: a token
(env `OSF_ACCESS_TOKEN`) or an `auth_hook` decorating each request (the
operator's credential-vault pattern). This module never reads, stores,
or logs a credential value beyond injecting what the caller supplied.
"""

from __future__ import annotations

import http.client
import io
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

from .deposit import DepositError
from .deposit import osf_metadata
from .export import verify_bundle

OSF_API_BASE = "https://api.osf.io/v2"
OSF_FILES_BASE = "https://files.osf.io/v1"
OPEN_ENDED_SCHEMA = "Open-Ended Registration"


# ------------------------------------------------------------------ transport

class OSFTransport:
    """OSF API v2 + WaterButler file storage (api.osf.io, files.osf.io).

    One method per provider operation the deposit needs, returning the
    provider's parsed JSON. All failures raise `DepositError` carrying
    the provider's actual status and response body excerpt.
    """

    mechanism = "osf"

    def __init__(self, token: Optional[str] = None, *,
                 base_url: str = OSF_API_BASE,
                 files_base: str = OSF_FILES_BASE,
                 auth_hook: Any = None,
                 opener: Any = None) -> None:
        self.token = token if token is not None else os.environ.get("OSF_ACCESS_TOKEN")
        self.base_url = base_url.rstrip("/")
        self.files_base = files_base.rstrip("/")
        self.auth_hook = auth_hook
        self._opener = opener or urllib.request.urlopen
        self._last = 0.0

    # -- plumbing ----------------------------------------------------

    def _request(self, method: str, url: str, *, data: Optional[bytes] = None,
                 content_type: str = "application/vnd.api+json",
                 authenticate: bool = True) -> Any:
        gap = time.time() - self._last
        if gap < 1.0:
            time.sleep(1.0 - gap)
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", content_type)
            if not req.has_header("Content-Length"):
                # urllib omits the header for an empty body; WaterButler
                # (folder creation) rejects that with HTTP 411.
                req.add_header("Content-Length", str(len(data)))
        req.add_header("Accept", "application/vnd.api+json")
        if authenticate:
            if self.auth_hook is not None:
                self.auth_hook(req)
            elif self.token:
                req.add_header("Authorization", f"Bearer {self.token}")
        self._last = time.time()
        if data == b"":
            return self._empty_body_request(method, url, req)
        try:
            with self._opener(req, timeout=90) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body.strip() else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            if exc.code == 429:
                raise DepositError(
                    "OSF rate limit (429) — stopping, not retrying") from exc
            raise DepositError(
                f"OSF {method} {url} failed: HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise DepositError(
                f"OSF {method} {url} failed: {exc.reason}") from exc

    def _empty_body_request(self, method: str, url: str,
                            req: urllib.request.Request) -> Any:
        """Send a zero-length-body request with chunked framing.

        Folder creation is this transport's only empty-body call, and
        it sits between two hard constraints: WaterButler forbids a
        body on folder creation (HTTP 413), while its frontend rejects
        a request whose length framing was lost (HTTP 411) — and a
        `Content-Length: 0` header does not survive every egress proxy
        (observed in the build sandbox: the proxy re-originates the
        request and the zero-length framing is dropped, 411 on every
        attempt, via urllib and via a hand-written request alike).
        Chunked framing with an empty body is the encoding both sides
        accept. Honors the environment's https proxy like urllib does.
        """
        parsed = urllib.parse.urlparse(url)
        proxies = urllib.request.getproxies()
        proxy_url = proxies.get("https") or proxies.get("http")
        context = ssl.create_default_context()
        if proxy_url:
            proxy = urllib.parse.urlparse(proxy_url)
            conn = http.client.HTTPSConnection(
                proxy.hostname, proxy.port, context=context, timeout=90)
            conn.set_tunnel(parsed.hostname, parsed.port or 443)
        else:
            conn = http.client.HTTPSConnection(
                parsed.hostname, parsed.port or 443, context=context, timeout=90)
        try:
            target = parsed.path + (f"?{parsed.query}" if parsed.query else "")
            conn.putrequest(method, target, skip_accept_encoding=True)
            for key, value in req.header_items():
                if key.lower() != "content-length":
                    conn.putheader(key, value)
            conn.putheader("Transfer-Encoding", "chunked")
            conn.endheaders()
            conn.send(b"0\r\n\r\n")
            resp = conn.getresponse()
            body = resp.read()
            if resp.status >= 400:
                raise urllib.error.HTTPError(
                    url, resp.status, resp.reason, resp.headers,
                    io.BytesIO(body))
            return json.loads(body.decode("utf-8")) if body.strip() else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            if exc.code == 429:
                raise DepositError(
                    "OSF rate limit (429) — stopping, not retrying") from exc
            raise DepositError(
                f"OSF {method} {url} failed: HTTP {exc.code}: {detail}") from exc
        except (OSError, http.client.HTTPException) as exc:
            raise DepositError(f"OSF {method} {url} failed: {exc}") from exc
        finally:
            conn.close()

    def _json(self, method: str, url: str, payload: Optional[dict] = None,
              **kw: Any) -> Any:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        return self._request(method, url, data=data, **kw)

    @staticmethod
    def _data(resp: Any) -> Any:
        return resp.get("data") if isinstance(resp, dict) else None

    # -- nodes --------------------------------------------------------

    def create_node(self, *, title: str, description: str = "",
                    category: Optional[str] = None, tags: Optional[list] = None,
                    public: bool = True, parent: Optional[str] = None) -> dict:
        attrs: dict[str, Any] = {"title": title, "description": description,
                                 "public": public}
        if category:
            attrs["category"] = category
        if tags:
            attrs["tags"] = tags
        url = (f"{self.base_url}/nodes/{parent}/children/" if parent
               else f"{self.base_url}/nodes/")
        return self._data(self._json("POST", url,
                                     {"data": {"type": "nodes", "attributes": attrs}}))

    def get_node(self, guid: str) -> dict:
        return self._data(self._json("GET", f"{self.base_url}/nodes/{guid}/"))

    def list_children(self, guid: str) -> list:
        resp = self._json("GET", f"{self.base_url}/nodes/{guid}/children/")
        return self._data(resp) or []

    def list_contributors(self, guid: str) -> list:
        resp = self._json("GET", f"{self.base_url}/nodes/{guid}/contributors/")
        return self._data(resp) or []

    # -- files (WaterButler) ------------------------------------------

    def _wb_url(self, guid: str, folder_path: str, kind: str, name: str) -> str:
        path = folder_path if folder_path.startswith("/") else f"/{folder_path}"
        if not path.endswith("/"):
            path += "/"
        q = urllib.parse.urlencode({"kind": kind, "name": name})
        return f"{self.files_base}/resources/{guid}/providers/osfstorage{path}?{q}"

    def ensure_folder(self, guid: str, name: str, parent_path: str = "/") -> str:
        """Create a folder in the node's storage; return its path."""
        resp = self._request("PUT", self._wb_url(guid, parent_path, "folder", name),
                             data=b"", content_type="application/octet-stream")
        data = self._data(resp) or {}
        path = (data.get("attributes") or {}).get("path")
        return path or f"/{data.get('id')}/"

    def upload_file(self, guid: str, name: str, data: bytes,
                    folder_path: str = "/") -> dict:
        resp = self._request("PUT", self._wb_url(guid, folder_path, "file", name),
                             data=data, content_type="application/octet-stream")
        return self._data(resp) or {}

    def list_files(self, guid: str) -> list:
        """All files under the node's osfstorage, recursively, as
        root-relative paths (folders traversed via their files
        relationship)."""
        out: list[dict] = []

        def walk(url: str, prefix: str) -> None:
            resp = self._json("GET", url)
            for entry in self._data(resp) or []:
                attrs = entry.get("attributes") or {}
                name = attrs.get("name", "")
                if attrs.get("kind") == "folder":
                    href = ((((entry.get("relationships") or {}).get("files") or {})
                             .get("links") or {}).get("related") or {}).get("href")
                    if href:
                        walk(href, f"{prefix}{name}/")
                else:
                    out.append({"name": name, "path": f"{prefix}{name}",
                                "id": entry.get("id"),
                                "size": attrs.get("size")})

        walk(f"{self.base_url}/nodes/{guid}/files/osfstorage/", "")
        return out

    # -- registrations --------------------------------------------------

    def find_registration_schema(self, name: str = OPEN_ENDED_SCHEMA) -> str:
        """Resolve a registration schema id by its exact name — never a
        hardcoded GUID, so a provider-side schema change fails loudly
        here instead of silently mis-registering."""
        url: Optional[str] = f"{self.base_url}/schemas/registrations/?page[size]=100"
        while url:
            resp = self._json("GET", url)
            for entry in self._data(resp) or []:
                if (entry.get("attributes") or {}).get("name") == name:
                    return entry["id"]
            url = ((resp.get("links") or {}).get("next")) if isinstance(resp, dict) else None
        raise DepositError(f"OSF registration schema not found by name: {name!r}")

    def list_registrations(self, guid: str) -> list:
        resp = self._json("GET", f"{self.base_url}/nodes/{guid}/registrations/")
        return self._data(resp) or []

    def list_draft_registrations(self, guid: str) -> list:
        resp = self._json("GET", f"{self.base_url}/nodes/{guid}/draft_registrations/")
        return self._data(resp) or []

    def get_draft_registration(self, draft_id: str) -> dict:
        return self._data(self._json(
            "GET", f"{self.base_url}/draft_registrations/{draft_id}/"))

    def create_draft_registration(self, guid: str, schema_id: str) -> dict:
        payload = {"data": {"type": "draft_registrations", "attributes": {},
                            "relationships": {
                                "registration_schema": {"data": {
                                    "id": schema_id,
                                    "type": "registration-schemas"}}}}}
        return self._data(self._json(
            "POST", f"{self.base_url}/nodes/{guid}/draft_registrations/", payload))

    def set_draft_responses(self, draft_id: str, responses: dict) -> dict:
        payload = {"data": {"type": "draft_registrations", "id": draft_id,
                            "attributes": {"registration_responses": responses}}}
        return self._data(self._json(
            "PATCH", f"{self.base_url}/draft_registrations/{draft_id}/", payload))

    def find_subject(self, name: str) -> str:
        """Resolve an OSF taxonomy subject id by its exact text — the
        same by-name discipline as the registration schema."""
        url = (f"{self.base_url}/subjects/?filter[text]="
               f"{urllib.parse.quote(name)}&page[size]=100")
        resp = self._json("GET", url)
        for entry in self._data(resp) or []:
            if (entry.get("attributes") or {}).get("text") == name:
                return entry["id"]
        raise DepositError(f"OSF subject not found by exact text: {name!r}")

    def set_draft_subjects(self, draft_id: str, subject_ids: list) -> Any:
        payload = {"data": [{"type": "subjects", "id": sid}
                             for sid in subject_ids]}
        return self._json(
            "PATCH",
            f"{self.base_url}/draft_registrations/{draft_id}/relationships/subjects/",
            payload)

    def submit_registration(self, draft_id: str, *, component_ids: list,
                            embargo_end_date: Optional[str] = None) -> dict:
        # Field names as the provider's own validation names them: a
        # create sent with `draft_registration_id` is refused with
        # "/data/attributes/draft_registration: This field is required"
        # (observed live, 2026-10-12). The component list travels as
        # `children` in the same (default-version) shape.
        attrs: dict[str, Any] = {
            "draft_registration": draft_id,
            "registration_choice": "embargo" if embargo_end_date else "immediate",
            "children": list(component_ids),
        }
        if embargo_end_date:
            attrs["embargo_end_date"] = embargo_end_date
            # Also required by the provider when embargoing (its own
            # validation names the field, and its format error names
            # the type): the datetime at which the embargo lifts,
            # i.e. the embargo becomes public automatically then — an
            # embargoed anchor is a delayed anchor, not a private one.
            attrs["lift_embargo"] = (
                embargo_end_date if "T" in embargo_end_date
                else f"{embargo_end_date}T00:00:00")
        return self._data(self._json(
            "POST", f"{self.base_url}/registrations/",
            {"data": {"type": "registrations", "attributes": attrs}}))

    def get_registration(self, registration_id: str) -> dict:
        return self._data(self._json(
            "GET", f"{self.base_url}/registrations/{registration_id}/"))

    def list_registration_identifiers(self, registration_id: str) -> list:
        resp = self._json(
            "GET", f"{self.base_url}/registrations/{registration_id}/identifiers/")
        return self._data(resp) or []


# ------------------------------------------------------------------ helpers

def _registration_summary_text(record: dict) -> str:
    """All text in a registration record that can carry the anchor
    statement: the description plus the summary response, in whichever
    of the provider's shapes it arrives (`registration_responses` or
    `registered_meta`)."""
    attrs = record.get("attributes") or {}
    parts = [str(attrs.get("description") or "")]
    for key in ("registration_responses", "registered_meta"):
        blob = attrs.get(key)
        if isinstance(blob, dict):
            summary = blob.get("summary")
            if isinstance(summary, dict):
                parts.append(str(summary.get("value") or ""))
            elif summary is not None:
                parts.append(str(summary))
    return "\n".join(parts)


def _record_states_anchor(record: dict, anchor_values: dict) -> bool:
    text = _registration_summary_text(record)
    return all(str(anchor_values[k]) in text
               for k in ("checkpoint_root", "bundle_hash", "registration_hash"))


def _registration_locator(record: dict) -> Optional[str]:
    links = record.get("links") or {}
    return links.get("html") or (f"https://osf.io/{record['id']}/" if record.get("id") else None)


def _registration_terminal(record: dict, *, embargo_end_date: Optional[str]) -> bool:
    attrs = record.get("attributes") or {}
    if attrs.get("reviews_state") != "accepted":
        return False
    if attrs.get("pending_registration_approval"):
        return False
    if embargo_end_date:
        return bool(attrs.get("embargoed")) and bool(attrs.get("embargo_end_date"))
    return True


def _component_file_plan(bundle_dir: Path, mapping: dict) -> tuple[dict, list]:
    """Per component: the files to upload (component-relative paths ->
    bundle paths) and the mapped paths absent from this bundle."""
    plan: dict[str, list] = {}
    absent: list[str] = []
    for component, mapped in (mapping.get("components") or {}).items():
        entries: list[tuple[str, Path]] = []
        for item in mapped:
            if item.endswith("/"):
                base = bundle_dir / item
                if base.is_dir():
                    for path in sorted(base.rglob("*")):
                        if path.is_file():
                            rel = path.relative_to(bundle_dir).as_posix()
                            entries.append((_component_relative(component, rel), path))
                else:
                    absent.append(item)
                continue
            path = bundle_dir / item
            if path.is_file():
                entries.append((_component_relative(component, item), path))
            else:
                absent.append(item)
        plan[component] = entries
    return plan, absent


def _component_relative(component: str, bundle_rel: str) -> str:
    prefix = f"{component}/"
    return bundle_rel[len(prefix):] if bundle_rel.startswith(prefix) else bundle_rel


def _load_state(state_path: Optional[str]) -> dict:
    if state_path and Path(state_path).is_file():
        return json.loads(Path(state_path).read_text(encoding="utf-8"))
    return {}


def _save_state(state_path: Optional[str], state: dict) -> None:
    if state_path:
        path = Path(state_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


# ------------------------------------------------------------------ the action

def deposit_bundle_osf(bundle_dir: str, transport: OSFTransport, *,
                       approved_by: str,
                       subjects: Optional[tuple] = None,
                       state_path: Optional[str] = None,
                       embargo_end_date: Optional[str] = None,
                       schema_name: str = OPEN_ENDED_SCHEMA,
                       resume_project_guid: Optional[str] = None) -> dict:
    """Deposit a verified bundle to OSF and return the anchor receipt.

    Same gate as `deposit_bundle` (WS5 §3 + DESIGN §4.2.1): a named
    approver, a bundle that verifies standalone, and a freeze binding
    in the manifest — all checked before any OSF object is created.
    Idempotent and resumable via the deposit state (see module
    docstring); a completed deposit returns its receipt, and a repeat
    run returns the same receipt marked `already_existed` rather than
    creating a second registration.
    """
    if not approved_by or not approved_by.strip():
        raise DepositError(
            "deposit refused: deposits are adjudicator-approved actions "
            "(WS5 §3) — name the approver; without one the bundle stays internal")
    result = verify_bundle(bundle_dir)
    if not result.ok:
        raise DepositError(f"deposit refused: bundle does not verify: {result.failures}")

    root = Path(bundle_dir)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    study = manifest.get("study") or {}
    if not study.get("registration_hash") or not study.get("checkpoint_root"):
        raise DepositError(
            "deposit refused: bundle carries no freeze binding (manifest study "
            "lacks registration_hash / checkpoint_root) — an unfrozen study "
            "has nothing to anchor")

    if not subjects:
        raise DepositError(
            "deposit refused: the provider requires at least one subject "
            "on a registration — name the subject(s) for this study; the "
            "choice is part of the deposit decision, not a default")

    mapping = osf_metadata(manifest)
    anchor = mapping["anchor_values"]

    state = _load_state(state_path)
    if state:
        if (state.get("registration_hash") != anchor["registration_hash"]
                or state.get("bundle_hash") != anchor["bundle_hash"]):
            raise DepositError(
                "deposit state belongs to a different bundle "
                f"(state registration_hash={state.get('registration_hash')!r}); "
                "refusing to continue it against this bundle")
        if state.get("receipt"):
            return dict(state["receipt"], already_existed=True)
    state.update({"registration_hash": anchor["registration_hash"],
                  "bundle_hash": anchor["bundle_hash"], "schema_name": schema_name})
    _save_state(state_path, state)

    # -- project ------------------------------------------------------
    project_guid = state.get("project_guid") or resume_project_guid
    if not project_guid:
        node = transport.create_node(
            title=mapping["title"], description=mapping["description"],
            category=mapping["category"], tags=mapping["tags"], public=True)
        project_guid = node["id"]
        state["project_guid"] = project_guid
        state["stage"] = "project_created"
        _save_state(state_path, state)
    else:
        transport.get_node(project_guid)  # stale state fails here, loudly

    # -- components + files -------------------------------------------
    plan, absent = _component_file_plan(root, mapping)
    if absent:
        state["absent_mapped_paths"] = absent
    children = {((c.get("attributes") or {}).get("title")): c
                for c in transport.list_children(project_guid)}
    state.setdefault("components", {})
    state.setdefault("uploaded", [])
    for component, entries in plan.items():
        comp = state["components"].get(component)
        resumed_into_existing = bool(comp)
        if not comp:
            existing = children.get(component)
            if existing:
                comp = existing["id"]
                resumed_into_existing = True
            else:
                # The provider requires a category on child nodes; the
                # component's identity is its title (the mapping key),
                # so the neutral category is used.
                node = transport.create_node(title=component, parent=project_guid,
                                             category="other", public=True)
                comp = node["id"]
            state["components"][component] = comp
            _save_state(state_path, state)
        if resumed_into_existing:
            # A resumed run does not re-upload what already landed.
            present = {f["path"] for f in transport.list_files(comp)}
            for rel, _p in entries:
                key = f"{component}:{rel}"
                if rel in present and key not in state["uploaded"]:
                    state["uploaded"].append(key)
            _save_state(state_path, state)
        folders: dict[str, str] = {}
        for rel, path in entries:
            key = f"{component}:{rel}"
            if key in state["uploaded"]:
                continue
            parts = rel.split("/")
            folder_path = "/"
            for folder in parts[:-1]:
                if folder not in folders:
                    folders[folder] = transport.ensure_folder(comp, folder, folder_path)
                folder_path = folders[folder]
            transport.upload_file(comp, parts[-1], path.read_bytes(),
                                  folder_path=folder_path)
            state["uploaded"].append(key)
            _save_state(state_path, state)
    state["stage"] = "files_uploaded"
    _save_state(state_path, state)

    # -- existing-registration check (before any draft is created) -----
    registration = None
    if state.get("registration_guid"):
        try:
            registration = transport.get_registration(state["registration_guid"])
        except DepositError:
            registration = None
    if registration is None:
        for candidate in transport.list_registrations(project_guid):
            if ((candidate.get("attributes") or {}).get("registration_supplement")
                    in (schema_name, None)
                    and _record_states_anchor(candidate, anchor)):
                registration = candidate
                state["registration_guid"] = candidate["id"]
                _save_state(state_path, state)
                break

    found_existing = registration is not None

    # -- draft + submission --------------------------------------------
    if registration is None:
        draft = None
        if state.get("draft_id"):
            try:
                draft = transport.get_draft_registration(state["draft_id"])
            except DepositError:
                draft = None
        if draft is None:
            for candidate in transport.list_draft_registrations(project_guid):
                if _record_states_anchor(
                        {"attributes": {"description": "",
                                        "registration_responses":
                                            (candidate.get("attributes") or {})
                                            .get("registration_responses")}},
                        anchor):
                    draft = candidate
                    break
        schema_id = state.get("schema_id") or transport.find_registration_schema(schema_name)
        state["schema_id"] = schema_id
        if draft is None:
            draft = transport.create_draft_registration(project_guid, schema_id)
            state["draft_id"] = draft["id"]
            state["stage"] = "draft_created"
            _save_state(state_path, state)
        responses = (draft.get("attributes") or {}).get("registration_responses") or {}
        if anchor["registration_hash"] not in str(responses):
            transport.set_draft_responses(
                draft["id"], {"summary": mapping["description"]})
            state["stage"] = "draft_answered"
            _save_state(state_path, state)
        subject_ids = [transport.find_subject(name) for name in subjects]
        transport.set_draft_subjects(draft["id"], subject_ids)
        state["subjects"] = list(subjects)
        _save_state(state_path, state)
        registration = transport.submit_registration(
            draft["id"],
            component_ids=[state["components"][c] for c in plan],
            embargo_end_date=embargo_end_date)
        state["registration_guid"] = registration["id"]
        state["stage"] = "submitted"
        _save_state(state_path, state)

    # -- finalize: the record's own state decides ----------------------
    # Plain OSF is an unmoderated provider: review-actions are refused
    # (HTTP 409, observed live), and the API names the account "not a
    # pending approver" for the schema response (HTTP 403, observed
    # live). Admin approval of a registration/embargo runs through
    # OSF's own channel (the approval email link), not this API — so a
    # record the provider still holds as pending is a recorded,
    # resumable deposit state, never a completed anchor.
    record = transport.get_registration(state["registration_guid"])
    if not _registration_terminal(record, embargo_end_date=embargo_end_date):
        attrs = record.get("attributes") or {}
        pending = [k for k in ("pending_registration_approval",
                               "pending_embargo_approval",
                               "pending_embargo_termination_approval")
                   if attrs.get(k)]
        raise DepositError(
            "registration created and submitted but the provider holds it "
            f"in a non-final state (reviews_state={attrs.get('reviews_state')!r}, "
            f"pending={pending}) — admin approval runs through OSF's own "
            "channel (approval email link), not the API. The deposit is "
            "NOT complete and must not be cited as an anchor; re-run to "
            "resume once the record is final. Observed: "
            f"{json.dumps({k: attrs.get(k) for k in ('reviews_state', 'public', 'embargoed', 'embargo_end_date', *pending)}, default=str)}")

    # -- receipt ---------------------------------------------------------
    doi = None
    for ident in transport.list_registration_identifiers(record["id"]):
        attrs = ident.get("attributes") or {}
        if attrs.get("category") == "doi":
            doi = attrs.get("value")
    attrs = record.get("attributes") or {}
    receipt = {
        "mechanism": transport.mechanism,
        "root": anchor["checkpoint_root"],
        "bundle_hash": anchor["bundle_hash"],
        "registration_hash": anchor["registration_hash"],
        "doi": doi,
        "record_id": record["id"],
        "locator": _registration_locator(record),
        "anchored_at": attrs.get("date_registered"),
        "approved_by": approved_by,
        "project_guid": project_guid,
        "registration_guid": record["id"],
        "registration_url": _registration_locator(record),
        "embargoed": bool(attrs.get("embargoed")),
        "embargo_end_date": attrs.get("embargo_end_date"),
        "reviews_state": attrs.get("reviews_state"),
        "schema": schema_name,
        "components": dict(state["components"]),
        "absent_mapped_paths": absent,
    }
    if not receipt["root"] or not receipt["locator"] or not receipt["anchored_at"]:
        raise DepositError(f"anchor record incomplete — receipt would not verify: {receipt}")
    if found_existing:
        receipt["already_existed"] = True
    state["receipt"] = receipt
    state["stage"] = "complete"
    _save_state(state_path, state)
    return receipt


# ------------------------------------------------------------------ verification

def verify_osf_anchor(bundle_dir: str, registration_guid: str, *,
                      project_guid: Optional[str] = None,
                      opener: Any = None,
                      base_url: str = OSF_API_BASE,
                      reader: Any = None) -> dict:
    """Verify an OSF anchor using only the bundle and a fresh,
    unauthenticated fetch of the public OSF record — the AR-1
    read-back standard. Passes only if the registration record states
    the bundle's anchor values (read from the registration, never the
    mutable project — CLM-010-08) and the project structure matches the
    component mapping. A private/embargoed record is reported as not
    publicly fetchable, never as a pass."""
    failures: list[str] = []
    checks: dict[str, Any] = {}
    root = Path(bundle_dir)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    mapping = osf_metadata(manifest)
    anchor = mapping["anchor_values"]

    if reader is None:
        reader = OSFTransport(token="", base_url=base_url, opener=opener)
    try:
        record = reader.get_registration(registration_guid)
    except DepositError as exc:
        return {"ok": False,
                "failures": [f"registration not publicly fetchable: {exc}"],
                "checks": checks}
    checks["reviews_state"] = (record.get("attributes") or {}).get("reviews_state")
    checks["embargoed"] = (record.get("attributes") or {}).get("embargoed")
    if _record_states_anchor(record, anchor):
        checks["anchor_values"] = "stated in registration record"
    else:
        failures.append(
            "registration record does not state the bundle's anchor values "
            "(checkpoint root / bundle hash / registration hash)")

    proj = project_guid
    if not proj:
        rel = ((record.get("relationships") or {}).get("registered_from") or {})
        proj = ((rel.get("data") or {}).get("id")) or None
    if not proj:
        failures.append("registration record names no source project")
        return {"ok": not failures, "failures": failures, "checks": checks}
    checks["project_guid"] = proj

    try:
        children = reader.list_children(proj)
        titles = sorted((c.get("attributes") or {}).get("title")
                        for c in children)
        expected = sorted((mapping.get("components") or {}).keys())
        checks["components"] = titles
        if titles != expected:
            failures.append(
                f"component structure diverges from the mapping: {titles} != {expected}")
        plan, _absent = _component_file_plan(root, mapping)
        by_title = {((c.get("attributes") or {}).get("title")): c for c in children}
        for component, entries in plan.items():
            comp = by_title.get(component)
            if not comp:
                continue
            have = sorted(f["path"] for f in reader.list_files(comp["id"]))
            want = sorted(rel for rel, _p in entries)
            checks[f"files:{component}"] = have
            if have != want:
                failures.append(
                    f"component {component!r} file set diverges: {have} != {want}")
        contributors = reader.list_contributors(proj)
        names = []
        for entry in contributors:
            user = ((entry.get("embeds") or {}).get("users") or {}).get("data") or {}
            name = (user.get("attributes") or {}).get("full_name") \
                or (entry.get("attributes") or {}).get("full_name")
            if name:
                names.append(name)
        checks["contributors"] = names
        creator_surnames = {c["name"].split(",")[0].strip().lower()
                            for c in mapping.get("creators") or []}
        if creator_surnames and not any(
                surname in name.lower()
                for name in names for surname in creator_surnames):
            failures.append(
                f"project contributors {names} match no creator in the mapping "
                f"{sorted(creator_surnames)}")
    except DepositError as exc:
        failures.append(f"project structure fetch failed: {exc}")
    return {"ok": not failures, "failures": failures, "checks": checks}
