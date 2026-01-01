# Volatility Basket - Business Guide

A tool that provides volatility metrics to enhance SWOT analysis with market risk indicators.

## What It Measures

| Volatility Type | Metric | What It Tells You |
|-----------------|--------|-------------------|
| Market-Wide | **VIX** | Overall market fear level - when investors are nervous, VIX rises |
| Relative Risk | **Beta** | How much a stock moves compared to the market - high beta = more volatile |
| Past Stability | **Historical Volatility** | How much the stock price has fluctuated recently |
| Expected Move | **Implied Volatility** | What the options market expects for future price swings |

## How to Interpret

### VIX (Market Fear Index)

| Level | Market Mood | What It Means for SWOT |
|-------|-------------|------------------------|
| Below 15 | Calm, optimistic | Opportunity - favorable conditions for growth |
| 15 - 20 | Normal | Neutral - standard market conditions |
| 20 - 30 | Nervous | Threat - increased uncertainty |
| Above 30 | Fearful/Crisis | Severe Threat - high market stress |

### Beta (Stock Risk vs Market)

| Value | Stock Behavior | What It Means for SWOT |
|-------|----------------|------------------------|
| Below 0.8 | Moves less than market | Strength - defensive, stable |
| 0.8 - 1.2 | Moves with market | Neutral |
| 1.2 - 1.5 | Moves more than market | Weakness - higher risk |
| Above 1.5 | Much more volatile | Weakness - significantly riskier |

### Historical Volatility (Past Price Swings)

| Range | Price Stability | What It Means for SWOT |
|-------|-----------------|------------------------|
| Below 20% | Very stable | Strength - predictable |
| 20% - 35% | Normal | Neutral |
| 35% - 50% | Volatile | Weakness - unpredictable |
| Above 50% | Highly volatile | Weakness - high risk |

### Implied Volatility (Expected Future Movement)

| Range | Market Expectation | What It Means for SWOT |
|-------|-------------------|------------------------|
| Below 25% | Limited price movement expected | Opportunity - stability ahead |
| 25% - 40% | Normal expected movement | Neutral |
| 40% - 60% | Significant movement expected | Threat - upcoming uncertainty |
| Above 60% | Extreme movement expected (earnings, events) | Threat - high risk period |

*Note: Implied Volatility requires Alpha Vantage API key (optional).*

## Example: Tesla (TSLA)

| Metric | Value | Interpretation | SWOT Category |
|--------|-------|----------------|---------------|
| VIX | 14.08 | Market is calm | Opportunity |
| Beta | 2.35 | Moves 2.3x more than market | Weakness |
| Historical Vol | 43% | High price swings | Weakness |

**Summary:** While market conditions are favorable (low VIX), Tesla itself carries higher-than-average volatility risk compared to the broader market.

## Use Cases

- **Pre-investment analysis**: Understand risk profile before investing
- **Competitive comparison**: Compare volatility metrics across companies
- **Market timing**: Assess current market conditions via VIX
- **Risk reporting**: Include quantitative risk metrics in SWOT reports
