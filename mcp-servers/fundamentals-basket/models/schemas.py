"""
Data schemas for Financials-Basket MCP Server

Defines the data contracts between services using dataclasses.
All temporal metadata (end_date, fiscal_year, form) is preserved.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class TemporalMetric:
    """
    A metric value with temporal metadata from SEC filings.

    Preserves audit period context for calculated ratios.
    """
    value: Optional[float] = None
    data_type: Optional[str] = None  # "FY", "Q", "TTM", "Point-in-time", "Real-time"
    end_date: Optional[str] = None  # YYYY-MM-DD (period end date / "as of" date)
    filed: Optional[str] = None  # YYYY-MM-DD (SEC filing date / updated date)
    fiscal_year: Optional[int] = None
    form: Optional[str] = None  # "10-K", "10-Q", etc.

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        result = {}
        if self.value is not None:
            result["value"] = self.value
        if self.data_type:
            result["data_type"] = self.data_type
        if self.end_date:
            result["end_date"] = self.end_date
        if self.filed:
            result["filed"] = self.filed
        if self.fiscal_year:
            result["fiscal_year"] = self.fiscal_year
        if self.form:
            result["form"] = self.form
        return result if result else {"value": None}

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "TemporalMetric":
        """Create from dictionary."""
        if not data:
            return cls()
        if isinstance(data, (int, float)):
            return cls(value=float(data))
        return cls(
            value=data.get("value"),
            data_type=data.get("data_type"),
            end_date=data.get("end_date"),
            filed=data.get("filed"),
            fiscal_year=data.get("fiscal_year"),
            form=data.get("form"),
        )


@dataclass
class ParsedFinancials:
    """Parsed financial metrics from SEC EDGAR or Yahoo Finance."""
    ticker: str
    revenue: Optional[TemporalMetric] = None
    net_income: Optional[TemporalMetric] = None
    gross_profit: Optional[TemporalMetric] = None
    operating_income: Optional[TemporalMetric] = None
    gross_margin_pct: Optional[TemporalMetric] = None
    operating_margin_pct: Optional[TemporalMetric] = None
    net_margin_pct: Optional[TemporalMetric] = None
    revenue_growth_3yr: Optional[TemporalMetric] = None
    total_assets: Optional[TemporalMetric] = None
    total_liabilities: Optional[TemporalMetric] = None
    stockholders_equity: Optional[TemporalMetric] = None
    eps: Optional[TemporalMetric] = None
    source: str = "Unknown"
    as_of: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    # Industry classification
    sector: str = "GENERAL"
    sic_code: str = ""

    # Insurance-specific metrics (SIC 63xx, 64xx)
    premiums_earned: Optional[TemporalMetric] = None
    claims_incurred: Optional[TemporalMetric] = None
    underwriting_income: Optional[TemporalMetric] = None
    investment_income: Optional[TemporalMetric] = None
    policy_acquisition_costs: Optional[TemporalMetric] = None

    # Bank-specific metrics (SIC 60xx, 61xx)
    net_interest_income: Optional[TemporalMetric] = None
    provision_credit_losses: Optional[TemporalMetric] = None
    noninterest_income: Optional[TemporalMetric] = None
    noninterest_expense: Optional[TemporalMetric] = None
    net_loans: Optional[TemporalMetric] = None
    deposits: Optional[TemporalMetric] = None
    tier1_capital_ratio: Optional[TemporalMetric] = None

    # REIT-specific metrics (SIC 65xx, 67xx)
    rental_revenue: Optional[TemporalMetric] = None
    noi: Optional[TemporalMetric] = None
    ffo: Optional[TemporalMetric] = None
    property_operating_expenses: Optional[TemporalMetric] = None

    # Energy/Oil & Gas-specific metrics (SIC 13xx, 29xx)
    oil_gas_revenue: Optional[TemporalMetric] = None
    production_expense: Optional[TemporalMetric] = None
    depletion: Optional[TemporalMetric] = None
    exploration_expense: Optional[TemporalMetric] = None
    impairment: Optional[TemporalMetric] = None

    # Utility-specific metrics (SIC 49xx)
    electric_revenue: Optional[TemporalMetric] = None
    gas_revenue: Optional[TemporalMetric] = None
    fuel_cost: Optional[TemporalMetric] = None
    regulatory_assets: Optional[TemporalMetric] = None
    rate_base: Optional[TemporalMetric] = None

    # Technology-specific metrics (SIC 35xx, 36xx, 38xx, 73xx)
    rd_expense: Optional[TemporalMetric] = None
    deferred_revenue: Optional[TemporalMetric] = None
    subscription_revenue: Optional[TemporalMetric] = None
    cost_of_revenue: Optional[TemporalMetric] = None
    stock_compensation: Optional[TemporalMetric] = None
    intangible_assets: Optional[TemporalMetric] = None
    goodwill: Optional[TemporalMetric] = None
    acquired_ip: Optional[TemporalMetric] = None

    # Healthcare-specific metrics (SIC 28xx, 80xx)
    selling_general_admin: Optional[TemporalMetric] = None
    acquired_iprd: Optional[TemporalMetric] = None
    milestone_payments: Optional[TemporalMetric] = None
    inventory: Optional[TemporalMetric] = None
    product_revenue: Optional[TemporalMetric] = None
    license_revenue: Optional[TemporalMetric] = None

    # Retail-specific metrics (SIC 52xx-59xx)
    cost_of_goods_sold: Optional[TemporalMetric] = None
    store_count: Optional[TemporalMetric] = None
    depreciation: Optional[TemporalMetric] = None
    lease_expense: Optional[TemporalMetric] = None
    same_store_sales: Optional[TemporalMetric] = None
    ecommerce_revenue: Optional[TemporalMetric] = None

    # Financials-specific metrics (SIC 62xx, 67xx - non-bank)
    advisory_fees: Optional[TemporalMetric] = None
    assets_under_management: Optional[TemporalMetric] = None
    trading_revenue: Optional[TemporalMetric] = None
    commission_revenue: Optional[TemporalMetric] = None
    compensation_expense: Optional[TemporalMetric] = None
    performance_fees: Optional[TemporalMetric] = None
    fund_expenses: Optional[TemporalMetric] = None

    # Industrials-specific metrics (SIC 37xx)
    backlog: Optional[TemporalMetric] = None
    capital_expenditure: Optional[TemporalMetric] = None
    property_plant_equipment: Optional[TemporalMetric] = None
    pension_expense: Optional[TemporalMetric] = None
    warranty_expense: Optional[TemporalMetric] = None

    # Transportation-specific metrics (SIC 40xx-45xx)
    operating_revenue: Optional[TemporalMetric] = None
    fuel_expense: Optional[TemporalMetric] = None
    labor_expense: Optional[TemporalMetric] = None
    maintenance_expense: Optional[TemporalMetric] = None
    revenue_passenger_miles: Optional[TemporalMetric] = None
    available_seat_miles: Optional[TemporalMetric] = None
    load_factor: Optional[TemporalMetric] = None
    fleet_size: Optional[TemporalMetric] = None

    # Materials-specific metrics (SIC 14xx, 24xx, 26xx, 32xx, 33xx)
    energy_costs: Optional[TemporalMetric] = None
    environmental_liabilities: Optional[TemporalMetric] = None
    raw_materials: Optional[TemporalMetric] = None

    # Mining-specific metrics (SIC 10xx, 12xx)
    mining_revenue: Optional[TemporalMetric] = None
    cost_of_production: Optional[TemporalMetric] = None
    reclamation_liabilities: Optional[TemporalMetric] = None
    mineral_reserves: Optional[TemporalMetric] = None
    royalty_expense: Optional[TemporalMetric] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Only emits metrics (no redundant metadata like ticker, source, sector).
        Metadata is provided via company_info in the orchestrator.
        """
        result = {}

        # Add temporal metrics - universal fields
        for field_name in [
            "revenue", "net_income", "gross_profit", "operating_income",
            "gross_margin_pct", "operating_margin_pct", "net_margin_pct",
            "revenue_growth_3yr", "total_assets", "total_liabilities", "stockholders_equity",
            "eps"
        ]:
            value = getattr(self, field_name)
            if value:
                result[field_name] = value.to_dict() if isinstance(value, TemporalMetric) else value

        # Add industry-specific fields (only if present)
        industry_fields = [
            # Insurance
            "premiums_earned", "claims_incurred", "underwriting_income",
            "investment_income", "policy_acquisition_costs",
            # Banks
            "net_interest_income", "provision_credit_losses", "noninterest_income",
            "noninterest_expense", "net_loans", "deposits", "tier1_capital_ratio",
            # REITs
            "rental_revenue", "noi", "ffo", "property_operating_expenses",
            # Energy
            "oil_gas_revenue", "production_expense", "depletion",
            "exploration_expense", "impairment",
            # Utilities
            "electric_revenue", "gas_revenue", "fuel_cost",
            "regulatory_assets", "rate_base",
            # Technology
            "rd_expense", "deferred_revenue", "subscription_revenue", "cost_of_revenue",
            "stock_compensation", "intangible_assets", "goodwill", "acquired_ip",
            # Healthcare
            "selling_general_admin", "acquired_iprd", "milestone_payments",
            "inventory", "product_revenue", "license_revenue",
            # Retail
            "cost_of_goods_sold", "store_count", "depreciation", "lease_expense",
            "same_store_sales", "ecommerce_revenue",
            # Financials
            "advisory_fees", "assets_under_management", "trading_revenue",
            "commission_revenue", "compensation_expense", "performance_fees", "fund_expenses",
            # Industrials
            "backlog", "capital_expenditure", "property_plant_equipment",
            "pension_expense", "warranty_expense",
            # Transportation
            "operating_revenue", "fuel_expense", "labor_expense", "maintenance_expense",
            "revenue_passenger_miles", "available_seat_miles", "load_factor", "fleet_size",
            # Materials
            "energy_costs", "environmental_liabilities", "raw_materials",
            # Mining
            "mining_revenue", "cost_of_production", "reclamation_liabilities",
            "mineral_reserves", "royalty_expense",
        ]

        for field_name in industry_fields:
            value = getattr(self, field_name)
            if value:
                result[field_name] = value.to_dict() if isinstance(value, TemporalMetric) else value

        return result


@dataclass
class DebtMetrics:
    """Debt and leverage metrics."""
    ticker: str
    long_term_debt: Optional[TemporalMetric] = None
    short_term_debt: Optional[TemporalMetric] = None
    total_debt: Optional[TemporalMetric] = None
    cash: Optional[TemporalMetric] = None
    net_debt: Optional[TemporalMetric] = None
    debt_to_equity: Optional[TemporalMetric] = None
    source: str = "Unknown"
    as_of: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization. Only emits metrics."""
        result = {}

        for field_name in [
            "long_term_debt", "short_term_debt", "total_debt",
            "cash", "net_debt", "debt_to_equity"
        ]:
            value = getattr(self, field_name)
            if value:
                result[field_name] = value.to_dict() if isinstance(value, TemporalMetric) else value

        return result


@dataclass
class CashFlowMetrics:
    """Cash flow metrics."""
    ticker: str
    operating_cash_flow: Optional[TemporalMetric] = None
    capital_expenditure: Optional[TemporalMetric] = None
    free_cash_flow: Optional[TemporalMetric] = None
    rd_expense: Optional[TemporalMetric] = None
    source: str = "Unknown"
    as_of: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization. Only emits metrics."""
        result = {}

        for field_name in [
            "operating_cash_flow", "capital_expenditure",
            "free_cash_flow", "rd_expense"
        ]:
            value = getattr(self, field_name)
            if value:
                result[field_name] = value.to_dict() if isinstance(value, TemporalMetric) else value

        return result


@dataclass
class SwotSummary:
    """SWOT analysis summary generated from financial metrics."""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    threats: List[str] = field(default_factory=list)
    note: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "opportunities": self.opportunities,
            "threats": self.threats,
        }
        if self.note:
            result["note"] = self.note
        return result


@dataclass
class FinancialsBasket:
    """Complete financials basket response."""
    ticker: str
    company: Dict[str, Any] = field(default_factory=dict)
    financials: Optional[ParsedFinancials] = None
    debt: Optional[DebtMetrics] = None
    cash_flow: Optional[CashFlowMetrics] = None
    swot_summary: Optional[SwotSummary] = None
    source: str = "Unknown"
    fallback: bool = False
    fallback_reason: Optional[str] = None
    generated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "ticker": self.ticker,
            "company": self.company,
            "source": self.source,
            "generated_at": self.generated_at,
        }

        if self.financials:
            result["financials"] = self.financials.to_dict()
        if self.debt:
            result["debt"] = self.debt.to_dict()
        if self.cash_flow:
            result["cash_flow"] = self.cash_flow.to_dict()
        if self.swot_summary:
            result["swot_summary"] = self.swot_summary.to_dict()
        if self.fallback:
            result["fallback"] = self.fallback
            if self.fallback_reason:
                result["fallback_reason"] = self.fallback_reason

        return result


@dataclass
class FetchResult:
    """Result from a fetch operation."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    source: str = "Unknown"
    latency_ms: float = 0.0
    retries_used: int = 0
    is_fallback: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "success": self.success,
            "source": self.source,
            "latency_ms": self.latency_ms,
            "retries_used": self.retries_used,
        }
        if self.data:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        if self.is_fallback:
            result["is_fallback"] = self.is_fallback
        return result
