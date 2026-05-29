"""Conversations and routing. Tracks turn history so brains can build context, and
routes player utterances to agents (with overhearing handled at the server layer)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .world import Entity, Player, World

# Players within this xz radius of a speaker overhear dialogue (protocol/messages.md).
NEARBY_RADIUS = 12.0


@dataclass
class Turn:
    speaker: str  # entity id
    text: str
    ts: float = 0.0


@dataclass
class Conversation:
    id: str
    participants: list[str] = field(default_factory=list)
    turns: list[Turn] = field(default_factory=list)

    def add_turn(self, speaker: str, text: str, ts: float = 0.0) -> Turn:
        turn = Turn(speaker=speaker, text=text, ts=ts)
        self.turns.append(turn)
        if speaker not in self.participants:
            self.participants.append(speaker)
        return turn

    def history(self, limit: int | None = None) -> list[Turn]:
        """Turns oldest-first. With `limit`, only the most recent `limit` turns."""
        if limit is None:
            return list(self.turns)
        if limit <= 0:
            return []
        return self.turns[-limit:]


def overhearers(
    world: World,
    speaker: Entity,
    radius: float = NEARBY_RADIUS,
    exclude_id: str | None = None,
) -> list[Player]:
    """Players who overhear `speaker`: within `radius` (xz, same zone), excluding the
    speaker and the directly-addressed player (`exclude_id`). These receive the
    `dialogue` message with overheard=True."""
    nearby = world.within_radius(
        speaker.position, radius, zone=speaker.zone, exclude_id=speaker.id
    )
    return [e for e in nearby if isinstance(e, Player) and e.id != exclude_id]


class DialogueManager:
    """Owns conversations, keyed by (player, agent) pair, and routes messages."""

    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}

    @staticmethod
    def _key(player_id: str, agent_id: str) -> str:
        return f"{player_id}->{agent_id}"

    def start(self, player_id: str, agent_id: str) -> Conversation:
        """Get the existing conversation between player and agent, or start one."""
        key = self._key(player_id, agent_id)
        convo = self._conversations.get(key)
        if convo is None:
            convo = Conversation(id=key, participants=[player_id, agent_id])
            self._conversations[key] = convo
        return convo

    def route_player_message(
        self, player_id: str, agent_id: str, text: str, ts: float = 0.0
    ) -> Conversation:
        """Record a player utterance directed at an agent and return the conversation."""
        convo = self.start(player_id, agent_id)
        convo.add_turn(player_id, text, ts)
        return convo

    def append_agent_reply(
        self, player_id: str, agent_id: str, text: str, ts: float = 0.0
    ) -> Conversation:
        """Record the agent's reply in the conversation with this player."""
        convo = self.start(player_id, agent_id)
        convo.add_turn(agent_id, text, ts)
        return convo

    def history(
        self, player_id: str, agent_id: str, limit: int | None = None
    ) -> list[Turn]:
        """Turn history for a (player, agent) pair; empty if no conversation yet."""
        convo = self._conversations.get(self._key(player_id, agent_id))
        return convo.history(limit) if convo is not None else []

    def group(
        self, conversation_id: str, participant_ids: tuple[str, ...] | list[str] = ()
    ) -> Conversation:
        """Get or create a multi-party conversation (e.g. NPC↔NPC) by id."""
        convo = self._conversations.get(conversation_id)
        if convo is None:
            convo = Conversation(id=conversation_id, participants=list(participant_ids))
            self._conversations[conversation_id] = convo
        return convo

    def route_group_message(
        self, conversation_id: str, speaker_id: str, text: str, ts: float = 0.0
    ) -> Conversation:
        """Record a turn from `speaker_id` in a multi-party conversation."""
        convo = self.group(conversation_id)
        convo.add_turn(speaker_id, text, ts)
        return convo
