"""Run auditor — stage-by-stage observed-vs-intended for every run.

Supplemental to the core result adapter. Produces a human-readable summary
of what a run was supposed to do and what it actually produced, so the user
can always see whether they're looking at a complete answer or a slice.

Phase A (this module): scaffolding + auto-detection from the Result dataclass.
Phase B (follow-up): consume declarative `stages:` from capability.yaml and
apply advice rules based on gaps.

Audit is purely additive — never blocks a run, never rewrites the summary.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Literal


StageStatus = Literal["ok", "missing", "partial", "degraded", "implicit", "unknown"]


@dataclass(slots=True)
class StageAudit:
    """Observed-vs-intended result for one stage of a protocol."""

    name: str
    intent: str = ""
    status: StageStatus = "unknown"
    observed: str = ""
    advice: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "intent": self.intent,
            "status": self.status,
            "observed": self.observed,
            "advice": self.advice,
        }


@dataclass(slots=True)
class RunAudit:
    """Full audit for a single run."""

    stages: list[StageAudit] = field(default_factory=list)
    completeness: str = ""
    overall_advice: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "stages": [s.as_dict() for s in self.stages],
            "completeness": self.completeness,
            "overall_advice": self.overall_advice,
        }

    @property
    def is_empty(self) -> bool:
        return not self.stages


# Fields that are never a "stage output" worth auditing — bookkeeping only.
_AUDIT_BLOCKLIST: frozenset[str] = frozenset({
    "question",
    "time_horizon",
    "timings",
    "model_calls",
    "cost",
    "raw_output",
})


def _field_populated(value: Any) -> bool:
    """True if the field holds meaningful output (non-empty str/list/dict/num)."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    if isinstance(value, (int, float)):
        return value != 0
    return True


def _prettify(name: str) -> str:
    return name.replace("_", " ").title()


def audit_run(protocol_key: str, result: Any, manifest_stages: list[dict] | None = None) -> RunAudit:
    """Produce a RunAudit by inspecting the result against stage expectations.

    If `manifest_stages` is provided (from capability.yaml's `stages:` key),
    audit against each declared stage. Otherwise, auto-detect non-blocklisted
    populated fields and report their status.
    """
    if manifest_stages:
        return _audit_with_manifest(result, manifest_stages)
    return _audit_auto(result)


def _audit_with_manifest(result: Any, manifest_stages: list[dict]) -> RunAudit:
    """Audit each declared stage against the actual result fields."""
    stages: list[StageAudit] = []
    populated_count = 0
    total_required = 0

    for stage in manifest_stages:
        name = stage.get("name", "")
        intent = stage.get("description", "")
        implicit = bool(stage.get("implicit", False))
        required = bool(stage.get("required", True))
        produces = stage.get("produces")

        if implicit:
            stages.append(StageAudit(
                name=name,
                intent=intent,
                status="implicit",
                observed="Framed in the agent prompt; no runtime step",
            ))
            continue

        if required:
            total_required += 1

        produces_fields = [produces] if isinstance(produces, str) else list(produces or [])
        produced: list[str] = []
        missing: list[str] = []
        for field_name in produces_fields:
            if field_name and _field_populated(_getattr_or_key(result, field_name)):
                produced.append(field_name)
            elif field_name:
                missing.append(field_name)

        if produced and not missing:
            status: StageStatus = "ok"
            observed = "Produced: " + ", ".join(produced) if produces_fields else "Produced"
            populated_count += 1
        elif produced and missing:
            status = "partial"
            observed = f"Partial — produced {', '.join(produced)}; missing {', '.join(missing)}"
        elif not produces_fields:
            status = "unknown"
            observed = "No `produces` declared in manifest"
        else:
            status = "missing"
            observed = f"Expected field(s) empty: {', '.join(missing)}"

        advice = None
        if status == "missing" and required:
            advice = "Stage appears to have failed — re-check logs for errors."

        stages.append(StageAudit(
            name=name,
            intent=intent,
            status=status,
            observed=observed,
            advice=advice,
        ))

    completeness = f"{populated_count} / {total_required} required stages produced output" if total_required else ""
    overall = None
    if total_required and populated_count == 0:
        overall = "No required stages produced output — investigate before trusting results."
    elif total_required and populated_count < total_required:
        overall = f"{total_required - populated_count} stage(s) missing output. See details above."

    return RunAudit(stages=stages, completeness=completeness, overall_advice=overall)


def _audit_auto(result: Any) -> RunAudit:
    """Auto-detect stages by walking the result dataclass fields.

    Conservative: emits one StageAudit per non-blocklisted populated field,
    labeled by the field's cleaned-up name. No advice.
    """
    stages: list[StageAudit] = []

    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        items: list[tuple[str, Any]] = [(f.name, getattr(result, f.name)) for f in dataclasses.fields(result)]
    elif isinstance(result, dict):
        items = list(result.items())
    else:
        return RunAudit(stages=[], completeness="Result has no introspectable fields.")

    for name, value in items:
        if name in _AUDIT_BLOCKLIST:
            continue
        populated = _field_populated(value)
        if not populated:
            continue
        observed = _describe_field_value(value)
        stages.append(StageAudit(
            name=_prettify(name),
            intent="",
            status="ok",
            observed=observed,
        ))

    return RunAudit(
        stages=stages,
        completeness=f"{len(stages)} output field(s) populated",
    )


def _getattr_or_key(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _describe_field_value(value: Any) -> str:
    if isinstance(value, str):
        preview = value[:80].replace("\n", " ")
        tail = "…" if len(value) > 80 else ""
        return f"{len(value)} chars: \"{preview}{tail}\""
    if isinstance(value, list):
        return f"{len(value)} item(s)"
    if isinstance(value, dict):
        return f"{len(value)} key(s): {', '.join(list(value.keys())[:4])}"
    return str(value)[:120]
