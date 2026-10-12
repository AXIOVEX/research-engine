"""Spec 010 tests: OSF deposit + registration anchor — payload
derivation from the osf_metadata mapping, the adjudicator/freeze gate,
idempotency, failure surfacing + resume, the receipt, and
verify_osf_anchor — all against a fake transport implementing the
OSFTransport method surface with provider-shaped records. The live OSF
demonstration is a recorded build step (specs/010-osf-registration/
records/), not a CI dependency — the same posture as Phase 5's Zenodo
tests. The fixture study builder mirrors tests/test_phase5.py.
"""

import hashlib
import inspect
import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("axiomere")

from tekmerion.claims import Claim, ClaimRegister
from tekmerion.connectors import CrossrefConnector, HttpJson, run_query
from tekmerion.deposit import DepositError, osf_metadata, record_anchor
from tekmerion.export import export_bundle, verify_bundle
from tekmerion.freeze import freeze
from tekmerion.osf_deposit import (
    OPEN_ENDED_SCHEMA,
    deposit_bundle_osf,
    verify_osf_anchor,
)
from tekmerion.store import StudyStore
from tekmerion.verdicts import Control, evaluate_run
from tekmerion.verification import (
    Citation,
    decide,
    pending_second_reviews,
    to_evidence_item,
    verify_citations,
)

PROP = "Auricular stimulation improves sleep quality"

REAL_WORK = {
    "DOI": "10.1000/xyz123",
    "title": ["Auricular Stimulation and Sleep Quality"],
    "author": [{"given": "Ada", "family": "Lovelace"}],
    "issued": {"date-parts": [[2024, 5, 1]]},
    "container-title": ["Journal of X"],
    "abstract": "Auricular stimulation improved sleep quality significantly in a controlled trial.",
    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
}

META_WORK = {
    "DOI": "10.1000/metaonly",
    "title": ["Auricular Stimulation and Sleep Quality"],
    "author": [{"given": "Ada", "family": "Lovelace"}],
    "issued": {"date-parts": [[2024, 5, 1]]},
    "container-title": ["Journal of X"],
    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
}


class RoutingHttp(HttpJson):
    def get(self, url, headers=None):
        if "query.bibliographic" in url:
            return {"message": {"items": [REAL_WORK]}}
        for marker, work in (("xyz123", REAL_WORK), ("metaonly", META_WORK)):
            if marker in url:
                return {"message": work}
        raise RuntimeError("404 from source of record")


def crossref():
    return CrossrefConnector(http=RoutingHttp())


def claim(cid, **kw):
    base = dict(statement="X holds", falsifier="observing not-X in a powered test",
                margin=0.1, sufficiency_floor=1)
    base.update(kw)
    return Claim(claim_id=cid, **base)


def controls():
    pos = Control(
        failure_mode="retrieval broken: known-true claim not supported",
        kind="positive",
        claim=claim("CLM-S-900"),
        groups=[{"origin_group": "G1", "support_mass": 0.9, "contradiction_mass": 0.0,
                 "could_falsify": True, "falsifier_observation": False, "verified": True,
                 "items": 1, "metadata_only": False}],
        expected="supported",
        representative_rationale="same domain and difficulty class as the study claims")
    neg = Control(
        failure_mode="verification decorative: fabricated citation accepted",
        kind="negative",
        claim=claim("CLM-S-901"),
        groups=[{"origin_group": "G9", "support_mass": 0.0, "contradiction_mass": 0.9,
                 "could_falsify": True, "falsifier_observation": True, "verified": True,
                 "items": 1, "metadata_only": False}],
        expected="contradicted")
    swap = Control(failure_mode="integrity machinery decorative: provenance swap undetected",
                   kind="swap")
    return [pos, neg, swap]


def citation(cid, claim_id, doi):
    return Citation(citation_id=cid, claim_id=claim_id, proposition=PROP, doi=doi,
                    title="Auricular Stimulation and Sleep Quality",
                    authors=["Ada Lovelace"], year=2024, venue="Journal of X")


def build_study(tmp_path, name="s"):
    """A complete small study through the production paths (mirrors
    tests/test_phase5.py): register, retrieve, verify, adjudicate,
    freeze, verdict — ready to export."""
    store = StudyStore.create(str(tmp_path / f"{name}.axmr"))
    reg = ClaimRegister()
    for cid, stmt, actor in (
            ("CLM-S-001", "Auricular stimulation improves sleep quality", "researcher"),
            ("CLM-S-002", "The effect replicates in a second cohort", "co-researcher")):
        c = claim(cid, statement=stmt)
        reg.register(c)
        store.register_claim(cid, c.as_dict(), actor=actor)

    run_query(store, crossref(), "auricular stimulation sleep", actor="researcher")
    cits = [citation("CIT-1", "CLM-S-001", "10.1000/xyz123"),
            citation("CIT-2", "CLM-S-002", "10.1000/metaonly"),
            citation("CIT-3", "CLM-S-001", "10.1000/doesnotexist")]
    report = verify_citations(store, cits, [crossref()], actor="researcher")
    by_id = {r.citation_id: r for r in report.results}
    assert by_id["CIT-1"].content == "supports"
    assert by_id["CIT-2"].content == "metadata_only"
    assert by_id["CIT-3"].resolution == "not_found"

    for qid in report.queue_item_ids:
        decide(store, qid, "exclude", adjudicator="adjudicator",
               rationale="fabricated DOI — excluded from the evidence basis")
    for qid in pending_second_reviews(store, fraction=0.10, seed=7):
        store.log_second_review(qid, reviewer="second-reviewer", agrees=True)

    reg.add_evidence("CLM-S-001", to_evidence_item(cits[0], by_id["CIT-1"]))
    reg.add_evidence("CLM-S-002", to_evidence_item(cits[1], by_id["CIT-2"]))

    frozen = freeze(store, reg, controls(), actor="researcher", linked_exploratory=[])
    result = evaluate_run(reg, mode="confirmation", controls=controls(),
                          store_path=str(tmp_path / f"{name}.axmr"))
    assert result.run_verdict == "valid"
    for verdict in result.claim_verdicts:
        store.issue_verdict(verdict.claim_id, verdict.as_dict(), actor="verdict-service")
    retrieved = {r.citation_id: r.retrieved for r in report.results if r.retrieved}
    return store, reg, frozen, retrieved


def export(tmp_path, store, reg, retrieved, name="bundle"):
    export_bundle(store, str(tmp_path / "s.axmr"), str(tmp_path / name),
                  register=reg, controls=controls(), linked_exploratory=[],
                  retrieved=retrieved)
    return str(tmp_path / name)


def rehash_manifest(bundle_dir):
    bundle = Path(bundle_dir)
    manifest = json.loads((bundle / "manifest.json").read_text())
    for entry in manifest["files"]:
        data = (bundle / entry["path"]).read_bytes()
        entry["sha256"] = hashlib.sha256(data).hexdigest()
        entry["bytes"] = len(data)
    core = {k: v for k, v in manifest.items() if k != "bundle_hash"}
    canonical = json.dumps(core, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode()
    manifest["bundle_hash"] = hashlib.sha256(canonical).hexdigest()
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


# ------------------------------------------------------------------ fake OSF

class FakeOSFTransport:
    """In-memory OSF: same method surface as OSFTransport, records in
    provider shapes. Registrations are born accepted (the depositing
    account is the admin); failures are injected per method, once."""

    mechanism = "osf"

    def __init__(self):
        self.nodes = {}
        self.files = {}
        self.folder_paths = {}
        self.drafts = {}
        self.registrations = {}
        self.calls = []
        self.fail_once = {}
        self._seq = 0

    def _next(self, prefix):
        self._seq += 1
        return f"{prefix}{self._seq:04d}"

    def _fail(self, name):
        if name in self.fail_once:
            raise self.fail_once.pop(name)

    @staticmethod
    def _node_view(node):
        return {"id": node["id"], "attributes": dict(node["attributes"]),
                "links": {"html": f"https://osf.io/{node['id']}/"}}

    def create_node(self, *, title, description="", category=None, tags=None,
                    public=True, parent=None):
        self.calls.append(("create_node", title))
        self._fail("create_node")
        guid = self._next("node")
        self.nodes[guid] = {
            "id": guid, "parent": parent,
            "attributes": {"title": title, "description": description,
                           "category": category, "tags": list(tags or []),
                           "public": public}}
        self.files[guid] = {}
        return self._node_view(self.nodes[guid])

    def get_node(self, guid):
        self.calls.append(("get_node", guid))
        if guid not in self.nodes:
            raise DepositError(f"OSF GET /nodes/{guid}/ failed: HTTP 404: not found")
        return self._node_view(self.nodes[guid])

    def list_children(self, guid):
        self.calls.append(("list_children", guid))
        return [self._node_view(n) for n in self.nodes.values()
                if n["parent"] == guid]

    def list_contributors(self, guid):
        return [{"embeds": {"users": {"data": {
            "attributes": {"full_name": "Tristen Pierson"}}}}}]

    def ensure_folder(self, guid, name, parent_path="/"):
        self.calls.append(("ensure_folder", f"{guid}:{name}"))
        path = f"/{guid}-{name}/"
        self.folder_paths[path] = name
        return path

    def upload_file(self, guid, name, data, folder_path="/"):
        self.calls.append(("upload_file", f"{guid}:{name}"))
        self._fail("upload_file")
        folder = self.folder_paths.get(folder_path)
        rel = f"{folder}/{name}" if folder else name
        self.files[guid][rel] = bytes(data)
        return {"id": self._next("file"), "attributes": {"name": name, "path": rel}}

    def list_files(self, guid):
        return [{"name": rel.rsplit("/", 1)[-1], "path": rel, "id": None,
                 "size": len(data)} for rel, data in sorted(self.files[guid].items())]

    def find_registration_schema(self, name=OPEN_ENDED_SCHEMA):
        self.calls.append(("find_registration_schema", name))
        if name != OPEN_ENDED_SCHEMA:
            raise DepositError(f"OSF registration schema not found by name: {name!r}")
        return "schema-open-ended"

    def list_registrations(self, guid):
        return [dict(r["view"]) for r in self.registrations.values()
                if r["project"] == guid]

    def list_draft_registrations(self, guid):
        return [self._draft_view(d) for d in self.drafts.values()
                if d["project"] == guid and not d["consumed"]]

    @staticmethod
    def _draft_view(draft):
        return {"id": draft["id"],
                "attributes": {"registration_responses": dict(draft["responses"])}}

    def get_draft_registration(self, draft_id):
        if draft_id not in self.drafts:
            raise DepositError(f"OSF GET /draft_registrations/{draft_id}/ failed: HTTP 404")
        return self._draft_view(self.drafts[draft_id])

    def create_draft_registration(self, guid, schema_id):
        self.calls.append(("create_draft_registration", guid))
        self._fail("create_draft_registration")
        assert schema_id == "schema-open-ended"
        draft = {"id": self._next("draft"), "project": guid, "schema": schema_id,
                 "responses": {}, "consumed": False}
        self.drafts[draft["id"]] = draft
        return self._draft_view(draft)

    def set_draft_responses(self, draft_id, responses):
        self.calls.append(("set_draft_responses", draft_id))
        self.drafts[draft_id]["responses"] = dict(responses)
        return self._draft_view(self.drafts[draft_id])

    def submit_registration(self, draft_id, *, component_ids, embargo_end_date=None):
        self.calls.append(("submit_registration", draft_id))
        self._fail("submit_registration")
        draft = self.drafts[draft_id]
        draft["consumed"] = True
        guid = self._next("reg")
        project = self.nodes[draft["project"]]
        view = {
            "id": guid,
            "attributes": {
                "title": project["attributes"]["title"],
                "description": project["attributes"]["description"],
                "registration_responses": dict(draft["responses"]),
                "registration_supplement": OPEN_ENDED_SCHEMA,
                "reviews_state": "accepted",
                "pending_registration_approval": False,
                "pending_embargo_approval": False,
                "embargoed": bool(embargo_end_date),
                "embargo_end_date": embargo_end_date,
                "date_registered": "2026-10-12T00:00:00.000000",
                "public": not embargo_end_date,
            },
            "relationships": {"registered_from": {"data": {"id": draft["project"]}}},
            "links": {"html": f"https://osf.io/{guid}/"},
        }
        self.registrations[guid] = {"project": draft["project"], "view": view,
                                    "components": list(component_ids)}
        return dict(view)

    def registration_action(self, registration_id, trigger):
        self.calls.append(("registration_action", trigger))
        return {}

    def get_registration(self, registration_id):
        if registration_id not in self.registrations:
            raise DepositError(
                f"OSF GET /registrations/{registration_id}/ failed: HTTP 404: not found")
        return dict(self.registrations[registration_id]["view"])

    def list_registration_identifiers(self, registration_id):
        return [{"attributes": {"category": "doi",
                                "value": f"10.17605/OSF.IO/{registration_id.upper()}"}}]


@pytest.fixture()
def bundle(tmp_path):
    store, reg, _frozen, retrieved = build_study(tmp_path)
    return export(tmp_path, store, reg, retrieved)


# ------------------------------------------------------------------ the claims

def test_payload_is_derived_from_the_mapping(bundle, tmp_path):
    """CLM-010-01: every OSF-visible field equals osf_metadata(manifest);
    the action's signature offers no title/description override."""
    params = set(inspect.signature(deposit_bundle_osf).parameters)
    assert "title" not in params and "description" not in params

    manifest = json.loads((Path(bundle) / "manifest.json").read_text())
    mapping = osf_metadata(manifest)
    fake = FakeOSFTransport()
    receipt = deposit_bundle_osf(bundle, fake, approved_by="owner",
                                 state_path=str(tmp_path / "state.json"))
    project = fake.nodes[receipt["project_guid"]]
    assert project["attributes"]["title"] == mapping["title"]
    assert project["attributes"]["description"] == mapping["description"]
    assert project["attributes"]["category"] == mapping["category"]
    assert project["attributes"]["tags"] == mapping["tags"]
    components = {fake.nodes[g]["attributes"]["title"]
                  for g in receipt["components"].values()}
    assert components == set(mapping["components"])
    draft = next(iter(fake.drafts.values()))
    assert draft["responses"] == {"summary": mapping["description"]}
    for component, entries in mapping["components"].items():
        comp_guid = receipt["components"][component]
        have = {f["path"] for f in fake.list_files(comp_guid)}
        want = set()
        for item in entries:
            base = Path(bundle) / item
            if item.endswith("/"):
                if base.is_dir():
                    for p in sorted(base.rglob("*")):
                        if p.is_file():
                            rel = p.relative_to(bundle).as_posix()
                            want.add(rel[len(component) + 1:]
                                     if rel.startswith(component + "/") else rel)
            elif base.is_file():
                rel = item[len(component) + 1:] if item.startswith(component + "/") else item
                want.add(rel)
        assert have == want, component
    assert receipt["root"] == mapping["anchor_values"]["checkpoint_root"]
    assert receipt["bundle_hash"] == mapping["anchor_values"]["bundle_hash"]
    assert receipt["registration_hash"] == mapping["anchor_values"]["registration_hash"]
    assert receipt["doi"] == f"10.17605/OSF.IO/{receipt['registration_guid'].upper()}"


def test_gate_refusals_create_nothing(bundle, tmp_path):
    """CLM-010-02 / F-010-2: no approver, a tampered bundle, and an
    unfrozen bundle are each refused before any OSF object exists."""
    fake = FakeOSFTransport()
    with pytest.raises(DepositError, match="name the approver"):
        deposit_bundle_osf(bundle, fake, approved_by="  ",
                           state_path=str(tmp_path / "s1.json"))
    assert fake.calls == [] and fake.nodes == {}

    tampered = tmp_path / "tampered"
    shutil.copytree(bundle, tampered)
    target = tampered / "verdicts.json"
    target.write_bytes(target.read_bytes() + b" ")
    assert not verify_bundle(str(tampered)).ok
    with pytest.raises(DepositError, match="does not verify"):
        deposit_bundle_osf(str(tampered), fake, approved_by="owner",
                           state_path=str(tmp_path / "s2.json"))
    assert fake.calls == [] and fake.nodes == {}

    unfrozen = tmp_path / "unfrozen"
    shutil.copytree(bundle, unfrozen)
    manifest = json.loads((unfrozen / "manifest.json").read_text())
    manifest["study"]["registration_hash"] = None
    (unfrozen / "manifest.json").write_text(json.dumps(manifest, indent=2))
    rehash_manifest(unfrozen)
    with pytest.raises(DepositError):
        deposit_bundle_osf(str(unfrozen), fake, approved_by="owner",
                           state_path=str(tmp_path / "s3.json"))
    assert fake.calls == [] and fake.nodes == {}


def test_repeat_deposit_creates_no_second_registration(bundle, tmp_path):
    """CLM-010-03 / F-010-3: a repeat run — with the deposit state, and
    again with fresh state but the project GUID — reports the existing
    registration instead of duplicating it."""
    fake = FakeOSFTransport()
    state = str(tmp_path / "state.json")
    first = deposit_bundle_osf(bundle, fake, approved_by="owner", state_path=state)
    assert len(fake.registrations) == 1

    again = deposit_bundle_osf(bundle, fake, approved_by="owner", state_path=state)
    assert again["already_existed"] is True
    assert again["registration_guid"] == first["registration_guid"]
    assert len(fake.registrations) == 1

    fresh = deposit_bundle_osf(bundle, fake, approved_by="owner",
                               state_path=str(tmp_path / "fresh.json"),
                               resume_project_guid=first["project_guid"])
    assert fresh["already_existed"] is True
    assert fresh["registration_guid"] == first["registration_guid"]
    assert len(fake.registrations) == 1
    assert len(fake.drafts) == 1  # the scan found it before drafting anew


def test_provider_failure_surfaces_and_state_resumes(bundle, tmp_path):
    """CLM-010-04 / F-010-4: a provider 500 aborts with the provider's
    own words in the error; the recorded state resumes without creating
    a second project or components."""
    fake = FakeOSFTransport()
    fake.fail_once["submit_registration"] = DepositError(
        "OSF POST https://api.osf.io/v2/registrations/ failed: "
        "HTTP 500: provider exploded")
    state = str(tmp_path / "state.json")
    with pytest.raises(DepositError, match="HTTP 500: provider exploded"):
        deposit_bundle_osf(bundle, fake, approved_by="owner", state_path=state)

    saved = json.loads(Path(state).read_text())
    assert saved["stage"] in ("draft_created", "draft_answered")
    projects = [n for n in fake.nodes.values() if n["parent"] is None]
    components = [n for n in fake.nodes.values() if n["parent"] is not None]
    assert len(projects) == 1 and len(components) == 5
    assert len(fake.registrations) == 0  # partial state is not an anchor

    receipt = deposit_bundle_osf(bundle, fake, approved_by="owner", state_path=state)
    assert receipt["registration_guid"]
    assert len([n for n in fake.nodes.values() if n["parent"] is None]) == 1
    assert len([n for n in fake.nodes.values() if n["parent"] is not None]) == 5
    assert len(fake.registrations) == 1


def test_receipt_ledgers_into_a_live_study_ledger(tmp_path):
    """DESIGN §4.2.4 mechanism: the OSF receipt appends to a live
    study's ledger via the existing record_anchor (anchor.recorded),
    and the re-exported bundle carries it in its manifest."""
    live = tmp_path / "live"
    live.mkdir()
    store, reg, _frozen, retrieved = build_study(live)
    bundle2 = export(live, store, reg, retrieved, name="bundle-live")
    fake = FakeOSFTransport()
    receipt = deposit_bundle_osf(bundle2, fake, approved_by="owner",
                                 state_path=str(live / "state.json"))
    record_anchor(store, receipt, actor="researcher")
    bundle3 = export(live, store, reg, retrieved, name="bundle-live-v2")
    manifest = json.loads((Path(bundle3) / "manifest.json").read_text())
    anchors = [a for a in manifest.get("anchors", []) if a["mechanism"] == "osf"]
    assert len(anchors) == 1
    assert anchors[0]["registration_guid"] == receipt["registration_guid"]
    assert anchors[0]["locator"] == receipt["locator"]


def test_verify_osf_anchor_passes_and_catches_divergence(bundle, tmp_path):
    """CLM-010-05 / F-010-5: verification passes on the deposited
    record and fails when the record stops stating the anchor values
    or the structure diverges."""
    fake = FakeOSFTransport()
    receipt = deposit_bundle_osf(bundle, fake, approved_by="owner",
                                 state_path=str(tmp_path / "state.json"))
    good = verify_osf_anchor(bundle, receipt["registration_guid"],
                             project_guid=receipt["project_guid"], reader=fake)
    assert good["ok"], good["failures"]

    view = fake.registrations[receipt["registration_guid"]]["view"]
    view["attributes"]["description"] = "a different bundle entirely"
    view["attributes"]["registration_responses"] = {"summary": "nothing anchored"}
    bad = verify_osf_anchor(bundle, receipt["registration_guid"],
                            project_guid=receipt["project_guid"], reader=fake)
    assert not bad["ok"]
    assert any("anchor values" in f for f in bad["failures"])

    view["attributes"]["description"] = view["attributes"]["title"]
    manifest = json.loads((Path(bundle) / "manifest.json").read_text())
    view["attributes"]["description"] = osf_metadata(manifest)["description"]
    view["attributes"]["registration_responses"] = {
        "summary": osf_metadata(manifest)["description"]}
    victim = receipt["components"]["verdicts"]
    del fake.nodes[victim]
    diverged = verify_osf_anchor(bundle, receipt["registration_guid"],
                                 project_guid=receipt["project_guid"], reader=fake)
    assert not diverged["ok"]
    assert any("component structure" in f for f in diverged["failures"])


def test_embargoed_submission_records_its_state(bundle, tmp_path):
    """CLM-010-07: a deposit under embargo returns a receipt whose
    embargo state comes from the provider record (unit-level here; the
    live demonstration is recorded in the spec's records/)."""
    fake = FakeOSFTransport()
    receipt = deposit_bundle_osf(bundle, fake, approved_by="owner",
                                 state_path=str(tmp_path / "state.json"),
                                 embargo_end_date="2027-10-12")
    assert receipt["embargoed"] is True
    assert receipt["embargo_end_date"] == "2027-10-12"
    view = fake.registrations[receipt["registration_guid"]]["view"]
    assert view["attributes"]["public"] is False
