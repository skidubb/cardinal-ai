"""
Inter-Agent Constraint Propagation for C-Suite.

Agents negotiate to feasible joint plans. CFO's budget bounds CMO's spend.
Group output couldn't be produced by any single agent.
"""

from csuite.coordination.constraints import (
    Constraint,
    ConstraintExtractor,
    ConstraintStore,
    ConstraintValidator,
)

__all__ = ["Constraint", "ConstraintExtractor", "ConstraintStore", "ConstraintValidator"]
