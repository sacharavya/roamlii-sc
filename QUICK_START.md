# Quick Start Guide - After Improvements

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep -E "(celery|firecrawl|redis)"
```

## Environment Setup

Ensure your `.env` file has:
```bash
FIRECRAWL_API_KEY=fc-your-actual-api-key
REDIS_URL=rediss://default:password@host:port/0
```

## Running the Application

### 1. Start FastAPI Server
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start Celery Worker (in new terminal)
```bash
celery -A src.bg_jobs.tasks worker --loglevel=info
```

### 3. (Optional) Start Celery Beat for Monitoring
```bash
celery -A src.bg_jobs.tasks beat --loglevel=info
```

### 4. (Optional) Start Flower for Web Monitoring
```bash
pip install flower
celery -A src.bg_jobs.tasks flower --port=5555
```
Visit: http://localhost:5555

## Testing the API

### Test Event Scraping
```bash
curl -X POST http://localhost:8000/api/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "main_links": [
      "https://www.destinationcanada.com/en-ca/events",
      "https://www.showpass.com/s/events/all/"
    ]
  }'
```

### Check Redis Data
```bash
# Connect to Redis
redis-cli -u "your-redis-url"

# Check queue
SMEMBERS event_links_queue

# Check processed links
SMEMBERS processed_event_links

# Check stored events (returns count)
LLEN events_details

# View first event
LRANGE events_details 0 0
```

## Monitoring

### Check Celery Tasks
```python
from src.bg_jobs.tasks import app

# Inspect active tasks
i = app.control.inspect()
i.active()

# Check registered tasks
i.registered()

# Check stats
i.stats()
```

### Monitor Credits
```python
from src.bg_jobs.tasks import monitor_firecrawl_credits

# Run manually
result = monitor_firecrawl_credits.delay()
print(result.get())
```

## Common Issues

### Issue: Celery worker not starting
**Solution:** Check Redis connection and SSL certificates
```bash
# Test Redis connection
redis-cli -u "your-redis-url" ping
```

### Issue: Firecrawl API errors
**Solution:** Check API key and credits
```bash
# Verify API key is set
python -c "from src.firecrawl.core import firecrawl_api_key; print(firecrawl_api_key[:10] + '...')"
```

### Issue: No events being stored
**Solution:** Check Celery logs and Redis
```bash
# View Celery logs (verbose)
celery -A src.bg_jobs.tasks worker --loglevel=debug

# Check if tasks are queued
python -c "from celery import Celery; app = Celery(); print(app.control.inspect().active())"
```

## What Changed?

### Files Modified
1. [src/firecrawl/core.py](src/firecrawl/core.py) - Fixed hardcoded API key
2. [src/events/schemas.py](src/events/schemas.py) - Fixed schema, added Pydantic models
3. [src/bg_jobs/tasks.py](src/bg_jobs/tasks.py) - Added error handling, logging, monitoring
4. [requirements.txt](requirements.txt) - Added missing dependencies

### New Features
- ✅ Comprehensive error handling (rate limits, credits)
- ✅ Redis deduplication (no duplicate processing)
- ✅ Detailed logging at all levels
- ✅ Credit monitoring task
- ✅ Improved retry logic (exponential backoff, jitter)
- ✅ Timeout configuration
- ✅ Pydantic schema validation

## Next Steps

1. **Implement Batch Scraping** (see IMPROVEMENTS_SUMMARY.md)
   - 50x faster performance
   - 5x lower credit usage

2. **Add Database Persistence**
   - Move from Redis to PostgreSQL/MongoDB
   - Proper data modeling

3. **Consider Task Queue Alternative**
   - Evaluate ARQ for better async support
   - Simpler than Celery

See [IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md) for detailed recommendations.
