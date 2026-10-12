"""Spec 008 (statcheck + GRIM-family adapter, P7) tests — seeded
negatives through production paths.

Validation strategy for the native GRIM/GRIMMER implementation,
stated plainly:

- the published worked examples from the scrutiny reference manual
  (Brown & Heathers 2017): a mean of 5.19 is inconsistent with n=28
  and consistent with n=32;
- a brute-force enumeration of ACTUAL integer datasets: every
  (mean, SD, N) triple a real dataset achieves must be judged
  consistent — a false flag on achieved data would be a manufactured
  falsifier, the worst defect this adapter could have;
- hand-verified arithmetic cases for the GRIMMER-only failure mode
  (mean GRIM-consistent, SD impossible), each checkable by hand from
  the integers involved;
- a documented divergence: scrutiny's full GRIMMER flags
  (5.23, 2.55, 35) via its parity/reconstruction test, which this
  adapter deliberately does not apply (the reference maintainer
  flags that test as buggy in the current release). The core tests
  judge the case consistent (a witness sum-of-squares exists) — a
  miss in the safe direction, recorded here as in the module.

statcheck is exercised through its recorded output (fixture built
exclusively from classifications the statcheck project asserts in
its own public test suite — provenance in
tests/fixtures/adapters/statcheck/PROVENANCE.json). No R runtime
exists in this environment, and this module never pretends one ran.
"""

import hashlib
import itertools
from fractions import Fraction
from pathlib import Path

import pytest

pytest.importorskip("axiomere")

from tekmerion.adapters.core import adapter_runs
from tekmerion.adapters.statconsistency import (
    StatcheckRunner,
    extraction_coverage,
    extract_nhst,
    grim_applicability,
    grim_consistent,
    grimmer_core_consistent,
    parse_statcheck_csv,
    run_grim_family,
    run_statcheck,
)
from tekmerion.claims import Claim, ClaimRegister
from tekmerion.store import StudyStore

FIXTURES = Path(__file__).parent / "fixtures" / "adapters" / "statcheck"
RECORDED_CSV = (FIXTURES / "statcheck-recorded-output.csv").read_bytes()
PROVENANCE = "MicheleNuijten/statcheck testthat suite (recorded output)"


def _store(tmp_path):
    return StudyStore.create(str(tmp_path / "study.axmr"))


def _register():
    reg = ClaimRegister()
    reg.register(Claim(
        claim_id="CLM-S-301",
        statement="The paper's reported statistics are internally consistent",
        falsifier="a reported mean/SD is arithmetically impossible given its N, "
                  "or a reported p-value contradicts its own test statistic",
        kind="data"))
    return reg


def _raw_string(row):
    t, df1, df2, val, p = (row["test_type"], row["df1"], row["df2"],
                           row["test_value"], row["reported_p"])
    p_str = f"{p:.2f}".lstrip("0") if p < 1 else f"{p:.2f}"
    if t == "t":
        return f"t({df1}) = {val}, p = {p_str}"
    if t == "F":
        return f"F({df1}, {df2}) = {val}, p = {p_str}"
    if t == "r":
        return f"r({df1}) = {val}, p = {p_str}"
    if t == "z":
        return f"z = {val}, p = {p_str}"
    return f"{t}({df1}) = {val}, p = {p_str}"


ROWS = parse_statcheck_csv(RECORDED_CSV.decode("utf-8"))
MANUSCRIPT = "Results. " + " ".join(_raw_string(r) for r in ROWS)


# ------------------------------------------------------- published examples

def test_grim_published_examples():
    # scrutiny reference manual, grim(): "A mean of 5.19 is not
    # consistent with a sample size of 28" — and consistent with 32.
    assert grim_consistent("5.19", 28) is False
    assert grim_consistent("5.19", 32) is True
    # The manual's two-item scale example: 2.84, n=16, items=2
    # (91/(16*2) = 2.84375 rounds to 2.84 — consistent).
    assert grim_consistent("2.84", 16, items=2) is True


def test_grimmer_hand_verified_cases():
    # Mean consistent, SD impossible: n=10, mean 2.00 (total 20,
    # exact), SD 0.10 -> (n-1)s^2 in [0.081, 0.099] above S^2/n = 40,
    # so the sum of squares would have to lie in [40.081, 40.099] —
    # no integer exists. GRIM passes; GRIMMER core fails.
    assert grim_consistent("2.00", 10) is True
    ok, detail = grimmer_core_consistent("2.00", "0.10", 10)
    assert ok is False and detail["failed"] == "sum_of_squares_integrality"
    # Achieved by the dataset {4,1,1,2,2,2,2,2,2,2} (total 20,
    # sum of squares 46, sample SD = sqrt(6/9) = 0.816 -> 0.82).
    ok, detail = grimmer_core_consistent("2.00", "0.82", 10)
    assert ok is True and detail["witness"]["total"] == 20
    # pigs5 row (scrutiny GRIMMER vignette): the mean itself fails.
    ok, detail = grimmer_core_consistent("7.22", "5.30", 38)
    assert ok is False and detail["failed"] == "grim_mean"
    # Documented divergence (module docstring): full GRIMMER flags
    # (5.23, 2.55, 35) via the parity/reconstruction test this
    # adapter does not apply; a witness (total 183, sum of squares
    # 1178) exists, so the core tests judge it consistent — a miss
    # in the safe direction, never a false falsifier.
    ok, _ = grimmer_core_consistent("5.23", "2.55", 35)
    assert ok is True


def _round2_half_up(frac: Fraction) -> str:
    scaled = frac * 100
    cents = scaled.numerator // scaled.denominator
    if scaled - cents >= Fraction(1, 2):
        cents += 1
    return f"{cents // 100}.{cents % 100:02d}"


def _achieved_sd_str(total_sq: int, total: int, n: int) -> str:
    # The 2dp value (half-up) the sample SD of a dataset with these
    # sums rounds to, decided by exact Fraction comparison.
    # var = (sum x^2 - (sum x)^2/n) / (n-1) = (n*sum x^2 - (sum x)^2) / (n*(n-1)).
    var = Fraction(total_sq * n - total * total, n * (n - 1))
    cents = 0
    approx = (float(var)) ** 0.5 * 100
    for cand in range(max(0, int(approx) - 2), int(approx) + 3):
        lo = Fraction(2 * cand - 1, 200) ** 2
        hi = Fraction(2 * cand + 1, 200) ** 2
        if lo <= var < hi:
            cents = cand
            break
    return f"{cents // 100}.{cents % 100:02d}"


def test_no_false_falsifiers_against_brute_force_datasets():
    checked = 0
    for n in range(2, 8):
        for dataset in itertools.combinations_with_replacement(range(0, 7), n):
            total = sum(dataset)
            total_sq = sum(x * x for x in dataset)
            mean_str = _round2_half_up(Fraction(total, n))
            assert grim_consistent(mean_str, n) is True, (dataset, mean_str)
            sd_str = _achieved_sd_str(total_sq, total, n)
            ok, detail = grimmer_core_consistent(mean_str, sd_str, n)
            assert ok is True, (dataset, mean_str, sd_str, detail)
            checked += 1
    assert checked > 1000  # the enumeration actually ran


# -------------------------------------------------------------- applicability

def test_applicability_regimes():
    assert grim_applicability(n=28, mean_str="5.19")[0] is True
    # Large N at 2dp: granularity finer than reporting precision.
    applicable, why = grim_applicability(n=150, mean_str="5.19")
    assert applicable is False and "no power" in why
    # The same N at 3dp reporting is informative again.
    assert grim_applicability(n=150, mean_str="5.190")[0] is True
    # Continuous data: the method does not apply at all.
    assert grim_applicability(n=28, mean_str="5.19", data_kind="continuous")[0] is False


# --------------------------------------------------------------- GRIM runs

def test_grim_run_impossibility_is_falsifier_observation(tmp_path):
    store, reg = _store(tmp_path), _register()
    run = run_grim_family(
        store, cases=[
            {"label": "condition A", "mean": "5.19", "n": 28},
            {"label": "condition B", "mean": "5.19", "n": 32},
        ], actor="op", claim_id="CLM-S-301", register=reg,
        item_id="EV-GRIM-1", origin_group="EVG-GRIM-1")
    assert run.outcome == "run_by_us"
    kinds = [f["kind"] for f in run.findings]
    assert kinds == ["grim_impossibility", "consistent"]
    item = reg.evidence["CLM-S-301"][0]
    assert item.stance == "contradicts" and item.contradiction_mass == 1.00
    assert item.falsifier_observation is True
    rec = adapter_runs(store, "statcheck-grim")[0]
    assert rec["scope_claim_id"] == "CLM-008-02"
    assert "Brown & Heathers" in rec["checker"]["name"]


def test_grim_run_all_not_applicable_emits_no_evidence(tmp_path):
    store, reg = _store(tmp_path), _register()
    run = run_grim_family(
        store, cases=[{"label": "big-N", "mean": "5.19", "n": 150}],
        actor="op", claim_id="CLM-S-301", register=reg,
        item_id="EV-GRIM-2", origin_group="EVG-GRIM-2")
    assert run.findings[0]["kind"] == "not_applicable"
    assert "CLM-S-301" not in reg.evidence
    assert "CLM-008-04" in run.extra["evidence_withheld"]


def test_grim_run_consistent_only_supports_the_subclaim(tmp_path):
    store, reg = _store(tmp_path), _register()
    run_grim_family(
        store, cases=[{"label": "ok", "mean": "5.19", "n": 32}],
        actor="op", claim_id="CLM-S-301", register=reg,
        item_id="EV-GRIM-3", origin_group="EVG-GRIM-3")
    item = reg.evidence["CLM-S-301"][0]
    assert item.stance == "supports" and item.support_mass == 0.50


# ------------------------------------------------------- extraction & parse

def test_extraction_and_coverage_on_fixture_manuscript():
    extracted = extract_nhst(MANUSCRIPT)
    assert len(extracted) == 19
    coverage = extraction_coverage(MANUSCRIPT)
    assert coverage["extracted"] == 19 and coverage["present_p_mentions"] == 19
    by_type = {}
    for e in extracted:
        by_type[e["test_type"]] = by_type.get(e["test_type"], 0) + 1
    assert by_type == {"t": 5, "F": 3, "r": 3, "chi2": 3, "z": 3, "Q": 2}


def test_extraction_silence_is_visible_in_coverage():
    text = ("The effect was reliable (p < .05) and the interaction "
            "pattern is shown in Table 2. No APA-formatted results "
            "appear in this paragraph at all.")
    coverage = extraction_coverage(text)
    assert coverage["extracted"] == 0
    assert coverage["present_p_mentions"] == 1  # present, not extractable


def test_parse_recorded_statcheck_output():
    assert len(ROWS) == 19
    assert sum(r["decision_error"] for r in ROWS) == 12
    assert sum(r["error"] for r in ROWS) == 18
    consistent = [r for r in ROWS if not r["error"]]
    assert len(consistent) == 1 and consistent[0]["test_type"] == "t"
    with pytest.raises(ValueError):
        parse_statcheck_csv("a,b,c\n1,2,3\n")


# ---------------------------------------------------------- statcheck runs

def test_statcheck_recorded_run_maps_findings_and_replays(tmp_path):
    store, reg = _store(tmp_path), _register()
    run = run_statcheck(
        store, text=MANUSCRIPT, actor="op", claim_id="CLM-S-301",
        register=reg, item_id="EV-SC-1", origin_group="EVG-SC-1",
        runner=StatcheckRunner(rscript="/nonexistent/Rscript"),
        recorded_output=RECORDED_CSV, recorded_provenance=PROVENANCE)
    assert run.outcome == "recorded_output"
    assert run.extra["summary"] == {"results": 19, "decision_errors": 12,
                                    "inconsistencies": 6, "consistent": 1}
    assert run.extra["coverage"]["extracted"] == 19
    kinds = [f["kind"] for f in run.findings]
    assert kinds.count("decision_error") == 12
    assert kinds.count("inconsistency") == 6
    item = reg.evidence["CLM-S-301"][0]
    # Decision errors: partial contradiction, never a falsifier observation.
    assert item.stance == "contradicts" and item.contradiction_mass == 0.50
    assert item.falsifier_observation is False
    rec = adapter_runs(store, "statcheck-grim")[0]
    assert rec["raw_output_sha256"] == hashlib.sha256(RECORDED_CSV).hexdigest()
    assert PROVENANCE in rec["checker"]["version"]


def test_statcheck_unavailable_is_honest_state(tmp_path):
    store, reg = _store(tmp_path), _register()
    run = run_statcheck(
        store, text=MANUSCRIPT, actor="op", claim_id="CLM-S-301",
        register=reg, item_id="EV-SC-2", origin_group="EVG-SC-2",
        runner=StatcheckRunner(rscript="/nonexistent/Rscript"))
    assert run.outcome == "not_runnable_here"
    assert "no R runtime" in run.reason
    assert "CLM-S-301" not in reg.evidence
    assert len(adapter_runs(store, "statcheck-grim")) == 1  # ledgered, not silent
    # The coverage record still lands: extraction is ours and ran.
    assert run.extra["coverage"]["extracted"] == 19


def test_statcheck_recorded_without_provenance_withholds_evidence(tmp_path):
    store, reg = _store(tmp_path), _register()
    run = run_statcheck(
        store, text=MANUSCRIPT, actor="op", claim_id="CLM-S-301",
        register=reg, item_id="EV-SC-3", origin_group="EVG-SC-3",
        runner=StatcheckRunner(rscript="/nonexistent/Rscript"),
        recorded_output=RECORDED_CSV)  # no recorded_provenance
    assert run.outcome == "recorded_output"
    assert len(run.findings) == 19  # findings stand as context
    assert "CLM-S-301" not in reg.evidence
    assert "provenance" in run.extra["evidence_withheld"]


def test_statcheck_unverifiable_recorded_output(tmp_path):
    store, reg = _store(tmp_path), _register()
    run = run_statcheck(
        store, actor="op", claim_id="CLM-S-301", register=reg,
        item_id="EV-SC-4", origin_group="EVG-SC-4",
        runner=StatcheckRunner(rscript="/nonexistent/Rscript"),
        recorded_output=b"some,other,columns\n1,2,3\n",
        recorded_provenance=PROVENANCE)
    assert "output_unverifiable" in run.extra
    assert "CLM-S-301" not in reg.evidence
