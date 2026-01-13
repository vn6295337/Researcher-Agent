## Endpoint
`POST https://api.tavily.com/search`

## Request Fields
```
api_key
query
search_depth        (basic, advanced)
max_results         (1-10)
include_answer
include_raw_content
include_domains[]
exclude_domains[]
days
```

## Response Structure
```
answer
results[]
  title
  url
  content
  score
  published_date
```
