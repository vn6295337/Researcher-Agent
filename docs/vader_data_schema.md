VADER Sentiment Data Schema
===========================

Library: vaderSentiment.vaderSentiment.SentimentIntensityAnalyzer
Method: polarity_scores(text)

VADER (Valence Aware Dictionary and sEntiment Reasoner) is a lexicon and
rule-based sentiment analysis tool specifically attuned to social media.


Input

| field | type   | description     |
|-------|--------|-----------------|
| text  | string | Text to analyze |


Output (polarity_scores)

| field    | type  | range       | description              |
|----------|-------|-------------|--------------------------|
| neg      | float | 0.0 - 1.0   | Negative sentiment ratio |
| neu      | float | 0.0 - 1.0   | Neutral sentiment ratio  |
| pos      | float | 0.0 - 1.0   | Positive sentiment ratio |
| compound | float | -1.0 - +1.0 | Normalized composite     |

Note: neg + neu + pos = 1.0


Example

Input: "Apple reports record earnings, stock surges on strong iPhone sales"

| field    | value |
|----------|-------|
| neg      | 0.0   |
| neu      | 0.594 |
| pos      | 0.406 |
| compound | 0.765 |
