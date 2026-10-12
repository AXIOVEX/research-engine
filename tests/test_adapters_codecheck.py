"""Spec 007 (CODECHECK adapter, P3) tests — seeded negatives through
production paths.

The adapter consumes the public CODECHECK register. Tests are
hermetic: an injected fetcher serves RECORDED register material
(fixtures with provenance in tests/fixtures/adapters/codecheck/
PROVENANCE.json) — the real register.csv snapshot, certificate
2020-001's real codecheck.yml, and its real certificate PDF. The
live fetch path is the same code with the default fetcher.

Certificate 2020-001 (Piccolo et al., ShinyLearner) is a genuinely
partial-scope certificate on its own text: the codechecker ran only
the visualisation steps and states the results data files were not
independently reproduced — the fixture exercises CLM-007-03 with a
real partial certificate, not a synthetic one.
"""

import hashlib
from pathlib import Path

import pytest

pytest.importorskip("axiomere")

from tekmerion.adapters.codecheck import (
    ingest_codecheck_certificate,
    parse_codecheck_yml,
    parse_register,
)
from tekmerion.adapters.core import adapter_runs
from tekmerion.claims import Claim, ClaimRegister
from tekmerion.store import StudyStore

FIXTURES = Path(__file__).parent / "fixtures" / "adapters" / "codecheck" / "piccolo-2020"
REGISTER_BYTES = (FIXTURES / "register.csv").read_bytes()
YML_BYTES = (FIXTURES / "codecheck.yml").read_bytes()
PDF_BYTES = (FIXTURES / "codecheck.pdf").read_bytes()
MANIFEST_FILES = [
    "Figures/Datasets_Basic_AUROC.pdf", "Figures/Predictions_Histograms.pdf",
    "Figures/Algorithms_ParamsImprovement_AUROC.pdf",
    "Figures/Algorithms_FSImprovement_AUROC.pdf", "Figures/FS_vs_CL.pdf",
    "Figures/FS_NumFeatures.pdf", "Tables/Basic_DiffFromMedian.tsv",
    "Tables/ParamOpt_Improvement.tsv",
]


def _fetcher(mapping):
    def fetch(url):
        if url not in mapping:
            raise OSError(f"no such URL in fixture map: {url}")
        return mapping[url]
    return fetch


def _good_fetcher(**overrides):
    mapping = {
        "https://raw.githubusercontent.com/codecheckers/register/master/register.csv":
            REGISTER_BYTES,
        "https://raw.githubusercontent.com/codecheckers/Piccolo-2020/master/codecheck.yml":
            YML_BYTES,
        "https://raw.githubusercontent.com/codecheckers/Piccolo-2020/master/codecheck/codecheck.pdf":
            PDF_BYTES,
    }
    mapping.update(overrides)
    return _fetcher(mapping)


def _store(tmp_path):
    return StudyStore.create(str(tmp_path / "study.axmr"))


def _register():
    reg = ClaimRegister()
    reg.register(Claim(
        claim_id="CLM-S-201",
        statement="The paper's computational results were independently re-executed",
        falsifier="no independent re-execution record exists for the work",
        kind="data"))
    return reg


def _ingest(store, reg=None, **kwargs):
    kwargs.setdefault("actor", "op")
    kwargs.setdefault("fetcher", _good_fetcher())
    if reg is not None:
        kwargs.update(claim_id="CLM-S-201", register=reg,
                      item_id="EV-CC-1", origin_group="EVG-CC-1")
    return ingest_codecheck_certificate(store, certificate_id="2020-001", **kwargs)


# ------------------------------------------------------------- yml parser

def test_yml_parser_extracts_certificate_fields():
    yml = parse_codecheck_yml(YML_BYTES.decode("utf-8"))
    assert yml["certificate"] == "2020-001"
    assert yml["paper"]["title"].startswith("ShinyLearner")
    assert yml["paper"]["reference"] == "https://doi.org/10.1093/gigascience/giaa026"
    assert len(yml["paper"]["authors"]) == 4
    assert [e["file"] for e in yml["manifest"]] == MANIFEST_FILES
    assert yml["codechecker"][0]["name"] == "Stephen J. Eglen"
    assert yml["codechecker"][0]["ORCID"] == "0000-0001-8607-8025"
    assert yml["report"] == "http://doi.org/10.5281/zenodo.3674056"


def test_register_parser():
    rows = parse_register(REGISTER_BYTES)
    assert len(rows) >= 130
    row = next(r for r in rows if r["Certificate"] == "2020-001")
    assert row["Repository"] == "github::codecheckers/Piccolo-2020"
    assert row["Venue"] == "GigaScience"


# ------------------------------------------------------------- happy path

def test_ingest_partial_scope_by_default_and_replay(tmp_path):
    store, reg = _store(tmp_path), _register()
    run = _ingest(store, reg)
    assert run.outcome == "recorded_output"
    assert run.checker_name.startswith("CODECHECK codechecker Stephen J. Eglen")
    cert = run.extra["certificate"]
    assert cert["check_time"] == "2019-02-14 10:00:00"
    assert cert["report_doi"] == "10.5281/zenodo.3674056"
    assert cert["work_identifier"] == "https://doi.org/10.1093/gigascience/giaa026"
    assert cert["missing"] == []
    # The real certificate is partial on its own text; with no
    # study-supplied output list the cap applies by default.
    scope = run.extra["scope"]
    assert scope["partial_scope"] is True
    assert scope["certified_outputs"] == MANIFEST_FILES
    assert scope["uncertified_outputs"] is None
    # The yml summary itself declares the partial scope: only the
    # visualisation steps were performed; other output files unchecked.
    assert "Only visualiation steps performed" in (cert["summary"] or "")
    assert "The content of other output files was not checked" in (cert["summary"] or "")
    item = reg.evidence["CLM-S-201"][0]
    assert item.stance == "supports" and item.support_mass == 0.40
    # Replay: provenance intact in the ledger.
    runs = adapter_runs(store, "codecheck")
    assert len(runs) == 1
    rec = runs[0]
    assert rec["scope_claim_id"] == "CLM-007-02"
    assert rec["artifact"]["sha256"] == hashlib.sha256(PDF_BYTES).hexdigest()
    assert rec["raw_output_sha256"] == hashlib.sha256(YML_BYTES).hexdigest()
    assert rec["extra"]["register_snapshot_sha256"] == hashlib.sha256(REGISTER_BYTES).hexdigest()
    assert rec["extra"]["lane2_effect"].startswith("none")
    # 2020-001 predates the disclaimer template: recorded as absent,
    # with the standing text carried in the record regardless.
    disc = rec["extra"]["disclaimer"]
    assert disc["present_in_certificate_material"] is False
    assert "does not check whether the original computational analysis is correct" in disc["text"]


def test_ingest_with_study_output_list_names_uncertified(tmp_path):
    store, reg = _store(tmp_path), _register()
    run = _ingest(store, reg, work_outputs=MANIFEST_FILES + [
        "results data files (not independently reproduced, per certificate summary)"])
    scope = run.extra["scope"]
    assert scope["partial_scope"] is True
    assert scope["uncertified_outputs"] == [
        "results data files (not independently reproduced, per certificate summary)"]
    assert reg.evidence["CLM-S-201"][0].support_mass == 0.40


def test_ingest_full_scope_when_manifest_covers_output_list(tmp_path):
    store, reg = _store(tmp_path), _register()
    run = _ingest(store, reg, work_outputs=list(MANIFEST_FILES))
    assert run.extra["scope"]["partial_scope"] is False
    assert run.extra["scope"]["uncertified_outputs"] == []
    assert reg.evidence["CLM-S-201"][0].support_mass == 0.70


# --------------------------------------------------------------- negatives

def test_incomplete_certificate_record_is_context_not_evidence(tmp_path):
    # Seeded defect (F-007-1): strip the codechecker block from the
    # real yml — the record now lacks the named checker.
    lines = YML_BYTES.decode("utf-8").splitlines()
    kept, skip = [], False
    for line in lines:
        if line.startswith("codechecker:"):
            skip = True
            continue
        if skip and line and not line.startswith(" ") and not line.startswith("-"):
            skip = False
        if not skip:
            kept.append(line)
    broken = "\n".join(kept).encode()
    assert b"Eglen" not in broken
    fetcher = _good_fetcher(**{
        "https://raw.githubusercontent.com/codecheckers/Piccolo-2020/master/codecheck.yml": broken})
    store, reg = _store(tmp_path), _register()
    run = _ingest(store, reg, fetcher=fetcher)
    assert run.outcome == "recorded_output"
    assert "named codechecker" in run.extra["certificate"]["missing"]
    assert "CLM-S-201" not in reg.evidence
    assert "CLM-007-01" in run.extra["evidence_withheld"]


def test_certificate_not_in_register(tmp_path):
    store, reg = _store(tmp_path), _register()
    run = ingest_codecheck_certificate(
        store, certificate_id="1999-999", actor="op",
        claim_id="CLM-S-201", register=reg, item_id="EV-CC-9",
        origin_group="EVG-CC-9", fetcher=_good_fetcher())
    assert run.outcome == "not_attempted"
    assert "not in the public register" in run.reason
    assert "CLM-S-201" not in reg.evidence
    assert len(adapter_runs(store, "codecheck")) == 1  # the gap is ledgered


def test_register_unreachable_is_honest_unavailable(tmp_path):
    def dead_fetch(url):
        raise OSError("network unreachable")
    store, reg = _store(tmp_path), _register()
    run = ingest_codecheck_certificate(
        store, certificate_id="2020-001", actor="op",
        claim_id="CLM-S-201", register=reg, item_id="EV-CC-9",
        origin_group="EVG-CC-9", fetcher=dead_fetch)
    assert run.outcome == "not_runnable_here"
    assert "CLM-S-201" not in reg.evidence
    assert len(adapter_runs(store, "codecheck")) == 1


def test_certificate_pdf_missing_is_recorded_not_fatal(tmp_path):
    fetcher = _fetcher({
        "https://raw.githubusercontent.com/codecheckers/register/master/register.csv":
            REGISTER_BYTES,
        "https://raw.githubusercontent.com/codecheckers/Piccolo-2020/master/codecheck.yml":
            YML_BYTES,
    })
    store, reg = _store(tmp_path), _register()
    run = _ingest(store, reg, fetcher=fetcher)
    assert run.outcome == "recorded_output"
    assert run.extra["certificate_pdf_missing"] is True
    assert run.artifact_sha256 == hashlib.sha256(YML_BYTES).hexdigest()
    assert len(reg.evidence["CLM-S-201"]) == 1
