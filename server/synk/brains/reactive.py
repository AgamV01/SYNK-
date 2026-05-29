"""The reactive brain: cheap, synchronous, zero-I/O behavior every tick."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..geometry import Vec3
from ..pathfinding import astar, simplify_path
from ..world import Player
from .base import Action, ConverseResult, Face, Idle, MoveTo, Wander

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

    def _steer_towards(self, agent: Agent, target: Vec3) -> MoveTo:
        """Return a MoveTo aimed at the next waypoint of the A* path to `target`.

        With no grid, steer straight. With a grid, follow the path so the agent
        rounds obstacles instead of walking into them."""
        if self.grid is None:
            return MoveTo(target=target)
        start = self.grid.world_to_cell(agent.position)
        goal = self.grid.world_to_cell(target)
        path = simplify_path(astar(self.grid, start, goal))
        if len(path) >= 2:
            return MoveTo(target=self.grid.cell_center(path[1]))
        return MoveTo(target=target)

    def _candidates(self, agent: Agent, percept: Percept) -> list[tuple[float, Action]]:
        """Score candidate behaviors. Highest utility wins. Social behaviors
        (face/approach) outrank ambient ones (wander/idle)."""
        cands: list[tuple[float, Action]] = [
            (1.0 if self.restless else 0.2, Wander()),
            (0.1 if self.restless else 0.5, Idle()),
        ]
        player = self._nearest_player(agent, percept)
        if player is not None:
            if agent.position.distance_to(player.position) <= self.arrive_radius:
                cands.append((3.0, Face(target_id=player.id)))
            else:
                cands.append((2.0, self._steer_towards(agent, player.position)))
        return cands

    def decide(self, agent: Agent, percept: Percept) -> Action:
        candidates = self._candidates(agent, percept)
        return max(candidates, key=lambda c: c[0])[1]

    async def converse(
        self, agent: Agent, percept: Percept, utterance: str
    ) -> ConverseResult:
        """Templated dialogue, no LLM. Greets by name (and personality if set) and
        acknowledges what the player said, so the demo works with zero API keys."""
        name = agent.name or "The figure"
        flavor = f" {agent.personality}." if agent.personality else ""
        said = utterance.strip()
        if said:
            text = f'{name}: Well met.{flavor} You said, "{said}".'
        else:
            text = f"{name}: Well met.{flavor} What brings you here?"
        return ConverseResult(text=text)
