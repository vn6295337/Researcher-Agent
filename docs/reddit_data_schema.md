## Search Endpoint
`GET https://www.reddit.com/r/{subreddit}/search.json`

## Request Parameters
```
q
sort          (relevance, top, new, comments)
t             (week, month, all)
limit         (1-100)
restrict_sr   (true/false)
```

## Request Headers
```
User-Agent    (required)
```

## Response Structure
```
data
  children[]
    data
      title
      selftext
      permalink
      ups
      created_utc
```

## Subreddits Searched
```
wallstreetbets
stocks
```
