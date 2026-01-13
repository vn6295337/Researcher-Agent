## Endpoint
`GET https://newsapi.org/v2/everything`

## Request Parameters
```
apiKey
q
sortBy       (publishedAt, relevancy, popularity)
language
pageSize     (1-100)
domains
```

## Response Structure
```
status
totalResults
articles[]
  title
  url
  description
  content
  publishedAt
  source
    name
```
