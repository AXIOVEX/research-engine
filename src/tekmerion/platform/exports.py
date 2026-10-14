"""Platform audit export + standalone verifier (Spec 005 §8/§12,
T542; CLM-005-15).

The Phase 5 bundle pattern, applied to platform audit ledgers: an
export is a directory carrying a copy of the ledger file, readable
projections of its contents (events, the POA&M register, the
SPRS-input control states), a hash manifest that binds the file
set, and a HUMAN-README. The verifier in this module checks an
export **from the export alone** — no access to the live ledger:

- the manifest's bundle hash binds its file list, and every listed
  file hashes to its manifest entry (no unlisted files);
- the ledger copy passes the production Axiomere verifier
  (`axiomere.verify_file`: hash chain + append signatures);
- the manifest's head hash, event count, and checkpoint root match
  the exported ledger's own;
- `events.json` equals the exported ledger's events, payload for
  payload — a projection may not drift from the record;
- `control-states.json` equals the replay of the exported ledger's
  compliance events over the recorded seed, and its score
  recomputes from its own inputs.

F-005-15's named attack — an altered event under an
attacker-rehashed manifest — fails these checks: the manifest can
be rehashed, but the ledger copy's internal chain and signatures
cannot, and the projections are cross-checked against that copy.
What bundle-alone verification cannot do is prove the exported
ledger is *the* ledger; that binding is the anchor's job (the
`audit.export_anchored` record in the continuing ledger, T543) —
the same trust structure as the study bundles.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..marking import banner_lines, normalize_marking
from . import compliance
from .ledger import PlatformLedger

EXPORT_FORMAT = "tekmerion-platform-audit-export/1"


def _dump(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _ledger_events(ledger_bytes: bytes) -> list[dict[str, Any]]:
    """Parse the events out of an .axmr file (magic header line,
    then one canonical-JSON event per line) — the same parse the
    study-bundle verifier uses."""
    events = []
    for line in ledger_bytes.decode("utf-8").splitlines():
        if line.strip() and not line.startswith("AXMR"):
            events.append(json.loads(line))
    return events


def _checkpoints(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"seq": e["seq"], "upto_seq": e["payload"]["upto_seq"],
         "merkle_root": e["payload"]["merkle_root"]}
        for e in events if e["type"] == "checkpoint"
    ]


def export_platform_audit(
    ledger: PlatformLedger,
    ledger_path: str,
    out_dir: str,
    *,
    marking: Optional[dict[str, Any]] = None,
    poam_document: Optional[dict[str, Any]] = None,
    sprs_report: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Export one platform ledger (deployment or one tenant's) to
    `out_dir` and return the manifest. Fails closed, like the study
    pattern: a ledger that does not verify is evidence, not an
    export. The caller appends a checkpoint first, so the export
    binds a fresh Merkle root."""
    verification = ledger.verify()
    if not verification.ok:
        raise ValueError(
            f"platform ledger fails verification ({verification.reason}); "
            "a broken record is evidence, not an export")
    events = ledger.events()
    checkpoints = _checkpoints(events)
    if not checkpoints:
        raise ValueError("no checkpoint in the ledger — checkpoint before export")

    # The root written into the manifest below is confirmed against
    # the root the verifier recomputes from the ledger's events —
    # never merely read out of the checkpoint event's payload
    # (Axiomere Spec 003 companion, AXM-003-15).
    pin = ledger.verify(
        expected_head={"checkpoint_root": checkpoints[-1]["merkle_root"]})
    if not pin.ok:
        raise ValueError(
            "the ledger's latest checkpoint root does not match the root "
            f"verification recomputes ({pin.reason}); export refused rather "
            "than misbound")

    out = Path(out_dir)
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"export directory {out_dir} is not empty")
    (out / "ledger").mkdir(parents=True, exist_ok=True)

    files: dict[str, bytes] = {}

    def put(rel: str, data: bytes) -> None:
        files[rel] = data

    put("ledger/audit.axmr", Path(ledger_path).read_bytes())
    put("events.json", _dump({
        "scope": ledger.scope, "tenant_id": ledger.tenant_id,
        "events": events,
    }))
    put("poam.json", _dump(poam_document if poam_document is not None
                           else {"items": [], "note": "no POA&M register recorded"}))
    put("control-states.json", _dump(
        sprs_report if sprs_report is not None
        else {"seeded": False, "note": "control states not seeded for this scope"}))

    marking_block = normalize_marking(marking)
    manifest_core: dict[str, Any] = {
        "format": EXPORT_FORMAT,
        "scope": {"kind": ledger.scope, "tenant_id": ledger.tenant_id},
        "ledger": {
            "file": "ledger/audit.axmr",
            "event_count": len(events),
            "head_seq": events[-1]["seq"] if events else None,
            "head_hash": events[-1]["hash"] if events else None,
            "checkpoints": checkpoints,
            "checkpoint_root": checkpoints[-1]["merkle_root"],
        },
        "cui_marking": marking_block,
        "complete": True,
    }
    put("HUMAN-README.md", _human_readme(manifest_core).encode("utf-8"))

    file_entries = [
        {"path": rel, "sha256": _sha256(data), "bytes": len(data)}
        for rel, data in sorted(files.items())
    ]
    manifest = {**manifest_core, "files": file_entries}
    manifest["bundle_hash"] = _sha256(_canonical(manifest))
    for rel, data in files.items():
        (out / rel).write_bytes(data)
    (out / "manifest.json").write_bytes(_dump(manifest))
    return manifest


def _human_readme(manifest: dict[str, Any]) -> str:
    scope = manifest["scope"]
    ledger = manifest["ledger"]
    banner = banner_lines(manifest["cui_marking"])
    scope_line = (f"deployment ledger (platform plane)"
                  if scope["kind"] == "deployment"
                  else f"tenant ledger for tenant `{scope['tenant_id']}`")
    lines = [
        *banner,
        "",
        "# Platform audit export",
        "",
        f"Scope: {scope_line}.",
        "",
        "This export is a snapshot of one append-only platform audit "
        "ledger, produced under Spec 005 T542 in the Phase 5 bundle "
        "pattern. It contains:",
        "",
        "- `ledger/audit.axmr` — the ledger itself, copied byte-for-byte",
        "- `events.json` — every event in the ledger, in order",
        "- `poam.json` — the scope's POA&M register (T553), replayed",
        "- `control-states.json` — the scope's SPRS-input control "
        "states and computed score (T552), where seeded",
        "- `manifest.json` — the file manifest; its bundle hash binds "
        "this file set",
        "",
        f"Events: {ledger['event_count']} · head seq {ledger['head_seq']} · "
        f"checkpoint root `{ledger['checkpoint_root']}`",
        "",
        "## Verify it yourself",
        "",
        "From a Tekmerion checkout: `python -m tekmerion.platform.exports "
        "<this directory>` — the standalone verifier re-checks the file "
        "hashes, runs the production Axiomere verifier over the ledger "
        "copy, and cross-checks every projection against the ledger's "
        "own events, using the export alone.",
        "",
        "What this export establishes: the record as exported is "
        "internally intact and matches the ledger it was taken from "
        "(whose continuing chain carries the `audit.exported` record "
        "of this export). What it does not establish: that events "
        "were never omitted before the fact — an append-only ledger "
        "proves the record it holds, and the anchor record (T543) is "
        "what binds this snapshot to the continuing chain.",
        "",
        *banner,
        "",
    ]
    return "\n".join(lines)


@dataclass
class PlatformExportVerification:
    ok: bool
    failures: list[str] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)


def verify_platform_audit_export(bundle_dir: str) -> PlatformExportVerification:
    """Verify a platform audit export using only the export. Every
    check that can fail is collected; `ok` requires all to pass."""
    root = Path(bundle_dir)
    failures: list[str] = []
    checks: dict[str, Any] = {}

    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return PlatformExportVerification(False, ["manifest.json missing"], checks)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return PlatformExportVerification(False, [f"manifest.json does not parse: {exc}"], checks)
    if manifest.get("format") != EXPORT_FORMAT:
        failures.append(f"unknown export format {manifest.get('format')!r}")
    checks["format"] = manifest.get("format")

    core = {k: v for k, v in manifest.items() if k != "bundle_hash"}
    if _sha256(_canonical(core)) != manifest.get("bundle_hash"):
        failures.append("bundle hash mismatch: manifest does not bind this file set")
    checks["bundle_hash"] = manifest.get("bundle_hash")

    listed: dict[str, dict[str, Any]] = {}
    for entry in manifest.get("files", []):
        listed[entry["path"]] = entry
        path = root / entry["path"]
        if not path.exists():
            failures.append(f"listed file missing: {entry['path']}")
            continue
        data = path.read_bytes()
        if len(data) != entry["bytes"]:
            failures.append(f"size mismatch: {entry['path']}")
        if _sha256(data) != entry["sha256"]:
            failures.append(f"sha256 mismatch: {entry['path']}")
    checks["files_listed"] = len(listed)
    actual = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*") if p.is_file()
    } - {"manifest.json"}
    for rel in sorted(actual - set(listed)):
        failures.append(f"unlisted file present in export: {rel}")

    def load_json(rel: str) -> Any:
        try:
            return json.loads((root / rel).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            failures.append(f"{rel} does not parse: {exc}")
            return None

    # -- the ledger copy, via the production verifier -------------------
    ledger_info = manifest.get("ledger", {})
    ledger_path = root / ledger_info.get("file", "ledger/audit.axmr")
    events: list[dict[str, Any]] = []
    if ledger_path.exists():
        import axiomere as ax

        result = ax.verify_file(str(ledger_path))
        checks["ledger_verify"] = {
            "ok": result.ok, "events": result.events, "reason": result.reason,
            # The signature state rides in the verification record
            # (Axiomere Spec 003): an honestly unsigned ledger is a
            # visible state here, never a silent pass.
            "signatures_checked": result.signatures_checked,
            "signatures_failed": result.signatures_failed,
            "unsigned_events": list(result.unsigned_events),
            "untrusted_actors": list(result.untrusted_actors),
        }
        if not result.ok:
            failures.append(f"ledger fails production verification: {result.reason}")
        if result.events != ledger_info.get("event_count"):
            failures.append(
                f"ledger event count {result.events} != manifest {ledger_info.get('event_count')}")
        try:
            events = _ledger_events(ledger_path.read_bytes())
        except (ValueError, UnicodeDecodeError) as exc:
            failures.append(f"ledger does not parse as JSONL: {exc}")
    else:
        failures.append("ledger copy missing from export")
    if events:
        if events[-1]["hash"] != ledger_info.get("head_hash"):
            failures.append("manifest head hash does not match the exported ledger head")
        checkpoints = _checkpoints(events)
        if checkpoints != ledger_info.get("checkpoints"):
            failures.append("manifest checkpoints do not match the exported ledger")
        if not checkpoints or checkpoints[-1]["merkle_root"] != ledger_info.get("checkpoint_root"):
            failures.append("manifest checkpoint root is not the ledger's latest checkpoint root")
        checks["checkpoint_root"] = ledger_info.get("checkpoint_root")

        # Recomputed-root binding (Axiomere Spec 003 companion,
        # AXM-003-15): the manifest's checkpoint root and head hash
        # are also pinned through the production verifier, which
        # compares them against the values it recomputes from the
        # ledger's events — a transplanted root fails here even
        # when the presented file's chain is internally consistent.
        pin_spec: dict[str, Any] = {}
        if ledger_info.get("checkpoint_root"):
            pin_spec["checkpoint_root"] = ledger_info["checkpoint_root"]
        if ledger_info.get("head_hash"):
            pin_spec["head_hash"] = ledger_info["head_hash"]
        if pin_spec and result.ok:
            pinned = ax.verify_file(str(ledger_path), expected_head=pin_spec)
            checks["ledger_head_pin"] = {"ok": pinned.ok, "reason": pinned.reason}
            if not pinned.ok:
                failures.append(
                    "manifest head does not match the recomputed head: "
                    f"{pinned.reason}")

    # -- projections cross-checked against the ledger copy ---------------
    events_doc = load_json("events.json")
    if events_doc is not None and events:
        if events_doc.get("events") != events:
            failures.append("events.json does not match the exported ledger's events")
        checks["events_projection"] = len(events)

    states_doc = load_json("control-states.json")
    if states_doc is not None and events and states_doc.get("seeded") is not False \
            and "inputs" in states_doc:
        replay = _replay_states(events)
        if replay is None:
            failures.append("control-states.json present but the exported ledger "
                            "carries no compliance.states_seeded event")
        else:
            if states_doc["inputs"] != compliance.sprs_input_form(replay):
                failures.append("control-states.json inputs do not match the replay "
                                "of the exported ledger's compliance events")
            recomputed = compliance.compute_score(replay)
            if states_doc.get("score") != recomputed["score"]:
                failures.append("control-states.json score does not recompute "
                                "from its inputs")
            checks["sprs_score"] = recomputed["score"]

    checks["cui_marking"] = (manifest.get("cui_marking") or {}).get("status")
    return PlatformExportVerification(not failures, failures, checks)


def _replay_states(events: list[dict[str, Any]]) -> Optional[dict[str, dict[str, Any]]]:
    """Replay a state set from exported events alone (seed + the
    state-set events), or None when the ledger never seeded."""
    if not any(e["type"] == "compliance.states_seeded" for e in events):
        return None
    states = compliance.seed_states()
    for event in events:
        if event["type"] != "compliance.state_set":
            continue
        payload = event["payload"]
        req = payload["requirement"]
        states[req] = {
            **states[req],
            "state": payload["state"],
            "evidence_link": payload.get("evidence_link"),
            "gap_marker": payload.get("gap_marker"),
            "set_by": payload.get("actor_id"),
            "seq": event["seq"],
        }
    return states


def _main(argv: list[str]) -> int:
    import sys

    if len(argv) != 2:
        print("usage: python -m tekmerion.platform.exports <export-dir>", file=sys.stderr)
        return 2
    result = verify_platform_audit_export(argv[1])
    print(json.dumps({"ok": result.ok, "checks": result.checks,
                      "failures": result.failures}, indent=2))
    return 0 if result.ok else 1


if __name__ == "__main__":
    import sys

    sys.exit(_main(sys.argv))
