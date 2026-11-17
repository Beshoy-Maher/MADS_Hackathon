import pytest

import approval


def test_nothing_is_released_without_founder_approval(tmp_path):
    run = {"id": "r1", "dir": str(tmp_path), "outbound": []}
    item = approval.request(run, "send", "Launch post", {})
    with pytest.raises(approval.ApprovalRequired):
        approval.release(run, item["id"])
    assert not (tmp_path / "outbox.jsonl").exists()


def test_only_the_founder_can_approve(tmp_path):
    run = {"id": "r1", "dir": str(tmp_path), "outbound": []}
    item = approval.request(run, "publish", "Landing page", {})
    for actor in ("agent", "copywriter", "system", ""):
        with pytest.raises(PermissionError):
            approval.decide(run, item["id"], True, actor)
    approval.decide(run, item["id"], True, "founder")
    assert "STUBBED" in (tmp_path / "outbox.jsonl").read_text()


def test_rejected_item_is_never_released(tmp_path):
    run = {"id": "r1", "dir": str(tmp_path), "outbound": []}
    item = approval.request(run, "send", "Post", {})
    approval.decide(run, item["id"], False, "founder")
    with pytest.raises(approval.ApprovalRequired):
        approval.release(run, item["id"])
