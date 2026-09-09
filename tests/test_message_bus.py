# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Tests for the MessageBus."""

from __future__ import annotations

from src.message_bus import MessageBus
from src.models import AgentRole, Message


class TestMessageBus:
    """MessageBus tests."""

    def test_publish_subscribe(self, bus: MessageBus) -> None:
        """Subscriber should receive published messages."""
        received: list[Message] = []
        bus.subscribe("test", received.append)
        msg = Message(sender=AgentRole.ORCHESTRATOR, msg_type="test")
        delivered = bus.publish(msg)
        assert delivered == 1
        assert len(received) == 1
        assert received[0].msg_type == "test"

    def test_broadcast_delivery(self, bus: MessageBus) -> None:
        """Broadcast messages (recipient=None) reach all subscribers."""
        a_msgs: list[Message] = []
        b_msgs: list[Message] = []
        bus.subscribe("notify", a_msgs.append, agent_role=AgentRole.SECURITY)
        bus.subscribe("notify", b_msgs.append, agent_role=AgentRole.STYLE)
        msg = Message(sender=AgentRole.ORCHESTRATOR, recipient=None, msg_type="notify")
        bus.publish(msg)
        assert len(a_msgs) == 1
        assert len(b_msgs) == 1

    def test_targeted_delivery(self, bus: MessageBus) -> None:
        """Targeted messages reach only the intended agent."""
        sec: list[Message] = []
        sty: list[Message] = []
        bus.subscribe("review", sec.append, agent_role=AgentRole.SECURITY)
        bus.subscribe("review", sty.append, agent_role=AgentRole.STYLE)
        msg = Message(
            sender=AgentRole.ORCHESTRATOR,
            recipient=AgentRole.SECURITY,
            msg_type="review",
        )
        bus.publish(msg)
        assert len(sec) == 1
        assert len(sty) == 0

    def test_message_log(self, bus: MessageBus) -> None:
        """All published messages should appear in the log."""
        bus.subscribe("a", lambda m: None)
        bus.publish(Message(sender=AgentRole.ORCHESTRATOR, msg_type="a"))
        bus.publish(Message(sender=AgentRole.ORCHESTRATOR, msg_type="a"))
        assert bus.message_count == 2
        assert len(bus.get_log()) == 2

    def test_clear(self, bus: MessageBus) -> None:
        """Clear should reset subscriptions and log."""
        bus.subscribe("x", lambda m: None)
        bus.publish(Message(sender=AgentRole.ORCHESTRATOR, msg_type="x"))
        bus.clear()
        assert bus.message_count == 0
        assert bus.subscriber_count == 0
