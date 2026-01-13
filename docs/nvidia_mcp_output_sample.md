# NVDA - Aggregated Data from 6 MCPs

Sample output from `fetch_all_research_data('NVDA', 'NVIDIA Corporation')` showing standardized `{source: {data: {...}}}` structure across all MCP baskets.

---

## 1. Fundamentals
| Source | Metric | Value | data_type | as_of |
|--------|--------|-------|-----------|-------|
| **sec_edgar** | revenue | $130.5B | FY | 2025-01-26 |
| | net_income | $72.9B | FY | 2025-01-26 |
| | net_margin_pct | 55.85% | FY | 2025-01-26 |
| | total_assets | $111.6B | FY | 2025-01-26 |
| | total_liabilities | $32.3B | FY | 2025-01-26 |
| | stockholders_equity | $79.3B | FY | 2025-01-26 |
| | rd_expense | $12.9B | FY | 2025-01-26 |
| | goodwill | $5.2B | FY | 2025-01-26 |
| **yahoo_finance** | total_debt | $10.8B | Point-in-time | 2025-10-26 |
| | operating_cash_flow | $83.2B | TTM | 2025-10-26 |
| | free_cash_flow | $53.3B | TTM | 2025-10-26 |

---

## 2. Valuation
| Source | Metric | Value | data_type | as_of |
|--------|--------|-------|-----------|-------|
| **yahoo_finance** | current_price | $184.94 | Spot | 2026-01-12 |
| | market_cap | $4.50T | Spot | 2026-01-12 |
| | enterprise_value | $4.44T | Spot | 2026-01-12 |
| | trailing_pe | 45.89 | TTM | 2026-01-12 |
| | forward_pe | 24.38 | Forward | 2026-01-12 |
| | ps_ratio | 24.06 | TTM | 2026-01-12 |
| | pb_ratio | 37.80 | Spot | 2026-01-12 |
| | trailing_peg | 0.70 | TTM | 2026-01-12 |
| | earnings_growth | 66.7% | YoY | 2026-01-12 |
| | revenue_growth | 62.5% | YoY | 2026-01-12 |
| **alpha_vantage** | ev_ebitda | 37.31 | TTM | 2025-10-31 |

---

## 3. Volatility
| Source | Metric | Value | data_type | as_of |
|--------|--------|-------|-----------|-------|
| **fred** | vix | 14.49 | Daily | 2026-01-09 |
| | vxn | 19.06 | Daily | 2026-01-09 |
| **yahoo_finance** | beta | 1.929 | 1Y | 2026-01-12 |
| | historical_volatility | 27.1% | 30D | 2026-01-12 |
| | implied_volatility | 30.0% | Forward | 2026-01-13 *(is_estimated)* |

---

## 4. Macro
| Source | Metric | Value | data_type | as_of |
|--------|--------|-------|-----------|-------|
| **bea** | gdp_growth | 4.3% | Quarterly | 2025-09-30 |
| **bls** | cpi_inflation | 2.74% | Monthly | 2025-11-30 |
| | unemployment | 4.4% | Monthly | 2025-12-31 |
| **fred** | interest_rate | 3.72% | Monthly | 2025-12-01 |

---

## 5. News (news_aggregator)
| Source | items_count |
|--------|-------------|
| **Tavily** | 4 |

| title | source | datetime |
|-------|--------|----------|
| NVDA NVIDIA Corporation Stock Price & Overview | Tavily | - |
| NVIDIA Corporation (NVDA) Is a Trending Stock | Tavily | - |
| NVIDIA Corporation (NVDA) Stock Price, News, Quote & History | Tavily | - |
| NVIDIA Corp. Stock Quote (U.S.: Nasdaq) - NVDA | Tavily | - |

---

## 6. Sentiment (sentiment_aggregator)
| Source | items_count |
|--------|-------------|
| **Finnhub** | 50 |
| **Reddit** | 10 |

| title | source | subreddit | datetime |
|-------|--------|-----------|----------|
| How U.S. State Capital Is Reshaping Strategic Supply Chains | Finnhub | - | 2026-01-13 |
| 44th Annual J.P. Morgan Healthcare Conference | Finnhub | - | 2026-01-13 |
| NVIDIA Corporation (NVDA) Presents at 44th Annual J.P. Morgan Healthcare Conference Transcript | Finnhub | - | 2026-01-13 |
| Not Playing Long Ruined My College Hopes | Reddit | r/stocks | 2026-01-13 |
| Top Midday Gainers | Finnhub | - | 2026-01-12 |
| Apple calls on Google to help smarten up Siri and bring other AI features to the iPhone | Finnhub | - | 2026-01-12 |
| Sizing Up Whether The Global Select Equity ETF Is A Buy Right Now | Finnhub | - | 2026-01-12 |
| Traders Are Moving Past Powell's Investigation: U.S. Stock Index Outlook And Pre-CPI Trading Levels | Finnhub | - | 2026-01-12 |
| JPM26: Eli Lilly and NVIDIA deepen ties with $1bn AI partnership | Finnhub | - | 2026-01-12 |
| TSMC rises on reported US-Taiwan deal, Nvidia & Eli Lilly team up | Finnhub | - | 2026-01-12 |
| Nvidia Partners With Biotech Firms On AI Drug Discovery | Finnhub | - | 2026-01-12 |
| Eli Lilly and Nvidia Make $1 Billion AI Bet to Revolutionize Pharma's Future | Finnhub | - | 2026-01-12 |
| Here's What Wall Street Thinks About NVIDIA Corporation (NVDA) | Finnhub | - | 2026-01-12 |
| Alphabet Touches $4 Trillion Market Cap for the First Time | Finnhub | - | 2026-01-12 |
| Google parent Alphabet hits $4tn valuation after AI deal with Apple | Finnhub | - | 2026-01-12 |
| Abercrombie & Fitch Narrows Quarterly Guidance | Finnhub | - | 2026-01-12 |
| Nvidia Push Into NAND Fuels Global Memory Crunch | Finnhub | - | 2026-01-12 |
| Alphabet Becomes Newest $4 Trillion Company, Joining Nvidia | Finnhub | - | 2026-01-12 |
| TSMC's Revenue Outlook 'May Disappoint,' Says Analyst. There's a Silver Lining. | Finnhub | - | 2026-01-12 |
| Meta Needs So Much Capital It Hired Its Own Banker | Finnhub | - | 2026-01-12 |
| Speechmatics and Sully.ai Partner to Scale Healthcare AI Infrastructure Globally | Finnhub | - | 2026-01-12 |
| The Smartest Way to Invest $2,000 If You Believe in AI's Next Wave | Finnhub | - | 2026-01-12 |
| Nvidia, Eli Lilly announce $1 billion investment in AI drug discovery lab | Finnhub | - | 2026-01-12 |
| Stock Market Today: Dow Falls, Weighed Down By American Express; China Names Outperform | Finnhub | - | 2026-01-12 |
| Alphabet Stock Hits $4 Trillion Market Cap | Finnhub | - | 2026-01-12 |
| AI Memory Shortage Reshapes 2026 Outlook for Chipmakers | Finnhub | - | 2026-01-12 |
| From Training AI to Designing Chips: Nvidia's Next Platform Play | Finnhub | - | 2026-01-12 |
| These Stocks Are Today's Movers: Capital One, Amex, Affirm, JPMorgan, Nvidia, Walmart, Moderna, Abercrombie, and More | Finnhub | - | 2026-01-12 |
| Google's market cap hits $4 trillion, cementing its status as an AI trade champion | Finnhub | - | 2026-01-12 |
| Nvidia Stock Slips. The Chip Maker Is Launching an AI Lab with Eli Lilly. | Finnhub | - | 2026-01-12 |
| Is This Artificial Intelligence (AI) Stock Finally Entering Its Breakout Phase? | Finnhub | - | 2026-01-12 |
| CoreWeave stock surges after CEO rebuts GPU useful life concerns | Finnhub | - | 2026-01-12 |
| Why IREN Limited Skyrocketed 285% in 2025 | Finnhub | - | 2026-01-12 |
| 5 U.S. chip stocks to buy in 2026: Bernstein | Finnhub | - | 2026-01-12 |
| BC-Most Active Stocks | Finnhub | - | 2026-01-12 |
| Nvidia Stock Meanders Ahead Of Taiwan Semiconductor's Results; Is Nvidia A Buy Or Sell Now? | Finnhub | - | 2026-01-12 |
| Nvidia Partners With Eli Lilly on AI Drug Laboratory | Finnhub | - | 2026-01-12 |
| Nvidia Stock Wobbles Even as CEO Flags 'Very High' H200 Demand | Finnhub | - | 2026-01-12 |
| Alibaba Stock Jumps on Qwen Models Hit 700 Million Downloads | Finnhub | - | 2026-01-12 |
| Is TSMC Stock a 'Buy' or 'Sell' Ahead of Earnings? | Finnhub | - | 2026-01-12 |
| 2 ETFs That Are Too Cheap to Ignore | Finnhub | - | 2026-01-12 |
| Natera to Scale AI Foundation Models in Precision Medicine with NVIDIA | Finnhub | - | 2026-01-12 |
| NVIDIA and Lilly Announce Co-Innovation AI Lab to Reinvent Drug Discovery in the Age of AI | Finnhub | - | 2026-01-12 |
| NVIDIA BioNeMo Platform Adopted by Life Sciences Leaders to Accelerate AI-Driven Drug Discovery | Finnhub | - | 2026-01-12 |
| CytoReason unveils LINA, an AI Agent accelerated by NVIDIA for Pharma R&D | Finnhub | - | 2026-01-12 |
| Nvidia Stock Gains. China AI Chips and 1 Other Potential Driver. | Finnhub | - | 2026-01-12 |
| RedCloud Activates Early Customer Access to RedAI Trading Co-Pilot | Finnhub | - | 2026-01-12 |
| SKYX Announces it will Supply its Technologies to Enable a New Luxury Waterfront Smart Home Community | Finnhub | - | 2026-01-12 |
| Upgrades: Analysts are Still Bullish on Nvidia (NVDA), Crowdstrike (CRWD) and Oracle (ORCL) Upside | Finnhub | - | 2026-01-12 |
| Quantum Computing Stocks: 'Winner-Take-All Scenario' Possible, Says JPMorgan | Finnhub | - | 2026-01-12 |
| Exchange-Traded Funds, Equity Futures Lower Pre-Bell Monday Amid US DOJ Investigation Into Fed Chair Powell | Finnhub | - | 2026-01-12 |
| Deploying $130k now - seeking thoughts on 3 scenarios | Reddit | r/stocks | 2026-01-12 |
| Thoughts on OZEM ETF long term potential versus individual GLP-1 pharmaceutical stocks? | Reddit | r/stocks | 2026-01-12 |
| So many companies are making their own data centers. Who will actually benefit the most from this? | Reddit | r/stocks | 2026-01-11 |
| tough year 2025 | Reddit | r/wallstreetbets | 2026-01-09 |
| What's the most unexpected stock tip you got from a non-financial source? | Reddit | r/stocks | 2026-01-09 |
| China to Approve Nvidia H200 Purchases as Soon as This Quarter | Reddit | r/wallstreetbets | 2026-01-08 |
| r/Stocks Daily Discussion & Options Trading Thursday - Jan 08, 2026 | Reddit | r/stocks | 2026-01-08 |
| Going balls deep on GOOG thanks to insiders on Polymarket | Reddit | r/wallstreetbets | 2026-01-07 |
| NVDA 125k margin | Reddit | r/wallstreetbets | 2026-01-07 |
| Reddit's Top Stocks 2026 ETF Experiment | Reddit | r/stocks | 2026-01-07 |
| Nvidia launches Vera Rubin AI platform at CES 2026, claims 4x fewer GPUs needed vs Blackwell | Reddit | r/wallstreetbets | 2026-01-06 |
| Back again with Moderna calls 400 buys $36 calls | Reddit | r/wallstreetbets | 2026-01-06 |
| NVDA at CES feels like they're already playing the next AI cycle | Reddit | r/stocks | 2026-01-06 |
| What are your top stock picks for 2026? | Reddit | r/stocks | 2026-01-06 |
| Uber, Lyft Surge Following Nvidia's Self-Driving Tech Announcement | Reddit | r/stocks | 2026-01-06 |
