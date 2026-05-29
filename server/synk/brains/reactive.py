"""The reactive brain: cheap, synchronous, zero-I/O behavior every tick."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..world import Player
from .base import Action, ConverseResult, Idle, MoveTo, Wander

if TYPE_CHECKING:
    from ..pathfinding import Grid
    from ..perception import Percept
    from ..world import Agent


class ReactiveBrain:
    """Drives continuous behavior with no network I/O.

    `decide` runs every tick and must stay cheap. `converse` produces a templated
    line (no LLM) so the framework works fully with zero API keys.
    """

    def __init__(
        self,
        *,
        sense_radius: float = 10.0,
        arrive_radius: float = 1.5,
        restless: bool = True,
        grid: Grid | None = None,
    ) -> None:
        self.sense_radius = sense_radius
        self.arrive_radius = arrive_radius
        self.restless = restless
        self.grid = grid

    def _nearest_player(self, agent: Agent, percept: Percept) -> Player | None:
        players = [e for e in percept.nearby if isinstance(e, Player)]
        if not players:
            return None
        return min(players, key=lambda p: agent.position.distance_to(p.position))

    def decide(self, agent: Agent, percept: Percept) -> Action:
        player = self._nearest_player(agent, percept)
        if player is not None:
            # A player is nearby: approach them.
            return MoveTo(target=player.position)
        # Ambient behavior when nothing demands attention: wander, or idle if calm.
        return Wander() if self.restless else Idle()

    async def converse(
        self, agent: Agent, percept: Percept, utterance: str
    ) -> ConverseResult:
        name = agent.name or "The figure"
        return ConverseResult(text=f"{name} acknowledges you.")
