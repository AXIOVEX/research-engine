"""Phase 3 tests: register, freeze, verdicts — each pins a WS2/WS3 rule."""

import pytest

pytest.importorskip("axiomere")

from tekmerion.claims import Claim, ClaimRegister, EvidenceItem, RegistrationError
from tekmerion.freeze import FreezeError, freeze, freeze_check
from tekmerion.store import StudyStore
from tekmerion.verdicts import Control, evaluate_claim, evaluate_run


def claim(cid="CLM-S-001", **kw):
    base = dict(statement="X holds", falsifier="observing not-X in a powered test",
                margin=0.1, sufficiency_floor=2)
    base.update(kw)
    return Claim(claim_id=cid, **base)


def controls():
    pos = Control(
        failure_mode="retrieval broken: known-true claim not supported",
        kind="positive",
        claim=claim("CLM-S-900"),
        groups=[{"origin_group": "G1", "support_mass": 0.9, "contradiction_mass": 0.0,
                 "could_falsify": True, "falsifier_observation": False, "verified": True, "items": 1},
                {"origin_group": "G2", "support_mass": 0.9, "contradiction_mass": 0.0,
                 "could_falsify": True, "falsifier_observation": False, "verified": True, "items": 1}],
        expected="supported",
        representative_rationale="same domain and difficulty class as the study claims",
    )
    neg = Control(failure_mode="verification decorative: fabricated citation accepted",
                  kind="negative", claim=claim("CLM-S-901"),
                  groups=[{"origin_group": "G9", "support_mass": 0.0, "contradiction_mass": 0.9,
                           "could_falsify": True, "falsifier_observation": True, "verified": True, "items": 1},
                          {"origin_group": "G8", "support_mass": 0.0, "contradiction_mass": 0.9,
                           "could_falsify": True, "falsifier_observation": True, "verified": True, "items": 1}],
                  expected="contradicted")
    swap = Control(failure_mode="integrity machinery decorative: provenance swap undetected", kind="swap")
    return [pos, neg, swap]


def group(gid, s, c, **kw):
    base = {"origin_group": gid, "support_mass": s, "contradiction_mass": c,
            "could_falsify": True, "falsifier_observation": False, "verified": True, "items": 1}
    base.update(kw)
    return base


# -- register ---------------------------------------------------------------

def test_no_falsifier_no_registration():
    reg = ClaimRegister()
    with pytest.raises(RegistrationError, match="falsifier"):
        reg.register(claim(falsifier="  "))


def test_cycle_is_circular_support():
    reg = ClaimRegister()
    reg.register(claim("CLM-S-001"))
    reg.register(claim("CLM-S-002", dependencies=["CLM-S-001"]))
    reg.claims["CLM-S-001"].dependencies = ["CLM-S-002"]
    cycle = reg.find_cycle()
    assert cycle and cycle[0] == cycle[-1]


def test_statement_immutable_and_supersede_path():
    reg = ClaimRegister()
    reg.register(claim())
    # Immutability binds at every status, proposed included (Spec 013
    # CLM-013-11): a changed statement is refused, never edited in.
    with pytest.raises(RegistrationError, match="immutable"):
        reg.register(claim(statement="X holds, edited"))
    reg.frozen = True
    # While frozen the wall is unconditional (Spec 013 CLM-013-06, no
    # exceptions): not an edit, and not even the superseding claim —
    # a frozen register's claim set changes only through a labeled
    # freeze amendment. (The pre-013 form of this test registered the
    # superseding claim against the frozen register; that acceptance
    # was the RTA-03 freeze-wall hole.)
    with pytest.raises(RegistrationError, match="frozen"):
        reg.register(claim(statement="X holds, edited"))
    with pytest.raises(RegistrationError, match="frozen"):
        reg.register(claim("CLM-S-002", statement="X holds, narrowed",
                           supersedes="CLM-S-001"))
    reg.frozen = False
    reg.register(claim("CLM-S-002", statement="X holds, narrowed", supersedes="CLM-S-001"))
    assert reg.claims["CLM-S-001"].status == "superseded"


def test_group_folding_counts_groups_not_items():
    reg = ClaimRegister()
    reg.register(claim())
    for i in range(4):
        reg.add_evidence("CLM-S-001", EvidenceItem(item_id=f"i{i}", origin_group="G1",
                                                   stance="supports", support_mass=0.8))
    groups = reg.group_masses("CLM-S-001")
    assert len(groups) == 1 and groups[0]["items"] == 4  # 40 items in 1 group = 1 group


# -- verdicts -----------------------------------------------------------------

def test_supported_requires_exposure_and_margin():
    v = evaluate_claim(claim(), [group("G1", 0.9, 0.0), group("G2", 0.85, 0.05)])
    assert v.verdict == "supported"


def test_untested_is_inconclusive_never_supported():
    v = evaluate_claim(claim(), [group("G1", 0.95, 0.0, could_falsify=False),
                                 group("G2", 0.95, 0.0, could_falsify=False)])
    assert v.verdict == "inconclusive" and "untested" in v.reason


def test_below_floor_and_straddle_are_inconclusive():
    assert evaluate_claim(claim(), [group("G1", 0.9, 0.0)]).verdict == "inconclusive"
    v = evaluate_claim(claim(), [group("G1", 0.5, 0.3), group("G2", 0.5, 0.3)])
    assert v.verdict == "inconclusive" and "straddles" in v.reason  # interval [0.0, 0.4] vs margin 0.1


def test_falsifier_fired_is_contradicted():
    v = evaluate_claim(claim(), [group("G1", 0.1, 0.8, falsifier_observation=True),
                                 group("G2", 0.2, 0.7, falsifier_observation=True)])
    assert v.verdict == "contradicted" and "falsifier" in v.reason


def test_invalid_run_issues_no_claim_verdicts():
    reg = ClaimRegister()
    reg.register(claim())
    reg.add_evidence("CLM-S-001", EvidenceItem(item_id="bad", origin_group="G1", stance="supports",
                                               support_mass=0.9, verified=False))
    result = evaluate_run(reg, mode="exploratory", controls=[])
    assert result.run_verdict == "invalid" and result.claim_verdicts == []
    assert any("unverified citation" in r for r in result.invalid_reasons)


def test_confirmation_without_freeze_hits_the_wall():
    reg = ClaimRegister()
    reg.register(claim())
    result = evaluate_run(reg, mode="confirmation", controls=[])
    assert result.run_verdict == "invalid"
    assert any("wall" in r for r in result.invalid_reasons)


def test_failing_control_invalidates_the_run(tmp_path):
    store = StudyStore.create(str(tmp_path / "s.axmr"))
    store.register_claim("CLM-S-001", {"statement": "seed"}, actor="r")
    bad = controls()
    bad[0].expected = "contradicted"  # positive control now disagrees with production path
    reg = ClaimRegister()
    reg.register(claim())
    result = evaluate_run(reg, mode="exploratory", controls=bad, store_path=str(tmp_path / "s.axmr"))
    assert result.run_verdict == "invalid"
    assert any("positive control failed" in r for r in result.invalid_reasons)


# -- freeze ---------------------------------------------------------------------

def test_freeze_check_fails_closed():
    reg = ClaimRegister()
    reg.register(claim(margin=None, sufficiency_floor=None))
    failures = freeze_check(reg, [], mode="confirmation", linked_exploratory=None)
    assert any("margin" in f for f in failures)
    assert any("sufficiency floor" in f for f in failures)
    assert any("missing positive control" in f for f in failures)
    assert any("disclose" in f for f in failures)  # RT-3


def test_freeze_commits_registration_and_checkpoint(tmp_path):
    store = StudyStore.create(str(tmp_path / "s.axmr"))
    store.register_claim("CLM-S-001", {"statement": "X holds"}, actor="r")
    store.register_claim("CLM-S-900", {"statement": "control seed"}, actor="r")
    reg = ClaimRegister()
    reg.register(claim())
    out = freeze(store, reg, controls(), actor="adjudicator", linked_exploratory=[])
    assert out["registration_hash"] and out["checkpoint_root"]
    assert reg.frozen and reg.claims["CLM-S-001"].status == "registered"
    assert store.verify().ok
    with pytest.raises(FreezeError):
        freeze(store, ClaimRegister(), controls(), actor="a", linked_exploratory=[])
