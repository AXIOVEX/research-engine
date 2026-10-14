"""E6 compliance-evidence batteries (Spec 005 T541–T545, T547,
T551–T553).

- T552 / CLM-005-29: the DoD weight table's integrity, the seed's
  derivation from the matrix, score determinism, a state change
  moving the score by exactly its deduction class, evidence-link
  completeness, and the matrix/state agreement check (F-005-29).
- T553 / CLM-005-30: the POA&M register — items, milestones, and
  status as appended events only (F-005-30), seeded with the
  §3.13.11 FIPS item exactly as the records carry it.
- T542/T543 / CLM-005-15: platform audit exports in the Phase 5
  pattern — standalone verification, the tamper battery incl. the
  attacker-rehashed manifest (F-005-15), the anchor record, and
  the export-based residency flow.
- T541 / CLM-005-12: the residency pin moves only through
  export + anchor + migration; a bare field update is refused.
- T545 / CLM-005-17: legal hold — marker + export + anchor +
  access restriction; erasure and pin changes refused under a
  hold; the F-005-17 audit (no deletion path over ledger content).
- T551 / CLM-005-28: CUI marking in platform exports and study
  bundles — marked artifacts carry it in manifest + README;
  unmarked artifacts state their unmarked state.
- T544/T547 / CLM-005-16, CLM-005-23: the SOC 2 readiness mapping
  resolves (claims + code paths exist), and the wording sweep
  over public surfaces finds no unqualified certification claim
  beyond the reviewed baseline.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

pytest.importorskip("axiomere")

from tekmerion.export import export_bundle, verify_bundle  # noqa: E402
from tekmerion.marking import normalize_marking  # noqa: E402
from tekmerion.platform import compliance  # noqa: E402
from tekmerion.platform.errors import (  # noqa: E402
    AuthorizationDenied, ConfigurationError,
)
from tekmerion.platform.exports import (  # noqa: E402
    export_platform_audit, verify_platform_audit_export,
)
from tekmerion.platform.ledger import PlatformLedger  # noqa: E402
from tekmerion.platform.matrix_data import MATRIX_CLASSES  # noqa: E402

from e1_world import build_world, login_user  # noqa: E402
from test_phase5 import build_study, controls  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SPEC_DIR = REPO / "specs" / "005-enterprise-platform"


# ---------------------------------------------------------------- T552

def test_dod_weight_table_integrity():
    weights = compliance.DOD_WEIGHTS
    assert len(weights) == 110
    assert sum(1 for v in weights.values() if v == 5) == 44
    assert sum(1 for v in weights.values() if v == 3) == 14
    assert sum(1 for v in weights.values() if v == 1) == 51
    assert weights["3.12.4"] is None  # Annex A: NA — unscored, not zero-weight by stealth
    total = sum(v for v in weights.values() if v)
    assert total == 313
    assert 110 - total == -203  # the methodology's documented floor
    assert compliance.PARTIAL_DEDUCTIONS == {"3.5.3": 3, "3.13.11": 3}


def test_matrix_data_matches_the_matrix_document():
    """The generated classification table is the matrix document's
    table — re-parsed here from the maintained record itself."""
    text = (SPEC_DIR / "cmmc-responsibility-matrix.md").read_text()
    parsed = {}
    for line in text.splitlines():
        m = re.match(r"\| (3\.\d+\.\d+) \| ([^|]+) \| ([^|]+) \|", line)
        if m:
            parsed[m.group(1)] = m.group(3).strip().split(" — ")[0].strip("*")
    assert parsed == MATRIX_CLASSES
    assert len(parsed) == 110


def test_seed_derivation_and_score():
    states = compliance.seed_states()
    assert compliance.completeness_failures(states) == []
    assert compliance.agreement_failures(states) == []
    result = compliance.compute_score(states)
    # The seed measures the platform's inputs alone: the 17
    # Platform-classified requirements implemented, §3.13.11 at its
    # §5(e) partial deduction, every operator remainder open.
    assert result["deductions"]["3.13.11"] == 3
    assert result["total_deduction"] == 266
    assert result["score"] == -156
    assert result["unscored"] == ["3.12.4"]
    # Determinism: the same inputs always compute the same score.
    assert compliance.compute_score(compliance.seed_states()) == result
    fips = states["3.13.11"]
    assert fips["state"] == compliance.PARTIALLY_IMPLEMENTED
    assert "POAM-0001" in fips["gap_marker"]


def test_platform_seed_evidence_paths_exist():
    """A Platform-classified seed state cites machinery; machinery
    that does not exist is not evidence."""
    for req, record in compliance.seed_states().items():
        if record["matrix_class"] == "Platform":
            assert record["machinery"], req
            for path in record["machinery"]:
                assert (REPO / path).exists(), f"{req} cites missing {path}"


def test_agreement_check_catches_f005_29_shapes():
    states = compliance.seed_states()
    states["3.10.3"] = {**states["3.10.3"], "state": compliance.IMPLEMENTED}
    failures = compliance.agreement_failures(states)
    assert any("3.10.3" in f for f in failures)  # Organizational claimed by the seed
    states = compliance.seed_states()
    states["3.5.3"] = {**states["3.5.3"], "state": compliance.IMPLEMENTED}
    assert any("3.5.3" in f for f in compliance.agreement_failures(states))
    # An operator-set record is the organization's own statement —
    # constrained by completeness, not by the class rule.
    states = compliance.seed_states()
    states["3.10.3"] = {**states["3.10.3"], "state": compliance.IMPLEMENTED,
                        "set_by": "actor-123", "gap_marker": None,
                        "evidence_link": "org/facilities-record"}
    assert compliance.agreement_failures(states) == []


def test_state_change_moves_score_by_exactly_its_deduction_class(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    assert svc.seed_control_states(w.admin_session, tenant_id=w.tenant_id)
    before = svc.sprs_report(w.admin_session, tenant_id=w.tenant_id)
    assert before["score"] == -156
    # 3.13.6 is Supports, weight 5: closing it moves the score +5.
    svc.set_control_state(
        w.admin_session, tenant_id=w.tenant_id, requirement="3.13.6",
        state="implemented", evidence_link="org/network-rules-2026-10")
    after = svc.sprs_report(w.admin_session, tenant_id=w.tenant_id)
    assert after["score"] - before["score"] == 5
    # 3.5.3 partial (MFA for remote + privileged only): deduction 3 of 5.
    svc.set_control_state(
        w.admin_session, tenant_id=w.tenant_id, requirement="3.5.3",
        state="partially_implemented", evidence_link="org/idp-mfa-rollout")
    partial = svc.sprs_report(w.admin_session, tenant_id=w.tenant_id)
    assert partial["score"] - after["score"] == 2
    assert partial["deductions"]["3.5.3"] == 3
    # Recomputation is deterministic across replays.
    assert svc.sprs_report(w.admin_session, tenant_id=w.tenant_id) == partial


def test_state_set_requires_evidence_or_gap_and_ledgers_refusal(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    svc.seed_control_states(w.admin_session, tenant_id=w.tenant_id)
    with pytest.raises(ConfigurationError):
        svc.set_control_state(
            w.admin_session, tenant_id=w.tenant_id, requirement="3.1.3",
            state="implemented")
    types = svc._tenant_ledger(w.tenant_id).event_types()
    assert "compliance.state_set_refused" in types
    with pytest.raises(ConfigurationError):
        svc.set_control_state(
            w.admin_session, tenant_id=w.tenant_id, requirement="9.9.9",
            state="implemented", evidence_link="x")


def test_study_role_cannot_write_compliance_state(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    svc.seed_control_states(w.admin_session, tenant_id=w.tenant_id)
    alice_session, _ = login_user(w, "alice", role="researcher")
    with pytest.raises(AuthorizationDenied):
        svc.set_control_state(
            alice_session, tenant_id=w.tenant_id, requirement="3.1.3",
            state="implemented", evidence_link="org/x")


# ---------------------------------------------------------------- T553

def test_poam_register_seeded_with_fips_item(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    item_id = svc.seed_poam_fips_item(w.root_session)
    assert item_id == "POAM-0001"
    assert svc.seed_poam_fips_item(w.root_session) is None  # idempotent
    doc = svc.poam_register_document(w.root_session)
    (item,) = doc["items"]
    assert item["affected_requirements"] == ["3.13.11"]
    assert "FIPS 140-3" in item["weakness"]
    assert item["source_ref"].endswith("crypto-inventory.md")
    assert len(item["milestones"]) == 3
    assert item["status"] == "open"


def test_poam_status_changes_are_events_only(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    svc.seed_poam_fips_item(w.root_session)
    ledger = svc.deployment_ledger
    count_before = len(ledger.events())
    svc.poam_set_status(w.root_session, item_id="POAM-0001",
                        status="in_progress", note="owner review scheduled")
    events = ledger.events()
    assert len(events) == count_before + 1  # appended, never edited
    assert events[-1]["type"] == "poam.status_changed"
    item = svc.poam_register_document(w.root_session)["items"][0]
    assert item["status"] == "in_progress"
    assert [h["status"] for h in item["status_history"]] == ["open", "in_progress"]
    milestone_id = item["milestones"][0]["milestone_id"]
    svc.poam_complete_milestone(w.root_session, item_id="POAM-0001",
                                milestone_id=milestone_id, note="recorded")
    item = svc.poam_register_document(w.root_session)["items"][0]
    assert item["milestones"][0]["status"] == "completed"
    with pytest.raises(ConfigurationError):
        svc.poam_set_status(w.root_session, item_id="POAM-9999", status="open")


def test_tenant_poam_register_is_the_tenants_own(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    item_id = svc.poam_create_item(
        w.admin_session, tenant_id=w.tenant_id, title="Rotate IdP cert",
        weakness="certificate expires", affected_requirements=["3.5.2"],
        source_ref="tenant/ops-review")
    assert item_id == "POAM-0001"  # per-scope numbering
    assert svc.poam_register_document(w.root_session)["items"] == []
    doc = svc.poam_register_document(w.admin_session, tenant_id=w.tenant_id)
    assert [i["item_id"] for i in doc["items"]] == ["POAM-0001"]


# ------------------------------------------------------- T542/T543/T541

def _seeded_tenant(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    svc.seed_control_states(w.admin_session, tenant_id=w.tenant_id)
    svc.poam_create_item(
        w.admin_session, tenant_id=w.tenant_id, title="Tenant item",
        weakness="w", affected_requirements=["3.12.2"], source_ref="tenant/ssp")
    return w


def test_tenant_audit_export_verifies_standalone(tmp_path):
    w = _seeded_tenant(tmp_path)
    svc = w.service
    manifest = svc.export_tenant_audit(
        w.admin_session, w.tenant_id, str(tmp_path / "exp"))
    assert manifest["scope"] == {"kind": "tenant", "tenant_id": w.tenant_id}
    assert manifest["cui_marking"]["status"] == "unmarked"
    result = verify_platform_audit_export(str(tmp_path / "exp"))
    assert result.ok, result.failures
    assert result.checks["sprs_score"] == -156
    poam = json.loads((tmp_path / "exp" / "poam.json").read_text())
    assert [i["title"] for i in poam["items"]] == ["Tenant item"]
    readme = (tmp_path / "exp" / "HUMAN-README.md").read_text()
    assert readme.splitlines()[0].startswith("CUI marking: none recorded")
    # The export itself is a record in the continuing ledger.
    assert "audit.exported" in svc._tenant_ledger(w.tenant_id).event_types()


def _rehash_export(bundle: Path) -> None:
    """The F-005-15 attack: rewrite the manifest so its hashes bind
    whatever the files now say."""
    manifest = json.loads((bundle / "manifest.json").read_text())
    entries = []
    for entry in manifest["files"]:
        data = (bundle / entry["path"]).read_bytes()
        entries.append({"path": entry["path"],
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "bytes": len(data)})
    manifest["files"] = entries
    core = {k: v for k, v in manifest.items() if k != "bundle_hash"}
    canonical = json.dumps(core, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode()
    manifest["bundle_hash"] = hashlib.sha256(canonical).hexdigest()
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def test_export_tamper_battery_incl_rehashed_manifest(tmp_path):
    w = _seeded_tenant(tmp_path)
    svc = w.service
    svc.export_tenant_audit(w.admin_session, w.tenant_id, str(tmp_path / "good"))
    assert verify_platform_audit_export(str(tmp_path / "good")).ok

    # (a) a flipped projection entry fails.
    import shutil
    shutil.copytree(tmp_path / "good", tmp_path / "flip")
    events_doc = json.loads((tmp_path / "flip" / "events.json").read_text())
    events_doc["events"][0]["payload"]["outcome"] = "forged"
    (tmp_path / "flip" / "events.json").write_text(json.dumps(events_doc))
    assert not verify_platform_audit_export(str(tmp_path / "flip")).ok

    # (b) the same flip under a fully rehashed manifest still fails:
    # the ledger copy's chain is the ground truth projections are
    # checked against.
    shutil.copytree(tmp_path / "good", tmp_path / "rehash")
    events_doc = json.loads((tmp_path / "rehash" / "events.json").read_text())
    events_doc["events"][0]["payload"]["outcome"] = "forged"
    (tmp_path / "rehash" / "events.json").write_text(json.dumps(events_doc))
    _rehash_export(tmp_path / "rehash")
    result = verify_platform_audit_export(str(tmp_path / "rehash"))
    assert not result.ok
    assert any("events.json" in f for f in result.failures)

    # (c) an altered event inside the ledger copy fails the
    # production verifier, rehashed manifest or not. (The tenant
    # ledger carries the tenant's POA&M title — payload text whose
    # alteration breaks the chain hash.)
    shutil.copytree(tmp_path / "good", tmp_path / "ledgerflip")
    axmr = tmp_path / "ledgerflip" / "ledger" / "audit.axmr"
    data = axmr.read_bytes()
    assert b"Tenant item" in data
    axmr.write_bytes(data.replace(b"Tenant item", b"Tenant ixem", 1))
    _rehash_export(tmp_path / "ledgerflip")
    result = verify_platform_audit_export(str(tmp_path / "ledgerflip"))
    assert not result.ok
    assert any("ledger" in f for f in result.failures)


def test_export_refuses_a_broken_ledger(tmp_path):
    led = PlatformLedger.create(str(tmp_path / "broken.axmr"),
                                scope="tenant", tenant_id="uni-z")
    led.record("tenant.created", actor_id="a", target="tenant:uni-z")
    led.checkpoint(actor_id="a")
    path = Path(tmp_path / "broken.axmr")
    data = path.read_bytes()
    path.write_bytes(data.replace(b"tenant.created", b"tenant.creaxed", 1))
    # The record layer itself refuses to reopen a broken chain…
    with pytest.raises(ValueError):
        PlatformLedger.open(str(path), scope="tenant", tenant_id="uni-z")
    # …and the already-open handle's verification fails, so the
    # export refuses: a broken record is evidence, not an export.
    assert not led.verify().ok
    with pytest.raises(ValueError):
        export_platform_audit(led, str(path), str(tmp_path / "out"))


def test_residency_pin_moves_only_through_the_flow(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    pin = svc.residency_pin(w.root_session, w.tenant_id)
    assert pin == {"tenant_id": w.tenant_id, "shape": "hosted",
                   "region": None, "migrations": 0, "last_migration_seq": None}
    # A bare field update is refused — and the refusal is a record.
    with pytest.raises(ConfigurationError):
        svc.update_tenant(w.root_session, tenant_id=w.tenant_id, region="eu-west")
    assert "tenant.residency_change_refused" in \
        svc.deployment_ledger.event_types()
    # The migration without an anchored export is refused too.
    with pytest.raises(ConfigurationError):
        svc.change_residency_pin(w.root_session, tenant_id=w.tenant_id,
                                 shape="hosted", region="eu-west")
    # Export + anchor, then the migration lands as events in both
    # ledgers, carrying the export that authorized it.
    manifest = svc.export_tenant_audit(
        w.admin_session, w.tenant_id, str(tmp_path / "exp"))
    svc.record_export_anchor(
        w.admin_session, tenant_id=w.tenant_id,
        export_id=manifest["export_id"], mechanism="local-record",
        ref=manifest["bundle_hash"])
    pin = svc.change_residency_pin(w.root_session, tenant_id=w.tenant_id,
                                   shape="hosted", region="eu-west")
    assert pin["region"] == "eu-west" and pin["migrations"] == 1
    assert "tenant.residency_migrated" in svc.deployment_ledger.event_types()
    assert "tenant.residency_migrated" in \
        svc._tenant_ledger(w.tenant_id).event_types()


# ---------------------------------------------------------------- T545

def test_legal_hold_flow_and_enforcement(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    _, rudy = login_user(w, "rudy", role="reviewer")
    svc.deactivate_identity(w.admin_session, identity_id=rudy.identity_id)
    # Sanity: without a hold, erasure is available for the
    # deactivated identity's tenant-mate (done after release below).
    placed = svc.place_legal_hold(
        w.admin_session, tenant_id=w.tenant_id, scope_ref="tenant:uni-a",
        reason="litigation preservation", authority="court order 26-CV-1",
        out_dir=str(tmp_path / "hold-exp"))
    assert placed["hold_id"] == "HOLD-0001"
    assert verify_platform_audit_export(str(tmp_path / "hold-exp")).ok
    ledger = svc._tenant_ledger(w.tenant_id)
    assert "legal.hold_placed" in ledger.event_types()
    # Under the hold: erasure refused (and ledgered), tenant-plane
    # export refused, the pin does not move.
    with pytest.raises(ConfigurationError):
        svc.erase_directory_pii(w.admin_session, identity_id=rudy.identity_id)
    assert "legal.hold_enforced" in ledger.event_types()
    with pytest.raises(AuthorizationDenied):
        svc.export_tenant_audit(w.admin_session, w.tenant_id,
                                str(tmp_path / "held-exp"))
    svc.export_tenant_audit(w.root_session, w.tenant_id,
                            str(tmp_path / "platform-exp"))  # platform plane may
    with pytest.raises(ConfigurationError):
        svc.change_residency_pin(w.root_session, tenant_id=w.tenant_id,
                                 shape="hosted", region="eu-west")
    # Release is an event; afterwards erasure proceeds.
    svc.release_legal_hold(w.admin_session, tenant_id=w.tenant_id,
                           hold_id="HOLD-0001", note="order lifted")
    assert svc.active_holds(w.admin_session, tenant_id=w.tenant_id) == []
    assert svc.erase_directory_pii(w.admin_session,
                                   identity_id=rudy.identity_id)


def test_no_deletion_path_over_ledger_content():
    """F-005-17's audit: the platform exposes no operation that
    deletes or masks ledger content — in any module, at any plane.
    (The directory-PII erasure is off-ledger by design and is the
    T524 path; the DN-005 erasure certificate remains specified,
    not executable — Spec 005 §8.)"""
    ledger = PlatformLedger
    for name in ("delete", "remove", "update", "erase", "drop", "truncate"):
        assert not hasattr(ledger, name), name
    src = REPO / "src" / "tekmerion" / "platform"
    offenders = []
    for path in src.glob("*.py"):
        text = path.read_text()
        for pattern in (r"os\.remove", r"\.unlink\(", r"shutil\.rmtree",
                        r"os\.unlink"):
            if re.search(pattern, text):
                offenders.append(f"{path.name}: {pattern}")
    assert offenders == []


# ---------------------------------------------------------------- T551

def test_marking_in_platform_export_and_study_bundle(tmp_path):
    w = build_world(tmp_path)
    svc = w.service
    # Unmarked by default, and stated as such.
    manifest = svc.export_tenant_audit(
        w.admin_session, w.tenant_id, str(tmp_path / "unmarked"))
    assert manifest["cui_marking"]["status"] == "unmarked"
    # Record a marking, then export again: manifest + README carry it.
    svc.set_tenant_marking(
        w.admin_session, w.tenant_id, category="CUI//SP-CTI",
        authority="DoD", dissemination="FEDCON")
    manifest = svc.export_tenant_audit(
        w.admin_session, w.tenant_id, str(tmp_path / "marked"))
    block = manifest["cui_marking"]
    assert block["status"] == "marked" and block["category"] == "CUI//SP-CTI"
    readme = (tmp_path / "marked" / "HUMAN-README.md").read_text()
    lines = [ln for ln in readme.splitlines() if ln.strip()]
    assert "CUI//SP-CTI" in lines[0] and "CUI//SP-CTI" in lines[-1]
    assert verify_platform_audit_export(str(tmp_path / "marked")).ok

    # Study bundles: the same block + banner/footer discipline.
    store, reg, _frozen, retrieved = build_study(tmp_path)
    marked = export_bundle(
        store, str(tmp_path / "s.axmr"), str(tmp_path / "bundle-marked"),
        register=reg, controls=controls(), linked_exploratory=[],
        retrieved=retrieved,
        marking={"category": "CUI//SP-PVCY", "authority": "Institution",
                 "dissemination": "NOFORN"})
    assert marked["cui_marking"]["status"] == "marked"
    readme = (tmp_path / "bundle-marked" / "HUMAN-README.md").read_text()
    lines = [ln for ln in readme.splitlines() if ln.strip()]
    assert "CUI//SP-PVCY" in lines[0] and "CUI//SP-PVCY" in lines[-1]
    assert verify_bundle(str(tmp_path / "bundle-marked")).ok
    plain = export_bundle(
        store, str(tmp_path / "s.axmr"), str(tmp_path / "bundle-plain"),
        register=reg, controls=controls(), linked_exploratory=[],
        retrieved=retrieved)
    assert plain["cui_marking"]["status"] == "unmarked"
    assert verify_bundle(str(tmp_path / "bundle-plain")).ok


def test_normalize_marking_shapes():
    assert normalize_marking(None)["status"] == "unmarked"
    assert normalize_marking({})["status"] == "unmarked"
    block = normalize_marking({"category": "CUI"})
    assert block["status"] == "marked" and block["authority"] is None


# ------------------------------------------------------- T544 + T547

def test_soc2_mapping_entries_resolve():
    """F-005-16: every mapping entry points at machinery or a
    record that exists — claim IDs resolve into the bundle, code
    paths resolve into the tree."""
    doc = (SPEC_DIR / "soc2-readiness-mapping.md").read_text()
    assert "READINESS MAPPING ONLY" in doc
    assert "no SOC 2 report" in doc
    claims = {c["id"] for c in json.loads(
        (SPEC_DIR / "aee-claims.json").read_text())["claims"]}
    cited = set(re.findall(r"CLM-005-\d+", doc))
    assert len(cited) >= 15
    assert cited <= claims, cited - claims
    paths = set(re.findall(r"`(src/tekmerion/[^`]+)`", doc))
    assert len(paths) >= 10
    for path in paths:
        assert (REPO / path).exists(), path


#: The reviewed wording-sweep baseline (T547): lines whose
#: certification vocabulary is a negation, a non-claim, or
#: ecosystem description — reviewed hit by hit at E6. A NEW hit
#: fails this test until it is reviewed and either reworded or
#: added here with its reason.
_SWEEP_PATTERNS = [
    r"SOC 2[^\n]{0,48}certif", r"CMMC[^\n]{0,36}certif",
    r"CMMC[^\n]{0,24}\bcompliant\b", r"CMMC[^\n]{0,24}\bcompliance\b",
    r"FedRAMP[^\n]{0,24}(authorized|certified|compliant)",
    r"(HIPAA|FERPA|GDPR)[^\n]{0,24}(compliant|certified|certification)",
]
_NEGATIONS = ("not ", "never", "no ", "n't", "without", "do not",
              "not-yet", "not yet", "non-claim", "no claim")

#: Hits reviewed one by one at the E6 sweep (2026-10-12) that are
#: neither negations nor claims about the platform: the owner's
#: directive quoted verbatim in the records that adopt it in its
#: truthful form; the sanctioned §13 posture phrase; an entry in a
#: not-claimed list. Keyed on substrings so the baseline survives
#: line movement; a hit matching none of these and no negation
#: fails the sweep until a human reviews it.
_REVIEWED_SUBSTRINGS = (
    "also make this tool CMMC compliant",
    "CMMC Level 2 alignment / compliance",
    "CMMC compliance (DN-011 language governs)",
    # E6 sweep review, continued: framing/ecosystem statements and
    # non-goal or not-claimed list entries whose negation lives in
    # the surrounding sentence or section rather than on the line.
    "CMMC certification attaches to an organization",
    "certifies organizations and assessment",
    "CMMC certification or compliance (alignment language only",
    "readiness and evidence only (CLM-005-16)",
)


def _sweep_hits() -> list[str]:
    surfaces = [REPO / "README.md"] + sorted((REPO / "docs").rglob("*.md")) \
        + sorted(SPEC_DIR.glob("*.md"))
    hits = []
    for path in surfaces:
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            for pattern in _SWEEP_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    hits.append(f"{path.relative_to(REPO)}:{lineno}: {line.strip()}")
                    break
    return hits


def test_wording_sweep_no_unqualified_certification_claims():
    hits = _sweep_hits()
    unreviewed = []
    for hit in hits:
        line = hit.split(": ", 1)[1]
        lowered = line.lower()
        if any(neg in lowered for neg in _NEGATIONS):
            continue
        if any(sub in line for sub in _REVIEWED_SUBSTRINGS):
            continue
        unreviewed.append(hit)
    assert unreviewed == [], (
        "unqualified certification-claim wording on a public surface "
        "(T547 — reword, or review and record):\n" + "\n".join(unreviewed))
