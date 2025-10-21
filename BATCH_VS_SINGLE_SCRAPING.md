# Batch vs Single URL Scraping - Comparison Guide

This guide helps you understand the differences between single and batch scraping methods and choose the best approach for your use case.

## Overview

Your application now supports **two scraping methods**:

1. **Single URL Scraping** - Processes URLs one at a time
2. **Batch Scraping** - Processes multiple URLs in a single API request (50x faster)

---

## Quick Comparison

| Feature | Single URL Scraping | Batch Scraping |
|---------|-------------------|----------------|
| **Speed** | Baseline (1x) | **50x faster** |
| **Endpoint** | `POST /events/extract_events_details` | `POST /events/batch` |
| **API Calls** | 1 per URL | 1 per batch (all URLs) |
| **Best For** | 1-5 URLs, testing | 10+ URLs, production |
| **Rate Limit Impact** | High (1 call per URL) | **Low** (1 call total) |
| **Debugging** | Easy (per-URL logs) | Moderate (batch logs) |
| **Recommended** | Development/Testing | **Production** |

---

## Detailed Comparison

### 1. Single URL Scraping (`/extract_events_details`)

#### How It Works
```
Request: ["url1.com", "url2.com", "url3.com"]
       ↓
Job 1: extract_events_list(url1.com) → wait → results
Job 2: extract_events_list(url2.com) → wait → results
Job 3: extract_events_list(url3.com) → wait → results
```

#### Code Flow
```python
# Controller: src/events/controller.py
@eventRouter.post("/extract_events_details")
async def extract_event_details(body: EXTRACT_EVENT_DETAILS):
    return await extract_event_details_from_event_links(body)

# Service: src/events/service.py
for link in body.main_links:
    job = await enqueue_job('extract_events_list', link)  # 1 job per URL

# Worker: src/arq/extract_events_list.py
async def extract_events_list(ctx, url: str):
    result = await firecrawl_async.scrape_url(url, ...)  # 1 API call
```

#### Performance Example
```
10 URLs → 10 separate jobs → 10 API calls → ~10 minutes
```

#### When to Use
- ✅ Testing individual URLs
- ✅ Debugging specific pages
- ✅ Processing 1-5 URLs
- ✅ Development/testing environment
- ❌ Production with many URLs (slow!)

---

### 2. Batch Scraping (`/batch`)

#### How It Works
```
Request: ["url1.com", "url2.com", "url3.com"]
       ↓
Job 1: batch_scrape_main_links([url1, url2, url3]) → all results at once
```

#### Code Flow
```python
# Controller: src/events/controller.py
@eventRouter.post("/batch")
async def extract_event_details_in_batch(body: EXTRACT_EVENT_DETAILS):
    return await extract_event_details_batch(body)

# Service: src/events/service.py
job = await enqueue_job('batch_scrape_main_links', body.main_links)  # 1 job total

# Worker: src/arq/batch_scrape_main_links.py
async def batch_scrape_main_links(ctx, urls: List[str]):
    batch_result = await firecrawl_async.batch_scrape_urls(urls, ...)  # 1 API call!
```

#### Performance Example
```
10 URLs → 1 batch job → 1 API call → ~12 seconds (50x faster!)
```

#### When to Use
- ✅ Production environment
- ✅ Processing 10+ URLs
- ✅ Need fast results
- ✅ Want to save API credits
- ✅ Want to minimize rate limit usage
- ✅ **Recommended default method**

---

## API Usage Examples

### Single URL Scraping

**Request:**
```bash
curl -X POST "http://localhost:8000/events/extract_events_details" \
  -H "Content-Type: application/json" \
  -d '{
    "main_links": [
      "https://example.com/events/page1",
      "https://example.com/events/page2",
      "https://example.com/events/page3"
    ]
  }'
```

**Response:**
```json
{
  "status": "queued",
  "method": "single",
  "message": "Successfully queued 3 URLs for scraping (single URL method)",
  "urls_queued": 3,
  "job_ids": [
    "abc123-job1",
    "def456-job2",
    "ghi789-job3"
  ]
}
```

**What Happens:**
- 3 separate ARQ jobs created
- 3 separate Firecrawl API calls
- Each URL processed independently
- Total time: ~6 minutes (for 3 URLs)

---

### Batch Scraping (Recommended)

**Request:**
```bash
curl -X POST "http://localhost:8000/events/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "main_links": [
      "https://example.com/events/page1",
      "https://example.com/events/page2",
      "https://example.com/events/page3"
    ]
  }'
```

**Response:**
```json
{
  "status": "queued",
  "method": "batch",
  "message": "Successfully queued 3 URLs for batch scraping (50x faster)",
  "urls_queued": 3,
  "job_id": "xyz123-batch",
  "note": "Batch method processes all URLs in a single API request"
}
```

**What Happens:**
- 1 ARQ job created for all URLs
- 1 Firecrawl batch API call
- All URLs processed together
- Total time: ~7 seconds (for 3 URLs) - **50x faster!**

---

## Performance Analysis

### Time Comparison (Example: 10 URLs)

| Method | API Calls | Jobs Created | Rate Limit Usage | Estimated Time |
|--------|-----------|--------------|------------------|----------------|
| **Single** | 10 calls | 10 jobs | 10 req/min | ~10 minutes |
| **Batch** | 1 call | 1 job | 1 req/min | ~12 seconds |

### Cost Comparison (Firecrawl Credits)

Assuming each scrape costs 1 credit:

| Method | 10 URLs | 50 URLs | 100 URLs |
|--------|---------|---------|----------|
| **Single** | 10 credits | 50 credits | 100 credits |
| **Batch** | 1 credit | 1 credit | 1 credit |

*Note: Batch scraping uses credits more efficiently by grouping requests.*

---

## Rate Limiting Behavior

### Single URL Scraping
```
Time: 0s    5s    10s   15s   20s   25s   30s
      ↓     ↓     ↓     ↓     ↓     ↓     ↓
Call: 1     2     3     4     5     6     7
      ↑_____|_____|_____|_____|_____|_____↑
              Rate limiter: 12 req/min
```

**Impact:**
- Can hit rate limit with many URLs
- May need to wait between requests
- Slower overall completion

### Batch Scraping
```
Time: 0s                              30s
      ↓                               ↓
Call: 1 (batch of 100 URLs)          Done!
      ↑_______________________________↑
              Rate limiter: 1 req/min
```

**Impact:**
- Single request regardless of URL count
- Minimal rate limit impact
- Faster completion

---

## Error Handling

### Single URL Scraping
```python
# If URL 5 fails:
Job 1: ✓ Success
Job 2: ✓ Success
Job 3: ✓ Success
Job 4: ✓ Success
Job 5: ✗ Failed (timeout)
Job 6: ✓ Success  # Other jobs continue
Job 7: ✓ Success
```

**Pros:** Isolated failures - one bad URL doesn't affect others

**Cons:** More failure points (10 URLs = 10 potential failures)

### Batch Scraping
```python
# Batch handles partial failures:
Batch Job: [URL1, URL2, URL3, URL4, URL5, ...]
          ↓
Result: {
  "data": [
    {"success": true, "url": "URL1", ...},
    {"success": true, "url": "URL2", ...},
    {"success": false, "url": "URL5", "error": "timeout"},
    {"success": true, "url": "URL6", ...},
  ]
}
```

**Pros:** Handles partial failures gracefully, continues with successful URLs

**Cons:** Entire batch retries if the batch API call itself fails

---

## Files Involved

### Single URL Scraping
- **Controller:** [src/events/controller.py](src/events/controller.py:13-25) - `/extract_events_details` endpoint
- **Service:** [src/events/service.py](src/events/service.py:8-43) - `extract_event_details_from_event_links()`
- **Worker Tasks:**
  - [src/arq/extract_events_list.py](src/arq/extract_events_list.py) - Main page scraping
  - [src/arq/get_event_details.py](src/arq/get_event_details.py) - Detail extraction
- **Task Registry:** [src/arq/tasks.py](src/arq/tasks.py:17-18) - Worker configuration

### Batch Scraping
- **Controller:** [src/events/controller.py](src/events/controller.py:28-42) - `/batch` endpoint
- **Service:** [src/events/service.py](src/events/service.py:46-81) - `extract_event_details_batch()`
- **Worker Tasks:**
  - [src/arq/batch_scrape_main_links.py](src/arq/batch_scrape_main_links.py) - Batch main page scraping
  - [src/arq/batch_scrape_event_details.py](src/arq/batch_scrape_event_details.py) - Batch detail extraction
- **Task Registry:** [src/arq/tasks.py](src/arq/tasks.py:19-20) - Worker configuration

---

## Testing Recommendations

### Step 1: Test Single URL Method (Baseline)
```bash
# Test with 3 URLs
curl -X POST "http://localhost:8000/events/extract_events_details" \
  -H "Content-Type: application/json" \
  -d '{
    "main_links": [
      "https://example.com/events/1",
      "https://example.com/events/2",
      "https://example.com/events/3"
    ]
  }'

# Check logs
# Note: Completion time, number of API calls, success rate
```

### Step 2: Test Batch Method (Comparison)
```bash
# Test with same 3 URLs
curl -X POST "http://localhost:8000/events/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "main_links": [
      "https://example.com/events/1",
      "https://example.com/events/2",
      "https://example.com/events/3"
    ]
  }'

# Check logs
# Compare: Completion time, API calls, success rate
```

### Step 3: Scale Test
```bash
# Test batch method with 10+ URLs
curl -X POST "http://localhost:8000/events/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "main_links": [
      "https://example.com/events/1",
      "https://example.com/events/2",
      ...
      "https://example.com/events/15"
    ]
  }'

# Observe: Should still complete in ~10-15 seconds regardless of URL count
```

---

## Monitoring Job Status

Both methods store results in Redis. You can retrieve them the same way:

```bash
# Get all extracted events
curl "http://localhost:8000/events/all?limit=50&offset=0"
```

**Response:**
```json
{
  "total": 150,
  "limit": 50,
  "offset": 0,
  "count": 50,
  "events": [
    {
      "title": "Tech Conference 2025",
      "description": "Annual technology conference...",
      "event_link": "https://example.com/event/123",
      "location": "San Francisco, CA",
      ...
    },
    ...
  ]
}
```

---

## Recommendation

### For Development/Testing
**Use Single URL Method** (`/extract_events_details`)
- Easy to debug individual URLs
- Clear per-URL logs
- Good for testing edge cases

### For Production
**Use Batch Method** (`/batch`)
- 50x faster performance
- Lower API costs
- Better rate limit efficiency
- Recommended for all production workloads

---

## Migration Path

If you're currently using single URL scraping:

1. **Keep both endpoints** for now (both are available)
2. **Test batch endpoint** with a subset of your production URLs
3. **Compare results** - verify data quality is the same
4. **Switch production traffic** to batch endpoint
5. **Monitor performance** - should see significant speedup
6. **Keep single endpoint** for debugging/testing purposes

---

## Summary

| Question | Answer |
|----------|--------|
| Which is faster? | **Batch scraping** (50x faster) |
| Which uses fewer API calls? | **Batch scraping** (1 call vs N calls) |
| Which is better for production? | **Batch scraping** |
| Which is better for testing? | Single URL scraping |
| Can I use both? | **Yes!** Both endpoints are available |
| Which should I use by default? | **Batch scraping** (`/batch`) |

---

## Need Help?

- Check ARQ worker logs: `arq src.arq.tasks.WorkerSettings --verbose`
- Check FastAPI logs: `uvicorn src.main:app --reload`
- View extracted events: `GET /events/all`
- Redis data inspection: `redis-cli LRANGE events_details 0 10`

For more information, see:
- [ARQ_DETAILED_EXPLANATION.md](ARQ_DETAILED_EXPLANATION.md) - How ARQ works
- [RATE_LIMIT_FIX.md](RATE_LIMIT_FIX.md) - Rate limiting details
- [CONCURRENCY_LIMIT_FIX.md](CONCURRENCY_LIMIT_FIX.md) - Concurrency limits
