---
name: wikipedia-airports
description: Discover destinations served from any airport via Wikipedia. Sanity-check whether an airline flies a specific route, find regional service that fare tools miss, identify late-split-return airport options.
category: flights
summary: Route discovery and airline-service sanity check via Wikipedia airport pages. Answers "does carrier X fly A→B" and "what airports serve destination Y" when fare tools disagree or miss obscure regional service. No API key.
license: MIT
---

# Wikipedia Airports

Use Wikipedia as a **route discovery and sanity-check source** for airport destinations. This is especially useful when:

- an airport page has an **Airlines and destinations** section
- an airline's own city-pair marketing pages confirm service patterns
- flight search tools disagree about whether a route exists

Wikipedia is **not a booking source** and not a real-time schedule source. Use it to discover likely routes, then confirm them with airline or fare tools.

## Best Use Cases

- "What destinations does SAN serve?"
- "Does Southwest fly SAN -> EUG?"
- "What airports can I use for a late split return?"
- "Which airline serves this small airport nonstop?"

## Workflow

### 1. Resolve the airport page from an IATA code

Use Wikipedia search with the airport code plus the word `airport`.

```bash
curl -s "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=SAN+airport&format=json" \
  | jq '.query.search[0:5][] | {title}'
```

Usually the first result is the airport page, e.g. `San Diego International Airport`.

### 2. Fetch the page

Use the readable page HTML or the wikitext parse API.

```bash
curl -s "https://en.wikipedia.org/w/api.php?action=parse&page=San_Diego_International_Airport&prop=wikitext&formatversion=2&format=json" \
  | jq -r '.parse.wikitext'
```

Or fetch the rendered page:

```bash
curl -Ls "https://en.wikipedia.org/wiki/San_Diego_International_Airport"
```

### 3. Look for route sections

Search for headings like:

- `Airlines and destinations`
- `Destinations`
- `Passenger`
- `Airlines`

Example:

```bash
curl -s "https://en.wikipedia.org/w/api.php?action=parse&page=San_Diego_International_Airport&prop=wikitext&formatversion=2&format=json" \
  | jq -r '.parse.wikitext' \
  | rg -n "Airlines and destinations|Destinations|Passenger|Southwest|Eugene|Portland"
```

### 4. Treat airline city-pair pages as a second source

If the airport page is incomplete, use airline route pages to validate the pattern.

Examples:

```bash
curl -Ls "https://www.southwest.com/en/flights/flights-from-portland-or-to-san-diego" | rg "PDX|SAN|Portland|San Diego"
curl -Ls "https://www.southwest.com/en/flights/flights-from-portland-or-to-orange-county-santa-ana" | rg "PDX|SNA|Portland|Orange County"
```

This is especially useful for Southwest because:

- it is missing from most GDS sources
- route existence is often easier to verify from marketing pages than from award/cash APIs

### 5. Then confirm with fare tools

After Wikipedia suggests the route exists:

1. Check cash pricing with SerpAPI, Kiwi, Skiplagged, or Duffel (if supported)
2. Check Southwest separately when needed
3. Prefer airline/fare-tool evidence over Wikipedia if they disagree

## Decision Rules

### Use Wikipedia to answer:

- whether an airport likely has service to a destination
- which airlines appear to serve a city pair
- whether a small airport is worth searching

### Do NOT use Wikipedia to answer:

- exact daily schedules
- whether a flight is operating on a specific date
- current fares
- award availability

## Example: SAN and Southwest to EUG

If the SAN airport page or related route references indicate Southwest serves Eugene, treat that as a **lead**, not final proof.

Then validate with:

1. Southwest route pages or booking pages
2. Google Flights / SerpAPI
3. Southwest-specific search if available

This skill is most valuable when it tells you **"search this route, don't assume it doesn't exist."**

## Useful Patterns

### Airport page lookup by IATA code

```bash
CODE=SAN
curl -s "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=${CODE}+airport&format=json" \
  | jq -r '.query.search[0].title'
```

### Pull likely destination section lines

```bash
PAGE="San_Diego_International_Airport"
curl -s "https://en.wikipedia.org/w/api.php?action=parse&page=${PAGE}&prop=wikitext&formatversion=2&format=json" \
  | jq -r '.parse.wikitext' \
  | rg -n "Airlines and destinations|Destinations|Alaska|Southwest|United|Delta|Eugene|Portland|Redmond"
```

### Search for an airline + destination on the page

```bash
PAGE="San_Diego_International_Airport"
curl -s "https://en.wikipedia.org/w/api.php?action=parse&page=${PAGE}&prop=wikitext&formatversion=2&format=json" \
  | jq -r '.parse.wikitext' \
  | rg -n "Southwest|Eugene|EUG"
```

## Notes

- Wikipedia pages vary wildly in quality. Some airports have complete route tables; others are stale.
- Small airports are often better maintained than airline route databases for simple "does this exist?" checks.
- When Wikipedia and fare tools disagree, trust the fare/schedule sources for booking decisions.
- Use this skill as a **discovery and cross-check tool**, not a source of truth.
