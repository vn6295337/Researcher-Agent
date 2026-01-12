"""
Orchestrator Service for Financials-Basket MCP Server

Coordinates Fetcher, Parser, and Cache services:
- Request routing and tool execution
- Fallback chain: SEC EDGAR → Yahoo Finance → Minimal
- Timeout enforcement
- Response aggregation and SWOT compilation
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from config import TOOL_TIMEOUT
from models.schemas import (
    TemporalMetric,
    ParsedFinancials,
    DebtMetrics,
    CashFlowMetrics,
    SwotSummary,
    FinancialsBasket,
)
from models.errors import (
    CIKNotFoundError,
    APITimeoutError,
    CircuitOpenError,
)
from services.cache import CacheService, get_cache_service
from services.fetcher import FetcherService, get_fetcher_service
from services.parser import ParserService, get_parser_service

logger = logging.getLogger("fundamentals-basket.orchestrator")


class OrchestratorService:
    """
    Orchestrator service for coordinating data flow.

    Features:
    - 3-tier fallback chain (SEC EDGAR → Yahoo → Minimal)
    - Guarantees 100% response rate
    - Per-tool timeout enforcement
    - Cache-first data retrieval
    """

    def __init__(
        self,
        cache: Optional[CacheService] = None,
        fetcher: Optional[FetcherService] = None,
        parser: Optional[ParserService] = None,
    ):
        self.cache = cache or get_cache_service()
        self.fetcher = fetcher or get_fetcher_service()
        self.parser = parser or get_parser_service()

    # =========================================================================
    # COMPANY INFO
    # =========================================================================

    async def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """
        Get company information.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Company info dict with name, CIK, SIC, etc.
        """
        ticker = ticker.upper()

        # Check cache first
        cached = await self.cache.get_company_info(ticker)
        if cached:
            return cached

        # Get CIK
        cik = await self._get_cik_with_cache(ticker)
        if not cik:
            return {
                "ticker": ticker,
                "error": "CIK not found",
                "fallback": True,
            }

        try:
            # Fetch submissions
            submissions = await self.fetcher.fetch_company_submissions(cik)

            info = {
                "ticker": ticker,
                "cik": cik,
                "name": submissions.get("name"),
                "sic": submissions.get("sic"),
                "sic_description": submissions.get("sicDescription"),
                "state_of_incorporation": submissions.get("stateOfIncorporation"),
                "fiscal_year_end": submissions.get("fiscalYearEnd"),
                "source": "SEC EDGAR",
            }

            # Cache the result
            await self.cache.set_company_info(ticker, info)

            return info

        except Exception as e:
            logger.error(f"Failed to get company info for {ticker}: {e}")
            return {
                "ticker": ticker,
                "error": str(e),
                "fallback": True,
            }

    # =========================================================================
    # FINANCIALS
    # =========================================================================

    async def get_financials(self, ticker: str) -> Dict[str, Any]:
        """
        Get financial metrics.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Financials dict with revenue, margins, etc.
        """
        ticker = ticker.upper()

        # Get CIK
        cik = await self._get_cik_with_cache(ticker)
        if not cik:
            # Fallback to Yahoo Finance
            return await self._get_yfinance_financials(ticker)

        try:
            # Fetch company facts
            facts = await self._get_facts_with_cache(cik)
            if not facts:
                return await self._get_yfinance_financials(ticker)

            # Parse financials
            financials = self.parser.parse_financials(facts, ticker)
            return financials.to_dict()

        except (APITimeoutError, CircuitOpenError) as e:
            logger.warning(f"SEC EDGAR failed for {ticker}, using Yahoo fallback: {e}")
            return await self._get_yfinance_financials(ticker)

        except Exception as e:
            logger.error(f"Failed to get financials for {ticker}: {e}")
            return await self._get_yfinance_financials(ticker)

    async def get_debt_metrics(self, ticker: str) -> Dict[str, Any]:
        """
        Get debt and leverage metrics.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Debt metrics dict
        """
        ticker = ticker.upper()

        cik = await self._get_cik_with_cache(ticker)
        if not cik:
            return {"ticker": ticker, "error": "CIK not found", "fallback": True}

        try:
            facts = await self._get_facts_with_cache(cik)
            if not facts:
                return {"ticker": ticker, "error": "No facts available", "fallback": True}

            debt = self.parser.parse_debt_metrics(facts, ticker)
            return debt.to_dict()

        except Exception as e:
            logger.error(f"Failed to get debt metrics for {ticker}: {e}")
            return {"ticker": ticker, "error": str(e), "fallback": True}

    async def get_cash_flow(self, ticker: str) -> Dict[str, Any]:
        """
        Get cash flow metrics.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Cash flow metrics dict
        """
        ticker = ticker.upper()

        cik = await self._get_cik_with_cache(ticker)
        if not cik:
            return {"ticker": ticker, "error": "CIK not found", "fallback": True}

        try:
            facts = await self._get_facts_with_cache(cik)
            if not facts:
                return {"ticker": ticker, "error": "No facts available", "fallback": True}

            cash_flow = self.parser.parse_cash_flow(facts, ticker)
            return cash_flow.to_dict()

        except Exception as e:
            logger.error(f"Failed to get cash flow for {ticker}: {e}")
            return {"ticker": ticker, "error": str(e), "fallback": True}

    # =========================================================================
    # SEC FUNDAMENTALS BASKET (Main Aggregator)
    # =========================================================================

    async def get_sec_fundamentals_basket(self, ticker: str) -> Dict[str, Any]:
        """
        Get complete SEC fundamentals basket with SWOT.

        This is the primary aggregator that:
        1. Fetches all data from SEC EDGAR
        2. Falls back to Yahoo Finance if SEC fails
        3. Falls back to minimal response if all fail
        4. Always generates a SWOT summary

        Args:
            ticker: Stock ticker symbol

        Returns:
            Complete financials basket with SWOT
        """
        ticker = ticker.upper()
        logger.info(f"Getting SEC fundamentals basket for {ticker}")

        # Try SEC EDGAR first
        cik = await self._get_cik_with_cache(ticker)

        if cik:
            try:
                result = await self._get_sec_basket(ticker, cik)
                if result and "error" not in result:
                    return result
            except Exception as e:
                logger.warning(f"SEC EDGAR failed for {ticker}: {e}")

        # Fallback to Yahoo Finance
        try:
            result = await self._get_yahoo_basket(ticker)
            if result and "error" not in result:
                return result
        except Exception as e:
            logger.warning(f"Yahoo Finance failed for {ticker}: {e}")

        # Final fallback - minimal response
        return self._get_minimal_fallback(ticker)

    async def _get_sec_basket(self, ticker: str, cik: str) -> Dict[str, Any]:
        """Get complete basket from SEC EDGAR."""
        # Fetch company facts
        facts = await self._get_facts_with_cache(cik)
        if not facts:
            raise ValueError("No company facts available")

        # Parse all metrics
        financials = self.parser.parse_financials(facts, ticker)
        debt = self.parser.parse_debt_metrics(facts, ticker)
        cash_flow = self.parser.parse_cash_flow(facts, ticker)

        # Build SWOT
        swot = self.parser.build_swot_summary(financials, debt, cash_flow)

        # Get company info
        company_info = await self.get_company_info(ticker)

        # Build basket
        basket = FinancialsBasket(
            ticker=ticker,
            company=company_info,
            financials=financials,
            debt=debt,
            cash_flow=cash_flow,
            swot_summary=swot,
            source="SEC EDGAR XBRL",
        )

        return basket.to_dict()

    async def _get_yahoo_basket(self, ticker: str) -> Dict[str, Any]:
        """Get complete basket from Yahoo Finance (fallback)."""
        # Fetch from Yahoo
        data = await self.fetcher.fetch_yfinance(ticker)

        if "error" in data:
            raise ValueError(data["error"])

        # Parse Yahoo data
        financials, debt, cash_flow = self.parser.parse_yfinance_data(data, ticker)

        # Build SWOT
        swot = self.parser.build_swot_summary(financials, debt, cash_flow)

        # Build basket
        basket = FinancialsBasket(
            ticker=ticker,
            company={
                "ticker": ticker,
                "name": data.get("name"),
                "sector": data.get("sector"),
                "industry": data.get("industry"),
            },
            financials=financials,
            debt=debt,
            cash_flow=cash_flow,
            swot_summary=swot,
            source="Yahoo Finance",
            fallback=True,
            fallback_reason="SEC EDGAR unavailable",
        )

        return basket.to_dict()

    def _get_minimal_fallback(self, ticker: str) -> Dict[str, Any]:
        """
        Get minimal fallback response.

        This ALWAYS succeeds and returns a valid response structure.
        """
        return {
            "ticker": ticker.upper(),
            "company": {"name": ticker.upper()},
            "financials": {"note": "Data temporarily unavailable"},
            "debt": {"note": "Data temporarily unavailable"},
            "cash_flow": {"note": "Data temporarily unavailable"},
            "swot_summary": {
                "strengths": [],
                "weaknesses": [],
                "opportunities": [],
                "threats": [],
                "note": "SWOT unavailable - data sources temporarily unavailable",
            },
            "source": "Minimal Fallback",
            "fallback": True,
            "fallback_reason": "All data sources unavailable",
            "generated_at": datetime.now().strftime("%Y-%m-%d"),
        }

    # =========================================================================
    # ALL SOURCES (Multi-Source Comparison)
    # =========================================================================

    async def get_all_sources_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """
        Get financials from ALL sources for comparison.
        Returns NORMALIZED schema for source_comparison group.

        Fetches from SEC EDGAR and Yahoo Finance in parallel,
        returning side-by-side comparison.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Normalized source_comparison dict
        """
        ticker = ticker.upper()
        logger.info(f"Getting all sources financials for {ticker}")

        # Fetch from both sources in parallel
        sec_task = self._get_sec_data_safe(ticker)
        yahoo_task = self._get_yahoo_data_safe(ticker)

        sec_result, yahoo_result = await asyncio.gather(sec_task, yahoo_task)

        # Build normalized source_comparison schema
        sources = {}
        sec_failed = "error" in sec_result or not sec_result.get("data")

        # Add SEC EDGAR data if available
        if not sec_failed:
            sources["sec_edgar"] = {
                "source": sec_result.get("source"),
                "data": sec_result.get("data"),
            }

        # Add Yahoo Finance data
        if "error" not in yahoo_result:
            if sec_failed:
                # FALLBACK: Yahoo provides core + supplementary when SEC fails
                yahoo_data = await self._get_yahoo_fallback_data(ticker)
                if yahoo_data.get("data"):
                    sources["yahoo_finance"] = yahoo_data
            elif yahoo_result.get("data"):
                # SUPPLEMENTARY: Only additional metrics
                sources["yahoo_finance"] = {
                    "source": yahoo_result.get("source"),
                    "data": yahoo_result.get("data"),
                }

        return {
            "group": "source_comparison",
            "ticker": ticker,
            "sources": sources,
            "source": "fundamentals-basket",
            "as_of": datetime.now().strftime("%Y-%m-%d"),
        }

    async def _get_sec_data_safe(self, ticker: str) -> Dict[str, Any]:
        """Get SEC data with error handling. Returns 6 universal metrics only."""
        try:
            cik = await self._get_cik_with_cache(ticker)
            if not cik:
                return {"error": "CIK not found", "source": "SEC EDGAR"}

            facts = await self._get_facts_with_cache(cik)
            if not facts:
                return {"error": "No facts available", "source": "SEC EDGAR"}

            financials = self.parser.parse_financials(facts, ticker)

            # Helper to convert TemporalMetric to dict
            def to_metric_dict(tm):
                if tm is None:
                    return None
                return {
                    "value": tm.value,
                    "end_date": tm.end_date,
                    "data_type": tm.data_type,
                    "fiscal_year": tm.fiscal_year,
                    "form": tm.form,
                }

            # Only 6 universal metrics (works across all industries)
            return {
                "source": "SEC EDGAR XBRL",
                "as_of": datetime.now().strftime("%Y-%m-%d"),
                "data": {
                    "revenue": to_metric_dict(financials.revenue),
                    "net_income": to_metric_dict(financials.net_income),
                    "net_margin_pct": to_metric_dict(financials.net_margin_pct),
                    "total_assets": to_metric_dict(financials.total_assets),
                    "total_liabilities": to_metric_dict(financials.total_liabilities),
                    "stockholders_equity": to_metric_dict(financials.stockholders_equity),
                },
            }

        except Exception as e:
            logger.error(f"SEC data fetch failed for {ticker}: {e}")
            return {"error": str(e), "source": "SEC EDGAR"}

    async def _get_yahoo_data_safe(self, ticker: str) -> Dict[str, Any]:
        """Get Yahoo data with error handling. Returns supplementary metrics only."""
        try:
            data = await self.fetcher.fetch_yfinance(ticker)

            if "error" in data:
                return {"error": data["error"], "source": "Yahoo Finance"}

            financials, debt, cash_flow = self.parser.parse_yfinance_data(data, ticker)

            # Helper to convert TemporalMetric to dict
            def to_metric_dict(tm):
                if tm is None:
                    return None
                return {
                    "value": tm.value,
                    "end_date": tm.end_date,
                    "data_type": tm.data_type,
                    "fiscal_year": tm.fiscal_year,
                    "form": tm.form,
                }

            # Only supplementary metrics not in SEC EDGAR (avoid duplicates)
            return {
                "source": "Yahoo Finance",
                "as_of": datetime.now().strftime("%Y-%m-%d"),
                "data": {
                    "operating_margin_pct": to_metric_dict(financials.operating_margin_pct),
                    "total_debt": to_metric_dict(debt.total_debt) if hasattr(debt, 'total_debt') else None,
                    "operating_cash_flow": to_metric_dict(cash_flow.operating_cash_flow) if hasattr(cash_flow, 'operating_cash_flow') else None,
                    "free_cash_flow": to_metric_dict(cash_flow.free_cash_flow) if hasattr(cash_flow, 'free_cash_flow') else None,
                },
            }

        except Exception as e:
            logger.error(f"Yahoo data fetch failed for {ticker}: {e}")
            return {"error": str(e), "source": "Yahoo Finance"}

    async def _get_yahoo_fallback_data(self, ticker: str) -> Dict[str, Any]:
        """Get Yahoo data as fallback when SEC fails. Returns core + supplementary metrics."""
        try:
            data = await self.fetcher.fetch_yfinance(ticker)

            if "error" in data:
                return {"error": data["error"], "source": "Yahoo Finance"}

            financials, debt, cash_flow = self.parser.parse_yfinance_data(data, ticker)

            def to_metric_dict(tm):
                if tm is None:
                    return None
                return {
                    "value": tm.value,
                    "end_date": tm.end_date,
                    "data_type": tm.data_type,
                }

            # FALLBACK: Core metrics + supplementary metrics
            return {
                "source": "Yahoo Finance",
                "as_of": datetime.now().strftime("%Y-%m-%d"),
                "data": {
                    # Core metrics (normally from SEC)
                    "revenue": to_metric_dict(financials.revenue),
                    "net_income": to_metric_dict(financials.net_income),
                    "net_margin_pct": to_metric_dict(financials.net_margin_pct),
                    "total_assets": to_metric_dict(debt.total_assets) if hasattr(debt, 'total_assets') else None,
                    # Supplementary metrics
                    "operating_margin_pct": to_metric_dict(financials.operating_margin_pct),
                    "total_debt": to_metric_dict(debt.total_debt) if hasattr(debt, 'total_debt') else None,
                    "operating_cash_flow": to_metric_dict(cash_flow.operating_cash_flow) if hasattr(cash_flow, 'operating_cash_flow') else None,
                    "free_cash_flow": to_metric_dict(cash_flow.free_cash_flow) if hasattr(cash_flow, 'free_cash_flow') else None,
                },
            }

        except Exception as e:
            logger.error(f"Yahoo fallback fetch failed for {ticker}: {e}")
            return {"error": str(e), "source": "Yahoo Finance"}

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _get_cik_with_cache(self, ticker: str) -> Optional[str]:
        """Get CIK with caching."""
        ticker = ticker.upper()

        # Check cache
        cached_cik = await self.cache.get_cik(ticker)
        if cached_cik:
            return cached_cik

        # Fetch from SEC
        cik = await self.fetcher.fetch_cik(ticker)
        if cik:
            await self.cache.set_cik(ticker, cik)

        return cik

    async def _get_facts_with_cache(self, cik: str) -> Optional[Dict[str, Any]]:
        """Get company facts with caching."""
        # Check cache
        cached_facts = await self.cache.get_company_facts(cik)
        if cached_facts:
            return cached_facts

        # Fetch from SEC
        try:
            facts = await self.fetcher.fetch_company_facts(cik)
            await self.cache.set_company_facts(cik, facts)
            return facts
        except Exception as e:
            logger.error(f"Failed to fetch company facts for CIK {cik}: {e}")
            return None

    async def _get_yfinance_financials(self, ticker: str) -> Dict[str, Any]:
        """Get financials from Yahoo Finance (fallback)."""
        try:
            data = await self.fetcher.fetch_yfinance(ticker)

            if "error" in data:
                return {
                    "ticker": ticker.upper(),
                    "error": data["error"],
                    "fallback": True,
                }

            financials, _, _ = self.parser.parse_yfinance_data(data, ticker)
            result = financials.to_dict()
            result["fallback"] = True
            result["fallback_reason"] = "SEC EDGAR unavailable"
            return result

        except Exception as e:
            return {
                "ticker": ticker.upper(),
                "error": str(e),
                "fallback": True,
            }

    # =========================================================================
    # TOOL EXECUTION
    # =========================================================================

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name.

        This is the main entry point for MCP tool calls.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result dict
        """
        ticker = arguments.get("ticker", "").upper()

        tool_handlers = {
            "get_company_info": lambda: self.get_company_info(ticker),
            "get_financials": lambda: self.get_financials(ticker),
            "get_debt_metrics": lambda: self.get_debt_metrics(ticker),
            "get_cash_flow": lambda: self.get_cash_flow(ticker),
            "get_sec_fundamentals": lambda: self.get_sec_fundamentals_basket(ticker),
            "get_all_sources_fundamentals": lambda: self.get_all_sources_fundamentals(ticker),
        }

        handler = tool_handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}

        try:
            return await asyncio.wait_for(handler(), timeout=TOOL_TIMEOUT)
        except asyncio.TimeoutError:
            logger.error(f"Tool {name} timed out after {TOOL_TIMEOUT}s for {ticker}")
            return {
                "error": f"Tool execution timed out after {TOOL_TIMEOUT} seconds",
                "ticker": ticker,
                "tool": name,
                "fallback": True,
            }
        except Exception as e:
            logger.error(f"Tool {name} failed for {ticker}: {e}")
            return {
                "error": str(e),
                "ticker": ticker,
                "tool": name,
                "fallback": True,
            }

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator and service status."""
        return {
            "cache": self.cache.get_stats(),
            "fetcher": self.fetcher.get_status(),
        }


# Global orchestrator instance
_orchestrator_service: Optional[OrchestratorService] = None


def get_orchestrator_service() -> OrchestratorService:
    """Get or create the global orchestrator service instance."""
    global _orchestrator_service
    if _orchestrator_service is None:
        _orchestrator_service = OrchestratorService()
    return _orchestrator_service
