from __future__ import annotations

from synk.relationships import Relationships, sentiment_for


def test_adjust_and_sentiment() -> None:
    r = Relationships()
    assert r.sentiment("x") == 0.0
    r.adjust("x", 2.0)
    r.adjust("x", 0.5)
    assert r.sentiment("x") == 2.5


def test_describe_labels_and_skips_neutral() -> None:
    r = Relationships()
    r.adjust("ally", 3.0)
    r.adjust("foe", -3.0)
    r.adjust("meh", 0.2)
    desc = r.describe()
    assert any("trusts ally" in d for d in desc)
    assert any("distrusts foe" in d for d in desc)
    assert all("meh" not in d for d in desc)  # near-neutral is omitted


def test_sentiment_for_kinds_ordered() -> None:
    assert sentiment_for("gave_item") > sentiment_for("spoke") > sentiment_for("moved")
    assert sentiment_for("moved") == 0.0


def test_top() -> None:
    r = Relationships()
    r.adjust("a", 1.0)
    r.adjust("b", 3.0)
    r.adjust("c", 2.0)
    assert [i for i, _ in r.top(2)] == ["b", "c"]
