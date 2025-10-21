# ARQ Quick Start Guide

## Installation & Setup (5 minutes)

### Step 1: Install ARQ
```bash
cd D:\projects\work\scrape_app
pip install -r requirements.txt
```

### Step 2: Verify Installation
```bash
pip show arq
# Should show: arq 0.26.0
```

### Step 3: Start ARQ Worker
```bash
# Open Terminal 1
arq src.bg_jobs.arq_tasks.WorkerSettings
```

**Expected Output:**
```
INFO ARQ worker starting
INFO Registered 3 functions: extract_events_list, get_event_details, monitor_firecrawl_credits
INFO Listening on queue: arq:queue
```

### Step 4: Start FastAPI Server
```bash
# Open Terminal 2
uvicorn src.main:app --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

---

## Basic Usage

### Test 1: Queue a Scraping Job

```bash
curl -X POST http://localhost:8000/api/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "main_links": ["https://www.destinationcanada.com/en-ca/events"]
  }'
```

**Response:**
```json
{
  "status": "queued",
  "message": "Successfully queued 1 URLs for scraping",
  "urls_queued": 1,
  "job_ids": ["f3b8c9d2..."]
}
```

**What happens:**
1. Job is queued in Redis
2. ARQ worker picks it up
3. AsyncFirecrawl scrapes the URL
4. Event links are extracted
5. Each link queues a detail extraction job
6. Results stored in Redis

### Test 2: Check Queue Stats

```bash
curl http://localhost:8000/api/events/queue/stats
```

**Response:**
```json
{
  "queue": {
    "pending_event_links": 15,
    "processed_event_links": 5,
    "failed_main_links": 0,
    "failed_detail_links": 1
  },
  "results": {
    "total_events_extracted": 12
  }
}
```

### Test 3: View Extracted Events

```bash
curl "http://localhost:8000/api/events/events?limit=5"
```

**Response:**
```json
{
  "total": 12,
  "limit": 5,
  "offset": 0,
  "count": 5,
  "events": [
    {
      "title": "Canada Day Celebration",
      "description": "...",
      "event_link": "...",
      ...
    }
  ]
}
```

---

## Common Commands

### Check Worker Status
```bash
# Find ARQ process
ps aux | grep arq

# View logs in real-time
arq src.bg_jobs.arq_tasks.WorkerSettings --verbose
```

### Check Redis
```bash
# Connect to Redis
redis-cli -u "your-redis-url"

# Check job queue
> LLEN arq:queue

# Check processed links
> SCARD processed_event_links

# Check failed links
> SMEMBERS failed_event_links
```

### Stop Worker
```bash
# Gracefully stop (Ctrl+C)
# Or force kill
pkill -f "arq src.bg_jobs"
```

---

## Architecture Overview

```
┌─────────────────┐
│   FastAPI       │
│   Controller    │
│                 │
│  POST /events/  │
└────────┬────────┘
         │ enqueue_job()
         ↓
┌─────────────────┐
│   Redis Queue   │
│                 │
│  arq:queue      │
└────────┬────────┘
         │ pickup
         ↓
┌─────────────────┐
│   ARQ Worker    │
│                 │
│ - async tasks   │
│ - retry logic   │
│ - AsyncFirecrawl│
└────────┬────────┘
         │ store results
         ↓
┌─────────────────┐
│  Redis Storage  │
│                 │
│ - events_details│
│ - processed_urls│
│ - failed_urls   │
└─────────────────┘
```

---

## Monitoring

### Real-Time Logs

**ARQ Worker Terminal:**
```
INFO [ARQ] Starting async scrape for URL: ... (attempt 1, timeout: 120s)
INFO [ARQ] Extracted 15 links (12 new) from https://...
INFO [ARQ] Queued job extract_events_list with ID: abc123
INFO [ARQ] Extracting event details from: ... (attempt 1, timeout: 120s)
INFO [ARQ] Stored 3 event(s) from: https://...
```

### Stats Endpoint

```bash
# Check every few seconds
watch -n 5 'curl -s http://localhost:8000/api/events/queue/stats | jq'
```

### Redis Monitoring

```python
# Create monitoring script: monitor.py
from src.database.core import redis_client

def show_stats():
    print(f"Pending: {redis_client.scard('event_links_queue')}")
    print(f"Processed: {redis_client.scard('processed_event_links')}")
    print(f"Failed main: {redis_client.scard('failed_event_links')}")
    print(f"Failed details: {redis_client.scard('failed_event_detail_links')}")
    print(f"Total events: {redis_client.llen('events_details')}")

if __name__ == "__main__":
    show_stats()
```

```bash
python monitor.py
```

---

## Configuration

### Adjust Worker Settings

**File:** `src/bg_jobs/arq_tasks.py`

```python
class WorkerSettings:
    # Increase concurrent jobs (default: 10)
    max_jobs = 20

    # Increase timeout (default: 600)
    job_timeout = 900  # 15 minutes

    # Increase retries (default: 4)
    max_tries = 5

    # Keep results longer (default: 3600 = 1 hour)
    keep_result = 7200  # 2 hours
```

### Adjust Timeouts

**File:** `src/bg_jobs/arq_tasks.py`

```python
# In extract_events_list() or get_event_details()
timeout_map = {
    0: 180,  # Start at 3 minutes instead of 2
    1: 300,  # 5 minutes
    2: 420,  # 7 minutes
    3: 600   # 10 minutes
}
```

---

## Troubleshooting

### Jobs Not Processing

1. **Check worker is running:**
   ```bash
   ps aux | grep arq
   ```

2. **Check Redis connection:**
   ```bash
   redis-cli -u "$REDIS_URL" ping
   # Should return: PONG
   ```

3. **Check logs:**
   ```bash
   arq src.bg_jobs.arq_tasks.WorkerSettings --verbose
   ```

### Timeout Errors

1. **Increase timeout:**
   Edit `timeout_map` in `arq_tasks.py`

2. **Check Firecrawl credits:**
   ```bash
   curl http://localhost:8000/api/events/queue/stats
   ```

3. **View failed URLs:**
   ```bash
   redis-cli -u "$REDIS_URL" SMEMBERS failed_event_links
   ```

### Memory Issues

1. **Reduce concurrent jobs:**
   ```python
   class WorkerSettings:
       max_jobs = 5  # Lower from 10
   ```

2. **Monitor memory:**
   ```bash
   watch -n 1 'ps aux | grep arq'
   ```

---

## Performance Tips

### 1. Batch Processing

Instead of queuing URLs one by one:

```python
# Good: Queue all at once
async def queue_batch(urls):
    redis = await create_pool(REDIS_SETTINGS)
    jobs = []
    for url in urls:
        job = await redis.enqueue_job('extract_events_list', url)
        jobs.append(job)
    return jobs
```

### 2. Connection Pooling

Reuse Redis connections:

```python
# At module level
_redis_pool = None

async def get_redis():
    global _redis_pool
    if not _redis_pool:
        _redis_pool = await create_pool(REDIS_SETTINGS)
    return _redis_pool
```

### 3. Monitor Performance

Add timing to tasks:

```python
import time

async def extract_events_list(ctx, url):
    start = time.time()
    # ... task code ...
    logger.info(f"Completed in {time.time() - start:.2f}s")
```

---

## API Reference

### POST /api/events/
Queue scraping jobs

**Request:**
```json
{
  "main_links": ["https://example.com/events"]
}
```

**Response:**
```json
{
  "status": "queued",
  "urls_queued": 1,
  "job_ids": ["abc123..."]
}
```

### GET /api/events/queue/stats
Get queue statistics

**Response:**
```json
{
  "queue": {
    "pending_event_links": 10,
    "processed_event_links": 50
  },
  "results": {
    "total_events_extracted": 120
  }
}
```

### GET /api/events/events?limit=10&offset=0
Get extracted events (paginated)

**Response:**
```json
{
  "total": 120,
  "limit": 10,
  "offset": 0,
  "events": [...]
}
```

### GET /api/events/status/{job_id}
Check job status

**Response:**
```json
{
  "job_id": "abc123",
  "status": "exists"
}
```

---

## Next Steps

1. ✅ **You're done!** ARQ is running
2. 📊 Monitor queue stats regularly
3. 🔧 Tune worker settings based on performance
4. 📈 Consider implementing batch scraping
5. 🚀 Deploy to production

---

## Comparison: Celery vs ARQ

| Task | Celery Command | ARQ Command |
|------|---------------|-------------|
| Start worker | `celery -A src.bg_jobs.tasks worker` | `arq src.bg_jobs.arq_tasks.WorkerSettings` |
| Queue job | `task.delay(arg)` | `await redis.enqueue_job('task', arg)` |
| Check status | Flower UI | Custom endpoint |
| Configuration | celeryconfig.py | WorkerSettings class |

**ARQ is simpler and faster!** 🚀

---

## Resources

- **Full Migration Guide:** [CELERY_TO_ARQ_MIGRATION.md](CELERY_TO_ARQ_MIGRATION.md)
- **Timeout Guide:** [TIMEOUT_FIX_SUMMARY.md](TIMEOUT_FIX_SUMMARY.md)
- **ARQ Docs:** https://arq-docs.helpmanual.io/
- **Firecrawl Docs:** https://docs.firecrawl.dev/

---

**You're all set! Happy scraping with ARQ! 🎉**
