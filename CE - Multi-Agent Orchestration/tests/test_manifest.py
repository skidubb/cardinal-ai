"""Tests for api/manifest.py — protocol discovery and tools_enabled field."""

from api.manifest import get_protocol_manifest


def test_manifest_returns_all_protocols():
    manifest = get_protocol_manifest()
    assert len(manifest) >= 48, f"Expected 48+ protocols, got {len(manifest)}"


def test_manifest_protocol_has_required_fields():
    manifest = get_protocol_manifest()
    required = {"key", "protocol_id", "name", "category", "problem_types",
                "cost_tier", "min_agents", "max_agents", "supports_rounds",
                "description", "when_to_use", "when_not_to_use", "tools_enabled"}
    for p in manifest:
        missing = required - set(p.keys())
        assert not missing, f"Protocol {p.get('key')} missing fields: {missing}"


def test_tools_enabled_present_on_all_protocols():
    manifest = get_protocol_manifest()
    for p in manifest:
        assert "tools_enabled" in p, f"Protocol {p['key']} missing tools_enabled"
        assert isinstance(p["tools_enabled"], bool), f"Protocol {p['key']} tools_enabled is not bool"


def test_meta_protocols_have_tools_disabled():
    manifest = get_protocol_manifest()
    meta = [p for p in manifest if p["key"].startswith("p0") and not p["key"][2:3].isdigit()]
    assert len(meta) == 3, f"Expected 3 meta-protocols (p0a/b/c), got {len(meta)}: {[p['key'] for p in meta]}"
    for p in meta:
        assert p["tools_enabled"] is False, f"Meta-protocol {p['key']} should have tools_enabled=False"


def test_non_meta_protocols_have_tools_enabled():
    manifest = get_protocol_manifest()
    non_meta = [p for p in manifest if not p["key"].startswith("p0") or p["key"][2:3].isdigit()]
    assert len(non_meta) >= 45
    for p in non_meta:
        assert p["tools_enabled"] is True, f"Protocol {p['key']} should have tools_enabled=True"


def test_problem_types_are_lists():
    manifest = get_protocol_manifest()
    for p in manifest:
        assert isinstance(p["problem_types"], list), f"Protocol {p['key']} problem_types is not a list"


def test_known_problem_types():
    manifest = get_protocol_manifest()
    all_types = set()
    for p in manifest:
        all_types.update(p["problem_types"])
    expected = {"Diagnostic", "General Analysis", "Exploration", "Multi-Stakeholder",
                "Adversarial", "Systems Analysis", "Prioritization", "Constraint Definition",
                "Estimation", "Portfolio Management"}
    assert all_types == expected, f"Unexpected problem types: {all_types - expected}"
