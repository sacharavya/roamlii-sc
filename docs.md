### Create a Virtual Environment

```bash
uv venv
```

### Activate the Virtual Environment

```bash
.venv/Scripts/activate
```

### List all packages to requirements.txt

```bash
uv pip freeze > requirements.txt
```

### To install packages from requirements.txt

```bash
uv pip install -r requirements.txt
```

### Deactivate the Virtual Environment

```bash
deactivate
```

## Running the Application

### FastAPI Server
```bash
fastapi dev src/main.py
# or
uvicorn src.main:app --reload
```

### ARQ Worker (NEW - Replaces Celery)
```bash
arq src.bg_jobs.arq_tasks.WorkerSettings
# or with verbose logging
arq src.bg_jobs.arq_tasks.WorkerSettings --verbose
```

---

## OLD: Celery Commands (Deprecated - Use ARQ Instead)

```bash
# Old Celery worker (Don't use anymore)
celery -A src.bg_jobs.tasks worker --loglevel=info --concurrency=50 --pool=gevent

# Old Celery Flower monitoring (Don't use anymore)
celery -A src.bg_jobs.tasks flower --port=5555
```

**Note:** We've migrated from Celery to ARQ for better async support and performance.
See [CELERY_TO_ARQ_MIGRATION.md](CELERY_TO_ARQ_MIGRATION.md) for details.

---

## Quick Reference

### Start Everything
```bash
# Terminal 1: ARQ Worker
arq src.bg_jobs.arq_tasks.WorkerSettings

# Terminal 2: FastAPI
uvicorn src.main:app --reload
```

### Test the API
```bash
curl -X POST http://localhost:8000/api/events/ \
  -H "Content-Type: application/json" \
  -d '{"main_links": ["https://www.destinationcanada.com/en-ca/events"]}'
```

### Check Queue Stats
```bash
curl http://localhost:8000/api/events/queue/stats
```

### Get Extracted Events
```bash
curl http://localhost:8000/api/events/events?limit=10
```

---

## Documentation

- **[ARQ_QUICK_START.md](ARQ_QUICK_START.md)** - Get started with ARQ in 5 minutes
- **[CELERY_TO_ARQ_MIGRATION.md](CELERY_TO_ARQ_MIGRATION.md)** - Complete migration guide
- **[IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md)** - All improvements & best practices
- **[TIMEOUT_FIX_SUMMARY.md](TIMEOUT_FIX_SUMMARY.md)** - Handling timeout errors
- **[FIRECRAWL_TIMEOUT_GUIDE.md](FIRECRAWL_TIMEOUT_GUIDE.md)** - Complete timeout guide
