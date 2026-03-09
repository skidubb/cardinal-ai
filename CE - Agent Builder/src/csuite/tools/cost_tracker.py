"""
Agent Cost Tracking Module for Cardinal Element C-Suite.

Implements Directive D10: Track and analyze AI agent labor costs with the same
rigor as human payroll. This module provides:

1. API usage logging with per-query cost calculation
2. Cost aggregation by agent, task type, and time period
3. Trend analysis and anomaly detection
4. Export capabilities for dashboard integration

Cost Model (February 2026 Anthropic Pricing):
- Opus 4.6: $5/MTok input, $25/MTok output
- Sonnet 4.5: $3/MTok input, $15/MTok output
- Haiku 4.5: $1/MTok input, $5/MTok output

See: /Users/scottewalt/Documents/CE - C-Suite/Strategy Meeting/CFO-Agent-Economics.md
"""

import json
import os
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ce_shared.pricing import (
    BATCH_DISCOUNT,
    CACHE_READ_MULTIPLIER,
    CACHE_WRITE_MULTIPLIER,
    MODEL_PRICING,
    ModelTier,
    get_pricing,
)


# =============================================================================
# Task Type Classification
# =============================================================================

class TaskType(StrEnum):
    """Standard task types for cost tracking."""
    EXECUTIVE_SYNTHESIS = "executive_synthesis"
    EXECUTIVE_DEBATE = "executive_debate"
    INDUSTRY_RESEARCH = "industry_research"
    COMPETITIVE_ANALYSIS = "competitive_analysis"
    FINANCIAL_MODELING = "financial_modeling"
    CONTENT_GENERATION = "content_generation"
    DATA_EXTRACTION = "data_extraction"
    QA_REVIEW = "qa_review"
    AD_HOC_QUERY = "ad_hoc_query"
    INTERACTIVE_SESSION = "interactive_session"


# Expected token ranges per task type (for anomaly detection)
TASK_TOKEN_BENCHMARKS = {
    TaskType.EXECUTIVE_SYNTHESIS: {"input": (10000, 20000), "output": (2000, 5000)},
    TaskType.EXECUTIVE_DEBATE: {"input": (15000, 60000), "output": (2000, 6000)},
    TaskType.INDUSTRY_RESEARCH: {"input": (8000, 16000), "output": (5000, 12000)},
    TaskType.COMPETITIVE_ANALYSIS: {"input": (6000, 14000), "output": (4000, 8000)},
    TaskType.FINANCIAL_MODELING: {"input": (5000, 12000), "output": (3000, 7000)},
    TaskType.CONTENT_GENERATION: {"input": (4000, 10000), "output": (6000, 15000)},
    TaskType.DATA_EXTRACTION: {"input": (3000, 8000), "output": (1000, 4000)},
    TaskType.QA_REVIEW: {"input": (6000, 15000), "output": (2000, 6000)},
    TaskType.AD_HOC_QUERY: {"input": (1000, 20000), "output": (500, 8000)},
    TaskType.INTERACTIVE_SESSION: {"input": (500, 50000), "output": (200, 15000)},
}


# =============================================================================
# Data Models
# =============================================================================

class UsageRecord(BaseModel):
    """Single API usage record with cost calculation."""

    timestamp: datetime = Field(default_factory=datetime.now)
    agent: str  # CFO, CTO, CMO, COO, CEO, CPO, or sub-agent name
    model: str  # Full model ID
    task_type: TaskType = TaskType.AD_HOC_QUERY

    # Token counts
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0  # Tokens read from cache (at 0.1x rate)

    # Cost calculation (computed)
    input_cost: float = 0.0
    output_cost: float = 0.0
    cache_savings: float = 0.0
    total_cost: float = 0.0

    # Batch API flag
    is_batch: bool = False

    # Optional metadata
    session_id: str | None = None
    audit_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Calculate costs after initialization."""
        self._calculate_costs()

    def _calculate_costs(self) -> None:
        """Calculate costs based on token usage and model."""
        pricing = self._get_pricing()

        # Base costs per token
        input_rate = pricing["input"] / 1_000_000
        output_rate = pricing["output"] / 1_000_000

        # Calculate input cost (excluding cached tokens)
        non_cached_input = max(0, self.input_tokens - self.cached_tokens)
        self.input_cost = non_cached_input * input_rate

        # Add cached token cost at 0.1x rate
        cached_cost = self.cached_tokens * input_rate * CACHE_READ_MULTIPLIER
        self.input_cost += cached_cost

        # Calculate cache savings (what we would have paid at full rate)
        self.cache_savings = self.cached_tokens * input_rate * (1 - CACHE_READ_MULTIPLIER)

        # Output cost
        self.output_cost = self.output_tokens * output_rate

        # Apply batch discount if applicable
        if self.is_batch:
            self.input_cost *= (1 - BATCH_DISCOUNT)
            self.output_cost *= (1 - BATCH_DISCOUNT)

        # Total
        self.total_cost = self.input_cost + self.output_cost

    def _get_pricing(self) -> dict[str, float]:
        """Get pricing for this record's model.

        Delegates to ce_shared.pricing.get_pricing() which handles exact match,
        substring fallback, and conservative defaults.
        """
        input_rate, output_rate = get_pricing(self.model)
        return {"input": input_rate, "output": output_rate}


class AggregatedMetrics(BaseModel):
    """Aggregated metrics for a time period."""

    period_start: datetime
    period_end: datetime

    # Volume metrics
    total_queries: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0

    # Cost metrics
    total_cost: float = 0.0
    total_cache_savings: float = 0.0

    # Efficiency metrics
    avg_cost_per_query: float = 0.0
    avg_input_tokens: float = 0.0
    avg_output_tokens: float = 0.0
    efficiency_ratio: float = 0.0  # output_tokens / input_tokens
    cache_hit_rate: float = 0.0  # cached_tokens / input_tokens

    # Breakdown by agent
    cost_by_agent: dict[str, float] = Field(default_factory=dict)
    queries_by_agent: dict[str, int] = Field(default_factory=dict)

    # Breakdown by task type
    cost_by_task_type: dict[str, float] = Field(default_factory=dict)
    queries_by_task_type: dict[str, int] = Field(default_factory=dict)

    # Breakdown by model
    cost_by_model: dict[str, float] = Field(default_factory=dict)
    queries_by_model: dict[str, int] = Field(default_factory=dict)


class CostAlert(BaseModel):
    """Cost anomaly alert."""

    timestamp: datetime = Field(default_factory=datetime.now)
    alert_type: str  # "high_cost_query", "daily_budget_exceeded", "low_cache_rate", etc.
    severity: str  # "info", "warning", "critical"
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    acknowledged: bool = False


# =============================================================================
# Cost Tracker Core
# =============================================================================

class CostTracker:
    """
    Core cost tracking engine for AI agent labor costs.

    Provides:
    - Real-time cost logging
    - Aggregation and analysis
    - Anomaly detection and alerts
    - Export for dashboard integration

    Usage:
        tracker = CostTracker()

        # Log a query
        tracker.log_usage(
            agent="CFO",
            model="claude-opus-4-6",
            input_tokens=15234,
            output_tokens=3128,
            task_type=TaskType.EXECUTIVE_SYNTHESIS,
        )

        # Get weekly metrics
        metrics = tracker.get_weekly_metrics()

        # Check for alerts
        alerts = tracker.check_alerts()
    """

    def __init__(self, data_dir: Path | None = None):
        """
        Initialize cost tracker.

        Args:
            data_dir: Directory for cost data storage. Defaults to ./cost_data
        """
        if data_dir is None:
            # Use project root's cost_data directory
            project_root = Path(os.environ.get(
                "CSUITE_PROJECT_ROOT",
                Path(__file__).parent.parent.parent.parent
            ))
            data_dir = project_root / "cost_data"

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Subdirectories
        self.records_dir = self.data_dir / "records"
        self.aggregates_dir = self.data_dir / "aggregates"
        self.alerts_dir = self.data_dir / "alerts"

        for d in [self.records_dir, self.aggregates_dir, self.alerts_dir]:
            d.mkdir(exist_ok=True)

        # Alert thresholds (from CFO-Agent-Economics.md Section 4.4)
        self.thresholds = {
            "single_query_cost": 2.00,  # Alert if query > $2
            "daily_spend": 10.00,  # Alert if daily > $10
            "cache_hit_rate_min": 0.10,  # Alert if cache rate < 10%
            "efficiency_ratio_max": 1.50,  # Alert if output/input > 1.5
            "cost_per_audit_target": 4.75,  # From economics analysis
            "cost_per_audit_alert": 7.00,  # 47% above target
        }

    # =========================================================================
    # Logging
    # =========================================================================

    def log_usage(
        self,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        task_type: TaskType | str = TaskType.AD_HOC_QUERY,
        cached_tokens: int = 0,
        is_batch: bool = False,
        session_id: str | None = None,
        audit_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UsageRecord:
        """
        Log a single API usage event.

        Args:
            agent: Agent name (CFO, CTO, etc.)
            model: Model ID used
            input_tokens: Input token count
            output_tokens: Output token count
            task_type: Type of task performed
            cached_tokens: Tokens read from cache
            is_batch: Whether batch API was used
            session_id: Optional session ID
            audit_id: Optional audit/project ID
            metadata: Additional metadata

        Returns:
            The created UsageRecord with calculated costs
        """
        if isinstance(task_type, str):
            try:
                task_type = TaskType(task_type)
            except ValueError:
                task_type = TaskType.AD_HOC_QUERY

        record = UsageRecord(
            agent=agent.upper(),
            model=model,
            task_type=task_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            is_batch=is_batch,
            session_id=session_id,
            audit_id=audit_id,
            metadata=metadata or {},
        )

        # Persist record
        self._save_record(record)

        # Check for anomalies
        self._check_record_anomalies(record)

        return record

    def _save_record(self, record: UsageRecord) -> None:
        """Save a usage record to disk."""
        # Organize by date
        date_str = record.timestamp.strftime("%Y-%m-%d")
        day_file = self.records_dir / f"{date_str}.jsonl"

        with open(day_file, "a") as f:
            f.write(record.model_dump_json() + "\n")

    def _load_records(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[UsageRecord]:
        """Load records for a date range."""
        records = []

        if start_date is None:
            start_date = datetime.now() - timedelta(days=90)
        if end_date is None:
            end_date = datetime.now()

        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            day_file = self.records_dir / f"{date_str}.jsonl"

            if day_file.exists():
                with open(day_file) as f:
                    for line in f:
                        if line.strip():
                            records.append(UsageRecord.model_validate_json(line))

            current += timedelta(days=1)

        return records

    # =========================================================================
    # Aggregation
    # =========================================================================

    def get_metrics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> AggregatedMetrics:
        """
        Get aggregated metrics for a time period.

        Args:
            start_date: Period start (default: 7 days ago)
            end_date: Period end (default: now)

        Returns:
            Aggregated metrics with breakdowns
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()

        records = self._load_records(start_date, end_date)

        if not records:
            return AggregatedMetrics(
                period_start=start_date,
                period_end=end_date,
            )

        # Initialize aggregates
        metrics = AggregatedMetrics(
            period_start=start_date,
            period_end=end_date,
            total_queries=len(records),
        )

        # Aggregate
        for r in records:
            metrics.total_input_tokens += r.input_tokens
            metrics.total_output_tokens += r.output_tokens
            metrics.total_cached_tokens += r.cached_tokens
            metrics.total_cost += r.total_cost
            metrics.total_cache_savings += r.cache_savings

            # By agent
            agent = r.agent
            metrics.cost_by_agent[agent] = metrics.cost_by_agent.get(agent, 0) + r.total_cost
            metrics.queries_by_agent[agent] = metrics.queries_by_agent.get(agent, 0) + 1

            # By task type
            task = r.task_type.value
            metrics.cost_by_task_type[task] = metrics.cost_by_task_type.get(task, 0) + r.total_cost
            metrics.queries_by_task_type[task] = metrics.queries_by_task_type.get(task, 0) + 1

            # By model
            model = r.model
            metrics.cost_by_model[model] = metrics.cost_by_model.get(model, 0) + r.total_cost
            metrics.queries_by_model[model] = metrics.queries_by_model.get(model, 0) + 1

        # Calculate averages
        if metrics.total_queries > 0:
            metrics.avg_cost_per_query = metrics.total_cost / metrics.total_queries
            metrics.avg_input_tokens = metrics.total_input_tokens / metrics.total_queries
            metrics.avg_output_tokens = metrics.total_output_tokens / metrics.total_queries

        if metrics.total_input_tokens > 0:
            metrics.efficiency_ratio = metrics.total_output_tokens / metrics.total_input_tokens
            metrics.cache_hit_rate = metrics.total_cached_tokens / metrics.total_input_tokens

        return metrics

    def get_daily_metrics(self, date: datetime | None = None) -> AggregatedMetrics:
        """Get metrics for a specific day."""
        if date is None:
            date = datetime.now()
        start = datetime(date.year, date.month, date.day)
        end = start + timedelta(days=1) - timedelta(seconds=1)
        return self.get_metrics(start, end)

    def get_weekly_metrics(self, end_date: datetime | None = None) -> AggregatedMetrics:
        """Get metrics for the past 7 days."""
        if end_date is None:
            end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        return self.get_metrics(start_date, end_date)

    def get_monthly_metrics(self, end_date: datetime | None = None) -> AggregatedMetrics:
        """Get metrics for the past 30 days."""
        if end_date is None:
            end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        return self.get_metrics(start_date, end_date)

    # =========================================================================
    # Cost Per Deliverable
    # =========================================================================

    def get_cost_per_audit(self, audit_id: str) -> dict[str, Any]:
        """
        Calculate total cost for a specific audit.

        Args:
            audit_id: The audit identifier

        Returns:
            Cost breakdown for the audit
        """
        records = self._load_records()
        audit_records = [r for r in records if r.audit_id == audit_id]

        if not audit_records:
            return {"audit_id": audit_id, "found": False}

        total_cost = sum(r.total_cost for r in audit_records)
        total_tasks = len(audit_records)

        return {
            "audit_id": audit_id,
            "found": True,
            "total_cost": round(total_cost, 4),
            "total_tasks": total_tasks,
            "avg_cost_per_task": round(total_cost / total_tasks, 4) if total_tasks > 0 else 0,
            "cost_by_task_type": self._group_cost_by_task_type(audit_records),
            "cost_by_agent": self._group_cost_by_agent(audit_records),
            "vs_target": {
                "target": self.thresholds["cost_per_audit_target"],
                "actual": round(total_cost, 4),
                "delta": round(total_cost - self.thresholds["cost_per_audit_target"], 4),
                "delta_pct": round(
                    (total_cost / self.thresholds["cost_per_audit_target"] - 1) * 100, 1
                ),
            },
        }

    def _group_cost_by_task_type(self, records: list[UsageRecord]) -> dict[str, float]:
        """Group costs by task type."""
        result: dict[str, float] = {}
        for r in records:
            key = r.task_type.value
            result[key] = result.get(key, 0) + r.total_cost
        return {k: round(v, 4) for k, v in sorted(result.items(), key=lambda x: -x[1])}

    def _group_cost_by_agent(self, records: list[UsageRecord]) -> dict[str, float]:
        """Group costs by agent."""
        result: dict[str, float] = {}
        for r in records:
            result[r.agent] = result.get(r.agent, 0) + r.total_cost
        return {k: round(v, 4) for k, v in sorted(result.items(), key=lambda x: -x[1])}

    # =========================================================================
    # Trend Analysis
    # =========================================================================

    def get_trend_analysis(self, weeks: int = 4) -> dict[str, Any]:
        """
        Analyze cost trends over multiple weeks.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            Trend data with week-over-week comparisons
        """
        weekly_data = []
        end_date = datetime.now()

        for i in range(weeks):
            week_end = end_date - timedelta(weeks=i)
            week_start = week_end - timedelta(days=7)
            metrics = self.get_metrics(week_start, week_end)

            weekly_data.append({
                "week": i + 1,  # 1 = current week, 2 = last week, etc.
                "period": f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}",
                "total_cost": round(metrics.total_cost, 4),
                "total_queries": metrics.total_queries,
                "avg_cost_per_query": round(metrics.avg_cost_per_query, 4),
                "cache_hit_rate": round(metrics.cache_hit_rate * 100, 1),
            })

        # Calculate week-over-week changes
        for i in range(len(weekly_data) - 1):
            current = weekly_data[i]
            previous = weekly_data[i + 1]

            if previous["total_cost"] > 0:
                current["cost_wow_change"] = round(
                    (current["total_cost"] / previous["total_cost"] - 1) * 100, 1
                )
            else:
                current["cost_wow_change"] = None

            if previous["avg_cost_per_query"] > 0:
                current["avg_cost_wow_change"] = round(
                    (current["avg_cost_per_query"] / previous["avg_cost_per_query"] - 1) * 100, 1
                )
            else:
                current["avg_cost_wow_change"] = None

        return {
            "weeks_analyzed": weeks,
            "weekly_data": weekly_data,
            "summary": {
                "total_cost": round(sum(w["total_cost"] for w in weekly_data), 4),
                "total_queries": sum(w["total_queries"] for w in weekly_data),
                "trend_direction": self._calculate_trend_direction(weekly_data),
            },
        }

    def _calculate_trend_direction(self, weekly_data: list[dict]) -> str:
        """Determine if costs are increasing, decreasing, or stable."""
        if len(weekly_data) < 2:
            return "insufficient_data"

        costs = [w["total_cost"] for w in weekly_data]

        # Compare first half to second half
        mid = len(costs) // 2
        recent_avg = sum(costs[:mid]) / mid if mid > 0 else 0
        older_avg = sum(costs[mid:]) / (len(costs) - mid) if len(costs) - mid > 0 else 0

        if older_avg == 0:
            return "no_baseline"

        change = (recent_avg / older_avg - 1) * 100

        if change > 10:
            return "increasing"
        elif change < -10:
            return "decreasing"
        else:
            return "stable"

    # =========================================================================
    # Anomaly Detection
    # =========================================================================

    def _check_record_anomalies(self, record: UsageRecord) -> None:
        """Check a single record for anomalies."""
        # High cost query
        if record.total_cost > self.thresholds["single_query_cost"]:
            self._create_alert(
                alert_type="high_cost_query",
                severity="warning",
                message=(
                    f"High-cost query detected: ${record.total_cost:.4f}"
                    f" (threshold: ${self.thresholds['single_query_cost']:.2f})"
                ),
                details={
                    "agent": record.agent,
                    "model": record.model,
                    "cost": record.total_cost,
                    "input_tokens": record.input_tokens,
                    "output_tokens": record.output_tokens,
                    "task_type": record.task_type.value,
                },
            )

        # High efficiency ratio (possible inefficient prompting)
        if record.input_tokens > 0:
            ratio = record.output_tokens / record.input_tokens
            if ratio > self.thresholds["efficiency_ratio_max"]:
                self._create_alert(
                    alert_type="high_efficiency_ratio",
                    severity="info",
                    message=(
                        f"High output/input ratio: {ratio:.2f}"
                        f" (threshold: {self.thresholds['efficiency_ratio_max']:.2f})"
                    ),
                    details={
                        "agent": record.agent,
                        "ratio": ratio,
                        "input_tokens": record.input_tokens,
                        "output_tokens": record.output_tokens,
                    },
                )

    def check_daily_budget(self) -> CostAlert | None:
        """Check if daily budget has been exceeded."""
        daily = self.get_daily_metrics()

        if daily.total_cost > self.thresholds["daily_spend"]:
            alert = self._create_alert(
                alert_type="daily_budget_exceeded",
                severity="critical",
                message=(
                    f"Daily spend exceeded: ${daily.total_cost:.4f}"
                    f" (threshold: ${self.thresholds['daily_spend']:.2f})"
                ),
                details={
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "total_cost": daily.total_cost,
                    "query_count": daily.total_queries,
                },
            )
            return alert
        return None

    def check_cache_efficiency(self) -> CostAlert | None:
        """Check if cache hit rate is below threshold."""
        weekly = self.get_weekly_metrics()

        cache_min = self.thresholds["cache_hit_rate_min"]
        if weekly.total_queries > 10 and weekly.cache_hit_rate < cache_min:
            alert = self._create_alert(
                alert_type="low_cache_rate",
                severity="warning",
                message=(
                    f"Low cache hit rate: {weekly.cache_hit_rate*100:.1f}%"
                    f" (threshold: {cache_min*100:.0f}%)"
                ),
                details={
                    "cache_hit_rate": weekly.cache_hit_rate,
                    "potential_savings": weekly.total_cost * 0.20,  # Estimate 20% savings possible
                },
            )
            return alert
        return None

    def _create_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        details: dict[str, Any],
    ) -> CostAlert:
        """Create and save an alert."""
        alert = CostAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            details=details,
        )

        # Save alert
        date_str = alert.timestamp.strftime("%Y-%m-%d")
        alert_file = self.alerts_dir / f"{date_str}.jsonl"

        with open(alert_file, "a") as f:
            f.write(alert.model_dump_json() + "\n")

        return alert

    def get_alerts(
        self,
        start_date: datetime | None = None,
        unacknowledged_only: bool = False,
    ) -> list[CostAlert]:
        """Get alerts for review."""
        alerts = []

        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)

        current = start_date
        while current <= datetime.now():
            date_str = current.strftime("%Y-%m-%d")
            alert_file = self.alerts_dir / f"{date_str}.jsonl"

            if alert_file.exists():
                with open(alert_file) as f:
                    for line in f:
                        if line.strip():
                            alert = CostAlert.model_validate_json(line)
                            if not unacknowledged_only or not alert.acknowledged:
                                alerts.append(alert)

            current += timedelta(days=1)

        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)

    # =========================================================================
    # Reporting
    # =========================================================================

    def generate_weekly_report(self) -> str:
        """Generate a weekly cost report in markdown format."""
        metrics = self.get_weekly_metrics()
        trends = self.get_trend_analysis(weeks=4)
        alerts = self.get_alerts(unacknowledged_only=True)

        report = f"""# Agent Cost Report - Week of {datetime.now().strftime('%Y-%m-%d')}

## Summary

| Metric | Value |
|--------|-------|
| Total Spend | ${metrics.total_cost:.4f} |
| Total Queries | {metrics.total_queries} |
| Avg Cost/Query | ${metrics.avg_cost_per_query:.4f} |
| Cache Hit Rate | {metrics.cache_hit_rate*100:.1f}% |
| Cache Savings | ${metrics.total_cache_savings:.4f} |

## Cost by Agent

| Agent | Cost | Queries | Avg/Query |
|-------|------|---------|-----------|
"""
        for agent, cost in sorted(metrics.cost_by_agent.items(), key=lambda x: -x[1]):
            queries = metrics.queries_by_agent.get(agent, 0)
            avg = cost / queries if queries > 0 else 0
            report += f"| {agent} | ${cost:.4f} | {queries} | ${avg:.4f} |\n"

        report += """
## Cost by Model

| Model | Cost | Queries | % of Total |
|-------|------|---------|------------|
"""
        for model, cost in sorted(metrics.cost_by_model.items(), key=lambda x: -x[1]):
            queries = metrics.queries_by_model.get(model, 0)
            pct = (cost / metrics.total_cost * 100) if metrics.total_cost > 0 else 0
            report += f"| {model} | ${cost:.4f} | {queries} | {pct:.1f}% |\n"

        report += """
## 4-Week Trend

| Week | Cost | Queries | WoW Change |
|------|------|---------|------------|
"""
        for week in trends["weekly_data"]:
            change = week.get('cost_wow_change')
            wow = f"{change}%" if change is not None else "N/A"
            cost = week['total_cost']
            queries = week['total_queries']
            report += f"| {week['period']} | ${cost:.4f} | {queries} | {wow} |\n"

        report += f"""
**Trend Direction**: {trends['summary']['trend_direction']}

## Active Alerts

"""
        if alerts:
            for alert in alerts[:5]:
                report += f"- **[{alert.severity.upper()}]** {alert.message}\n"
        else:
            report += "_No active alerts._\n"

        report += f"""
## Comparison to Target

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Cost per Audit | ${self.thresholds['cost_per_audit_target']:.2f} | TBD | - |
| Daily Spend | <${self.thresholds['daily_spend']:.2f} | \
${self.get_daily_metrics().total_cost:.4f} | \
{'OK' if self.get_daily_metrics().total_cost < self.thresholds['daily_spend'] else 'EXCEEDED'} |
| Cache Hit Rate | >{self.thresholds['cache_hit_rate_min']*100:.0f}% | \
{metrics.cache_hit_rate*100:.1f}% | \
{'OK' if metrics.cache_hit_rate >= self.thresholds['cache_hit_rate_min'] else 'LOW'} |

---
*Generated: {datetime.now().isoformat()}*
"""
        return report

    def export_for_dashboard(self) -> dict[str, Any]:
        """Export data in format suitable for dashboard ingestion."""
        daily = self.get_daily_metrics()
        weekly = self.get_weekly_metrics()
        monthly = self.get_monthly_metrics()
        trends = self.get_trend_analysis()

        return {
            "generated_at": datetime.now().isoformat(),
            "metrics": {
                "daily": {
                    "total_cost": round(daily.total_cost, 4),
                    "queries": daily.total_queries,
                    "avg_cost_per_query": round(daily.avg_cost_per_query, 4),
                    "cache_hit_rate": round(daily.cache_hit_rate, 4),
                },
                "weekly": {
                    "total_cost": round(weekly.total_cost, 4),
                    "queries": weekly.total_queries,
                    "avg_cost_per_query": round(weekly.avg_cost_per_query, 4),
                    "cache_hit_rate": round(weekly.cache_hit_rate, 4),
                    "by_agent": {k: round(v, 4) for k, v in weekly.cost_by_agent.items()},
                    "by_model": {k: round(v, 4) for k, v in weekly.cost_by_model.items()},
                },
                "monthly": {
                    "total_cost": round(monthly.total_cost, 4),
                    "queries": monthly.total_queries,
                    "avg_cost_per_query": round(monthly.avg_cost_per_query, 4),
                },
            },
            "trends": trends,
            "thresholds": self.thresholds,
            "alerts_count": len(self.get_alerts(unacknowledged_only=True)),
        }


# =============================================================================
# Formulas Reference (from Directive D10)
# =============================================================================

def calculate_cost_per_audit(
    opus_queries: int = 8,
    sonnet_tasks: int = 33,
    haiku_tasks: int = 20,
    cache_pct: float = 0.25,
    batch_pct: float = 0.30,
) -> dict[str, float]:
    """
    Calculate expected cost per audit using the Cardinal Element cost model.

    Default values from CFO-Agent-Economics.md Section 1.3:
    - 8 executive synthesis tasks (Opus)
    - 33 specialist tasks (Sonnet: 6 research + 4 competitive + 5 financial + 12 content + 6 QA)
    - 20 data extraction tasks (Haiku)

    Args:
        opus_queries: Number of Opus queries (executive synthesis)
        sonnet_tasks: Number of Sonnet tasks (specialist work)
        haiku_tasks: Number of Haiku tasks (high-volume extraction)
        cache_pct: Percentage of tokens from cache (default 25%)
        batch_pct: Percentage of tasks on batch API (default 30%)

    Returns:
        Cost breakdown dictionary
    """
    # Base costs per task (from CFO-Agent-Economics.md)
    opus_cost = 0.225  # 15K in + 3K out
    sonnet_cost = 0.125  # Average across task types
    haiku_cost = 0.015  # 5K in + 2K out

    # Calculate gross costs
    gross_opus = opus_queries * opus_cost
    gross_sonnet = sonnet_tasks * sonnet_cost
    gross_haiku = haiku_tasks * haiku_cost
    gross_total = gross_opus + gross_sonnet + gross_haiku

    # Apply optimizations
    # Cache savings: 90% savings on cached tokens (cache_pct of input)
    # Roughly 60% of cost is input, so savings = 0.60 * cache_pct * 0.90
    cache_savings = gross_total * 0.60 * cache_pct * 0.90

    # Batch savings: 50% discount on batch_pct of non-urgent tasks
    # Assume all Sonnet tasks eligible, 50% of Haiku
    batch_eligible = gross_sonnet + (gross_haiku * 0.5)
    batch_savings = batch_eligible * batch_pct * 0.50

    optimized_total = gross_total - cache_savings - batch_savings

    return {
        "gross_cost": round(gross_total, 4),
        "cache_savings": round(cache_savings, 4),
        "batch_savings": round(batch_savings, 4),
        "optimized_cost": round(optimized_total, 4),
        "breakdown": {
            "opus": round(gross_opus, 4),
            "sonnet": round(gross_sonnet, 4),
            "haiku": round(gross_haiku, 4),
        },
        "task_counts": {
            "opus": opus_queries,
            "sonnet": sonnet_tasks,
            "haiku": haiku_tasks,
            "total": opus_queries + sonnet_tasks + haiku_tasks,
        },
    }


def calculate_monthly_burn_rate(
    audits_per_month: int,
    retainers_per_month: int = 0,
    ad_hoc_queries_per_month: int = 50,
    content_pieces_per_month: int = 10,
) -> dict[str, float]:
    """
    Calculate monthly API burn rate.

    Args:
        audits_per_month: Number of Growth Strategy Audits
        retainers_per_month: Number of active retainer clients
        ad_hoc_queries_per_month: Standalone executive queries
        content_pieces_per_month: Marketing content generation

    Returns:
        Monthly cost projection
    """
    # Cost per audit (optimized)
    audit_cost = calculate_cost_per_audit()["optimized_cost"]

    # Retainer activity (estimate 20 queries/month/client)
    retainer_query_cost = 0.225 * 5 + 0.099 * 15  # Mix of executive + specialist

    # Ad-hoc queries (mostly executive)
    ad_hoc_cost = 0.225 * 0.4 + 0.099 * 0.6  # 40% exec, 60% specialist

    # Content (specialist tier)
    content_cost = 0.168  # Per content piece

    # Calculate totals
    audit_total = audits_per_month * audit_cost
    retainer_total = retainers_per_month * retainer_query_cost * 20
    ad_hoc_total = ad_hoc_queries_per_month * ad_hoc_cost
    content_total = content_pieces_per_month * content_cost

    monthly_total = audit_total + retainer_total + ad_hoc_total + content_total

    return {
        "monthly_total": round(monthly_total, 2),
        "breakdown": {
            "audits": round(audit_total, 2),
            "retainers": round(retainer_total, 2),
            "ad_hoc": round(ad_hoc_total, 2),
            "content": round(content_total, 2),
        },
        "volume": {
            "audits": audits_per_month,
            "retainers": retainers_per_month,
            "ad_hoc_queries": ad_hoc_queries_per_month,
            "content_pieces": content_pieces_per_month,
        },
        "comparison": {
            "human_equivalent": audits_per_month * 4500,  # Midpoint human cost per audit
            "savings_pct": (
                round((1 - monthly_total / (audits_per_month * 4500)) * 100, 2)
                if audits_per_month > 0 else 0
            ),
        },
    }


def calculate_model_tier_cost(
    model_tier: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    is_batch: bool = False,
) -> dict[str, float]:
    """
    Calculate cost for a single query by model tier.

    Args:
        model_tier: "opus", "sonnet", or "haiku"
        input_tokens: Input token count
        output_tokens: Output token count
        cached_tokens: Tokens from cache (at 0.1x rate)
        is_batch: Whether batch API was used (50% discount)

    Returns:
        Cost breakdown
    """
    input_per_mtok, output_per_mtok = get_pricing(model_tier)

    input_rate = input_per_mtok / 1_000_000
    output_rate = output_per_mtok / 1_000_000

    # Non-cached input at full rate
    non_cached_input = max(0, input_tokens - cached_tokens)
    input_cost = non_cached_input * input_rate

    # Cached tokens at 0.1x rate
    cached_cost = cached_tokens * input_rate * CACHE_READ_MULTIPLIER
    input_cost += cached_cost

    # Output cost
    output_cost = output_tokens * output_rate

    # Batch discount
    if is_batch:
        input_cost *= (1 - BATCH_DISCOUNT)
        output_cost *= (1 - BATCH_DISCOUNT)

    total = input_cost + output_cost

    return {
        "model_tier": model_tier,
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(total, 6),
        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "cached": cached_tokens,
        },
        "discounts_applied": {
            "cache": cached_tokens > 0,
            "batch": is_batch,
        },
    }


# =============================================================================
# CLI Integration Helper
# =============================================================================

def get_tracker() -> CostTracker:
    """Get a configured CostTracker instance."""
    return CostTracker()


if __name__ == "__main__":
    # Quick test / demo
    tracker = CostTracker()

    # Log a sample usage
    record = tracker.log_usage(
        agent="CFO",
        model="claude-opus-4-6",
        input_tokens=15000,
        output_tokens=3000,
        task_type=TaskType.EXECUTIVE_SYNTHESIS,
    )

    print(f"Logged: {record.agent} query, cost: ${record.total_cost:.4f}")

    # Generate report
    report = tracker.generate_weekly_report()
    print("\n" + report)

    # Test formulas
    print("\n--- Cost Per Audit Formula ---")
    audit_cost = calculate_cost_per_audit()
    print(json.dumps(audit_cost, indent=2))

    print("\n--- Monthly Burn Rate (4 audits/month) ---")
    burn = calculate_monthly_burn_rate(audits_per_month=4, retainers_per_month=2)
    print(json.dumps(burn, indent=2))
