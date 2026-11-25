"""Gate logic: pre-set thresholds, honest STOP/PIVOT on weak evidence."""
import gates


def _cand(**kw):
    base = {"title": "x", "relevant_sources": 10, "voices": 8, "pain": 5, "demand_score": 70, "founder_fit": 80, "total": 70, "excluded": False}
    base.update(kw)
    return base


def test_strong_evidence_goes():
    assert gates.evidence_gate([_cand()]).recommendation == gates.GO


def test_weak_evidence_stops():
    weak = _cand(relevant_sources=1, voices=1, pain=0, demand_score=10, total=20)
    g = gates.evidence_gate([weak, _cand(title="alt", demand_score=5, total=10)])
    assert g.recommendation == gates.STOP


def test_weak_idea_with_strong_alternative_pivots():
    g = gates.evidence_gate([_cand(demand_score=5, total=20), _cand(title="better alt")])
    assert g.recommendation == gates.PIVOT and g.pivot_to == "better alt"


def test_excluded_product_only_allows_stop():
    g = gates.evidence_gate([_cand(excluded=True)])
    assert g.recommendation == gates.STOP and g.allowed == (gates.STOP,)


def test_waitlist_12_of_100_is_not_spun():
    """The case brief's example: target 100 sign-ups in 14 days, got 12."""
    g = gates.demand_gate(signups=12, target=100, days_elapsed=14, window_days=14, attempt=1)
    assert g.recommendation in (gates.PIVOT, gates.STOP)
    g2 = gates.demand_gate(signups=12, target=100, days_elapsed=14, window_days=14, attempt=2)
    assert g2.recommendation == gates.STOP


def test_untested_waitlist_never_passes():
    g = gates.demand_gate(signups=None, target=100, days_elapsed=None, window_days=14)
    assert g.recommendation != gates.GO


def test_build_gate_needs_every_test():
    assert gates.build_gate([{"name": "a", "passed": True}, {"name": "b", "passed": False}]).recommendation == gates.REPEAT
    assert gates.build_gate([{"name": "a", "passed": True}]).recommendation == gates.GO


def test_repeat_not_offered_forever():
    g = gates.evidence_gate([_cand(demand_score=5, total=20)], attempt=gates.MAX_ATTEMPTS, sources_ok=False)
    assert gates.REPEAT not in g.allowed


def test_no_evidence_repeats_then_stops():
    none = [_cand(relevant_sources=0, voices=0, pain=0, demand_score=0, total=30), _cand(title="alt", relevant_sources=1, voices=1, pain=0, demand_score=5, total=30)]
    assert gates.evidence_gate(none, attempt=1).recommendation == gates.REPEAT
    assert gates.evidence_gate(none, attempt=gates.MAX_ATTEMPTS).recommendation == gates.STOP


def test_no_evidence_and_no_founder_fit_stops_at_once():
    # A broader search can't fix founder fit, so there is no point recommending repeat.
    weak = _cand(relevant_sources=0, voices=0, pain=0, demand_score=0, founder_fit=4, total=16)
    assert gates.evidence_gate([weak, dict(weak, title="alt")], attempt=1).recommendation == gates.STOP


def test_no_evidence_but_good_founder_fit_still_repeats_first():
    thin = _cand(relevant_sources=1, voices=1, pain=0, demand_score=5, founder_fit=80, total=30)
    assert gates.evidence_gate([thin], attempt=1).recommendation == gates.REPEAT
