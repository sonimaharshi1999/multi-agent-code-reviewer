# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Message bus for inter-agent communication."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Optional

from src.models import AgentRole, Message


class MessageBus:
    """Simple in-process message bus for agent communication.

    Agents subscribe to message types and receive messages synchronously.
    Supports both targeted (single recipient) and broadcast messages.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[tuple[Optional[AgentRole], Callable[[Message], None]]]] = defaultdict(list)
        self._message_log: list[Message] = []

    def subscribe(
        self,
        msg_type: str,
        callback: Callable[[Message], None],
        agent_role: Optional[AgentRole] = None,
    ) -> None:
        """Subscribe to a message type.

        Args:
            msg_type: The message type to listen for.
            callback: Function to invoke when a matching message arrives.
            agent_role: If set, only receive messages addressed to this role or broadcasts.
        """
        self._subscribers[msg_type].append((agent_role, callback))

    def publish(self, message: Message) -> int:
        """Publish a message to all matching subscribers.

        Args:
            message: The message to deliver.

        Returns:
            Number of subscribers that received the message.
        """
        self._message_log.append(message)
        delivered = 0
        for role, callback in self._subscribers.get(message.msg_type, []):
            # Deliver if: broadcast (no recipient), or targeted to this subscriber
            if message.recipient is None or role is None or message.recipient == role:
                callback(message)
                delivered += 1
        return delivered

    def get_log(self) -> list[Message]:
        """Return a copy of the full message log."""
        return list(self._message_log)

    def clear(self) -> None:
        """Clear all subscriptions and message log."""
        self._subscribers.clear()
        self._message_log.clear()

    @property
    def message_count(self) -> int:
        """Total messages published."""
        return len(self._message_log)

    @property
    def subscriber_count(self) -> int:
        """Total active subscriptions."""
        return sum(len(subs) for subs in self._subscribers.values())
