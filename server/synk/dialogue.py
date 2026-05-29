"""Conversations and routing. Tracks turn history so brains can build context, and
routes player utterances to agents (with overhearing handled at the server layer)."""

from __future__ import annotations

from dataclasses import dataclass, field


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
