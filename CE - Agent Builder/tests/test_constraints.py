"""Tests for the inter-agent constraint propagation module."""

from csuite.coordination.constraints import (
    Constraint,
    ConstraintStore,
    ConstraintStrength,
    ConstraintType,
)


def test_constraint_store_add_and_retrieve():
    store = ConstraintStore()
    c = Constraint(
        source_role="cfo",
        constraint_type=ConstraintType.BUDGET,
        description="Marketing spend must not exceed $500K",
        value="$500K",
        strength=ConstraintStrength.HARD,
    )
    store.add(c)
    assert len(store.constraints) == 1
    assert store.constraints[0].source_role == "cfo"


def test_constraint_store_peer_constraints():
    store = ConstraintStore()
    store.add(Constraint(
        source_role="cfo",
        constraint_type=ConstraintType.BUDGET,
        description="Budget cap",
        strength=ConstraintStrength.HARD,
    ))
    store.add(Constraint(
        source_role="cmo",
        constraint_type=ConstraintType.STRATEGIC,
        description="Must target enterprise",
        strength=ConstraintStrength.SOFT,
    ))

    cmo_peers = store.get_peer_constraints("cmo")
    assert len(cmo_peers) == 1
    assert cmo_peers[0].source_role == "cfo"

    cfo_peers = store.get_peer_constraints("cfo")
    assert len(cfo_peers) == 1
    assert cfo_peers[0].source_role == "cmo"


def test_constraint_store_hard_only():
    store = ConstraintStore()
    store.add(Constraint(
        source_role="cfo", constraint_type=ConstraintType.BUDGET,
        description="Hard one", strength=ConstraintStrength.HARD,
    ))
    store.add(Constraint(
        source_role="coo", constraint_type=ConstraintType.RESOURCE,
        description="Soft one", strength=ConstraintStrength.SOFT,
    ))
    hard = store.get_hard_constraints()
    assert len(hard) == 1
    assert hard[0].description == "Hard one"


def test_constraint_store_format_for_prompt():
    store = ConstraintStore()
    store.add(Constraint(
        source_role="cfo",
        constraint_type=ConstraintType.BUDGET,
        description="Max $500K",
        value="$500K",
        strength=ConstraintStrength.HARD,
    ))
    formatted = store.format_for_prompt(exclude_role="cmo")
    assert "[HARD]" in formatted
    assert "CFO" in formatted
    assert "$500K" in formatted


def test_constraint_store_empty_format():
    store = ConstraintStore()
    assert "No constraints" in store.format_for_prompt()


def test_constraint_add_many():
    store = ConstraintStore()
    constraints = [
        Constraint(source_role="cfo", constraint_type=ConstraintType.BUDGET, description="A"),
        Constraint(source_role="cto", constraint_type=ConstraintType.TECHNICAL, description="B"),
    ]
    store.add_many(constraints)
    assert len(store.constraints) == 2
