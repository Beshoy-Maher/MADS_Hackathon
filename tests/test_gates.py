import gates


def score(**kw):
    s = {"sources": 30, "recent_voices": 8, "demand": 70, "fit": 80}
    s.update(kw)
    return s


def test_go_when_every_threshold_met():
    assert gates.evidence_gate(score(), [])["outcome"] == "go"


def test_stop_on_weak_evidence():
    g = gates.evidence_gate(score(recent_voices=1, demand=10), [])
    assert g["outcome"] == "stop"
    assert "do not build" in " ".join(g["reasons"]).lower()


def test_pivot_on_critical_risk():
    g = gates.evidence_gate(score(), [{"risk": "dominant free tool", "source": None, "severity": "critical"}])
    assert g["outcome"] == "pivot"


def test_repeat_when_nothing_could_be_fetched():
    assert gates.evidence_gate(score(sources=0, recent_voices=0, demand=0), [], nothing_fetched=True)["outcome"] == "repeat"


def test_stop_after_too_many_repeats():
    assert gates.evidence_gate(score(recent_voices=4), [], repeats=2)["outcome"] == "stop"


def test_preregistration_detects_changed_thresholds(monkeypatch):
    run = {"preregistered_hash": gates.threshold_hash()}
    assert gates.verify_preregistration(run)
    monkeypatch.setitem(gates.THRESHOLDS["evidence"], "min_demand", 1)
    assert not gates.verify_preregistration(run)


def test_operate_gate_will_not_judge_mocked_data():
    g = gates.operate_gate({"data_source": "MOCKED", "refund_rate": 0.0, "conversion": 0.5})
    assert g["outcome"] == "repeat"
