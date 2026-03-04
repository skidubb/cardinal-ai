"""
Session persistence manager for C-Suite agents.

Handles saving and loading conversation history to enable continuity across sessions.
Sessions are stored in DuckDB with metadata and message history.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from csuite.storage.provider import get_db


class Message(BaseModel):
    """A single message in the conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Session(BaseModel):
    """A conversation session with an agent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_role: str
    title: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    messages: list[Message] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    parent_session_id: str | None = None  # For forked sessions

    def add_message(self, role: str, content: str, **metadata: Any) -> Message:
        """Add a message to the session."""
        message = Message(role=role, content=content, metadata=metadata)
        self.messages.append(message)
        self.updated_at = datetime.now()
        return message

    def get_conversation_history(self) -> list[dict[str, str]]:
        """Get conversation history in format suitable for Claude API."""
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]

    def to_summary(self) -> str:
        """Generate a summary line for session listing."""
        title = self.title or (self.messages[0].content[:50] if self.messages else "Empty session")
        return f"[{self.id}] {self.agent_role.upper()} - {title}... ({len(self.messages)} msgs)"


def _session_to_db_args(session: Session) -> dict[str, Any]:
    """Convert a Session model to DuckDB save args."""
    return {
        "session_id": session.id,
        "agent_role": session.agent_role,
        "title": session.title,
        "parent_session_id": session.parent_session_id,
        "metadata": session.metadata,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata,
            }
            for msg in session.messages
        ],
    }


def _db_row_to_session(data: dict[str, Any]) -> Session:
    """Convert a DuckDB row dict back to a Session model."""
    messages = [
        Message(
            role=m["role"],
            content=m["content"],
            timestamp=m["timestamp"],
            metadata=m.get("metadata", {}),
        )
        for m in data.get("messages", [])
    ]
    return Session(
        id=data["id"],
        agent_role=data["agent_role"],
        title=data.get("title"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        messages=messages,
        metadata=data.get("metadata", {}),
        parent_session_id=data.get("parent_session_id"),
    )


class SessionManager:
    """Manages session persistence via DuckDB."""

    def __init__(self, session_dir: Any = None):
        # session_dir kept for signature compat but unused with DuckDB
        pass

    def save(self, session: Session) -> None:
        """Save a session to DuckDB."""
        db = get_db()
        db.save_session(**_session_to_db_args(session))

    def load(self, session_id: str, agent_role: str | None = None) -> Session | None:
        """Load a session from DuckDB."""
        db = get_db()
        data = db.load_session(session_id, agent_role)
        if data is None:
            return None
        return _db_row_to_session(data)

    def cleanup_old_sessions(self, max_age_days: int = 90) -> int:
        """Delete sessions older than max_age_days. Returns count deleted."""
        db = get_db()
        return db.delete_old_sessions(max_age_days)

    def list_sessions(
        self,
        agent_role: str | None = None,
        limit: int = 20,
    ) -> list[Session]:
        """List sessions, optionally filtered by agent role."""
        db = get_db()
        # Lazily clean up old sessions on list
        try:
            db.delete_old_sessions()
        except Exception:
            pass  # Non-critical — don't block listing
        rows = db.list_sessions(agent_role=agent_role, limit=limit)
        sessions = []
        for row in rows:
            # list_sessions doesn't return messages, add empty + count
            s = Session(
                id=row["id"],
                agent_role=row["agent_role"],
                title=row.get("title"),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=row.get("metadata", {}),
                parent_session_id=row.get("parent_session_id"),
            )
            # Stash message count in metadata for display
            s.metadata["_message_count"] = row.get("message_count", 0)
            sessions.append(s)
        return sessions

    def delete(self, session_id: str, agent_role: str | None = None) -> bool:
        """Delete a session."""
        db = get_db()
        return db.delete_session(session_id)

    def fork(self, session_id: str, title: str, agent_role: str | None = None) -> Session | None:
        """Fork a session to create a new branch from it."""
        original = self.load(session_id, agent_role)
        if not original:
            return None

        forked = Session(
            agent_role=original.agent_role,
            title=title,
            messages=original.messages.copy(),
            metadata=original.metadata.copy(),
            parent_session_id=original.id,
        )
        self.save(forked)
        return forked

    def create_session(self, agent_role: str, title: str | None = None) -> Session:
        """Create a new session."""
        session = Session(agent_role=agent_role, title=title)
        self.save(session)
        return session


# ---------------------------------------------------------------------------
# Debate models (used by debate.py and prompts/debate_prompt.py)
# ---------------------------------------------------------------------------


class DebateArgument(BaseModel):
    """A single argument made by one agent in one round of a debate."""

    role: str
    agent_name: str
    content: str
    round_number: int


class DebateRound(BaseModel):
    """One round of a multi-round debate."""

    round_number: int
    round_type: str  # "opening" | "rebuttal" | "final" | "negotiation"
    arguments: list[DebateArgument] = Field(default_factory=list)


class DebateSession(BaseModel):
    """Full state of a multi-round debate."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str
    agent_roles: list[str]
    total_rounds: int
    rounds: list[DebateRound] = Field(default_factory=list)
    synthesis: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    def add_round(self, round_: DebateRound) -> None:
        self.rounds.append(round_)

    def set_synthesis(self, text: str) -> None:
        self.synthesis = text

    def get_all_arguments_through_round(self, through_round: int) -> list[DebateArgument]:
        args: list[DebateArgument] = []
        for r in self.rounds:
            if r.round_number <= through_round:
                args.extend(r.arguments)
        return args


class DebateSessionManager:
    """Minimal persistence shim for DebateSession (saves to DuckDB if available)."""

    def save(self, debate: DebateSession) -> None:  # noqa: B027
        """Persist a debate session. No-op if storage is unavailable."""
        try:
            db = get_db()
            db.save_session(
                session_id=debate.id,
                agent_role="debate",
                title=debate.question[:80],
                parent_session_id=None,
                metadata={"question": debate.question, "agent_roles": debate.agent_roles},
                created_at=debate.created_at.isoformat(),
                updated_at=datetime.now().isoformat(),
                messages=[],
            )
        except Exception:
            pass

