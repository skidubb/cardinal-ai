"""Tests for api/routers/runs.py — request schema validation."""

from pydantic import ValidationError
import pytest


def test_protocol_run_request_accepts_no_tools():
    from api.routers.runs import ProtocolRunRequest
    req = ProtocolRunRequest(
        protocol_key="p03_parallel_synthesis",
        question="Test question",
        agent_keys=["ceo", "cfo"],
        no_tools=True,
    )
    assert req.no_tools is True


def test_protocol_run_request_no_tools_defaults_false():
    from api.routers.runs import ProtocolRunRequest
    req = ProtocolRunRequest(
        protocol_key="p03_parallel_synthesis",
        question="Test question",
        agent_keys=["ceo", "cfo"],
    )
    assert req.no_tools is False


def test_pipeline_step_request_accepts_no_tools():
    from api.routers.runs import PipelineStepRequest
    req = PipelineStepRequest(
        protocol_key="p06_triz",
        question_template="Analyze: {prev_output}",
        no_tools=True,
    )
    assert req.no_tools is True


def test_pipeline_step_request_no_tools_defaults_false():
    from api.routers.runs import PipelineStepRequest
    req = PipelineStepRequest(
        protocol_key="p06_triz",
        question_template="Question",
    )
    assert req.no_tools is False


def test_protocol_run_request_requires_fields():
    from api.routers.runs import ProtocolRunRequest
    with pytest.raises(ValidationError):
        ProtocolRunRequest()
