"""Market statements without a cited link are labelled ASSUMPTION."""
from agents.market_analyst import label_unsourced_bullets


def test_unsourced_bullets_are_labelled_and_sourced_ones_are_not():
    body = "\n".join([
        "## What they use today",
        "- Free repos like [sql-prep](https://github.com/x/sql-prep) lack worked answers.",
        "- LeetCode-style platforms feel abstract for analyst roles.",
        "- ASSUMPTION: bootcamp notes.",
        "1. No curated workbook exists.",
        "Plain sentence stays as it is.",
    ])
    out = label_unsourced_bullets(body).splitlines()
    assert out[1].endswith("lack worked answers.")
    assert out[2].endswith("analyst roles. (ASSUMPTION)")
    assert out[3] == "- ASSUMPTION: bootcamp notes."
    assert out[4].endswith("exists. (ASSUMPTION)")
    assert out[5] == "Plain sentence stays as it is."
