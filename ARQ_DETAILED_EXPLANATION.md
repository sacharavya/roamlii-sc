# ARQ - Complete Detailed Explanation

## What is ARQ?

**ARQ** = **A**sync **R**edis **Q**ueue

It's a simple, fast task queue for Python that:
- Uses Redis as the message broker
- Built specifically for async/await (asyncio)
- Perfect for FastAPI and other async frameworks
- Much simpler than Celery

---

## Core Concepts

### 1. Job Queue (Redis)

Think of it like a to-do list stored in Redis:

```
Redis Queue: "arq:queue"
┌────────────────────────────┐
│ Job 1: scrape URL A        │ ← Worker picks this first
│ Job 2: scrape URL B        │
│ Job 3: scrape URL C        │
│ Job 4: get details for X   │
│ Job 5: get details for Y   │
└────────────────────────────┘
```

### 2. Worker Process

A separate Python process that:
- Watches the Redis queue
- Picks up jobs
- Executes async functions
- Stores results back in Redis

```
┌─────────────────────────────────┐
│   ARQ Worker Process            │
│                                 │
│   While True:                   │
│     1. Check Redis queue        │
│     2. Pick up a job            │
│     3. Execute async function   │
│     4. Store result             │
│     5. Mark job complete        │
│     6. Repeat                   │
└─────────────────────────────────┘
```

### 3. Job Lifecycle

```
1. QUEUED → Job added to Redis queue
2. DEFERRED → Waiting (e.g., for rate limit)
3. IN_PROGRESS → Worker picked it up, executing
4. COMPLETE → Function returned successfully
5. FAILED → Function raised exception
```

---

## How Your Code Works (Step by Step)

### Part 1: FastAPI Receives Request

**File:** `src/events/controller.py`

```python
@eventRouter.post("/")
async def generate_event_details(body: Body):
    # User sends: {"main_links": ["https://example.com/events"]}

    redis = await create_pool(REDIS_SETTINGS)  # Connect to Redis

    for link in body.main_links:
        # Queue the job (doesn't execute yet!)
        job = await redis.enqueue_job('extract_events_list', link)
        # job.job_id = "abc123..."

    return {"status": "queued", "job_ids": [...]}
```

**What happens:**
```
FastAPI
   ↓ (enqueue_job)
Redis Queue
   ↓ (stores)
Job Entry: {
  "function": "extract_events_list",
  "args": ["https://example.com/events"],
  "job_id": "abc123...",
  "enqueue_time": 1234567890
}
```

---

### Part 2: ARQ Worker Picks Up Job

**Terminal command:** `arq src.bg_jobs.arq_tasks.WorkerSettings`

```python
# Worker starts up
1. Loads WorkerSettings class
2. Registers functions: [extract_events_list, get_event_details, ...]
3. Connects to Redis
4. Starts listening on queue: "arq:queue"

# Main loop (simplified)
while True:
    # 1. Check for jobs (BLPOP from Redis queue)
    job_data = await redis.blpop('arq:queue', timeout=1)

    if job_data:
        # 2. Parse job
        function_name = job_data['function']  # 'extract_events_list'
        args = job_data['args']  # ['https://example.com/events']

        # 3. Find and execute function
        func = registered_functions[function_name]
        result = await func(ctx, *args)  # Async execution!

        # 4. Store result
        await redis.set(f'arq:result:{job_id}', result)
```

---

### Part 3: Job Execution

**File:** `src/bg_jobs/arq_tasks.py`

```python
async def extract_events_list(ctx, url: str, retry_count: int = 0):
    """
    ctx: ARQ context (has redis connection, job info, etc.)
    url: The URL to scrape
    retry_count: Current retry attempt
    """

    # 1. Rate limiting (NEW!)
    await rate_limiter.acquire()
    # If too many requests/minute, WAITS here until allowed

    # 2. Call Firecrawl API (async!)
    result = await firecrawl_async.scrape_url(url, params={...})
    # This is non-blocking! Worker can handle other jobs while waiting

    # 3. Process results
    events_links = result.get('json', {}).get('event_links', [])

    # 4. Store in Redis
    for link in events_links:
        redis_client.sadd('event_links_queue', link)

        # 5. Queue MORE jobs!
        await ctx['redis'].enqueue_job('get_event_details', link)
        # This creates new jobs for detail extraction

    return {"success": True, "total_links": len(events_links)}
```

**Visual flow:**
```
Worker picks job: extract_events_list("https://example.com/events")
   ↓
Rate limiter: acquire() → Wait if needed
   ↓
Firecrawl API: scrape_url() → (async, non-blocking)
   ↓ (while waiting, worker can process other jobs if max_jobs > 1)
API returns: {"event_links": ["link1", "link2", ...]}
   ↓
For each link:
   - Store in Redis set
   - Queue new job: get_event_details("link1")
   ↓
Return result → ARQ stores in Redis
```

---

## Detailed Breakdown: WorkerSettings

```python
class WorkerSettings:
    # 1. Which functions can be called as jobs
    functions = [
        extract_events_list,
        get_event_details,
        monitor_firecrawl_credits,
    ]

    # 2. How to connect to Redis
    redis_settings = REDIS_SETTINGS  # Connection info

    # 3. Concurrency control
    max_jobs = 2  # Max jobs running AT THE SAME TIME

    # Example:
    # max_jobs=1: One job at a time (serial)
    # max_jobs=2: Two jobs can run simultaneously
    # max_jobs=10: Ten jobs can run simultaneously

    # 4. Retry behavior
    max_tries = 4  # Total attempts (1 initial + 3 retries)
    retry_jobs = True  # Auto-retry on failure

    # 5. Timeouts
    job_timeout = 900  # Max 15 minutes per job

    # 6. Result storage
    keep_result = 3600  # Keep results for 1 hour
```

---

## How max_jobs Works

### Scenario: You have 10 jobs queued, max_jobs = 2

```
Time: 0s
Redis Queue: [Job1, Job2, Job3, Job4, Job5, Job6, Job7, Job8, Job9, Job10]
Worker: Picks Job1 and Job2 (max_jobs = 2)

Worker State:
┌──────────────────────┐
│ Job1: Running        │ ← Async call to Firecrawl
│ Job2: Running        │ ← Async call to Firecrawl
│ Slot 3: Empty        │ (waiting for Job1 or Job2 to finish)
└──────────────────────┘

Time: 30s
Job1 completes!
Worker: Picks Job3

Worker State:
┌──────────────────────┐
│ Job2: Running        │ ← Still scraping
│ Job3: Running        │ ← Just started
│ Slot 3: Empty        │
└──────────────────────┘

Time: 60s
Job2 completes!
Worker: Picks Job4

And so on...
```

**Key Point:** With `max_jobs=2`, only 2 Firecrawl API requests happen simultaneously!

---

## Understanding ctx (Context)

```python
async def extract_events_list(ctx, url: str):
    # ctx is a dictionary with:
    {
        'redis': <Redis connection>,  # To queue more jobs
        'job_id': 'abc123...',        # Current job ID
        'job_try': 1,                 # Attempt number
        'enqueue_time': 1234567890,   # When job was queued
        'score': 1234567890,          # Priority score
    }

    # You can:
    # 1. Queue more jobs
    await ctx['redis'].enqueue_job('another_task', arg)

    # 2. Check retry count
    if ctx['job_try'] > 2:
        logger.warning("This is our 3rd attempt!")

    # 3. Access job metadata
    logger.info(f"Processing job: {ctx['job_id']}")
```

---

## How Retries Work

```python
# Your function raises an exception
async def extract_events_list(ctx, url):
    await rate_limiter.acquire()

    result = await firecrawl_async.scrape_url(url, ...)

    if not result.get('success'):
        raise FirecrawlError("Scraping failed!")  # Exception!

# ARQ's retry logic (automatic):
"""
Attempt 1: Exception raised
   ↓
ARQ: "Job failed, retry count: 1/4"
   ↓
Wait: 1 second (exponential backoff)
   ↓
Attempt 2: Re-queue job with retry_count=1
   ↓
Function called again: extract_events_list(ctx, url, retry_count=1)
   ↓
If fails again: Wait 2 seconds
   ↓
Attempt 3: retry_count=2, wait 4 seconds
   ↓
Attempt 4: retry_count=3, if still fails → GIVE UP
   ↓
Store in Redis: Job failed after 4 attempts
"""
```

---

## How Rate Limiting Works

```python
class RateLimiter:
    def __init__(self, requests_per_minute=12):
        self.tokens = 12  # Start with 12 tokens
        self.max_tokens = 12
        self.last_update = time.time()

    async def acquire(self):
        # 1. Refill tokens based on time passed
        now = time.time()
        time_passed = now - self.last_update
        self.tokens += time_passed * (12 / 60.0)  # 0.2 tokens/second

        # 2. Check if we have tokens
        if self.tokens < 1:
            # 3. Calculate wait time
            wait_time = (1 - self.tokens) / (12 / 60.0)

            # 4. WAIT (this pauses the job!)
            await asyncio.sleep(wait_time)

            self.tokens = 1

        # 5. Consume a token
        self.tokens -= 1

# In your job:
await rate_limiter.acquire()  # ← Job waits HERE if rate limit reached
result = await firecrawl_async.scrape_url(...)  # Only runs when allowed
```

**Example timeline:**
```
00:00 - Job 1: acquire() → 12 tokens → 11 left
00:05 - Job 2: acquire() → 11 tokens → 10 left (+ 1 refilled = 11)
00:10 - Job 3: acquire() → 11 tokens → 10 left
...
00:60 - All tokens refilled back to 12

01:00 - Job 13: acquire() → 0 tokens → WAIT 5 seconds
01:05 - Job 13: acquire() → 1 token → OK, proceed
```

---

## Complete Flow: Your 4 URLs

Let's trace exactly what happens when you send 4 URLs:

### Step 1: User Request
```bash
curl -X POST /api/events/ -d '{"main_links": [
  "https://site1.com",
  "https://site2.com",
  "https://site3.com",
  "https://site4.com"
]}'
```

### Step 2: FastAPI Queues Jobs
```python
# controller.py
for link in body.main_links:  # 4 links
    job = await redis.enqueue_job('extract_events_list', link)

# Redis queue now has:
# Job 1: extract_events_list("site1.com")
# Job 2: extract_events_list("site2.com")
# Job 3: extract_events_list("site3.com")
# Job 4: extract_events_list("site4.com")
```

### Step 3: ARQ Worker Starts Processing

```
Time: 0s
Worker picks: Job 1, Job 2 (max_jobs=2)

Worker Slot 1: extract_events_list("site1.com")
   ↓
   Rate limiter: acquire() → OK (12 tokens → 11)
   ↓
   Firecrawl API: scrape_url() → Async waiting...

Worker Slot 2: extract_events_list("site2.com")
   ↓
   Rate limiter: acquire() → OK (11 tokens → 10)
   ↓
   Firecrawl API: scrape_url() → Async waiting...

Worker: Both slots busy, waiting for completion...
```

### Step 4: First Job Completes

```
Time: 30s
Job 1 completes → Returns 15 event links

extract_events_list() does:
   for link in event_links:  # 15 links
       await ctx['redis'].enqueue_job('get_event_details', link)

Redis queue now has:
✓ Job 1: DONE
- Job 2: Still running
- Job 3: extract_events_list("site3.com") - Waiting
- Job 4: extract_events_list("site4.com") - Waiting
- Job 5: get_event_details("event1") - NEW! From Job 1
- Job 6: get_event_details("event2") - NEW!
- ... (13 more detail jobs)
```

### Step 5: Worker Picks Next Job

```
Time: 30s
Worker Slot 1 is free!
Worker picks: Job 3

Worker Slot 1: extract_events_list("site3.com")
   ↓
   Rate limiter: acquire() → OK (tokens refilled)
   ↓
   Firecrawl API: scrape_url() → Async waiting...

Worker Slot 2: Still on Job 2
```

### Step 6: More Jobs Complete

```
Time: 60s
Job 2 completes → 15 more event links queued
Job 3 completes → 15 more event links queued

Redis queue now has:
✓ Job 1, 2, 3: DONE
- Job 4: extract_events_list("site4.com") - Waiting
- Job 5-19: get_event_details(...) - From Job 1
- Job 20-34: get_event_details(...) - From Job 2
- Job 35-49: get_event_details(...) - From Job 3

Total: 45 detail jobs + 1 main job = 46 jobs queued!
```

### Step 7: Worker Processes Detail Jobs

```
Time: 90s
Job 4 completes → 15 more event links (60 total detail jobs now!)

Worker now processes 2 detail jobs at a time:
Slot 1: get_event_details("event1")
Slot 2: get_event_details("event2")

With rate limiting (12 req/min):
- ~5 seconds between each request
- 2 jobs at a time = ~2.5 jobs per minute per slot
- Total: ~5 jobs per minute

60 detail jobs ÷ 5 jobs/min = ~12 minutes to complete all
```

---

## Why ARQ is Better Than Celery

### Celery (Old Way)
```python
# Sync function - BLOCKS the worker
@app.task
def extract_events_list(url):
    result = firecrawl_app.scrape(url, ...)  # Blocks for 30 seconds!
    return result

# Problem: While waiting for Firecrawl API, worker can't do anything else
```

### ARQ (New Way)
```python
# Async function - NON-BLOCKING
async def extract_events_list(ctx, url):
    result = await firecrawl_async.scrape_url(url, ...)  # Non-blocking!
    return result

# Benefit: While waiting for Firecrawl API, worker can:
# - Process other jobs (if max_jobs > 1)
# - Handle rate limiting
# - Be more efficient with I/O
```

**Real example:**
```
Celery (2 workers, sync):
Worker 1: scrape URL → Wait 30s (blocked) → Return
Worker 2: scrape URL → Wait 30s (blocked) → Return
Total time: 30s for 2 URLs

ARQ (1 worker, max_jobs=2, async):
Slot 1: scrape URL → Async wait (non-blocking)
Slot 2: scrape URL → Async wait (non-blocking)
Both complete after: 30s for 2 URLs

Same performance with HALF the workers! 🎉
```

---

## Common Patterns

### 1. Chain Jobs (Job creates more jobs)
```python
async def main_job(ctx, url):
    result = await process(url)

    # Create follow-up jobs
    for item in result:
        await ctx['redis'].enqueue_job('detail_job', item)
```

### 2. Conditional Retry
```python
async def my_job(ctx, url, retry_count=0):
    try:
        result = await api_call(url)
    except TemporaryError:
        if retry_count < 3:
            # Retry
            raise
        else:
            # Give up
            return {"success": False, "error": "max retries"}
```

### 3. Job with Timeout
```python
async def my_job(ctx, url):
    try:
        result = await asyncio.wait_for(
            slow_operation(url),
            timeout=300  # 5 minutes
        )
    except asyncio.TimeoutError:
        return {"success": False, "error": "timeout"}
```

---

## Monitoring ARQ

### Check Queue Size
```python
import redis
r = redis.from_url(redis_url)

# How many jobs waiting?
queue_size = r.llen('arq:queue')
print(f"Jobs in queue: {queue_size}")

# List job IDs
job_ids = r.keys('arq:job:*')
print(f"Active jobs: {len(job_ids)}")
```

### Check Job Status
```python
# In your FastAPI endpoint
@eventRouter.get("/status/{job_id}")
async def get_status(job_id: str):
    redis = await create_pool(REDIS_SETTINGS)

    # Get job result
    result = await redis.get(f'arq:result:{job_id}')

    return {"job_id": job_id, "result": result}
```

### Watch Worker Logs
```bash
arq src.bg_jobs.arq_tasks.WorkerSettings --verbose

# You'll see:
# INFO Starting job extract_events_list...
# INFO Job complete in 32.1s
# WARNING Rate limit reached. Waiting 4.2s...
```

---

## Advanced: How Redis Stores Jobs

```redis
# Queue (list)
LPUSH arq:queue '{"function":"extract_events_list","args":["url"],"job_id":"abc123"}'

# Job data (hash)
HSET arq:job:abc123 function extract_events_list
HSET arq:job:abc123 args ["url"]
HSET arq:job:abc123 enqueue_time 1234567890

# Result (string, expires after keep_result seconds)
SETEX arq:result:abc123 3600 '{"success":true,"links":15}'

# In-progress set
SADD arq:in-progress abc123  # Added when job starts
SREM arq:in-progress abc123  # Removed when job completes
```

---

## Summary: How ARQ Works

1. **Queue Jobs**: FastAPI calls `redis.enqueue_job()` → Stores in Redis
2. **Worker Picks Jobs**: ARQ worker watches queue (`BLPOP`)
3. **Execute Async**: Calls your async function with `await`
4. **Rate Limiting**: Waits if needed before API calls
5. **Store Results**: Saves return value to Redis
6. **Retry on Failure**: Automatic retry with exponential backoff
7. **Repeat**: Goes back to step 2

**Key Benefits:**
- ✅ Async/await native (non-blocking I/O)
- ✅ Simple configuration (one class)
- ✅ Automatic retries
- ✅ Rate limiting support
- ✅ Perfect for FastAPI

**Your specific setup:**
- `max_jobs=2` → 2 concurrent Firecrawl requests
- `rate_limiter` → 12 requests/minute limit
- Progressive timeouts → Longer timeout on each retry
- Failed URL tracking → Never lose data

---

**That's ARQ in complete detail! Any questions about specific parts?** 🚀
