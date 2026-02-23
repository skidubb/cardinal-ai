"""
Tests for Agent Cost Tracking (Directive D10).

Tests cover:
1. Cost calculation accuracy
2. Usage logging
3. Aggregation functions
4. Formula functions
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from csuite.tools.cost_tracker import (
    CostTracker,
    TaskType,
    UsageRecord,
    calculate_cost_per_audit,
    calculate_model_tier_cost,
    calculate_monthly_burn_rate,
)


class TestUsageRecord:
    """Tests for UsageRecord cost calculation."""

    def test_opus_cost_calculation(self):
        """Verify Opus pricing: $5/MTok input, $25/MTok output."""
        record = UsageRecord(
            agent="CFO",
            model="claude-opus-4-6",
            input_tokens=15000,  # 15K tokens
            output_tokens=3000,  # 3K tokens
        )

        # Expected: (15000 * 5 / 1M) + (3000 * 25 / 1M) = 0.075 + 0.075 = 0.15
        assert record.input_cost == pytest.approx(0.075, rel=0.01)
        assert record.output_cost == pytest.approx(0.075, rel=0.01)
        assert record.total_cost == pytest.approx(0.15, rel=0.01)

    def test_sonnet_cost_calculation(self):
        """Verify Sonnet pricing: $3/MTok input, $15/MTok output."""
        record = UsageRecord(
            agent="MARKET_RESEARCH",
            model="claude-sonnet-4-5-20250929",
            input_tokens=10000,
            output_tokens=5000,
        )

        # Expected: (10000 * 3 / 1M) + (5000 * 15 / 1M) = 0.03 + 0.075 = 0.105
        assert record.input_cost == pytest.approx(0.03, rel=0.01)
        assert record.output_cost == pytest.approx(0.075, rel=0.01)
        assert record.total_cost == pytest.approx(0.105, rel=0.01)

    def test_haiku_cost_calculation(self):
        """Verify Haiku pricing: $1/MTok input, $5/MTok output."""
        record = UsageRecord(
            agent="DATA_EXTRACTOR",
            model="claude-haiku-4-5-20251001",
            input_tokens=5000,
            output_tokens=2000,
        )

        # Expected: (5000 * 1 / 1M) + (2000 * 5 / 1M) = 0.005 + 0.01 = 0.015
        assert record.input_cost == pytest.approx(0.005, rel=0.01)
        assert record.output_cost == pytest.approx(0.01, rel=0.01)
        assert record.total_cost == pytest.approx(0.015, rel=0.01)

    def test_cache_discount(self):
        """Verify cache read tokens get 90% discount (0.1x rate)."""
        record = UsageRecord(
            agent="CFO",
            model="claude-opus-4-6",
            input_tokens=15000,
            output_tokens=3000,
            cached_tokens=10000,  # 10K of the 15K came from cache
        )

        # Non-cached: 5000 * 5 / 1M = 0.025
        # Cached: 10000 * 5 / 1M * 0.1 = 0.005
        # Total input: 0.025 + 0.005 = 0.03
        # Output: 3000 * 25 / 1M = 0.075
        # Total: 0.03 + 0.075 = 0.105

        assert record.input_cost == pytest.approx(0.03, rel=0.01)
        assert record.cache_savings == pytest.approx(0.045, rel=0.01)  # What we saved
        assert record.total_cost == pytest.approx(0.105, rel=0.01)

    def test_batch_discount(self):
        """Verify batch API gets 50% discount."""
        record = UsageRecord(
            agent="RESEARCHER",
            model="claude-sonnet-4-5-20250929",
            input_tokens=10000,
            output_tokens=5000,
            is_batch=True,
        )

        # Without batch: 0.03 + 0.075 = 0.105
        # With batch: 0.105 * 0.5 = 0.0525
        assert record.total_cost == pytest.approx(0.0525, rel=0.01)

    def test_model_fallback_pricing(self):
        """Verify substring matching for model variants."""
        # Should match "opus" substring
        record = UsageRecord(
            agent="CFO",
            model="claude-opus-4-6-extended",  # Hypothetical variant
            input_tokens=1000,
            output_tokens=1000,
        )

        # Should use Opus pricing
        expected = (1000 * 5 / 1_000_000) + (1000 * 25 / 1_000_000)
        assert record.total_cost == pytest.approx(expected, rel=0.01)


class TestCostTracker:
    """Tests for CostTracker functionality."""

    @pytest.fixture
    def temp_tracker(self):
        """Create a tracker with temporary data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(data_dir=Path(tmpdir))
            yield tracker

    def test_log_usage(self, temp_tracker):
        """Test logging a usage record."""
        record = temp_tracker.log_usage(
            agent="CFO",
            model="claude-opus-4-6",
            input_tokens=15000,
            output_tokens=3000,
            task_type=TaskType.EXECUTIVE_SYNTHESIS,
            session_id="test-session-001",
        )

        assert record.agent == "CFO"
        assert record.model == "claude-opus-4-6"
        assert record.total_cost > 0

    def test_get_daily_metrics(self, temp_tracker):
        """Test daily metrics aggregation."""
        # Log some usage
        for i in range(5):
            temp_tracker.log_usage(
                agent="CFO",
                model="claude-opus-4-6",
                input_tokens=15000,
                output_tokens=3000,
            )

        metrics = temp_tracker.get_daily_metrics()

        assert metrics.total_queries == 5
        assert metrics.total_input_tokens == 75000
        assert metrics.total_output_tokens == 15000
        assert metrics.total_cost > 0

    def test_get_metrics_by_agent(self, temp_tracker):
        """Test metrics breakdown by agent."""
        # Log usage for different agents
        temp_tracker.log_usage(agent="CFO", model="claude-opus-4-6", input_tokens=10000, output_tokens=2000)
        temp_tracker.log_usage(agent="CFO", model="claude-opus-4-6", input_tokens=10000, output_tokens=2000)
        temp_tracker.log_usage(agent="CTO", model="claude-opus-4-6", input_tokens=10000, output_tokens=2000)

        metrics = temp_tracker.get_daily_metrics()

        assert "CFO" in metrics.cost_by_agent
        assert "CTO" in metrics.cost_by_agent
        assert metrics.queries_by_agent["CFO"] == 2
        assert metrics.queries_by_agent["CTO"] == 1

    def test_generate_weekly_report(self, temp_tracker):
        """Test report generation."""
        temp_tracker.log_usage(
            agent="CFO",
            model="claude-opus-4-6",
            input_tokens=15000,
            output_tokens=3000,
        )

        report = temp_tracker.generate_weekly_report()

        assert "Agent Cost Report" in report
        assert "CFO" in report
        assert "$" in report

    def test_export_for_dashboard(self, temp_tracker):
        """Test dashboard export format."""
        temp_tracker.log_usage(
            agent="CFO",
            model="claude-opus-4-6",
            input_tokens=15000,
            output_tokens=3000,
        )

        export = temp_tracker.export_for_dashboard()

        assert "generated_at" in export
        assert "metrics" in export
        assert "daily" in export["metrics"]
        assert "weekly" in export["metrics"]
        assert "thresholds" in export


class TestCostFormulas:
    """Tests for formula functions from CFO-Agent-Economics.md."""

    def test_calculate_cost_per_audit_default(self):
        """Test default audit cost calculation."""
        result = calculate_cost_per_audit()

        # From CFO-Agent-Economics.md: target is $4.75 optimized
        assert result["optimized_cost"] == pytest.approx(4.75, rel=0.20)  # Allow 20% variance
        assert "breakdown" in result
        assert "opus" in result["breakdown"]
        assert "sonnet" in result["breakdown"]
        assert "haiku" in result["breakdown"]

    def test_calculate_cost_per_audit_no_optimization(self):
        """Test audit cost without caching/batch."""
        result = calculate_cost_per_audit(cache_pct=0, batch_pct=0)

        # Should be higher without optimizations
        assert result["optimized_cost"] == result["gross_cost"]
        assert result["cache_savings"] == 0
        assert result["batch_savings"] == 0

    def test_calculate_monthly_burn_rate(self):
        """Test monthly burn rate calculation."""
        result = calculate_monthly_burn_rate(
            audits_per_month=4,
            retainers_per_month=2,
            ad_hoc_queries_per_month=50,
            content_pieces_per_month=10,
        )

        # From CFO-Agent-Economics.md: Moderate scenario ~$60-80/mo
        assert result["monthly_total"] < 150  # Should be well under $150
        assert "breakdown" in result
        assert "comparison" in result
        assert result["comparison"]["savings_pct"] > 99  # Should be >99% savings

    def test_calculate_model_tier_cost_opus(self):
        """Test per-query cost calculation for Opus."""
        result = calculate_model_tier_cost(
            model_tier="opus",
            input_tokens=15000,
            output_tokens=3000,
        )

        # From CFO-Agent-Economics.md: ~$0.225 per executive query
        assert result["total_cost"] == pytest.approx(0.15, rel=0.10)
        assert result["model_tier"] == "opus"

    def test_calculate_model_tier_cost_with_cache(self):
        """Test cost reduction with cache."""
        without_cache = calculate_model_tier_cost(
            model_tier="opus",
            input_tokens=15000,
            output_tokens=3000,
            cached_tokens=0,
        )

        with_cache = calculate_model_tier_cost(
            model_tier="opus",
            input_tokens=15000,
            output_tokens=3000,
            cached_tokens=10000,
        )

        assert with_cache["total_cost"] < without_cache["total_cost"]
        assert with_cache["discounts_applied"]["cache"] is True


class TestAlertThresholds:
    """Tests for alert and threshold functionality."""

    @pytest.fixture
    def temp_tracker(self):
        """Create a tracker with temporary data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(data_dir=Path(tmpdir))
            yield tracker

    def test_high_cost_query_alert(self, temp_tracker):
        """Test alert triggered for expensive query."""
        # Log a very expensive query (>$2 threshold)
        temp_tracker.log_usage(
            agent="CFO",
            model="claude-opus-4-6",
            input_tokens=100000,  # 100K input = $0.50
            output_tokens=100000,  # 100K output = $2.50
        )

        alerts = temp_tracker.get_alerts()

        # Should have at least one alert for high cost
        high_cost_alerts = [a for a in alerts if a.alert_type == "high_cost_query"]
        assert len(high_cost_alerts) >= 1

    def test_thresholds_configurable(self, temp_tracker):
        """Test that thresholds match CFO-Agent-Economics.md specs."""
        assert temp_tracker.thresholds["single_query_cost"] == 2.00
        assert temp_tracker.thresholds["daily_spend"] == 10.00
        assert temp_tracker.thresholds["cache_hit_rate_min"] == 0.10
        assert temp_tracker.thresholds["cost_per_audit_target"] == 4.75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
