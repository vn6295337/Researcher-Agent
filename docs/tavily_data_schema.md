Tavily Data Schema
==================

Endpoint: https://api.tavily.com/search
Method: POST


Request Parameters

| field           | type   | description                 |
|-----------------|--------|-----------------------------|
| api_key         | string | API key                     |
| query           | string | Search query                |
| search_depth    | string | "basic" or "advanced"       |
| max_results     | int    | 1-10 results                |
| include_answer  | bool   | Include AI-generated answer |
| include_domains | array  | Limit to specific domains   |
| exclude_domains | array  | Exclude specific domains    |


Response (results[])

| field          | type   | description             |
|----------------|--------|-------------------------|
| title          | string | Article title           |
| url            | string | Article URL             |
| content        | string | Article snippet/content |
| score          | float  | Relevance score (0-1)   |
| published_date | string | Publication date        |


Example Result

| field          | value                                    |
|----------------|------------------------------------------|
| title          | "Apple Q4 Earnings Beat Expectations"    |
| url            | "https://example.com/apple-earnings"     |
| content        | "Apple reported revenue of $119.6B..."   |
| score          | 0.89                                     |
| published_date | "2025-01-09"                             |
