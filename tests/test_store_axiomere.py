"""StudyStore over real Axiomere (DN-007). Skipped when the axiomere
package is not installed — the store has no fallback implementation,
by design: a silent substitute would fake the DN-005 guarantee."""

import pytest

pytest.importorskip("axiomere")

import axiomere as ax  # noqa: E402
from tekmerion.store import StudyStore  # noqa: E402


def test_study_lifecycle_on_axiomere(tmp_path):
    seed, _pk = ax.generate_keypair()
    store = StudyStore.create(str(tmp_path / "study.axmr"), seed_hex=seed)
    store.register_claim("CLM-1", {"statement": "X holds", "falsifier": "obs Y"}, actor="researcher", score=0.8)
    store.issue_verdict("CLM-1", {"verdict": "supported", "margin": 0.1}, actor="adjudicator")
    store.log_query("crossref", {"query": "X", "results": 3}, actor="researcher")
    assert store.current_claims()["CLM-1"]["content"]["statement"] == "X holds"
    cp = store.freeze(actor="researcher")
    assert cp["payload"]["merkle_root"]
    v = store.verify()
    assert v.ok and v.signatures_checked >= 4


def test_withdrawal_is_dead_snapshot_not_deletion(tmp_path):
    store = StudyStore.create(str(tmp_path / "study.axmr"))
    store.register_claim("CLM-2", {"statement": "Y"}, actor="researcher", score=0.5)
    store.withdraw("CLM-2", reason="entered-in-error", actor="adjudicator")
    assert "CLM-2" not in store.current_claims()
    audit = store.current_claims(include_dead=True)
    assert audit["CLM-2"]["status"] == "dead" and audit["CLM-2"]["score"] == 0.0
    assert store.verify().ok
