"""Tests for anonymization and metadata stripping."""

from ce_evals.protocols.blind import anonymize, strip_metadata


def test_anonymize_labels_and_shuffles():
    responses = {"proto_a": "output A", "proto_b": "output B", "proto_c": "output C"}
    labeled, mapping = anonymize(responses)

    # Should have same count
    assert len(labeled) == 3
    assert len(mapping) == 3

    # Labels should be Response A, B, C
    labels = {label for label, _ in labeled}
    assert labels == {"Response A", "Response B", "Response C"}

    # Mapping should map labels back to original names
    assert set(mapping.values()) == set(responses.keys())

    # Each labeled text should match one of the original outputs
    for label, text in labeled:
        original_name = mapping[label]
        assert text == responses[original_name]


def test_strip_metadata_removes_protocol_markers():
    text = "ACH analysis: The debate mode suggests a round-robin approach."
    cleaned = strip_metadata(text)
    assert "ACH" not in cleaned
    assert "debate" not in cleaned.lower() or "mode" not in cleaned.lower()


def test_strip_metadata_preserves_normal_text():
    text = "The company should expand into new markets to increase revenue."
    cleaned = strip_metadata(text)
    assert "expand into new markets" in cleaned


def test_strip_metadata_custom_patterns():
    text = "SECRET_MARKER: this should be removed. Normal text stays."
    cleaned = strip_metadata(text, patterns=[r"SECRET_MARKER:\s*[^.]+\."])
    assert "SECRET_MARKER" not in cleaned
    assert "Normal text stays" in cleaned
