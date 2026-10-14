"""Spec 013, WS-3 (Lane B2) — falsifier-naming exactness, stance
negation parity, DOI normalized once at intake.

Ported from the 2026-10-13 red-team probes (rt-a p06, p07,
p10(a)/(f)) that demonstrated RTA-06, RTA-07, RTA-09. Each ported
case asserts the post-fix behavior, and the held truths the probes
recorded — the genuine Phase 7 Wandel facts still fire (p10(a)),
positive propositions behave exactly as before (p07 controls) —
are asserted alongside, in both directions.
"""
from tekmerion.claims import Claim
from tekmerion.connectors import RetrievedItem
from tekmerion.verification import (
    Citation,
    CitationResult,
    KeywordStanceChecker,
    _resolve,
    _surname,
    assign_origin_groups,
    falsifier_names_record,
)


def _result_for(authors, year, doi="10.1000/other", title="t"):
    res = CitationResult(citation_id="CIT-X", claim_id="CLM-X-001",
                         resolution="resolved", agreement="agree",
                         content="contradicts")
    res.retrieved = RetrievedItem(source="stub", source_id=doi, title=title,
                                  authors=authors, year=year, abstract="x")
    return res


# ------------------------------------------------------- CLM-013-12 (p06)

def test_falsifier_doi_prefix_of_another_never_fires():
    # rt-a p06 case A: the falsifier names 10.1000/xyz22; the cited
    # record's DOI 10.1000/xyz2 is a substring of it. Pre-fix this
    # fired on the substring; identity-grade matching must not.
    claim = Claim(claim_id="CLM-X-001", statement="s",
                  falsifier="Falsified if 10.1000/xyz22 fails to replicate.")
    cit = Citation(citation_id="CIT-X", claim_id="CLM-X-001",
                   proposition="p", doi="10.1000/xyz2")
    res = _result_for(["Jones, A."], 2020, doi="10.1000/xyz2")
    assert falsifier_names_record(claim, cit, res) is False


def test_falsifier_doi_exact_token_fires_in_its_forms():
    # The other direction: the exact DOI named bare, behind a doi:
    # prefix, as a doi.org URL, or with sentence punctuation fires.
    cit = Citation(citation_id="CIT-X", claim_id="CLM-X-001",
                   proposition="p", doi="10.1000/xyz2")
    res = _result_for(["Jones, A."], 2020, doi="10.1000/xyz2")
    for text in ("Falsified if 10.1000/xyz2 fails to replicate.",
                 "Falsified by the observation at doi:10.1000/xyz2.",
                 "See https://doi.org/10.1000/xyz2 for the observation.",
                 "Falsified if (10.1000/xyz2) is not replicated."):
        claim = Claim(claim_id="CLM-X-001", statement="s", falsifier=text)
        assert falsifier_names_record(claim, cit, res) is True, text


def test_falsifier_other_smith_same_year_never_fires():
    # rt-a p06 case B: the falsifier names one specific Smith (2019);
    # the resolved record is a DIFFERENT Smith 2019 (unrelated DOI,
    # no title or given name tying the falsifier to this record).
    # Surname+year adjacency alone is not identity.
    claim = Claim(claim_id="CLM-X-001", statement="s",
                  falsifier="Falsified if Smith (2019) is not replicated "
                            "by an independent group.")
    cit = Citation(citation_id="CIT-X", claim_id="CLM-X-001",
                   proposition="p", doi="10.5555/unrelated")
    res = _result_for(["John Smith"], 2019, doi="10.5555/unrelated")
    assert falsifier_names_record(claim, cit, res) is False


def test_falsifier_generic_names_nothing():
    # rt-a p06 case C (control, held before and after): a generic
    # falsifier naming no record leaves the observation unset.
    claim = Claim(claim_id="CLM-X-001", statement="s",
                  falsifier="Falsified if the effect vanishes under "
                            "pre-registered conditions.")
    cit = Citation(citation_id="CIT-X", claim_id="CLM-X-001",
                   proposition="p", doi="10.5555/unrelated")
    res = _result_for(["John Smith"], 2019, doi="10.5555/unrelated")
    assert falsifier_names_record(claim, cit, res) is False


def test_falsifier_phase7_wandel_facts_still_fire():
    # rt-a p10(a), a HELD result: the genuine Phase 7 facts — the
    # falsifier names the Wandel 2010 network meta-analysis, the
    # record is Wandel 2010 — fired under the old rule and must
    # still fire under exact matching (adjacency "Wandel 2010" plus
    # the record's title subject, glucosamine, in the falsifier).
    claim = Claim(claim_id="CLM-E-004", statement="glucosamine works",
                  falsifier="A large-scale synthesis finds glucosamine does "
                            "not reduce joint pain versus placebo (the "
                            "registered falsifying observation is the "
                            "Wandel 2010 network meta-analysis's conclusion)")
    cit = Citation(citation_id="CIT-E-401", claim_id="CLM-E-004",
                   proposition="glucosamine reduces joint pain",
                   doi="10.1136/bmj.c4675")
    res = CitationResult(citation_id="CIT-E-401", claim_id="CLM-E-004",
                         resolution="resolved", agreement="agree",
                         content="contradicts")
    res.retrieved = RetrievedItem(
        source="openalex", source_id="https://doi.org/10.1136/bmj.c4675",
        title="Effects of glucosamine...", authors=["Simon Wandel"],
        year=2010, abstract="x")
    assert falsifier_names_record(claim, cit, res) is True


def test_falsifier_surname_year_with_given_name_fires():
    # The second identity element may be the author's given name:
    # "Simon Wandel 2010" names the person, not just the surname —
    # fires even with no title on the record to tie by subject.
    claim = Claim(claim_id="CLM-X-001", statement="s",
                  falsifier="Falsified if Simon Wandel 2010 is overturned.")
    cit = Citation(citation_id="CIT-X", claim_id="CLM-X-001",
                   proposition="p", doi="10.5555/anything")
    res = _result_for(["Simon Wandel"], 2010, doi="10.5555/anything", title="")
    assert falsifier_names_record(claim, cit, res) is True


def test_falsifier_surname_and_year_not_adjacent_never_fires():
    # Surname in one clause, the year in another: the old rule fired
    # on co-occurrence anywhere; the pair must be one unit.
    claim = Claim(claim_id="CLM-X-001", statement="s",
                  falsifier="Falsified if Wandel is overturned; the 2010 "
                            "literature is settled either way, and "
                            "glucosamine is the subject throughout.")
    cit = Citation(citation_id="CIT-X", claim_id="CLM-X-001",
                   proposition="p", doi="10.5555/anything")
    res = _result_for(["Simon Wandel"], 2010, doi="10.5555/anything",
                      title="Effects of glucosamine")
    assert falsifier_names_record(claim, cit, res) is False


def test_surname_extraction_bibliographic_forms():
    # RTA-06's format note: "Lastname, F." keyed as "f" under the old
    # last-token rule and surname matching silently disabled itself.
    assert _surname("Simon Wandel") == "wandel"
    assert _surname("Wandel, Simon") == "wandel"
    assert _surname("Wandel, S.") == "wandel"
    assert _surname("Jones, A.") == "jones"
    assert _surname("Wandel") == "wandel"
    assert _surname("") == ""


def test_falsifier_fires_with_bibliographic_author_form():
    # A record whose first author arrives as "Wandel, S." names and
    # fires exactly as the "Simon Wandel" form does.
    claim = Claim(claim_id="CLM-X-001", statement="s",
                  falsifier="Falsified if the Wandel 2010 synthesis on "
                            "glucosamine is overturned.")
    cit = Citation(citation_id="CIT-X", claim_id="CLM-X-001",
                   proposition="p", doi="10.5555/anything")
    res = _result_for(["Wandel, S."], 2010, doi="10.5555/anything",
                      title="Effects of glucosamine")
    assert falsifier_names_record(claim, cit, res) is True


# ------------------------------------------------------- CLM-013-13 (p07)

def test_stance_positive_proposition_controls_unchanged():
    # rt-a p07 control cases (held before the fix, must stay held):
    # positive propositions behave exactly as the historical rule.
    chk = KeywordStanceChecker()
    assert chk.check(
        "the treatment reduces symptoms",
        "In this trial the treatment reduces symptoms in adults."
    ) == "supports"
    assert chk.check(
        "the treatment reduces symptoms",
        "In this trial the treatment does not reduce symptoms in adults."
    ) == "contradicts"


def test_stance_negative_proposition_no_longer_inverts():
    # rt-a p07: both directions inverted pre-fix. Agreeing content
    # (same negation parity) affirms the proposition as stated;
    # disagreeing content (opposite parity) denies it.
    chk = KeywordStanceChecker()
    prop = "the treatment does not reduce symptoms"
    assert chk.check(
        prop,
        "In this trial the treatment does not reduce symptoms in adults."
    ) == "supports"        # was: contradicts
    assert chk.check(
        prop,
        "In this trial the treatment reduces symptoms in adults."
    ) == "contradicts"     # was: supports


def test_stance_negative_proposition_mixed_parity_abstains():
    # Both parities match somewhere in the content: parity cannot
    # decide, so the checker abstains rather than pick a sign.
    chk = KeywordStanceChecker()
    prop = "the treatment does not reduce symptoms"
    content = ("One cohort found the treatment does not reduce symptoms. "
               "Another found the treatment reduces symptoms.")
    assert chk.check(prop, content) == "contextual"


def test_stance_unrelated_content_stays_contextual():
    chk = KeywordStanceChecker()
    assert chk.check("the treatment does not reduce symptoms",
                     "We review clinic intake procedures.") == "contextual"


# -------------------------------------------------- CLM-013-14 (p10(f))

class _BareOnly:
    """A connector keyed on the bare DOI form only (rt-a p10(f))."""
    name = "bare-only"

    def resolve(self, doi):
        if doi == "10.1000/stub1":
            return RetrievedItem(source="bare", source_id=doi, title="t",
                                 abstract="a")
        return None

    def search(self, q, *, limit=10):
        return []


_DOI_FORMS = ("10.1000/stub1", "https://doi.org/10.1000/stub1",
              "10.1000/STUB1")


def test_doi_normalized_once_at_intake():
    # Whatever form a citation arrives in, its working DOI is the
    # shared normalizer's output from construction on; the verbatim
    # string survives only as the preserved input record.
    for form in _DOI_FORMS:
        cit = Citation(citation_id="CIT-F", claim_id="CLM-F-001",
                       proposition="p", doi=form)
        assert cit.doi == "10.1000/stub1"
        assert cit.doi_as_cited == form
        assert cit.as_dict()["doi"] == form      # the input record
    # No DOI stays no DOI.
    cit = Citation(citation_id="CIT-F", claim_id="CLM-F-001", proposition="p")
    assert cit.doi is None and cit.doi_as_cited is None


def test_doi_forms_resolve_identically():
    # rt-a p10(f): URL-form and uppercase DOIs of a resolvable work
    # returned not_found pre-remediation; all forms resolve alike.
    for form in _DOI_FORMS:
        cit = Citation(citation_id="CIT-F", claim_id="CLM-F-001",
                       proposition="p", doi=form)
        _item, outcome, _detail = _resolve(cit, [_BareOnly()])
        assert outcome == "resolved", form


def test_doi_forms_group_together():
    # Origin grouping consumes the intake-normalized DOI: one work
    # cited in two surface forms is one origin.
    a = Citation(citation_id="CIT-F1", claim_id="CLM-F-001",
                 proposition="p", doi="10.1000/stub1")
    b = Citation(citation_id="CIT-F2", claim_id="CLM-F-001",
                 proposition="p", doi="https://doi.org/10.1000/STUB1")
    groups, _suspects = assign_origin_groups([a, b], [])
    assert groups["CIT-F1"] == groups["CIT-F2"]


def test_falsifier_matching_consumes_normalized_doi():
    # A citation taken in URL form still matches a falsifier that
    # names the bare DOI (both sides meet at the normalized form).
    claim = Claim(claim_id="CLM-X-001", statement="s",
                  falsifier="Falsified if 10.1000/xyz2 fails to replicate.")
    cit = Citation(citation_id="CIT-X", claim_id="CLM-X-001",
                   proposition="p", doi="https://doi.org/10.1000/XYZ2")
    res = _result_for(["Jones, A."], 2020, doi="10.1000/xyz2")
    assert falsifier_names_record(claim, cit, res) is True
