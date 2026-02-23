"""Tests for session models and managers — uses DuckDB fixture."""

from unittest.mock import patch

from csuite.session import (
    DebateArgument,
    DebateRound,
    DebateSession,
    DebateSessionManager,
    Session,
    SessionManager,
)


class TestSessionModel:
    def test_add_message(self):
        s = Session(agent_role="ceo")
        msg = s.add_message("user", "What is our strategy?")
        assert msg.role == "user"
        assert msg.content == "What is our strategy?"
        assert len(s.messages) == 1

    def test_get_conversation_history(self):
        s = Session(agent_role="cfo")
        s.add_message("user", "Q1")
        s.add_message("assistant", "A1")
        history = s.get_conversation_history()
        assert history == [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]

    def test_to_summary_with_title(self):
        s = Session(agent_role="ceo", title="Strategy Review")
        summary = s.to_summary()
        assert "Strategy Review" in summary
        assert "CEO" in summary

    def test_to_summary_from_first_message(self):
        s = Session(agent_role="cto")
        s.add_message("user", "What tech stack should we use?")
        summary = s.to_summary()
        assert "What tech stack" in summary

    def test_to_summary_empty(self):
        s = Session(agent_role="cpo")
        summary = s.to_summary()
        assert "Empty session" in summary

    def test_parent_session_id_default_none(self):
        s = Session(agent_role="ceo")
        assert s.parent_session_id is None

    def test_metadata_stores_kwargs(self):
        s = Session(agent_role="ceo")
        msg = s.add_message("assistant", "response", model="opus", usage={"tokens": 100})
        assert msg.metadata["model"] == "opus"


class TestSessionManager:
    def test_create_and_load(self, duckdb_store):
        with patch("csuite.session._get_store", return_value=duckdb_store):
            mgr = SessionManager()
            session = mgr.create_session("ceo", title="Test")
            loaded = mgr.load(session.id, "ceo")
            assert loaded is not None
            assert loaded.id == session.id
            assert loaded.agent_role == "ceo"

    def test_save_with_messages(self, duckdb_store):
        with patch("csuite.session._get_store", return_value=duckdb_store):
            mgr = SessionManager()
            session = mgr.create_session("cfo")
            session.add_message("user", "Hello")
            session.add_message("assistant", "Hi there")
            mgr.save(session)
            loaded = mgr.load(session.id, "cfo")
            assert loaded is not None
            assert len(loaded.messages) == 2
            assert loaded.messages[0].content == "Hello"

    def test_list_sessions(self, duckdb_store):
        with patch("csuite.session._get_store", return_value=duckdb_store):
            mgr = SessionManager()
            mgr.create_session("ceo", title="S1")
            mgr.create_session("ceo", title="S2")
            mgr.create_session("cfo", title="S3")
            ceo_sessions = mgr.list_sessions("ceo")
            assert len(ceo_sessions) == 2

    def test_delete(self, duckdb_store):
        with patch("csuite.session._get_store", return_value=duckdb_store):
            mgr = SessionManager()
            session = mgr.create_session("cto")
            assert mgr.delete(session.id) is True
            assert mgr.load(session.id, "cto") is None

    def test_delete_nonexistent(self, duckdb_store):
        with patch("csuite.session._get_store", return_value=duckdb_store):
            mgr = SessionManager()
            assert mgr.delete("nonexistent") is False

    def test_fork(self, duckdb_store):
        with patch("csuite.session._get_store", return_value=duckdb_store):
            mgr = SessionManager()
            original = mgr.create_session("ceo")
            original.add_message("user", "Original Q")
            mgr.save(original)
            forked = mgr.fork(original.id, "Forked Session", "ceo")
            assert forked is not None
            assert forked.id != original.id
            assert forked.parent_session_id == original.id
            assert len(forked.messages) == 1
            assert forked.title == "Forked Session"

    def test_fork_nonexistent(self, duckdb_store):
        with patch("csuite.session._get_store", return_value=duckdb_store):
            mgr = SessionManager()
            assert mgr.fork("nope", "title", "ceo") is None


class TestDebateSessionModel:
    def test_add_round(self):
        ds = DebateSession(question="Q?", agent_roles=["ceo", "cfo"], total_rounds=3)
        rnd = DebateRound(round_number=1, round_type="opening", arguments=[
            DebateArgument(role="ceo", agent_name="CEO", content="My take", round_number=1),
            DebateArgument(role="cfo", agent_name="CFO", content="My take", round_number=1),
        ])
        ds.add_round(rnd)
        assert len(ds.rounds) == 1
        assert ds.status == "in_progress"

    def test_set_synthesis(self):
        ds = DebateSession(question="Q?", agent_roles=["ceo"], total_rounds=1)
        ds.set_synthesis("Final synthesis")
        assert ds.synthesis == "Final synthesis"
        assert ds.status == "completed"

    def test_get_all_arguments_through_round(self):
        ds = DebateSession(question="Q?", agent_roles=["ceo", "cfo"], total_rounds=2)
        r1 = DebateRound(round_number=1, round_type="opening", arguments=[
            DebateArgument(role="ceo", agent_name="CEO", content="R1", round_number=1),
        ])
        r2 = DebateRound(round_number=2, round_type="final", arguments=[
            DebateArgument(role="ceo", agent_name="CEO", content="R2", round_number=2),
        ])
        ds.add_round(r1)
        ds.add_round(r2)
        args_r1 = ds.get_all_arguments_through_round(1)
        assert len(args_r1) == 1
        args_r2 = ds.get_all_arguments_through_round(2)
        assert len(args_r2) == 2

    def test_get_arguments_round_zero(self):
        ds = DebateSession(question="Q?", agent_roles=["ceo"], total_rounds=1)
        ds.add_round(DebateRound(round_number=1, round_type="opening", arguments=[
            DebateArgument(role="ceo", agent_name="CEO", content="X", round_number=1),
        ]))
        assert ds.get_all_arguments_through_round(0) == []


class TestDebateSessionManager:
    def test_save_and_load(self, duckdb_store):
        with patch("csuite.session._get_store", return_value=duckdb_store):
            mgr = DebateSessionManager()
            ds = DebateSession(question="Q?", agent_roles=["ceo", "cfo"], total_rounds=2)
            ds.add_round(DebateRound(round_number=1, round_type="opening", arguments=[
                DebateArgument(role="ceo", agent_name="CEO", content="Take", round_number=1),
            ]))
            mgr.save(ds)
            loaded = mgr.load(ds.id)
            assert loaded is not None
            assert loaded.question == "Q?"
            assert len(loaded.rounds) == 1

    def test_list_debates(self, duckdb_store):
        with patch("csuite.session._get_store", return_value=duckdb_store):
            mgr = DebateSessionManager()
            for i in range(3):
                ds = DebateSession(question=f"Q{i}?", agent_roles=["ceo"], total_rounds=1)
                mgr.save(ds)
            sessions = mgr.list_sessions(limit=10)
            assert len(sessions) == 3

    def test_delete(self, duckdb_store):
        with patch("csuite.session._get_store", return_value=duckdb_store):
            mgr = DebateSessionManager()
            ds = DebateSession(question="Q?", agent_roles=["ceo"], total_rounds=1)
            mgr.save(ds)
            assert mgr.delete(ds.id) is True
            assert mgr.load(ds.id) is None
