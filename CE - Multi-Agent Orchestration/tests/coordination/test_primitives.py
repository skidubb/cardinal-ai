"""Tests for coordination primitives."""

from coordination.primitives.base import (
    Composition,
    CompositionStep,
    Primitive,
    PrimitiveInput,
    PrimitiveOutput,
    PrimitiveTrace,
    PrimitiveType,
)
from coordination.primitives.implementations import (
    PRIMITIVE_REGISTRY,
    Challenge,
    Compress,
    Decompose,
    Propose,
    Retrieve,
    get_primitive,
)


class TestPrimitiveTypes:
    def test_all_nine_types_exist(self):
        types = list(PrimitiveType)
        assert len(types) == 9
        assert PrimitiveType.DECOMPOSE in types
        assert PrimitiveType.COMPRESS in types

    def test_registry_has_all_types(self):
        for pt in PrimitiveType:
            assert pt in PRIMITIVE_REGISTRY

    def test_get_primitive_returns_instance(self):
        p = get_primitive(PrimitiveType.DECOMPOSE)
        assert isinstance(p, Decompose)
        assert p.primitive_type == PrimitiveType.DECOMPOSE


class TestPrimitiveIO:
    def test_input_has_defaults(self):
        inp = PrimitiveInput(content="test")
        assert inp.context == {}
        assert inp.constraints == {}

    def test_output_confidence_clamped(self):
        out = PrimitiveOutput(content="test", confidence=0.9)
        assert 0.0 <= out.confidence <= 1.0

    def test_trace_has_primitive_type(self):
        trace = PrimitiveTrace(primitive_type=PrimitiveType.PROPOSE)
        assert trace.primitive_type == PrimitiveType.PROPOSE
        assert trace.primitive_id  # UUID generated


class TestComposition:
    def test_composition_stores_steps(self):
        comp = Composition(
            name="test",
            steps=[
                CompositionStep(primitive_type=PrimitiveType.DECOMPOSE),
                CompositionStep(primitive_type=PrimitiveType.PROPOSE),
                CompositionStep(primitive_type=PrimitiveType.COMPRESS),
            ],
        )
        assert len(comp.steps) == 3
        assert comp.steps[0].primitive_type == PrimitiveType.DECOMPOSE

    def test_composition_serializes_to_json(self):
        comp = Composition(name="test", steps=[
            CompositionStep(primitive_type=PrimitiveType.SCORE),
        ])
        data = comp.model_dump()
        assert data["name"] == "test"
        assert len(data["steps"]) == 1

    def test_composition_tracks_lineage(self):
        parent = Composition(name="parent")
        child = Composition(name="child", parent_id=parent.composition_id, source="mutated")
        assert child.parent_id == parent.composition_id
        assert child.source == "mutated"
