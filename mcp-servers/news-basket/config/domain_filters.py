"""
Domain whitelist for business/finance/tech news sources.
Helps disambiguate company names from common words (e.g., Visa vs travel visa).
"""

# Finance/Business domains for Tavily
FINANCE_DOMAINS = [
    "bloomberg.com",
    "reuters.com",
    "wsj.com",
    "cnbc.com",
    "finance.yahoo.com",
    "marketwatch.com",
    "fool.com",
    "seekingalpha.com",
    "barrons.com",
    "ft.com",
    "businessinsider.com",
    "forbes.com",
    "investopedia.com",
]

# Tech domains for Tavily
TECH_DOMAINS = [
    "techcrunch.com",
    "wired.com",
    "theverge.com",
    "arstechnica.com",
    "zdnet.com",
]

# Combined whitelist for Tavily
NEWS_DOMAINS = FINANCE_DOMAINS + TECH_DOMAINS

# NYT news desks to filter
NYT_NEWS_DESKS = ["Business", "Technology", "DealBook"]

# NewsAPI domains (comma-separated string)
NEWSAPI_DOMAINS = ",".join(FINANCE_DOMAINS + TECH_DOMAINS)
