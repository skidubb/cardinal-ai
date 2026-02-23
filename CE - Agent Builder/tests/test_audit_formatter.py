"""Tests for audit formatter — pure logic, no mocks needed."""

from csuite.formatters.audit_formatter import AuditFormatter, AuditMetrics


class TestAuditFormatter:
    def _make_formatter(self) -> AuditFormatter:
        return AuditFormatter(
            company_description="Acme Corp, a $12M professional services firm",
            revenue="$12M",
            employees=45,
            industry="Professional Services",
        )

    def test_add_section(self):
        f = self._make_formatter()
        f.add_section("Financial Analysis", "CFO", "Revenue looks strong.")
        assert len(f.sections) == 1
        assert f.sections[0].title == "Financial Analysis"
        assert f.sections[0].source_agent == "CFO"

    def test_set_synthesis(self):
        f = self._make_formatter()
        f.set_synthesis("All agents agree: invest in growth.")
        assert f.synthesis == "All agents agree: invest in growth."

    def test_set_metrics(self):
        f = self._make_formatter()
        m = AuditMetrics(
            total_cost=1.23, query_count=5,
            execution_time_minutes=2.5, cost_by_agent={"CFO": 0.8, "CMO": 0.43},
        )
        f.set_metrics(m)
        assert f.metrics is not None
        assert f.metrics.total_cost == 1.23

    def test_format_markdown_contains_header(self):
        f = self._make_formatter()
        f.add_section("Financial", "CFO", "Good margins.")
        f.set_synthesis("Invest now.")
        md = f.format_markdown()
        assert "# Growth Strategy Audit" in md
        assert "Acme Corp" in md
        assert "$12M" in md
        assert "45" in md
        assert "Professional Services" in md
        assert "Financial" in md
        assert "Good margins." in md
        assert "Invest now." in md
        assert "Cardinal Element" in md

    def test_format_markdown_with_metrics(self):
        f = self._make_formatter()
        f.set_synthesis("synth")
        f.set_metrics(AuditMetrics(
            total_cost=2.50, query_count=10,
            execution_time_minutes=3.0, cost_by_agent={"CFO": 1.5, "CTO": 1.0},
        ))
        md = f.format_markdown()
        assert "$2.50" in md
        assert "10" in md
        assert "3.0 minutes" in md
        assert "CFO" in md

    def test_format_markdown_without_metrics(self):
        f = self._make_formatter()
        f.set_synthesis("synth")
        md = f.format_markdown()
        assert "Audit Metrics" not in md

    def test_format_markdown_truncates_long_description(self):
        f = AuditFormatter(company_description="A" * 100)
        f.set_synthesis("synth")
        md = f.format_markdown()
        assert "..." in md

    def test_format_console_summary(self):
        f = self._make_formatter()
        f.add_section("Sec1", "CFO", "Content")
        f.add_section("Sec2", "CTO", "Content")
        f.set_synthesis("synth text")
        f.set_metrics(AuditMetrics(
            total_cost=0.5, query_count=3,
            execution_time_minutes=1.2, cost_by_agent={},
        ))
        summary = f.format_console_summary()
        assert summary["sections"] == 2
        assert summary["has_synthesis"] is True
        assert summary["metrics"]["cost"] == "$0.50"

    def test_format_console_summary_no_metrics(self):
        f = self._make_formatter()
        summary = f.format_console_summary()
        assert summary["metrics"]["cost"] == "N/A"

    def test_minimal_formatter(self):
        f = AuditFormatter(company_description="Test Co")
        f.set_synthesis("")
        md = f.format_markdown()
        assert "Test Co" in md
        assert "Annual Revenue" not in md
        assert "Employees" not in md
