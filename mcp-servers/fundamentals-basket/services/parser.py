"""
Parser Service for Financials-Basket MCP Server

Handles XBRL data parsing, ratio calculations, and SWOT analysis:
- Extracts metrics from SEC EDGAR company facts
- Calculates margins, growth rates, and ratios
- Preserves temporal metadata (end_date, fiscal_year, form)
- Generates SWOT summaries based on thresholds
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from config import (
    REVENUE_GROWTH_STRONG,
    REVENUE_GROWTH_POSITIVE,
    REVENUE_GROWTH_DECLINING,
    NET_MARGIN_HIGH,
    NET_MARGIN_HEALTHY,
    NET_MARGIN_THIN,
    NET_MARGIN_UNPROFITABLE,
    OPERATING_MARGIN_STRONG,
    DEBT_TO_EQUITY_HIGH,
    DEBT_TO_EQUITY_ELEVATED,
    DEBT_TO_EQUITY_LOW,
    RD_HIGH_INVESTMENT,
    # Industry-specific concepts
    INDUSTRY_CONCEPTS,
    INSURANCE_CONCEPTS,
    BANK_CONCEPTS,
    REIT_CONCEPTS,
    ENERGY_OG_CONCEPTS,
    UTILITY_CONCEPTS,
    TECHNOLOGY_CONCEPTS,
    HEALTHCARE_CONCEPTS,
    RETAIL_CONCEPTS,
    FINANCIALS_CONCEPTS,
    INDUSTRIALS_CONCEPTS,
    TRANSPORTATION_CONCEPTS,
    MATERIALS_CONCEPTS,
    MINING_CONCEPTS,
)
from models.schemas import (
    TemporalMetric,
    ParsedFinancials,
    DebtMetrics,
    CashFlowMetrics,
    SwotSummary,
)

logger = logging.getLogger("fundamentals-basket.parser")


# =============================================================================
# XBRL CONCEPT MAPPINGS
# =============================================================================

# Revenue concepts (in order of preference - newer ASC 606 concept first)
REVENUE_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",  # ASC 606 (post-2018)
    "Revenues",  # Legacy concept
    "SalesRevenueNet",
    "TotalRevenuesAndOtherIncome",
]

# Net income concepts
NET_INCOME_CONCEPTS = [
    "NetIncomeLoss",
    "ProfitLoss",
    "NetIncomeLossAvailableToCommonStockholdersBasic",
]

# EPS concepts (unit: USD/shares)
EPS_CONCEPTS = [
    "EarningsPerShareBasic",
    "EarningsPerShareDiluted",
]

# Gross profit concepts
GROSS_PROFIT_CONCEPTS = [
    "GrossProfit",
]

# Operating income concepts
OPERATING_INCOME_CONCEPTS = [
    "OperatingIncomeLoss",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
]

# Asset concepts
TOTAL_ASSETS_CONCEPTS = ["Assets"]
TOTAL_LIABILITIES_CONCEPTS = ["Liabilities", "LiabilitiesAndStockholdersEquity"]
STOCKHOLDERS_EQUITY_CONCEPTS = [
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
]

# Debt concepts - include comprehensive concepts that may have more recent data
LONG_TERM_DEBT_CONCEPTS = [
    "LongTermDebtAndCapitalLeaseObligations",  # Most comprehensive, often most recent
    "LongTermDebt",
    "LongTermDebtNoncurrent",
]
SHORT_TERM_DEBT_CONCEPTS = ["ShortTermBorrowings", "DebtCurrent"]
TOTAL_DEBT_CONCEPTS = ["DebtAndCapitalLeaseObligations", "LongTermDebtAndCapitalLeaseObligations", "DebtLongtermAndShorttermCombinedAmount"]

# Cash concepts
CASH_CONCEPTS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsAndShortTermInvestments",
    "Cash",
]

# Cash flow concepts
OPERATING_CF_CONCEPTS = ["NetCashProvidedByUsedInOperatingActivities"]
CAPEX_CONCEPTS = ["PaymentsToAcquirePropertyPlantAndEquipment", "CapitalExpendituresIncurredButNotYetPaid"]
RD_CONCEPTS = ["ResearchAndDevelopmentExpense"]


class ParserService:
    """
    Parser service for XBRL data extraction and analysis.

    Features:
    - Multi-concept fallback for XBRL extraction
    - Temporal metadata preservation
    - Ratio and margin calculations
    - SWOT analysis generation
    """

    # =========================================================================
    # XBRL VALUE EXTRACTION
    # =========================================================================

    def get_latest_value(
        self,
        facts: Dict[str, Any],
        concepts: List[str],
        unit: str = "USD",
        form_filter: Optional[str] = "10-K"
    ) -> Optional[TemporalMetric]:
        """
        Extract the latest value for a concept from XBRL facts.

        Args:
            facts: Company facts dict from SEC EDGAR
            concepts: List of concept names to try (in order of preference)
            unit: Unit type (USD, shares, etc.)
            form_filter: Optional form filter (10-K for annual)

        Returns:
            TemporalMetric with value and temporal metadata, or None if not found
        """
        us_gaap = facts.get("facts", {}).get("us-gaap", {})

        for concept in concepts:
            concept_data = us_gaap.get(concept, {})
            units = concept_data.get("units", {})
            values = units.get(unit, [])

            if not values:
                continue

            # Filter by form if specified
            if form_filter:
                values = [v for v in values if v.get("form") == form_filter]

            if not values:
                continue

            # Sort by end date (descending) to get latest
            values = sorted(values, key=lambda x: x.get("end", ""), reverse=True)

            if values:
                latest = values[0]
                form = latest.get("form")
                # Determine data_type from form: 10-K = FY, 10-Q = Q
                data_type = "FY" if form == "10-K" else "Q" if form == "10-Q" else None
                return TemporalMetric(
                    value=latest.get("val"),
                    data_type=data_type,
                    end_date=latest.get("end"),
                    filed=latest.get("filed"),
                    fiscal_year=latest.get("fy"),
                    form=form,
                )

        return None

    def get_most_recent_across_concepts(
        self,
        facts: Dict[str, Any],
        concepts: List[str],
        unit: str = "USD",
        form_filter: Optional[str] = "10-K"
    ) -> Optional[TemporalMetric]:
        """
        Get the value with the most recent end_date across all concepts.

        Unlike get_latest_value which returns the first concept found,
        this method compares end_dates across ALL concepts and returns
        the one with the most recent data.

        Args:
            facts: Company facts dict from SEC EDGAR
            concepts: List of concept names to check
            unit: Unit type (USD, shares, etc.)
            form_filter: Optional form filter (10-K for annual)

        Returns:
            TemporalMetric with the most recent end_date, or None if not found
        """
        candidates = []

        for concept in concepts:
            result = self.get_latest_value(facts, [concept], unit, form_filter)
            if result and result.end_date:
                candidates.append(result)

        if not candidates:
            return None

        # Sort by end_date descending and return most recent
        candidates.sort(key=lambda x: x.end_date or "", reverse=True)
        return candidates[0]

    def get_values_for_growth(
        self,
        facts: Dict[str, Any],
        concepts: List[str],
        years: int = 3,
        unit: str = "USD"
    ) -> List[Tuple[int, float]]:
        """
        Get historical values for growth calculation.

        Args:
            facts: Company facts dict
            concepts: List of concept names to try
            years: Number of years to fetch
            unit: Unit type

        Returns:
            List of (fiscal_year, value) tuples, sorted by year ascending
        """
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        results = {}

        for concept in concepts:
            concept_data = us_gaap.get(concept, {})
            units = concept_data.get("units", {})
            values = units.get(unit, [])

            # Only 10-K filings for annual data
            annual_values = [v for v in values if v.get("form") == "10-K"]

            for v in annual_values:
                fy = v.get("fy")
                val = v.get("val")
                if fy and val and fy not in results:
                    results[fy] = val

            if results:
                break  # Found values for first matching concept

        # Sort by year and return last N years
        sorted_years = sorted(results.items(), key=lambda x: x[0])
        return sorted_years[-(years + 1):]  # Include one extra year for growth calc

    def calculate_growth(
        self,
        facts: Dict[str, Any],
        concepts: List[str],
        years: int = 3
    ) -> Optional[float]:
        """
        Calculate compound annual growth rate (CAGR).

        Args:
            facts: Company facts dict
            concepts: List of concept names to try
            years: Number of years for CAGR

        Returns:
            CAGR as percentage, or None if insufficient data
        """
        values = self.get_values_for_growth(facts, concepts, years)

        if len(values) < 2:
            return None

        start_year, start_val = values[0]
        end_year, end_val = values[-1]

        if start_val <= 0 or end_val <= 0:
            return None

        years_diff = end_year - start_year
        if years_diff <= 0:
            return None

        # CAGR = (end/start)^(1/years) - 1
        cagr = ((end_val / start_val) ** (1 / years_diff) - 1) * 100
        return round(cagr, 2)

    # =========================================================================
    # TEMPORAL METRIC HELPER
    # =========================================================================

    def create_temporal_metric(
        self,
        value: Optional[float],
        source_metric: Optional[TemporalMetric]
    ) -> TemporalMetric:
        """
        Create a temporal metric inheriting temporal data from source.

        Used for calculated values (margins, ratios) to preserve audit context.

        Args:
            value: The calculated value
            source_metric: Source metric to inherit temporal data from

        Returns:
            TemporalMetric with value and inherited temporal data
        """
        if source_metric:
            return TemporalMetric(
                value=value,
                data_type=source_metric.data_type,
                end_date=source_metric.end_date,
                filed=source_metric.filed,
                fiscal_year=source_metric.fiscal_year,
                form=source_metric.form,
            )
        return TemporalMetric(value=value)

    # =========================================================================
    # FINANCIALS PARSING
    # =========================================================================

    def parse_financials(
        self,
        facts: Dict[str, Any],
        ticker: str,
        sector: str = "GENERAL",
        sic_code: str = ""
    ) -> ParsedFinancials:
        """
        Parse financial metrics from XBRL facts.

        Args:
            facts: Company facts dict from SEC EDGAR
            ticker: Stock ticker symbol
            sector: Industry sector (INSURANCE, BANKS, REAL_ESTATE, OIL_GAS, UTILITIES, GENERAL)
            sic_code: SIC code from SEC EDGAR

        Returns:
            ParsedFinancials with all metrics (universal + industry-specific)
        """
        # Extract core metrics (universal)
        # Use get_most_recent_across_concepts for revenue to ensure freshest data
        # (some companies have ASC 606 concept stale while legacy "Revenues" is current)
        revenue = self.get_most_recent_across_concepts(facts, REVENUE_CONCEPTS)
        net_income = self.get_latest_value(facts, NET_INCOME_CONCEPTS)
        gross_profit = self.get_latest_value(facts, GROSS_PROFIT_CONCEPTS)
        operating_income = self.get_latest_value(facts, OPERATING_INCOME_CONCEPTS)
        total_assets = self.get_latest_value(facts, TOTAL_ASSETS_CONCEPTS)
        total_liabilities = self.get_latest_value(facts, TOTAL_LIABILITIES_CONCEPTS)
        stockholders_equity = self.get_latest_value(facts, STOCKHOLDERS_EQUITY_CONCEPTS)

        # Extract EPS (unit is "USD/shares" not "USD")
        eps = self.get_latest_value(facts, EPS_CONCEPTS, unit="USD/shares")

        # Calculate margins
        gross_margin_pct = None
        operating_margin_pct = None
        net_margin_pct = None

        if revenue and revenue.value and revenue.value > 0:
            if gross_profit and gross_profit.value is not None:
                gross_margin_pct = self.create_temporal_metric(
                    round((gross_profit.value / revenue.value) * 100, 2),
                    revenue
                )

            if operating_income and operating_income.value is not None:
                operating_margin_pct = self.create_temporal_metric(
                    round((operating_income.value / revenue.value) * 100, 2),
                    revenue
                )

            if net_income and net_income.value is not None:
                net_margin_pct = self.create_temporal_metric(
                    round((net_income.value / revenue.value) * 100, 2),
                    revenue
                )

        # Calculate growth and wrap in TemporalMetric
        revenue_growth_val = self.calculate_growth(facts, REVENUE_CONCEPTS)
        revenue_growth_3yr = None
        if revenue_growth_val is not None:
            revenue_growth_3yr = self.create_temporal_metric(revenue_growth_val, revenue)

        # Initialize industry-specific fields
        industry_metrics = {}

        # Extract industry-specific metrics based on sector
        if sector == "INSURANCE":
            industry_metrics = self._extract_insurance_metrics(facts)
            logger.info(f"Extracted insurance metrics for {ticker}: {list(industry_metrics.keys())}")
        elif sector == "BANKS":
            industry_metrics = self._extract_bank_metrics(facts)
            logger.info(f"Extracted bank metrics for {ticker}: {list(industry_metrics.keys())}")
        elif sector == "REAL_ESTATE":
            industry_metrics = self._extract_reit_metrics(facts)
            logger.info(f"Extracted REIT metrics for {ticker}: {list(industry_metrics.keys())}")
        elif sector == "OIL_GAS":
            industry_metrics = self._extract_energy_metrics(facts)
            logger.info(f"Extracted energy metrics for {ticker}: {list(industry_metrics.keys())}")
        elif sector == "UTILITIES":
            industry_metrics = self._extract_utility_metrics(facts)
            logger.info(f"Extracted utility metrics for {ticker}: {list(industry_metrics.keys())}")
        elif sector == "TECHNOLOGY":
            industry_metrics = self._extract_technology_metrics(facts)
            logger.info(f"Extracted technology metrics for {ticker}: {list(industry_metrics.keys())}")
        elif sector == "HEALTHCARE":
            industry_metrics = self._extract_healthcare_metrics(facts)
            logger.info(f"Extracted healthcare metrics for {ticker}: {list(industry_metrics.keys())}")
        elif sector == "RETAIL":
            industry_metrics = self._extract_retail_metrics(facts)
            logger.info(f"Extracted retail metrics for {ticker}: {list(industry_metrics.keys())}")
        elif sector == "FINANCIALS":
            industry_metrics = self._extract_financials_metrics(facts)
            logger.info(f"Extracted financials metrics for {ticker}: {list(industry_metrics.keys())}")
        elif sector == "INDUSTRIALS":
            industry_metrics = self._extract_industrials_metrics(facts)
            logger.info(f"Extracted industrials metrics for {ticker}: {list(industry_metrics.keys())}")
        elif sector == "TRANSPORTATION":
            industry_metrics = self._extract_transportation_metrics(facts)
            logger.info(f"Extracted transportation metrics for {ticker}: {list(industry_metrics.keys())}")
        elif sector == "MATERIALS":
            industry_metrics = self._extract_materials_metrics(facts)
            logger.info(f"Extracted materials metrics for {ticker}: {list(industry_metrics.keys())}")
        elif sector == "MINING":
            industry_metrics = self._extract_mining_metrics(facts)
            logger.info(f"Extracted mining metrics for {ticker}: {list(industry_metrics.keys())}")

        return ParsedFinancials(
            ticker=ticker.upper(),
            revenue=revenue,
            net_income=net_income,
            gross_profit=gross_profit,
            operating_income=operating_income,
            gross_margin_pct=gross_margin_pct,
            operating_margin_pct=operating_margin_pct,
            net_margin_pct=net_margin_pct,
            revenue_growth_3yr=revenue_growth_3yr,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            stockholders_equity=stockholders_equity,
            eps=eps,
            source="SEC EDGAR XBRL",
            sector=sector,
            sic_code=sic_code,
            **industry_metrics,
        )

    # =========================================================================
    # INDUSTRY-SPECIFIC EXTRACTION METHODS
    # =========================================================================

    def _extract_insurance_metrics(self, facts: Dict[str, Any]) -> Dict[str, Optional[TemporalMetric]]:
        """Extract insurance-specific metrics from XBRL facts."""
        return {
            "premiums_earned": self.get_latest_value(facts, INSURANCE_CONCEPTS["premiums_earned"]),
            "claims_incurred": self.get_latest_value(facts, INSURANCE_CONCEPTS["claims_incurred"]),
            "underwriting_income": self.get_latest_value(facts, INSURANCE_CONCEPTS["underwriting_income"]),
            "investment_income": self.get_latest_value(facts, INSURANCE_CONCEPTS["investment_income"]),
            "policy_acquisition_costs": self.get_latest_value(facts, INSURANCE_CONCEPTS["policy_acquisition_costs"]),
        }

    def _extract_bank_metrics(self, facts: Dict[str, Any]) -> Dict[str, Optional[TemporalMetric]]:
        """Extract bank-specific metrics from XBRL facts."""
        return {
            "net_interest_income": self.get_latest_value(facts, BANK_CONCEPTS["net_interest_income"]),
            "provision_credit_losses": self.get_latest_value(facts, BANK_CONCEPTS["provision_credit_losses"]),
            "noninterest_income": self.get_latest_value(facts, BANK_CONCEPTS["noninterest_income"]),
            "noninterest_expense": self.get_latest_value(facts, BANK_CONCEPTS["noninterest_expense"]),
            "net_loans": self.get_latest_value(facts, BANK_CONCEPTS["net_loans"]),
            "deposits": self.get_latest_value(facts, BANK_CONCEPTS["deposits"]),
            "tier1_capital_ratio": self.get_latest_value(facts, BANK_CONCEPTS["tier1_capital_ratio"], unit="pure"),
        }

    def _extract_reit_metrics(self, facts: Dict[str, Any]) -> Dict[str, Optional[TemporalMetric]]:
        """Extract REIT-specific metrics from XBRL facts."""
        return {
            "rental_revenue": self.get_latest_value(facts, REIT_CONCEPTS["rental_revenue"]),
            "noi": self.get_latest_value(facts, REIT_CONCEPTS["noi"]),
            "ffo": self.get_latest_value(facts, REIT_CONCEPTS["ffo"]),
            "property_operating_expenses": self.get_latest_value(facts, REIT_CONCEPTS["property_operating_expenses"]),
        }

    def _extract_energy_metrics(self, facts: Dict[str, Any]) -> Dict[str, Optional[TemporalMetric]]:
        """Extract energy/oil & gas-specific metrics from XBRL facts."""
        return {
            "oil_gas_revenue": self.get_latest_value(facts, ENERGY_OG_CONCEPTS["oil_gas_revenue"]),
            "production_expense": self.get_latest_value(facts, ENERGY_OG_CONCEPTS["production_expense"]),
            "depletion": self.get_latest_value(facts, ENERGY_OG_CONCEPTS["depletion"]),
            "exploration_expense": self.get_latest_value(facts, ENERGY_OG_CONCEPTS["exploration_expense"]),
            "impairment": self.get_latest_value(facts, ENERGY_OG_CONCEPTS["impairment"]),
        }

    def _extract_utility_metrics(self, facts: Dict[str, Any]) -> Dict[str, Optional[TemporalMetric]]:
        """Extract utility-specific metrics from XBRL facts."""
        return {
            "electric_revenue": self.get_latest_value(facts, UTILITY_CONCEPTS["electric_revenue"]),
            "gas_revenue": self.get_latest_value(facts, UTILITY_CONCEPTS["gas_revenue"]),
            "fuel_cost": self.get_latest_value(facts, UTILITY_CONCEPTS["fuel_cost"]),
            "regulatory_assets": self.get_latest_value(facts, UTILITY_CONCEPTS["regulatory_assets"]),
            "rate_base": self.get_latest_value(facts, UTILITY_CONCEPTS["rate_base"]),
        }

    def _extract_technology_metrics(self, facts: Dict[str, Any]) -> Dict[str, Optional[TemporalMetric]]:
        """Extract technology-specific metrics from XBRL facts."""
        return {
            "rd_expense": self.get_latest_value(facts, TECHNOLOGY_CONCEPTS["rd_expense"]),
            "deferred_revenue": self.get_latest_value(facts, TECHNOLOGY_CONCEPTS["deferred_revenue"]),
            "subscription_revenue": self.get_latest_value(facts, TECHNOLOGY_CONCEPTS["subscription_revenue"]),
            "cost_of_revenue": self.get_latest_value(facts, TECHNOLOGY_CONCEPTS["cost_of_revenue"]),
            "stock_compensation": self.get_latest_value(facts, TECHNOLOGY_CONCEPTS["stock_compensation"]),
            "intangible_assets": self.get_latest_value(facts, TECHNOLOGY_CONCEPTS["intangible_assets"]),
            "goodwill": self.get_latest_value(facts, TECHNOLOGY_CONCEPTS["goodwill"]),
            "acquired_ip": self.get_latest_value(facts, TECHNOLOGY_CONCEPTS["acquired_ip"]),
        }

    def _extract_healthcare_metrics(self, facts: Dict[str, Any]) -> Dict[str, Optional[TemporalMetric]]:
        """Extract healthcare/pharma-specific metrics from XBRL facts."""
        return {
            "rd_expense": self.get_latest_value(facts, HEALTHCARE_CONCEPTS["rd_expense"]),
            "cost_of_revenue": self.get_latest_value(facts, HEALTHCARE_CONCEPTS["cost_of_revenue"]),
            "selling_general_admin": self.get_latest_value(facts, HEALTHCARE_CONCEPTS["selling_general_admin"]),
            "acquired_iprd": self.get_latest_value(facts, HEALTHCARE_CONCEPTS["acquired_iprd"]),
            "milestone_payments": self.get_latest_value(facts, HEALTHCARE_CONCEPTS["milestone_payments"]),
            "inventory": self.get_latest_value(facts, HEALTHCARE_CONCEPTS["inventory"]),
            "product_revenue": self.get_latest_value(facts, HEALTHCARE_CONCEPTS["product_revenue"]),
            "license_revenue": self.get_latest_value(facts, HEALTHCARE_CONCEPTS["license_revenue"]),
        }

    def _extract_retail_metrics(self, facts: Dict[str, Any]) -> Dict[str, Optional[TemporalMetric]]:
        """Extract retail-specific metrics from XBRL facts."""
        return {
            "cost_of_goods_sold": self.get_latest_value(facts, RETAIL_CONCEPTS["cost_of_goods_sold"]),
            "inventory": self.get_latest_value(facts, RETAIL_CONCEPTS["inventory"]),
            "selling_general_admin": self.get_latest_value(facts, RETAIL_CONCEPTS["selling_general_admin"]),
            "store_count": self.get_latest_value(facts, RETAIL_CONCEPTS["store_count"], unit="pure"),
            "depreciation": self.get_latest_value(facts, RETAIL_CONCEPTS["depreciation"]),
            "lease_expense": self.get_latest_value(facts, RETAIL_CONCEPTS["lease_expense"]),
            "same_store_sales": self.get_latest_value(facts, RETAIL_CONCEPTS["same_store_sales"], unit="pure"),
            "ecommerce_revenue": self.get_latest_value(facts, RETAIL_CONCEPTS["ecommerce_revenue"]),
        }

    def _extract_financials_metrics(self, facts: Dict[str, Any]) -> Dict[str, Optional[TemporalMetric]]:
        """Extract financials (non-bank) metrics from XBRL facts."""
        return {
            "advisory_fees": self.get_latest_value(facts, FINANCIALS_CONCEPTS["advisory_fees"]),
            "assets_under_management": self.get_latest_value(facts, FINANCIALS_CONCEPTS["assets_under_management"]),
            "trading_revenue": self.get_latest_value(facts, FINANCIALS_CONCEPTS["trading_revenue"]),
            "commission_revenue": self.get_latest_value(facts, FINANCIALS_CONCEPTS["commission_revenue"]),
            "compensation_expense": self.get_latest_value(facts, FINANCIALS_CONCEPTS["compensation_expense"]),
            "investment_income": self.get_latest_value(facts, FINANCIALS_CONCEPTS["investment_income"]),
            "performance_fees": self.get_latest_value(facts, FINANCIALS_CONCEPTS["performance_fees"]),
            "fund_expenses": self.get_latest_value(facts, FINANCIALS_CONCEPTS["fund_expenses"]),
        }

    def _extract_industrials_metrics(self, facts: Dict[str, Any]) -> Dict[str, Optional[TemporalMetric]]:
        """Extract industrials/manufacturing metrics from XBRL facts."""
        return {
            "cost_of_goods_sold": self.get_latest_value(facts, INDUSTRIALS_CONCEPTS["cost_of_goods_sold"]),
            "inventory": self.get_latest_value(facts, INDUSTRIALS_CONCEPTS["inventory"]),
            "depreciation": self.get_latest_value(facts, INDUSTRIALS_CONCEPTS["depreciation"]),
            "backlog": self.get_latest_value(facts, INDUSTRIALS_CONCEPTS["backlog"]),
            "capital_expenditure": self.get_latest_value(facts, INDUSTRIALS_CONCEPTS["capital_expenditure"]),
            "property_plant_equipment": self.get_latest_value(facts, INDUSTRIALS_CONCEPTS["property_plant_equipment"]),
            "pension_expense": self.get_latest_value(facts, INDUSTRIALS_CONCEPTS["pension_expense"]),
            "warranty_expense": self.get_latest_value(facts, INDUSTRIALS_CONCEPTS["warranty_expense"]),
        }

    def _extract_transportation_metrics(self, facts: Dict[str, Any]) -> Dict[str, Optional[TemporalMetric]]:
        """Extract transportation-specific metrics from XBRL facts."""
        return {
            "operating_revenue": self.get_latest_value(facts, TRANSPORTATION_CONCEPTS["operating_revenue"]),
            "fuel_expense": self.get_latest_value(facts, TRANSPORTATION_CONCEPTS["fuel_expense"]),
            "labor_expense": self.get_latest_value(facts, TRANSPORTATION_CONCEPTS["labor_expense"]),
            "depreciation": self.get_latest_value(facts, TRANSPORTATION_CONCEPTS["depreciation"]),
            "maintenance_expense": self.get_latest_value(facts, TRANSPORTATION_CONCEPTS["maintenance_expense"]),
            "revenue_passenger_miles": self.get_latest_value(facts, TRANSPORTATION_CONCEPTS["revenue_passenger_miles"], unit="pure"),
            "available_seat_miles": self.get_latest_value(facts, TRANSPORTATION_CONCEPTS["available_seat_miles"], unit="pure"),
            "load_factor": self.get_latest_value(facts, TRANSPORTATION_CONCEPTS["load_factor"], unit="pure"),
            "fleet_size": self.get_latest_value(facts, TRANSPORTATION_CONCEPTS["fleet_size"], unit="pure"),
        }

    def _extract_materials_metrics(self, facts: Dict[str, Any]) -> Dict[str, Optional[TemporalMetric]]:
        """Extract materials-specific metrics from XBRL facts."""
        return {
            "cost_of_goods_sold": self.get_latest_value(facts, MATERIALS_CONCEPTS["cost_of_goods_sold"]),
            "inventory": self.get_latest_value(facts, MATERIALS_CONCEPTS["inventory"]),
            "depreciation": self.get_latest_value(facts, MATERIALS_CONCEPTS["depreciation"]),
            "energy_costs": self.get_latest_value(facts, MATERIALS_CONCEPTS["energy_costs"]),
            "environmental_liabilities": self.get_latest_value(facts, MATERIALS_CONCEPTS["environmental_liabilities"]),
            "property_plant_equipment": self.get_latest_value(facts, MATERIALS_CONCEPTS["property_plant_equipment"]),
            "capital_expenditure": self.get_latest_value(facts, MATERIALS_CONCEPTS["capital_expenditure"]),
            "raw_materials": self.get_latest_value(facts, MATERIALS_CONCEPTS["raw_materials"]),
        }

    def _extract_mining_metrics(self, facts: Dict[str, Any]) -> Dict[str, Optional[TemporalMetric]]:
        """Extract mining-specific metrics from XBRL facts."""
        return {
            "mining_revenue": self.get_latest_value(facts, MINING_CONCEPTS["mining_revenue"]),
            "cost_of_production": self.get_latest_value(facts, MINING_CONCEPTS["cost_of_production"]),
            "depletion": self.get_latest_value(facts, MINING_CONCEPTS["depletion"]),
            "exploration_expense": self.get_latest_value(facts, MINING_CONCEPTS["exploration_expense"]),
            "reclamation_liabilities": self.get_latest_value(facts, MINING_CONCEPTS["reclamation_liabilities"]),
            "mineral_reserves": self.get_latest_value(facts, MINING_CONCEPTS["mineral_reserves"], unit="pure"),
            "depreciation": self.get_latest_value(facts, MINING_CONCEPTS["depreciation"]),
            "royalty_expense": self.get_latest_value(facts, MINING_CONCEPTS["royalty_expense"]),
        }

    def parse_debt_metrics(
        self,
        facts: Dict[str, Any],
        ticker: str
    ) -> DebtMetrics:
        """
        Parse debt and leverage metrics from XBRL facts.

        Args:
            facts: Company facts dict from SEC EDGAR
            ticker: Stock ticker symbol

        Returns:
            DebtMetrics with all debt-related metrics
        """
        # Use get_most_recent_across_concepts for debt to ensure freshest data
        long_term_debt = self.get_most_recent_across_concepts(facts, LONG_TERM_DEBT_CONCEPTS)
        short_term_debt = self.get_latest_value(facts, SHORT_TERM_DEBT_CONCEPTS)
        cash = self.get_latest_value(facts, CASH_CONCEPTS)
        stockholders_equity = self.get_latest_value(facts, STOCKHOLDERS_EQUITY_CONCEPTS)

        # Calculate total debt - use get_most_recent_across_concepts for freshest data
        total_debt_val = None
        total_debt = self.get_most_recent_across_concepts(facts, TOTAL_DEBT_CONCEPTS)
        if not total_debt:
            lt_val = long_term_debt.value if long_term_debt else 0
            st_val = short_term_debt.value if short_term_debt else 0
            if lt_val or st_val:
                total_debt_val = (lt_val or 0) + (st_val or 0)
                total_debt = self.create_temporal_metric(
                    total_debt_val,
                    long_term_debt or short_term_debt
                )

        # Calculate net debt
        net_debt = None
        if total_debt and total_debt.value is not None and cash and cash.value is not None:
            net_debt = self.create_temporal_metric(
                total_debt.value - cash.value,
                total_debt
            )

        # Calculate debt to equity
        debt_to_equity = None
        if total_debt and total_debt.value and stockholders_equity and stockholders_equity.value:
            if stockholders_equity.value > 0:
                debt_to_equity = self.create_temporal_metric(
                    round(total_debt.value / stockholders_equity.value, 2),
                    total_debt
                )

        return DebtMetrics(
            ticker=ticker.upper(),
            long_term_debt=long_term_debt,
            short_term_debt=short_term_debt,
            total_debt=total_debt,
            cash=cash,
            net_debt=net_debt,
            debt_to_equity=debt_to_equity,
            source="SEC EDGAR XBRL",
        )

    def parse_cash_flow(
        self,
        facts: Dict[str, Any],
        ticker: str
    ) -> CashFlowMetrics:
        """
        Parse cash flow metrics from XBRL facts.

        Args:
            facts: Company facts dict from SEC EDGAR
            ticker: Stock ticker symbol

        Returns:
            CashFlowMetrics with all cash flow metrics
        """
        operating_cf = self.get_latest_value(facts, OPERATING_CF_CONCEPTS)
        capex = self.get_latest_value(facts, CAPEX_CONCEPTS)
        rd_expense = self.get_latest_value(facts, RD_CONCEPTS)

        # Calculate free cash flow
        free_cash_flow = None
        if operating_cf and operating_cf.value is not None:
            capex_val = capex.value if capex and capex.value else 0
            free_cash_flow = self.create_temporal_metric(
                operating_cf.value - abs(capex_val),
                operating_cf
            )

        return CashFlowMetrics(
            ticker=ticker.upper(),
            operating_cash_flow=operating_cf,
            capital_expenditure=capex,
            free_cash_flow=free_cash_flow,
            rd_expense=rd_expense,
            source="SEC EDGAR XBRL",
        )

    # =========================================================================
    # YAHOO FINANCE PARSING
    # =========================================================================

    def parse_yfinance_data(
        self,
        data: Dict[str, Any],
        ticker: str
    ) -> Tuple[ParsedFinancials, DebtMetrics, CashFlowMetrics]:
        """
        Parse Yahoo Finance data into structured metrics.

        Args:
            data: Raw yfinance data dict
            ticker: Stock ticker symbol

        Returns:
            Tuple of (ParsedFinancials, DebtMetrics, CashFlowMetrics)
        """
        # Extract temporal fields from Yahoo Finance
        most_recent_quarter = data.get("most_recent_quarter")  # Period end for financials
        regular_market_time = data.get("regular_market_time")  # Last updated time

        # Income statement items - TTM (Trailing Twelve Months)
        revenue = TemporalMetric(
            value=data.get("revenue"),
            data_type="TTM",
            end_date=most_recent_quarter,
            filed=regular_market_time
        ) if data.get("revenue") else None
        net_income = TemporalMetric(
            value=data.get("net_income"),
            data_type="TTM",
            end_date=most_recent_quarter,
            filed=regular_market_time
        ) if data.get("net_income") else None
        gross_profit = TemporalMetric(
            value=data.get("gross_profit"),
            data_type="TTM",
            end_date=most_recent_quarter,
            filed=regular_market_time
        ) if data.get("gross_profit") else None
        operating_income = TemporalMetric(
            value=data.get("operating_income"),
            data_type="TTM",
            end_date=most_recent_quarter,
            filed=regular_market_time
        ) if data.get("operating_income") else None

        # Calculate margins - TTM
        gross_margin_pct = None
        operating_margin_pct = None
        net_margin_pct = None

        if revenue and revenue.value and revenue.value > 0:
            if gross_profit and gross_profit.value:
                gross_margin_pct = TemporalMetric(
                    value=round((gross_profit.value / revenue.value) * 100, 2),
                    data_type="TTM",
                    end_date=most_recent_quarter,
                    filed=regular_market_time
                )
            if operating_income and operating_income.value:
                operating_margin_pct = TemporalMetric(
                    value=round((operating_income.value / revenue.value) * 100, 2),
                    data_type="TTM",
                    end_date=most_recent_quarter,
                    filed=regular_market_time
                )
            if net_income and net_income.value:
                net_margin_pct = TemporalMetric(
                    value=round((net_income.value / revenue.value) * 100, 2),
                    data_type="TTM",
                    end_date=most_recent_quarter,
                    filed=regular_market_time
                )

        # Balance sheet items - Point-in-time
        financials = ParsedFinancials(
            ticker=ticker.upper(),
            revenue=revenue,
            net_income=net_income,
            gross_profit=gross_profit,
            operating_income=operating_income,
            gross_margin_pct=gross_margin_pct,
            operating_margin_pct=operating_margin_pct,
            net_margin_pct=net_margin_pct,
            total_assets=TemporalMetric(value=data.get("total_assets"), data_type="Point-in-time", end_date=most_recent_quarter, filed=regular_market_time) if data.get("total_assets") else None,
            total_liabilities=TemporalMetric(value=data.get("total_liabilities"), data_type="Point-in-time", end_date=most_recent_quarter, filed=regular_market_time) if data.get("total_liabilities") else None,
            stockholders_equity=TemporalMetric(value=data.get("stockholders_equity"), data_type="Point-in-time", end_date=most_recent_quarter, filed=regular_market_time) if data.get("stockholders_equity") else None,
            source="Yahoo Finance",
        )

        # Debt - Point-in-time (balance sheet)
        total_debt = TemporalMetric(value=data.get("total_debt"), data_type="Point-in-time", end_date=most_recent_quarter, filed=regular_market_time) if data.get("total_debt") else None
        cash = TemporalMetric(value=data.get("cash"), data_type="Point-in-time", end_date=most_recent_quarter, filed=regular_market_time) if data.get("cash") else None

        net_debt = None
        if total_debt and total_debt.value and cash and cash.value:
            net_debt = TemporalMetric(value=total_debt.value - cash.value, data_type="Point-in-time", end_date=most_recent_quarter, filed=regular_market_time)

        debt_to_equity = None
        equity_val = data.get("stockholders_equity")
        if total_debt and total_debt.value and equity_val and equity_val > 0:
            debt_to_equity = TemporalMetric(value=round(total_debt.value / equity_val, 2), data_type="Point-in-time", end_date=most_recent_quarter, filed=regular_market_time)

        debt = DebtMetrics(
            ticker=ticker.upper(),
            total_debt=total_debt,
            cash=cash,
            net_debt=net_debt,
            debt_to_equity=debt_to_equity,
            source="Yahoo Finance",
        )

        # Cash flow - TTM
        operating_cf = TemporalMetric(value=data.get("operating_cash_flow"), data_type="TTM", end_date=most_recent_quarter, filed=regular_market_time) if data.get("operating_cash_flow") else None
        free_cf = TemporalMetric(value=data.get("free_cash_flow"), data_type="TTM", end_date=most_recent_quarter, filed=regular_market_time) if data.get("free_cash_flow") else None

        cash_flow = CashFlowMetrics(
            ticker=ticker.upper(),
            operating_cash_flow=operating_cf,
            free_cash_flow=free_cf,
            source="Yahoo Finance",
        )

        return financials, debt, cash_flow

    # =========================================================================
    # SWOT ANALYSIS
    # =========================================================================

    def build_swot_summary(
        self,
        financials: ParsedFinancials,
        debt: DebtMetrics,
        cash_flow: CashFlowMetrics
    ) -> SwotSummary:
        """
        Build SWOT summary from financial metrics.

        Args:
            financials: Parsed financial metrics
            debt: Debt metrics
            cash_flow: Cash flow metrics

        Returns:
            SwotSummary with categorized insights
        """
        strengths = []
        weaknesses = []
        opportunities = []
        threats = []

        # Revenue growth analysis
        if financials.revenue_growth_3yr is not None:
            growth = financials.revenue_growth_3yr
            if growth > REVENUE_GROWTH_STRONG:
                strengths.append(f"Strong revenue growth: {growth:.1f}% 3-year CAGR")
            elif growth > REVENUE_GROWTH_POSITIVE:
                strengths.append(f"Positive revenue growth: {growth:.1f}% 3-year CAGR")
            elif growth < REVENUE_GROWTH_DECLINING:
                weaknesses.append(f"Declining revenue: {growth:.1f}% 3-year CAGR")

        # Net margin analysis
        if financials.net_margin_pct and financials.net_margin_pct.value is not None:
            margin = financials.net_margin_pct.value
            if margin > NET_MARGIN_HIGH:
                strengths.append(f"High profitability: {margin:.1f}% net margin")
            elif margin < NET_MARGIN_UNPROFITABLE:
                weaknesses.append(f"Unprofitable: {margin:.1f}% net margin")
            elif margin < NET_MARGIN_THIN:
                weaknesses.append(f"Thin margins: {margin:.1f}% net margin")

        # Operating margin analysis
        if financials.operating_margin_pct and financials.operating_margin_pct.value is not None:
            op_margin = financials.operating_margin_pct.value
            if op_margin > OPERATING_MARGIN_STRONG:
                strengths.append(f"Strong operating efficiency: {op_margin:.1f}% operating margin")

        # Debt analysis
        if debt.debt_to_equity and debt.debt_to_equity.value is not None:
            de_ratio = debt.debt_to_equity.value
            if de_ratio > DEBT_TO_EQUITY_HIGH:
                threats.append(f"High leverage: {de_ratio:.2f}x debt-to-equity ratio")
            elif de_ratio > DEBT_TO_EQUITY_ELEVATED:
                weaknesses.append(f"Elevated debt: {de_ratio:.2f}x debt-to-equity ratio")
            elif de_ratio < DEBT_TO_EQUITY_LOW:
                strengths.append(f"Low leverage: {de_ratio:.2f}x debt-to-equity ratio")

        # Cash flow analysis
        if cash_flow.free_cash_flow and cash_flow.free_cash_flow.value is not None:
            fcf = cash_flow.free_cash_flow.value
            if fcf > 0:
                strengths.append(f"Positive free cash flow: ${fcf / 1e9:.1f}B")
            else:
                weaknesses.append(f"Negative free cash flow: ${fcf / 1e9:.1f}B")

        # R&D analysis (opportunity indicator)
        if cash_flow.rd_expense and cash_flow.rd_expense.value:
            if financials.revenue and financials.revenue.value and financials.revenue.value > 0:
                rd_pct = (cash_flow.rd_expense.value / financials.revenue.value) * 100
                if rd_pct > RD_HIGH_INVESTMENT:
                    opportunities.append(f"High R&D investment: {rd_pct:.1f}% of revenue")

        return SwotSummary(
            strengths=strengths,
            weaknesses=weaknesses,
            opportunities=opportunities,
            threats=threats,
        )


# Global parser instance
_parser_service: Optional[ParserService] = None


def get_parser_service() -> ParserService:
    """Get or create the global parser service instance."""
    global _parser_service
    if _parser_service is None:
        _parser_service = ParserService()
    return _parser_service
