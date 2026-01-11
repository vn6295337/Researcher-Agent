"""
Output schemas for MCP data presentation in markdown files.
These define the field structure for each section in mcp_output_xxx.md files.
"""

OUTPUT_SCHEMAS = {
    "company_details": {
        "fields": ["longName", "address1", "city", "state", "zip", "country", "sector", "industry"],
        "description": "Company profile and classification"
    },
    "fundamentals": {
        "fields": ["value", "data_type", "end_date", "filed", "fiscal_year", "form"],
        "description": "Financial statement metrics from SEC EDGAR and Yahoo Finance"
    },
    "valuation": {
        "fields": ["value", "data_type", "as_of"],
        "description": "Valuation ratios and multiples"
    },
    "volatility": {
        "fields": ["value", "data_type", "as_of", "source", "fallback"],
        "description": "Market volatility and risk metrics"
    },
    "macro": {
        "fields": ["value", "data_type", "as_of", "source"],
        "description": "Macroeconomic indicators"
    },
    "news": {
        "fields": ["title", "content", "date", "url", "source"],
        "description": "News articles from financial sources"
    },
    "sentiment": {
        "fields": ["title", "content", "date", "url", "source", "subreddit"],
        "description": "Sentiment data from Finnhub and Reddit"
    },
}


def get_schema_string(section: str) -> str:
    """Get schema as formatted string for markdown display."""
    schema = OUTPUT_SCHEMAS.get(section)
    if not schema:
        return ""
    return "{ " + ", ".join(schema["fields"]) + " }"


def get_all_schema_strings() -> dict:
    """Get all schemas as formatted strings."""
    return {key: get_schema_string(key) for key in OUTPUT_SCHEMAS}
