# News Basket MCP Server - Technical Documentation

MCP server for web search using Tavily API. Provides real-time news, articles, and web content for SWOT analysis.

## Installation

```bash
cd mcp-servers/news-basket
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## API Key Required

Get free API key at: https://tavily.com

Add to `~/.env`:
```
TAVILY_API_KEY=tvly-xxxxxxxxxxxxx
```

**Free tier:** 1,000 API credits/month

## MCP Tools

| Tool | Parameters | Returns |
|------|------------|---------|
| `tavily_search` | `query`, `search_depth`, `max_results` | General web search results |
| `search_company_news` | `ticker`, `company_name` | Recent company news + SWOT hints |
| `search_going_concern_news` | `ticker`, `company_name` | Financial distress news + risk level |
| `search_industry_trends` | `industry` | Industry outlook articles |
| `search_competitor_news` | `ticker`, `competitors` | Competitor news coverage |

## Usage

### Standalone Test

```bash
source venv/bin/activate
python test_fetchers.py AAPL
python test_fetchers.py "semiconductor industry trends"
```

### Run MCP Server

```bash
source venv/bin/activate
python server.py
```

### Claude Desktop Integration

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "news-basket": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/mcp-servers/news-basket/server.py"]
    }
  }
}
```

## Example Output

```json
{
  "query": "AAPL stock news",
  "answer": "Apple shares rose 2% following...",
  "results": [
    {
      "title": "Apple Reports Record Q4 Earnings",
      "url": "https://...",
      "content": "Apple Inc. reported...",
      "score": 0.95
    }
  ],
  "swot_hints": {
    "opportunities": ["Apple Reports Record Q4 Earnings"],
    "threats": []
  }
}
```

## Search Depth

| Depth | Speed | Thoroughness | Credits |
|-------|-------|--------------|---------|
| basic | Fast | Good | 1 credit |
| advanced | Slower | Better | 2 credits |

## Rate Limits

| Tier | Credits/Month | Rate Limit |
|------|---------------|------------|
| Free | 1,000 | 100 req/min |
| Paid | Varies | Higher |

## Files

```
news-basket/
├── server.py           # MCP server implementation
├── test_fetchers.py    # Standalone test script
├── requirements.txt    # Python dependencies
├── mcp_tavily.md       # Business user guide
└── README.md           # This technical documentation
```
