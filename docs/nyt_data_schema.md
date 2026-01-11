NYT Article Search Data Schema
==============================

Endpoint: https://api.nytimes.com/svc/search/v2/articlesearch.json
Method: GET


Request Parameters

| field      | type   | description                     |
|------------|--------|---------------------------------|
| api-key    | string | API key                         |
| q          | string | Search query                    |
| sort       | string | "newest", "oldest", "relevance" |
| begin_date | string | YYYYMMDD format                 |
| end_date   | string | YYYYMMDD format                 |
| page       | int    | Pagination (0-indexed)          |


Response (response.docs[])

| field          | type   | description      |
|----------------|--------|------------------|
| headline.main  | string | Article headline |
| web_url        | string | Article URL      |
| snippet        | string | Article snippet  |
| lead_paragraph | string | First paragraph  |
| pub_date       | string | ISO date         |
| section_name   | string | NYT section      |


Example Result

| field          | value                                  |
|----------------|----------------------------------------|
| headline.main  | "Apple Stock Surges on Earnings"       |
| web_url        | "https://nytimes.com/2025/01/apple..." |
| snippet        | "Apple shares climbed on strong..."    |
| pub_date       | "2025-01-09T15:30:00Z"                 |
| section_name   | "Business"                             |
