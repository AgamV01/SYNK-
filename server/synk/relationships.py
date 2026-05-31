"""Per-agent social memory: a sentiment score toward each other entity, nudged by
perceived events and folded into the LLM prompt so NPCs treat friends and strangers
differently over time."""

from __future__ import annotations

# How a perceived event shifts the perceiver's sentiment toward its source.
SENTIMENT_BY_KIND: dict[str, float] = {
    "gave_item": 2.0,
    "handoff": 0.5,
    "spoke": 0.3,
    "emoted": 0.1,
    "moved": 0.0,
    "goal_changed": 0.0,
}


def sentiment_for(kind: str) -> float:
    return SENTIMENT_BY_KIND.get(kind, 0.0)


class Relationships:
    """Sentiment toward other entities, keyed by id (0 = neutral/unknown)."""

    def __init__(self) -> None:
        self._scores: dict[str, float] = {}

    def adjust(self, other_id: str, delta: float) -> None:
        if delta:
            self._scores[other_id] = self._scores.get(other_id, 0.0) + delta

    def sentiment(self, other_id: str) -> float:
        return self._scores.get(other_id, 0.0)

    def as_dict(self) -> dict[str, float]:
        """A copy of the raw sentiment scores, for persistence/inspection."""
        return dict(self._scores)

    @classmethod
    def from_scores(cls, scores: dict[str, float]) -> "Relationships":
        """Rebuild from persisted scores (the inverse of as_dict)."""
        rel = cls()
        rel._scores = {str(k): float(v) for k, v in scores.items()}
        return rel

    def top(self, n: int = 3) -> list[tuple[str, float]]:
        return sorted(self._scores.items(), key=lambda kv: kv[1], reverse=True)[:n]

    def describe(self) -> list[str]:
        """Human/LLM-readable sentiment lines for the prompt (skips ~neutral ties)."""
        out: list[str] = []
        for other_id, score in sorted(self._scores.items(), key=lambda kv: kv[1], reverse=True):
            if abs(score) < 0.5:
                continue
            if score >= 2.0:
                label = "trusts"
            elif score > 0:
                label = "likes"
            elif score > -2.0:
                label = "is wary of"
            else:
                label = "distrusts"
            out.append(f"{label} {other_id} (sentiment {score:+.1f})")
        return out
