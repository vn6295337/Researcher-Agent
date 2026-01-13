## Endpoint
`GET https://api.nytimes.com/svc/search/v2/articlesearch.json`

## Request Parameters
```
api-key
q
sort          (newest, oldest, relevance)
page
begin_date    (YYYYMMDD)
end_date      (YYYYMMDD)
fq            (filter query, e.g., news_desk filter)
```

## Response Structure
```
response
  meta
    hits
  docs[]
    headline
      main
    web_url
    snippet
    lead_paragraph
    pub_date
    section_name
```
