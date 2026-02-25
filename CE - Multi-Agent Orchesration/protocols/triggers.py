"""Trigger conditions for blackboard-driven orchestration.

Pure functions returning Callable[[Blackboard], bool].
Orchestrator evaluates these to decide when stages fire.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from protocols.blackboard import Blackboard


def always() -> Callable[[Blackboard], bool]:
    """Fires immediately — used for the first stage."""
    return lambda bb: True


def after(stage_name: str) -> Callable[[Blackboard], bool]:
    """Fires after a stage has written at least once."""
    return lambda bb: stage_name in bb.stages_completed()


def after_all(*stage_names: str) -> Callable[[Blackboard], bool]:
    """Fires when ALL listed stages have completed."""
    def check(bb: Blackboard) -> bool:
        completed = bb.stages_completed()
        return all(s in completed for s in stage_names)
    return check


def after_any(*stage_names: str) -> Callable[[Blackboard], bool]:
    """Fires when ANY listed stage has completed."""
    def check(bb: Blackboard) -> bool:
        completed = bb.stages_completed()
        return any(s in completed for s in stage_names)
    return check


def on_conflict(topic: str) -> Callable[[Blackboard], bool]:
    """Fires when conflicts exist on a topic."""
    return lambda bb: bb.conflicts(topic) is not None
