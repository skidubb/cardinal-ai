"""Tests for ConversationRuntime, ConversationThread, and performatives."""

from coordination.conversation.messages import (
    AgentMessage,
    ConversationBoundaries,
    Performative,
)
from coordination.conversation.runtime import (
    ConversationRuntime,
    ConversationState,
    ConversationThread,
)


class TestPerformatives:
    def test_all_performatives_are_strings(self):
        for p in Performative:
            assert isinstance(p.value, str)

    def test_convergence_signals(self):
        msg = AgentMessage(
            sender="agent1",
            performative=Performative.SIGNAL_CONVERGENCE,
            content="We're done",
        )
        assert msg.is_convergence_signal
        assert not msg.is_divergence_signal

    def test_divergence_signals(self):
        msg = AgentMessage(
            sender="agent1",
            performative=Performative.SIGNAL_DIVERGENCE,
            content="Not done",
            reason="Outstanding issues",
        )
        assert msg.is_divergence_signal
        assert not msg.is_convergence_signal

    def test_broadcast_detection(self):
        broadcast = AgentMessage(sender="a", performative=Performative.INFORM, content="hi")
        direct = AgentMessage(sender="a", addressee="b", performative=Performative.REQUEST, content="do X")
        assert broadcast.is_broadcast
        assert not direct.is_broadcast


class TestConversationThread:
    def test_add_message(self):
        thread = ConversationThread(thread_id="t1")
        msg = AgentMessage(sender="agent1", performative=Performative.PROPOSE, content="Let's do X")
        thread.add_message(msg)
        assert thread.turn_count == 1
        assert msg.thread_id == "t1"

    def test_unique_contributors(self):
        thread = ConversationThread(thread_id="t1")
        thread.add_message(AgentMessage(sender="a", performative=Performative.PROPOSE, content="1"))
        thread.add_message(AgentMessage(sender="b", performative=Performative.INFORM, content="2"))
        thread.add_message(AgentMessage(sender="a", performative=Performative.INFORM, content="3"))
        assert thread.unique_contributors == {"a", "b"}

    def test_filter_by_performative(self):
        thread = ConversationThread(thread_id="t1")
        thread.add_message(AgentMessage(sender="a", performative=Performative.PROPOSE, content="1"))
        thread.add_message(AgentMessage(sender="b", performative=Performative.ACCEPT, content="2"))
        thread.add_message(AgentMessage(sender="c", performative=Performative.PROPOSE, content="3"))
        proposals = thread.get_messages_by_performative(Performative.PROPOSE)
        assert len(proposals) == 2


class TestConversationRuntime:
    def _make_runtime(self, **kwargs) -> ConversationRuntime:
        bounds = ConversationBoundaries(**kwargs)
        return ConversationRuntime(
            thread_id="test",
            boundaries=bounds,
            agent_pool=["agent1", "agent2", "agent3"],
        )

    def test_accepts_messages(self):
        rt = self._make_runtime()
        msg = AgentMessage(sender="agent1", performative=Performative.PROPOSE, content="test")
        ok, reason = rt.accept_message(msg)
        assert ok
        assert reason is None
        assert rt.thread.turn_count == 1

    def test_rejects_after_max_turns(self):
        rt = self._make_runtime(max_turns=2)
        for i in range(2):
            rt.accept_message(AgentMessage(sender="agent1", performative=Performative.INFORM, content=f"msg{i}"))
        ok, reason = rt.accept_message(
            AgentMessage(sender="agent1", performative=Performative.INFORM, content="overflow")
        )
        assert not ok
        assert "Max turns" in reason

    def test_convergence_detection(self):
        rt = self._make_runtime(convergence_threshold=0.6)
        # 2 of 3 agents signal convergence = 66% > 60%
        rt.accept_message(AgentMessage(sender="agent1", performative=Performative.SIGNAL_DONE, content="done"))
        rt.accept_message(AgentMessage(sender="agent2", performative=Performative.SIGNAL_CONVERGENCE, content="done"))
        state = rt.get_state()
        assert state.is_converged
        assert state.convergence_signals == 2

    def test_divergence_resets_convergence(self):
        rt = self._make_runtime(convergence_threshold=0.6)
        rt.accept_message(AgentMessage(sender="agent1", performative=Performative.SIGNAL_DONE, content="done"))
        rt.accept_message(AgentMessage(sender="agent1", performative=Performative.SIGNAL_DIVERGENCE, content="wait", reason="issues"))
        state = rt.get_state()
        assert state.convergence_signals == 0
        assert state.divergence_signals == 1

    def test_abstain_tracking(self):
        rt = self._make_runtime()
        rt.accept_message(AgentMessage(sender="agent3", performative=Performative.ABSTAIN, content="nothing to add"))
        state = rt.get_state()
        assert "agent3" not in state.active_agents
        assert "agent1" in state.active_agents

    def test_escalation_tracking(self):
        rt = self._make_runtime()
        rt.accept_message(AgentMessage(
            sender="agent1", performative=Performative.ESCALATE,
            content="Need human", reason="Low confidence",
        ))
        flags = rt.get_escalation_flags()
        assert len(flags) == 1
        assert flags[0].sender == "agent1"

    def test_agent_stats(self):
        rt = self._make_runtime()
        rt.accept_message(AgentMessage(sender="agent1", performative=Performative.PROPOSE, content="a", confidence=0.8))
        rt.accept_message(AgentMessage(sender="agent1", performative=Performative.INFORM, content="b", confidence=0.6))
        stats = rt.get_agent_stats()
        assert stats["agent1"]["message_count"] == 2
        assert abs(stats["agent1"]["avg_confidence"] - 0.7) < 0.01

    def test_trace_export(self):
        rt = self._make_runtime()
        rt.accept_message(AgentMessage(sender="agent1", performative=Performative.PROPOSE, content="test"))
        trace = rt.to_trace()
        assert trace["thread_id"] == "test"
        assert trace["turn_count"] == 1
        assert len(trace["messages"]) == 1

    def test_feature_flag_isolation(self):
        """Coordination layer is off by default."""
        from coordination import is_enabled
        import os
        # Default should be off
        old = os.environ.pop("COORDINATION_LAYER_ENABLED", None)
        assert not is_enabled()
        os.environ["COORDINATION_LAYER_ENABLED"] = "true"
        assert is_enabled()
        os.environ["COORDINATION_LAYER_ENABLED"] = "false"
        assert not is_enabled()
        if old:
            os.environ["COORDINATION_LAYER_ENABLED"] = old
        else:
            os.environ.pop("COORDINATION_LAYER_ENABLED", None)
