NewsAPI Data Schema
===================

Endpoint: https://newsapi.org/v2/everything
Method: GET

Note: Free tier has 24-hour delay on articles


Request Parameters

| field    | type   | description                              |
|----------|--------|------------------------------------------|
| apiKey   | string | API key                                  |
| q        | string | Search query                             |
| sortBy   | string | "publishedAt", "relevancy", "popularity" |
| language | string | Language code (e.g., "en")               |
| pageSize | int    | Results per page (max 100)               |


Response (articles[])

| field       | type   | description                 |
|-------------|--------|-----------------------------|
| title       | string | Article title               |
| url         | string | Article URL                 |
| description | string | Article description         |
| content     | string | Article content (truncated) |
| publishedAt | string | ISO date                    |
| source.name | string | Publisher name              |


Example Result

| field       | value                                  |
|-------------|----------------------------------------|
| title       | "Apple Announces New Product Line"     |
| url         | "https://techcrunch.com/apple-new..."  |
| description | "Apple unveiled its latest products..."|
| publishedAt | "2025-01-08T10:15:00Z"                 |
| source.name | "TechCrunch"                           |
