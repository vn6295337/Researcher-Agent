"""
Configuration for Financials-Basket MCP Server

Centralized configuration for timeouts, rate limits, circuit breaker,
and SWOT analysis thresholds.
"""

# =============================================================================
# TIMEOUTS (seconds) - Increased for completeness-first mode
# =============================================================================

# Global timeout for MCP tool execution
TOOL_TIMEOUT = 90.0  # Match mcp_client timeout

# Per-source timeouts (increased for reliability)
SEC_EDGAR_TIMEOUT = 30.0
SEC_EDGAR_DOCUMENT_TIMEOUT = 45.0  # For fetching full 10-K documents
YAHOO_FINANCE_TIMEOUT = 30.0
CIK_LOOKUP_TIMEOUT = 15.0

# =============================================================================
# RATE LIMITING
# =============================================================================

# SEC EDGAR: 10 requests per second (official limit)
SEC_RATE_LIMIT_REQUESTS = 10
SEC_RATE_LIMIT_PERIOD = 1.0  # seconds

# Yahoo Finance: 5 requests per second (conservative)
YAHOO_RATE_LIMIT_REQUESTS = 5
YAHOO_RATE_LIMIT_PERIOD = 1.0

# =============================================================================
# RETRY CONFIGURATION
# =============================================================================

# Exponential backoff: 1s, 2s, 4s
RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_DELAY = 1.0
RETRY_EXPONENTIAL_BASE = 2

# HTTP status codes that trigger retry
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

# SEC EDGAR circuit breaker
SEC_CB_FAILURE_THRESHOLD = 5  # Open after 5 consecutive failures
SEC_CB_SUCCESS_THRESHOLD = 3  # Close after 3 consecutive successes
SEC_CB_HALF_OPEN_TIMEOUT = 30.0  # seconds

# Yahoo Finance circuit breaker
YAHOO_CB_FAILURE_THRESHOLD = 3
YAHOO_CB_SUCCESS_THRESHOLD = 2
YAHOO_CB_HALF_OPEN_TIMEOUT = 60.0

# =============================================================================
# CACHE TTL (seconds)
# =============================================================================

# CIK mappings rarely change
CIK_CACHE_TTL = 86400  # 24 hours

# Company facts change with filings
FACTS_CACHE_TTL = 3600  # 1 hour

# Company info (name, SIC, etc.)
COMPANY_INFO_CACHE_TTL = 86400  # 24 hours

# =============================================================================
# SWOT ANALYSIS THRESHOLDS
# =============================================================================

# Revenue growth (3-year CAGR)
REVENUE_GROWTH_STRONG = 15.0  # > 15% = strength
REVENUE_GROWTH_POSITIVE = 5.0  # > 5% = positive
REVENUE_GROWTH_DECLINING = 0.0  # < 0% = weakness

# Net margin
NET_MARGIN_HIGH = 15.0  # > 15% = strength (high profitability)
NET_MARGIN_HEALTHY = 5.0  # > 5% = healthy
NET_MARGIN_THIN = 5.0  # < 5% = thin margins (weakness)
NET_MARGIN_UNPROFITABLE = 0.0  # < 0% = unprofitable (weakness)

# Operating margin
OPERATING_MARGIN_STRONG = 20.0  # > 20% = strong efficiency

# Debt to equity
DEBT_TO_EQUITY_HIGH = 2.0  # > 2.0 = threat (high leverage)
DEBT_TO_EQUITY_ELEVATED = 1.0  # > 1.0 = weakness (elevated debt)
DEBT_TO_EQUITY_LOW = 0.5  # < 0.5 = strength (low leverage)

# R&D as percentage of revenue
RD_HIGH_INVESTMENT = 10.0  # > 10% = opportunity (high R&D investment)

# =============================================================================
# API ENDPOINTS
# =============================================================================

# SEC EDGAR
SEC_BASE_URL = "https://data.sec.gov"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# Required headers for SEC EDGAR
SEC_HEADERS = {
    "User-Agent": "AI-Strategy-Copilot/1.0 (contact@example.com)",
    "Accept": "application/json",
}

# Yahoo Finance headers
YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

# =============================================================================
# THREAD POOL (for blocking libraries like yfinance)
# =============================================================================

YFINANCE_THREAD_POOL_SIZE = 3
YFINANCE_SEMAPHORE_LIMIT = 3

# =============================================================================
# HTTP SERVER CONFIGURATION (for load-balanced deployment)
# =============================================================================

import os

# HTTP Server
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", "8001"))

# Load Balancer
NGINX_PORT = 8080
INSTANCE_PORTS = [8001, 8002, 8003]

# Instance identification
INSTANCE_ID = os.getenv("INSTANCE_ID", f"financials-default")
