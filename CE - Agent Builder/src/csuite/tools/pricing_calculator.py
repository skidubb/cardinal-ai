"""
Pricing Calculator for Cardinal Element Engagements.

Calculates engagement pricing based on scope, timeline, and complexity.
Used by CFO agent and cfo-pricing-strategist sub-agent for proposal generation.

Engagement Types:
- Growth Strategy Audit: $15-25K (diagnostic + recommendations)
- Implementation Engagement: $50-150K (build + deploy AI-native systems)
- Retainer: $10-25K/month (ongoing advisory + support)

Target Margins: 92-96% (AI-native delivery per Chairman's Directive D2)

See: /Users/scottewalt/Documents/CE - C-Suite/Strategy Meeting/CFO-Agent-Economics.md
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any

# =============================================================================
# Enums and Constants
# =============================================================================

class EngagementType(StrEnum):
    """Types of Cardinal Element engagements."""
    AUDIT = "audit"
    IMPLEMENTATION = "implementation"
    RETAINER = "retainer"


class ComplexityLevel(StrEnum):
    """Engagement complexity levels."""
    STANDARD = "standard"      # Typical scope, known patterns
    COMPLEX = "complex"        # Multi-stakeholder, custom requirements
    ENTERPRISE = "enterprise"  # Large org, regulatory, integration-heavy


class IndustryVertical(StrEnum):
    """Target industry verticals."""
    PROFESSIONAL_SERVICES = "professional_services"  # Our ICP
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCIAL_SERVICES = "financial_services"
    MANUFACTURING = "manufacturing"
    OTHER = "other"


class PaymentTerms(StrEnum):
    """Payment structure options."""
    FULL_UPFRONT = "full_upfront"           # 100% before start
    FIFTY_FIFTY = "fifty_fifty"             # 50% upfront, 50% on delivery
    MILESTONE = "milestone"                  # Split across milestones
    MONTHLY = "monthly"                      # Retainer billing
    NET_30 = "net_30"                       # Invoice on delivery


# =============================================================================
# Base Pricing Tables
# =============================================================================

# Base prices by engagement type (mid-range)
BASE_PRICES = {
    EngagementType.AUDIT: {
        "min": 15_000,
        "base": 20_000,
        "max": 25_000,
    },
    EngagementType.IMPLEMENTATION: {
        "min": 50_000,
        "base": 100_000,
        "max": 150_000,
    },
    EngagementType.RETAINER: {
        "min": 10_000,  # Per month
        "base": 15_000,
        "max": 25_000,
    },
}

# Complexity multipliers
COMPLEXITY_MULTIPLIERS = {
    ComplexityLevel.STANDARD: 1.0,
    ComplexityLevel.COMPLEX: 1.25,
    ComplexityLevel.ENTERPRISE: 1.50,
}

# Industry adjustments (some industries command premium)
INDUSTRY_ADJUSTMENTS = {
    IndustryVertical.PROFESSIONAL_SERVICES: 1.0,   # Our ICP, standard pricing
    IndustryVertical.TECHNOLOGY: 0.95,             # Tech-savvy, price-sensitive
    IndustryVertical.HEALTHCARE: 1.15,             # Regulatory complexity
    IndustryVertical.FINANCIAL_SERVICES: 1.20,     # High value, high scrutiny
    IndustryVertical.MANUFACTURING: 1.05,          # Traditional, value outcomes
    IndustryVertical.OTHER: 1.0,
}

# Timeline adjustments (rush = premium, extended = slight discount)
# Days relative to standard timeline
TIMELINE_ADJUSTMENTS = {
    "rush": 1.25,      # <50% of standard timeline
    "accelerated": 1.15,  # 50-75% of standard timeline
    "standard": 1.0,   # Normal timeline
    "extended": 0.95,  # >125% of standard timeline
}

# Standard timelines by engagement type (in weeks)
STANDARD_TIMELINES = {
    EngagementType.AUDIT: 3,           # 3 weeks
    EngagementType.IMPLEMENTATION: 12,  # 12 weeks
    EngagementType.RETAINER: 4,        # 4 weeks per billing cycle
}

# Retainer commitment discounts
RETAINER_COMMITMENT_DISCOUNTS = {
    1: 1.0,     # Month-to-month: no discount
    3: 0.95,    # 3-month commitment: 5% discount
    6: 0.90,    # 6-month commitment: 10% discount
    12: 0.85,   # Annual commitment: 15% discount
}


# =============================================================================
# Cost Model (AI-Native Delivery)
# =============================================================================

@dataclass
class CostModel:
    """Cost structure for engagement pricing.

    Based on CFO-Agent-Economics.md: AI-native delivery with zero human
    subcontractors per Chairman's Directive D2.
    """

    # Fixed costs (overhead per engagement)
    overhead_per_engagement: float = 500.0  # Legal, admin, tooling allocation

    # Agent costs (from cost_tracker.py)
    cost_per_audit: float = 4.75  # AI agent labor for full audit
    cost_per_implementation_week: float = 15.00  # Higher volume of agent tasks
    cost_per_retainer_month: float = 25.00  # Ongoing queries and monitoring

    # Founder time allocation (opportunity cost, not cash cost)
    founder_hourly_opportunity_cost: float = 500.0  # Scott's time value
    founder_hours_per_audit: float = 8.0
    founder_hours_per_implementation_week: float = 4.0
    founder_hours_per_retainer_month: float = 6.0

    def get_engagement_cost(
        self,
        engagement_type: EngagementType,
        duration_weeks: int = 0,
        duration_months: int = 0,
    ) -> dict[str, float]:
        """Calculate total cost for an engagement."""
        agent_cost = 0.0
        founder_hours = 0.0

        if engagement_type == EngagementType.AUDIT:
            agent_cost = self.cost_per_audit
            founder_hours = self.founder_hours_per_audit

        elif engagement_type == EngagementType.IMPLEMENTATION:
            weeks = duration_weeks or STANDARD_TIMELINES[EngagementType.IMPLEMENTATION]
            agent_cost = self.cost_per_implementation_week * weeks
            founder_hours = self.founder_hours_per_implementation_week * weeks

        elif engagement_type == EngagementType.RETAINER:
            months = duration_months or 1
            agent_cost = self.cost_per_retainer_month * months
            founder_hours = self.founder_hours_per_retainer_month * months

        founder_opportunity_cost = founder_hours * self.founder_hourly_opportunity_cost

        return {
            "agent_cost": round(agent_cost, 2),
            "overhead": self.overhead_per_engagement,
            "founder_hours": founder_hours,
            "founder_opportunity_cost": founder_opportunity_cost,
            "total_cash_cost": round(agent_cost + self.overhead_per_engagement, 2),
            "total_economic_cost": round(
                agent_cost + self.overhead_per_engagement + founder_opportunity_cost, 2
            ),
        }


# =============================================================================
# Output Data Classes
# =============================================================================

@dataclass
class MarginAnalysis:
    """Margin breakdown for an engagement."""
    revenue: float
    cash_cost: float  # Agent + overhead
    cash_margin: float  # Revenue - cash cost
    cash_margin_pct: float  # As percentage
    economic_cost: float  # Including founder opportunity cost
    economic_margin: float
    economic_margin_pct: float

    # Component breakdown
    agent_cost: float
    overhead_cost: float
    founder_opportunity_cost: float
    founder_hours: float


@dataclass
class PricingScenario:
    """A single pricing scenario (floor/target/premium)."""
    name: str  # "floor", "target", "premium"
    price: float
    margin: MarginAnalysis
    client_perception: str
    risk_assessment: str


@dataclass
class ROIProjection:
    """ROI projection for client value demonstration."""
    engagement_price: float
    estimated_client_benefit: float  # Conservative estimate
    roi_multiple: float  # benefit / price
    payback_period_months: float
    value_drivers: list[str] = field(default_factory=list)


@dataclass
class PricingProposal:
    """Complete pricing proposal output."""

    # Engagement details
    engagement_type: EngagementType
    complexity: ComplexityLevel
    industry: IndustryVertical
    timeline_weeks: int
    duration_months: int  # For retainers

    # Pricing
    recommended_price: float
    price_range: dict[str, float]  # min, target, max
    scenarios: list[PricingScenario]

    # Margins
    margin_analysis: MarginAnalysis
    target_margin_achieved: bool

    # Payment terms
    payment_terms: PaymentTerms
    payment_schedule: list[dict[str, Any]]

    # ROI
    roi_projection: ROIProjection

    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    valid_until: date | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "engagement_type": self.engagement_type.value,
            "complexity": self.complexity.value,
            "industry": self.industry.value,
            "timeline_weeks": self.timeline_weeks,
            "duration_months": self.duration_months,
            "recommended_price": self.recommended_price,
            "price_range": self.price_range,
            "scenarios": [
                {
                    "name": s.name,
                    "price": s.price,
                    "margin_pct": s.margin.cash_margin_pct,
                    "client_perception": s.client_perception,
                    "risk": s.risk_assessment,
                }
                for s in self.scenarios
            ],
            "margin_analysis": {
                "cash_margin_pct": self.margin_analysis.cash_margin_pct,
                "economic_margin_pct": self.margin_analysis.economic_margin_pct,
                "agent_cost": self.margin_analysis.agent_cost,
                "founder_hours": self.margin_analysis.founder_hours,
            },
            "target_margin_achieved": self.target_margin_achieved,
            "payment_terms": self.payment_terms.value,
            "payment_schedule": self.payment_schedule,
            "roi": {
                "client_benefit": self.roi_projection.estimated_client_benefit,
                "roi_multiple": self.roi_projection.roi_multiple,
                "payback_months": self.roi_projection.payback_period_months,
            },
            "generated_at": self.generated_at.isoformat(),
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "notes": self.notes,
        }


# =============================================================================
# Pricing Calculator
# =============================================================================

class PricingCalculator:
    """
    Calculate engagement pricing with margin analysis.

    Usage:
        calc = PricingCalculator()

        # Generate audit pricing
        proposal = calc.calculate_audit_price(
            complexity=ComplexityLevel.COMPLEX,
            industry=IndustryVertical.PROFESSIONAL_SERVICES,
            timeline_weeks=2,  # Rush job
            client_revenue=5_000_000,  # For ROI calculation
        )

        # Generate implementation pricing
        proposal = calc.calculate_implementation_price(
            complexity=ComplexityLevel.ENTERPRISE,
            industry=IndustryVertical.HEALTHCARE,
            timeline_weeks=16,
            scope_description="AI-native CRM implementation",
            client_revenue=25_000_000,
        )

        # Generate retainer pricing
        proposal = calc.calculate_retainer_price(
            complexity=ComplexityLevel.STANDARD,
            commitment_months=6,
            hours_per_month=10,
        )
    """

    # Target margin range (from CFO-Agent-Economics.md)
    TARGET_MARGIN_MIN = 0.92  # 92%
    TARGET_MARGIN_MAX = 0.96  # 96%

    def __init__(self, cost_model: CostModel | None = None):
        """Initialize calculator with cost model."""
        self.cost_model = cost_model or CostModel()

    # =========================================================================
    # Core Calculation Methods
    # =========================================================================

    def _calculate_base_price(
        self,
        engagement_type: EngagementType,
        complexity: ComplexityLevel,
        industry: IndustryVertical,
        timeline_adjustment: str,
    ) -> float:
        """Calculate base price with all adjustments."""
        base = BASE_PRICES[engagement_type]["base"]

        # Apply multipliers
        price = base
        price *= COMPLEXITY_MULTIPLIERS[complexity]
        price *= INDUSTRY_ADJUSTMENTS[industry]
        price *= TIMELINE_ADJUSTMENTS[timeline_adjustment]

        return round(price, -2)  # Round to nearest $100

    def _get_timeline_adjustment(
        self,
        engagement_type: EngagementType,
        actual_weeks: int,
    ) -> str:
        """Determine timeline adjustment category."""
        standard = STANDARD_TIMELINES[engagement_type]

        if actual_weeks < standard * 0.5:
            return "rush"
        elif actual_weeks < standard * 0.75:
            return "accelerated"
        elif actual_weeks > standard * 1.25:
            return "extended"
        else:
            return "standard"

    def _calculate_margin(
        self,
        revenue: float,
        engagement_type: EngagementType,
        duration_weeks: int = 0,
        duration_months: int = 0,
    ) -> MarginAnalysis:
        """Calculate margin analysis for a given revenue."""
        costs = self.cost_model.get_engagement_cost(
            engagement_type,
            duration_weeks=duration_weeks,
            duration_months=duration_months,
        )

        cash_cost = costs["total_cash_cost"]
        economic_cost = costs["total_economic_cost"]

        cash_margin = revenue - cash_cost
        economic_margin = revenue - economic_cost

        return MarginAnalysis(
            revenue=revenue,
            cash_cost=cash_cost,
            cash_margin=cash_margin,
            cash_margin_pct=round((cash_margin / revenue) * 100, 2) if revenue > 0 else 0,
            economic_cost=economic_cost,
            economic_margin=economic_margin,
            economic_margin_pct=round((economic_margin / revenue) * 100, 2) if revenue > 0 else 0,
            agent_cost=costs["agent_cost"],
            overhead_cost=costs["overhead"],
            founder_opportunity_cost=costs["founder_opportunity_cost"],
            founder_hours=costs["founder_hours"],
        )

    def _generate_scenarios(
        self,
        target_price: float,
        engagement_type: EngagementType,
        duration_weeks: int = 0,
        duration_months: int = 0,
    ) -> list[PricingScenario]:
        """Generate floor/target/premium scenarios."""
        floor_price = round(target_price * 0.80, -2)
        premium_price = round(target_price * 1.20, -2)

        scenarios = [
            PricingScenario(
                name="floor",
                price=floor_price,
                margin=self._calculate_margin(
                    floor_price, engagement_type, duration_weeks, duration_months
                ),
                client_perception="Competitive, may signal lower tier",
                risk_assessment="Margin compression, sets low anchor for future work",
            ),
            PricingScenario(
                name="target",
                price=target_price,
                margin=self._calculate_margin(
                    target_price, engagement_type, duration_weeks, duration_months
                ),
                client_perception="Fair value for specialized expertise",
                risk_assessment="Balanced risk/reward, sustainable pricing",
            ),
            PricingScenario(
                name="premium",
                price=premium_price,
                margin=self._calculate_margin(
                    premium_price, engagement_type, duration_weeks, duration_months
                ),
                client_perception="Premium positioning, high expectations",
                risk_assessment="May lose price-sensitive prospects, higher service bar",
            ),
        ]

        return scenarios

    def _calculate_roi_projection(
        self,
        engagement_type: EngagementType,
        engagement_price: float,
        client_revenue: float = 0,
    ) -> ROIProjection:
        """Calculate ROI projection for client value demonstration."""
        # Conservative benefit estimates by engagement type
        if engagement_type == EngagementType.AUDIT:
            # Audit typically identifies 5-15% efficiency gains
            benefit_pct = 0.05  # Conservative 5%
            benefit = client_revenue * benefit_pct if client_revenue > 0 else engagement_price * 10
            value_drivers = [
                "Growth opportunity identification",
                "Operational efficiency gains",
                "AI implementation roadmap",
                "Competitive positioning clarity",
            ]
            payback_months = 3

        elif engagement_type == EngagementType.IMPLEMENTATION:
            # Implementation drives 15-30% efficiency or revenue gains
            benefit_pct = 0.15
            benefit = client_revenue * benefit_pct if client_revenue > 0 else engagement_price * 5
            value_drivers = [
                "Process automation savings",
                "Revenue acceleration from AI tools",
                "Reduced manual labor costs",
                "Improved decision-making speed",
            ]
            payback_months = 6

        elif engagement_type == EngagementType.RETAINER:
            # Retainer provides ongoing 2-5% monthly value
            benefit_pct = 0.03  # 3% of monthly operations
            monthly_benefit = (
                client_revenue / 12 * benefit_pct
                if client_revenue > 0 else engagement_price * 2
            )
            benefit = monthly_benefit * 12  # Annualized
            value_drivers = [
                "Continuous strategic guidance",
                "Priority access to expertise",
                "Proactive opportunity identification",
                "Risk mitigation and monitoring",
            ]
            payback_months = 1

        else:
            benefit = engagement_price * 5
            value_drivers = ["General value creation"]
            payback_months = 6

        roi_multiple = round(benefit / engagement_price, 1) if engagement_price > 0 else 0

        return ROIProjection(
            engagement_price=engagement_price,
            estimated_client_benefit=round(benefit, -2),
            roi_multiple=roi_multiple,
            payback_period_months=payback_months,
            value_drivers=value_drivers,
        )

    def _generate_payment_schedule(
        self,
        price: float,
        payment_terms: PaymentTerms,
        duration_months: int = 0,
    ) -> list[dict[str, Any]]:
        """Generate payment schedule based on terms."""
        if payment_terms == PaymentTerms.FULL_UPFRONT:
            return [{"milestone": "Contract signing", "amount": price, "due": "Before start"}]

        elif payment_terms == PaymentTerms.FIFTY_FIFTY:
            half = round(price / 2, 2)
            return [
                {"milestone": "Contract signing", "amount": half, "due": "Before start"},
                {"milestone": "Final delivery", "amount": half, "due": "On delivery"},
            ]

        elif payment_terms == PaymentTerms.MILESTONE:
            third = round(price / 3, 2)
            return [
                {"milestone": "Kickoff", "amount": third, "due": "Week 1"},
                {"milestone": "Mid-point review", "amount": third, "due": "Week 6"},
                {"milestone": "Final delivery", "amount": third, "due": "Week 12"},
            ]

        elif payment_terms == PaymentTerms.MONTHLY:
            return [
                {"milestone": f"Month {i+1}", "amount": price, "due": f"1st of month {i+1}"}
                for i in range(duration_months or 1)
            ]

        elif payment_terms == PaymentTerms.NET_30:
            return [{"milestone": "Invoice on delivery", "amount": price, "due": "Net 30"}]

        return []

    # =========================================================================
    # Public Pricing Methods
    # =========================================================================

    def calculate_audit_price(
        self,
        complexity: ComplexityLevel = ComplexityLevel.STANDARD,
        industry: IndustryVertical = IndustryVertical.PROFESSIONAL_SERVICES,
        timeline_weeks: int = 3,
        client_revenue: float = 0,
        payment_terms: PaymentTerms = PaymentTerms.FIFTY_FIFTY,
    ) -> PricingProposal:
        """
        Calculate pricing for a Growth Strategy Audit.

        Args:
            complexity: Engagement complexity level
            industry: Client industry vertical
            timeline_weeks: Delivery timeline in weeks
            client_revenue: Client's annual revenue (for ROI calculation)
            payment_terms: Payment structure

        Returns:
            Complete PricingProposal with recommendations
        """
        timeline_adj = self._get_timeline_adjustment(EngagementType.AUDIT, timeline_weeks)

        target_price = self._calculate_base_price(
            EngagementType.AUDIT,
            complexity,
            industry,
            timeline_adj,
        )

        margin = self._calculate_margin(target_price, EngagementType.AUDIT)
        scenarios = self._generate_scenarios(target_price, EngagementType.AUDIT)
        roi = self._calculate_roi_projection(EngagementType.AUDIT, target_price, client_revenue)
        schedule = self._generate_payment_schedule(target_price, payment_terms)

        return PricingProposal(
            engagement_type=EngagementType.AUDIT,
            complexity=complexity,
            industry=industry,
            timeline_weeks=timeline_weeks,
            duration_months=0,
            recommended_price=target_price,
            price_range={
                "min": BASE_PRICES[EngagementType.AUDIT]["min"],
                "target": target_price,
                "max": round(target_price * 1.25, -2),
            },
            scenarios=scenarios,
            margin_analysis=margin,
            target_margin_achieved=margin.cash_margin_pct >= self.TARGET_MARGIN_MIN * 100,
            payment_terms=payment_terms,
            payment_schedule=schedule,
            roi_projection=roi,
            valid_until=date.today() + timedelta(days=30),
            notes=[
                f"Timeline: {timeline_weeks} weeks ({timeline_adj})",
                f"Complexity: {complexity.value}",
                f"Industry adjustment: {INDUSTRY_ADJUSTMENTS[industry]}x",
            ],
        )

    def calculate_implementation_price(
        self,
        complexity: ComplexityLevel = ComplexityLevel.COMPLEX,
        industry: IndustryVertical = IndustryVertical.PROFESSIONAL_SERVICES,
        timeline_weeks: int = 12,
        scope_description: str = "",
        client_revenue: float = 0,
        payment_terms: PaymentTerms = PaymentTerms.MILESTONE,
    ) -> PricingProposal:
        """
        Calculate pricing for an Implementation Engagement.

        Args:
            complexity: Engagement complexity level
            industry: Client industry vertical
            timeline_weeks: Delivery timeline in weeks
            scope_description: Brief description of implementation scope
            client_revenue: Client's annual revenue (for ROI calculation)
            payment_terms: Payment structure

        Returns:
            Complete PricingProposal with recommendations
        """
        timeline_adj = self._get_timeline_adjustment(EngagementType.IMPLEMENTATION, timeline_weeks)

        target_price = self._calculate_base_price(
            EngagementType.IMPLEMENTATION,
            complexity,
            industry,
            timeline_adj,
        )

        margin = self._calculate_margin(
            target_price, EngagementType.IMPLEMENTATION, duration_weeks=timeline_weeks
        )
        scenarios = self._generate_scenarios(
            target_price, EngagementType.IMPLEMENTATION, duration_weeks=timeline_weeks
        )
        roi = self._calculate_roi_projection(
            EngagementType.IMPLEMENTATION, target_price, client_revenue
        )
        schedule = self._generate_payment_schedule(target_price, payment_terms)

        notes = [
            f"Timeline: {timeline_weeks} weeks ({timeline_adj})",
            f"Complexity: {complexity.value}",
        ]
        if scope_description:
            notes.append(f"Scope: {scope_description}")

        return PricingProposal(
            engagement_type=EngagementType.IMPLEMENTATION,
            complexity=complexity,
            industry=industry,
            timeline_weeks=timeline_weeks,
            duration_months=0,
            recommended_price=target_price,
            price_range={
                "min": BASE_PRICES[EngagementType.IMPLEMENTATION]["min"],
                "target": target_price,
                "max": BASE_PRICES[EngagementType.IMPLEMENTATION]["max"],
            },
            scenarios=scenarios,
            margin_analysis=margin,
            target_margin_achieved=margin.cash_margin_pct >= self.TARGET_MARGIN_MIN * 100,
            payment_terms=payment_terms,
            payment_schedule=schedule,
            roi_projection=roi,
            valid_until=date.today() + timedelta(days=30),
            notes=notes,
        )

    def calculate_retainer_price(
        self,
        complexity: ComplexityLevel = ComplexityLevel.STANDARD,
        industry: IndustryVertical = IndustryVertical.PROFESSIONAL_SERVICES,
        commitment_months: int = 1,
        hours_per_month: int = 10,
        client_revenue: float = 0,
    ) -> PricingProposal:
        """
        Calculate pricing for a Retainer engagement.

        Args:
            complexity: Engagement complexity level
            industry: Client industry vertical
            commitment_months: Commitment term length (1, 3, 6, or 12)
            hours_per_month: Expected advisory hours per month
            client_revenue: Client's annual revenue (for ROI calculation)

        Returns:
            Complete PricingProposal with monthly rate
        """
        # Base monthly rate
        base_monthly = BASE_PRICES[EngagementType.RETAINER]["base"]

        # Apply adjustments
        monthly_rate = base_monthly
        monthly_rate *= COMPLEXITY_MULTIPLIERS[complexity]
        monthly_rate *= INDUSTRY_ADJUSTMENTS[industry]

        # Hours adjustment (base is 10 hours, adjust for more/less)
        hours_multiplier = hours_per_month / 10.0
        monthly_rate *= hours_multiplier

        # Commitment discount
        discount_key = min(commitment_months, 12)
        if discount_key not in RETAINER_COMMITMENT_DISCOUNTS:
            # Find closest lower tier
            discount_key = max(k for k in RETAINER_COMMITMENT_DISCOUNTS if k <= commitment_months)
        monthly_rate *= RETAINER_COMMITMENT_DISCOUNTS.get(discount_key, 1.0)

        monthly_rate = round(monthly_rate, -2)  # Round to nearest $100

        total_contract_value = monthly_rate * commitment_months

        margin = self._calculate_margin(
            monthly_rate, EngagementType.RETAINER, duration_months=1
        )
        scenarios = self._generate_scenarios(
            monthly_rate, EngagementType.RETAINER, duration_months=1
        )
        roi = self._calculate_roi_projection(
            EngagementType.RETAINER, monthly_rate, client_revenue
        )

        # Monthly billing schedule
        schedule = [
            {"milestone": f"Month {i+1}", "amount": monthly_rate, "due": "1st of month"}
            for i in range(commitment_months)
        ]

        discount_applied = RETAINER_COMMITMENT_DISCOUNTS.get(discount_key, 1.0)

        return PricingProposal(
            engagement_type=EngagementType.RETAINER,
            complexity=complexity,
            industry=industry,
            timeline_weeks=commitment_months * 4,
            duration_months=commitment_months,
            recommended_price=monthly_rate,
            price_range={
                "min": BASE_PRICES[EngagementType.RETAINER]["min"],
                "target": monthly_rate,
                "max": BASE_PRICES[EngagementType.RETAINER]["max"],
            },
            scenarios=scenarios,
            margin_analysis=margin,
            target_margin_achieved=margin.cash_margin_pct >= self.TARGET_MARGIN_MIN * 100,
            payment_terms=PaymentTerms.MONTHLY,
            payment_schedule=schedule,
            roi_projection=roi,
            valid_until=date.today() + timedelta(days=30),
            notes=[
                f"Monthly rate: ${monthly_rate:,.0f}",
                f"Commitment: {commitment_months} months",
                f"Total contract value: ${total_contract_value:,.0f}",
                f"Commitment discount: {(1 - discount_applied) * 100:.0f}% off",
                f"Hours per month: {hours_per_month}",
            ],
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def calculate_margin_floor(
        self,
        engagement_type: EngagementType,
        target_margin_pct: float = 92.0,
        duration_weeks: int = 0,
        duration_months: int = 0,
    ) -> float:
        """
        Calculate minimum price to achieve target margin.

        Args:
            engagement_type: Type of engagement
            target_margin_pct: Target margin percentage (default 92%)
            duration_weeks: Duration for implementation
            duration_months: Duration for retainer

        Returns:
            Minimum price to achieve target margin
        """
        costs = self.cost_model.get_engagement_cost(
            engagement_type,
            duration_weeks=duration_weeks,
            duration_months=duration_months,
        )

        cash_cost = costs["total_cash_cost"]

        # Price = Cost / (1 - margin_pct)
        margin_decimal = target_margin_pct / 100.0
        floor_price = cash_cost / (1 - margin_decimal)

        return round(floor_price, -2)

    def compare_scenarios(
        self,
        proposals: list[PricingProposal],
    ) -> dict[str, Any]:
        """
        Compare multiple pricing proposals side by side.

        Args:
            proposals: List of PricingProposal objects

        Returns:
            Comparison summary
        """
        return {
            "scenarios": [
                {
                    "type": p.engagement_type.value,
                    "price": p.recommended_price,
                    "margin": p.margin_analysis.cash_margin_pct,
                    "roi": p.roi_projection.roi_multiple,
                }
                for p in proposals
            ],
            "summary": {
                "total_value": sum(p.recommended_price for p in proposals),
                "avg_margin": (
                    sum(p.margin_analysis.cash_margin_pct for p in proposals)
                    / len(proposals) if proposals else 0
                ),
                "lowest_margin": min(p.margin_analysis.cash_margin_pct for p in proposals)
                if proposals else 0,
            },
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def quick_audit_price(
    complexity: str = "standard",
    timeline_weeks: int = 3,
) -> dict[str, Any]:
    """Quick audit pricing for CLI or simple queries."""
    calc = PricingCalculator()
    proposal = calc.calculate_audit_price(
        complexity=ComplexityLevel(complexity),
        timeline_weeks=timeline_weeks,
    )
    return {
        "price": proposal.recommended_price,
        "margin": proposal.margin_analysis.cash_margin_pct,
        "roi": proposal.roi_projection.roi_multiple,
    }


def quick_implementation_price(
    complexity: str = "complex",
    timeline_weeks: int = 12,
) -> dict[str, Any]:
    """Quick implementation pricing for CLI or simple queries."""
    calc = PricingCalculator()
    proposal = calc.calculate_implementation_price(
        complexity=ComplexityLevel(complexity),
        timeline_weeks=timeline_weeks,
    )
    return {
        "price": proposal.recommended_price,
        "margin": proposal.margin_analysis.cash_margin_pct,
        "roi": proposal.roi_projection.roi_multiple,
    }


def quick_retainer_price(
    commitment_months: int = 6,
    hours_per_month: int = 10,
) -> dict[str, Any]:
    """Quick retainer pricing for CLI or simple queries."""
    calc = PricingCalculator()
    proposal = calc.calculate_retainer_price(
        commitment_months=commitment_months,
        hours_per_month=hours_per_month,
    )
    return {
        "monthly_rate": proposal.recommended_price,
        "total_value": proposal.recommended_price * commitment_months,
        "margin": proposal.margin_analysis.cash_margin_pct,
    }


# =============================================================================
# Demo
# =============================================================================

if __name__ == "__main__":

    calc = PricingCalculator()

    print("=" * 60)
    print("AUDIT PRICING")
    print("=" * 60)
    audit = calc.calculate_audit_price(
        complexity=ComplexityLevel.COMPLEX,
        industry=IndustryVertical.PROFESSIONAL_SERVICES,
        timeline_weeks=2,  # Rush
        client_revenue=5_000_000,
    )
    print(f"Recommended: ${audit.recommended_price:,.0f}")
    print(f"Margin: {audit.margin_analysis.cash_margin_pct}%")
    print(f"ROI Multiple: {audit.roi_projection.roi_multiple}x")
    print(f"Target Margin Achieved: {audit.target_margin_achieved}")

    print("\n" + "=" * 60)
    print("IMPLEMENTATION PRICING")
    print("=" * 60)
    impl = calc.calculate_implementation_price(
        complexity=ComplexityLevel.ENTERPRISE,
        industry=IndustryVertical.HEALTHCARE,
        timeline_weeks=16,
        scope_description="AI-native customer service platform",
        client_revenue=25_000_000,
    )
    print(f"Recommended: ${impl.recommended_price:,.0f}")
    print(f"Margin: {impl.margin_analysis.cash_margin_pct}%")
    print(f"ROI Multiple: {impl.roi_projection.roi_multiple}x")

    print("\n" + "=" * 60)
    print("RETAINER PRICING")
    print("=" * 60)
    retainer = calc.calculate_retainer_price(
        complexity=ComplexityLevel.STANDARD,
        commitment_months=6,
        hours_per_month=15,
        client_revenue=10_000_000,
    )
    print(f"Monthly Rate: ${retainer.recommended_price:,.0f}")
    print(f"6-Month Value: ${retainer.recommended_price * 6:,.0f}")
    print(f"Margin: {retainer.margin_analysis.cash_margin_pct}%")

    print("\n" + "=" * 60)
    print("MARGIN FLOOR (92% target)")
    print("=" * 60)
    floor = calc.calculate_margin_floor(EngagementType.AUDIT)
    print(f"Audit minimum price for 92% margin: ${floor:,.0f}")
