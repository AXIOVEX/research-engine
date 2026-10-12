"""Deposit + anchor actions (Spec 002 Phase 5; T217, T218 / AR-1).

Deposit is an explicit, adjudicator-approved action, never automatic
(WS5 §3): what leaves the institution is a human decision, so
`deposit_bundle` refuses to run without a named approver, and the
approval is written into the receipt. The deposit is also the anchor
(DN-005 layer 5; Spec 002 §2): the bundle's Merkle checkpoint root is
deposited where the operator does not control it, the deposit
metadata states the root and the bundle hash, and the returned
receipt is appended to the study ledger (`anchor.recorded`) so the
anchor becomes part of the record (Article XIII).

Transports are the seam. `ZenodoTransport` speaks to Zenodo's deposit
API (the AR-1 mechanism: a DOI-minting repository); `LocalTransport`
persists the same record shape to a directory, for tests and for
demonstrating the loop mechanics without an external party — its
receipts are labeled `local-filesystem` and are **not** external
anchors, and nothing in this module pretends otherwise.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Optional

from .export import verify_bundle

ZENODO_BASE = "https://zenodo.org/api"


class DepositError(RuntimeError):
    pass


# ------------------------------------------------------------------ packaging + metadata

def package_bundle(bundle_dir: str, out_path: str) -> Path:
    """Package a bundle as a deterministic zip: sorted entries, fixed
    timestamps, fixed permissions — the same bundle packages to the
    same bytes, so the deposited file's checksum is stable."""
    root = Path(bundle_dir)
    out = Path(out_path)
    members = sorted(
        (p for p in root.rglob("*") if p.is_file()),
        key=lambda p: p.relative_to(root).as_posix(),
    )
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in members:
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(),
                                   date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())
    return out


def _anchor_statement(manifest: dict[str, Any]) -> str:
    study = manifest["study"]
    return (
        f"Tekmerion audit bundle (format {manifest['format']}).\n"
        f"Merkle checkpoint root (anchored value): {study['checkpoint_root']}\n"
        f"Bundle hash (SHA-256): {manifest['bundle_hash']}\n"
        f"Registration hash: {study['registration_hash']}\n"
        f"Ledger events: {study['event_count']}"
    )


def zenodo_metadata(manifest: dict[str, Any], *, title: Optional[str] = None,
                    creators: Optional[list[dict[str, str]]] = None,
                    description_extra: str = "") -> dict[str, Any]:
    """Deposit-ready Zenodo metadata. The description carries the
    checkpoint root and the bundle hash — that is what closes the
    anchoring loop (WS4 §4): the public record itself states the
    values an auditor checks the bundle against."""
    study = manifest["study"]
    description = _anchor_statement(manifest)
    if description_extra:
        description += f"\n\n{description_extra}"
    return {
        "metadata": {
            "title": title or f"Tekmerion audit bundle — {study['label']}",
            "upload_type": "dataset",
            "description": description,
            "creators": creators or [
                {"name": "Pierson, Tristen", "affiliation": "Axiovex Systems, LLC"}],
            "access_right": "open",
            "license": "cc-by-4.0",
            "keywords": ["tekmerion", "audit bundle", "research integrity",
                         "append-only ledger", "anchoring"],
        }
    }


def osf_metadata(manifest: dict[str, Any], *, title: Optional[str] = None,
                 creators: Optional[list[dict[str, str]]] = None) -> dict[str, Any]:
    """Deposit-ready OSF mapping (WS4 §4: OSF project + registration
    components map onto the bundle structure). This is the metadata
    document an OSF deposit is made from; the executable deposit
    action in this module targets Zenodo, whose API mints the DOI
    AR-1 requires."""
    study = manifest["study"]
    return {
        "title": title or f"Tekmerion audit bundle — {study['label']}",
        "description": _anchor_statement(manifest),
        "category": "project",
        "tags": ["tekmerion", "audit bundle", "research integrity"],
        "creators": creators or [
            {"name": "Pierson, Tristen", "affiliation": "Axiovex Systems, LLC"}],
        "components": {
            "registration": ["registration.json", "claims.json", "controls.json"],
            "evidence": ["evidence/items.json", "evidence/groups.json",
                         "evidence/content/", "coverage.json"],
            "verification": ["verification.json", "queries.json"],
            "verdicts": ["verdicts.json", "adjudication.json"],
            "record": ["ledger/study.axmr", "manifest.json", "HUMAN-README.md"],
        },
        "anchor_values": {
            "checkpoint_root": study["checkpoint_root"],
            "bundle_hash": manifest["bundle_hash"],
            "registration_hash": study["registration_hash"],
        },
    }


# ------------------------------------------------------------------ transports

class LocalTransport:
    """A directory standing in for the external party: depositions are
    folders, publishing writes a public-record-shaped `record.json`
    that verification reads back. For tests and local loop
    demonstrations — honestly labeled, never an AR-1 anchor."""

    mechanism = "local-filesystem"

    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _next_id(self) -> int:
        existing = [int(p.name) for p in self.root.iterdir()
                    if p.is_dir() and p.name.isdigit()]
        return (max(existing) + 1) if existing else 1

    def create(self, metadata: dict[str, Any]) -> str:
        dep_id = self._next_id()
        dep = self.root / str(dep_id)
        (dep / "files").mkdir(parents=True)
        (dep / "metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        return str(dep_id)

    def upload(self, ref: str, name: str, data: bytes) -> None:
        (self.root / ref / "files" / name).write_bytes(data)

    def publish(self, ref: str) -> dict[str, Any]:
        dep = self.root / ref
        metadata = json.loads((dep / "metadata.json").read_text(encoding="utf-8"))
        files = []
        for path in sorted((dep / "files").iterdir()):
            data = path.read_bytes()
            files.append({"key": path.name, "size": len(data),
                          "checksum": f"md5:{hashlib.md5(data).hexdigest()}"})
        record = {
            "id": int(ref),
            "doi": None,
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "metadata": metadata.get("metadata", {}),
            "files": files,
            "links": {"record": f"local://{dep}"},
        }
        (dep / "record.json").write_text(
            json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        return record

    def record(self, ref: str) -> dict[str, Any]:
        """Read back the public record, as an independent party would."""
        return json.loads((self.root / ref / "record.json").read_text(encoding="utf-8"))


class ZenodoTransport:
    """Zenodo deposit API (the AR-1 anchor transport). The access
    token comes from the caller (env `ZENODO_ACCESS_TOKEN` by
    default); an `auth_hook` may decorate each request instead (the
    operator's credential-vault pattern). Requests are serial with
    >= 1 s spacing, and a 429 is a stop, never a retry."""

    mechanism = "zenodo"

    def __init__(self, token: Optional[str] = None, *,
                 base_url: str = ZENODO_BASE,
                 auth_hook: Any = None,
                 opener: Any = None) -> None:
        self.token = token if token is not None else os.environ.get("ZENODO_ACCESS_TOKEN")
        self.base_url = base_url.rstrip("/")
        self.auth_hook = auth_hook
        self._opener = opener or urllib.request.urlopen
        self._last = 0.0
        self._bucket: Optional[str] = None

    def _request(self, method: str, url: str, *, data: Optional[bytes] = None,
                 content_type: str = "application/json") -> Any:
        gap = time.time() - self._last
        if gap < 1.0:
            time.sleep(1.0 - gap)
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", content_type)
        req.add_header("Accept", "application/json")
        if self.auth_hook is not None:
            self.auth_hook(req)
        elif self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        self._last = time.time()
        try:
            with self._opener(req, timeout=90) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body.strip() else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            if exc.code == 429:
                raise DepositError("Zenodo rate limit (429) — stopping, not retrying") from exc
            raise DepositError(f"Zenodo {method} {url} failed: HTTP {exc.code}: {detail}") from exc

    def create(self, metadata: dict[str, Any]) -> str:
        created = self._request("POST", f"{self.base_url}/deposit/depositions",
                                data=b"{}")
        dep_id = created["id"]
        self._bucket = created["links"]["bucket"]
        self._request("PUT", f"{self.base_url}/deposit/depositions/{dep_id}",
                      data=json.dumps(metadata).encode("utf-8"))
        return str(dep_id)

    def upload(self, ref: str, name: str, data: bytes) -> None:
        if not self._bucket:
            raise DepositError("no bucket — create() must precede upload()")
        self._request("PUT", f"{self._bucket}/{name}", data=data,
                      content_type="application/octet-stream")

    def publish(self, ref: str) -> dict[str, Any]:
        return self._request(
            "POST", f"{self.base_url}/deposit/depositions/{ref}/actions/publish",
            data=b"")


# ------------------------------------------------------------------ the action

def deposit_bundle(bundle_dir: str, transport: Any, *, approved_by: str,
                   title: Optional[str] = None,
                   creators: Optional[list[dict[str, str]]] = None,
                   description_extra: str = "",
                   package_out: Optional[str] = None) -> dict[str, Any]:
    """Deposit a verified bundle and return the anchor receipt.

    The adjudicator-approval gate (WS5 §3) is mechanical: no named
    approver, no deposit. A bundle that does not verify standalone is
    likewise refused — anchoring a broken record would certify it."""
    if not approved_by or not approved_by.strip():
        raise DepositError(
            "deposit refused: deposits are adjudicator-approved actions "
            "(WS5 §3) — name the approver; without one the bundle stays internal")
    result = verify_bundle(bundle_dir)
    if not result.ok:
        raise DepositError(f"deposit refused: bundle does not verify: {result.failures}")

    manifest = json.loads((Path(bundle_dir) / "manifest.json").read_text(encoding="utf-8"))
    package = Path(package_out) if package_out else (
        Path(bundle_dir).parent / f"{Path(bundle_dir).name}.zip")
    package_bundle(bundle_dir, str(package))
    data = package.read_bytes()

    metadata = zenodo_metadata(manifest, title=title, creators=creators,
                               description_extra=description_extra)
    ref = transport.create(metadata)
    transport.upload(ref, package.name, data)
    record = transport.publish(ref)

    study = manifest["study"]
    locator = None
    links = record.get("links") or {}
    if record.get("doi"):
        locator = f"https://doi.org/{record['doi']}"
    elif links.get("record_html"):
        locator = links["record_html"]
    elif links.get("record"):
        locator = links["record"]
    receipt = {
        "mechanism": transport.mechanism,
        "root": study["checkpoint_root"],
        "bundle_hash": manifest["bundle_hash"],
        "registration_hash": study["registration_hash"],
        "doi": record.get("doi"),
        "record_id": record.get("id"),
        "locator": locator,
        "anchored_at": record.get("created"),
        "approved_by": approved_by,
        "file": {
            "name": package.name,
            "md5": hashlib.md5(data).hexdigest(),
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        },
    }
    if not receipt["root"] or not receipt["locator"] or not receipt["anchored_at"]:
        raise DepositError(f"anchor record incomplete — receipt would not verify: {receipt}")
    return receipt


def record_anchor(store: Any, receipt: dict[str, Any], *, actor: str) -> dict:
    """Append the receipt to the study ledger (`anchor.recorded`):
    the anchor is part of the study record, and every bundle exported
    afterward carries it in its manifest (Article XIII)."""
    return store.log_anchor(receipt, actor=actor)
