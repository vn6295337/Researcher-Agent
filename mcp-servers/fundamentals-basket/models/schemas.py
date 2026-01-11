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
    source: str = "Unknown"
    as_of: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "ticker": self.ticker,
            "source": self.source,
            "as_of": self.as_of,
        }

        # Add temporal metrics
        for field_name in [
            "revenue", "net_income", "gross_profit", "operating_income",
            "gross_margin_pct", "operating_margin_pct", "net_margin_pct",
            "revenue_growth_3yr", "total_assets", "total_liabilities", "stockholders_equity"
        ]:
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
        """Convert to dictionary for JSON serialization."""
        result = {
            "ticker": self.ticker,
            "source": self.source,
            "as_of": self.as_of,
        }

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
        """Convert to dictionary for JSON serialization."""
        result = {
            "ticker": self.ticker,
            "source": self.source,
            "as_of": self.as_of,
        }

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
