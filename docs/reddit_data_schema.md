Reddit Data Schema
==================

Endpoint: https://www.reddit.com/r/{subreddit}/search.json
Method: GET
Subreddits: wallstreetbets, stocks


Request Parameters

| field       | type   | description                  |
| ----------- | ------ | ---------------------------- |
| q           | string | Search query (ticker)        |
| sort        | string | "relevance", "new", etc.     |
| t           | string | Time filter ("week")         |
| limit       | int    | Max results                  |
| restrict_sr | string | "true" to limit to subreddit |


Response (data.children[].data)

| field       | type   | description      |
|-------------|--------|------------------|
| title       | string | Post title       |
| selftext    | string | Post body text   |
| ups         | int    | Upvote count     |
| permalink   | string | Reddit permalink |
| created_utc | int    | Unix timestamp   |


Example Result

| field       | value                                     |
|-------------|-------------------------------------------|
| title       | "AAPL earnings crush - bullish long term" |
| selftext    | "Just saw the Q4 numbers and..."          |
| ups         | 2450                                      |
| permalink   | "/r/stocks/comments/abc123/..."           |
| created_utc | 1736351400                                |
