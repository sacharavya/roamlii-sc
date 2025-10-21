"""
ARQ Async Tasks for Event Scraping
Uses AsyncFirecrawl for better performance with FastAPI
"""
from arq.connections import RedisSettings
from src.database.core import redis_url
from src.config import settings
from src.arq.extract_events_list import extract_events_list
from src.arq.get_event_details import get_event_details


# Parse Redis URL for ARQ
REDIS_SETTINGS = RedisSettings.from_dsn(redis_url)


# ARQ Worker Settings
class WorkerSettings:
    """
    ARQ Worker Configuration - Uses centralized config
    """
    # Task functions to register
    functions = [
        extract_events_list,
        get_event_details,
    ]

    # Redis connection settings
    redis_settings = REDIS_SETTINGS

    # Retry configuration (from config)
    max_tries = settings.arq_max_tries  # Total attempts
    job_timeout = settings.arq_job_timeout  # Max per job

    # Retry with exponential backoff
    retry_jobs = True

    # Logging
    log_results = True

    # Worker settings (from config)
    max_jobs = settings.arq_max_jobs  # Number of concurrent jobs
    keep_result = settings.arq_keep_result  # Keep results duration

    # Cron jobs (periodic tasks)
    cron_jobs = [
        # Monitor credits every hour
        # ('monitor_firecrawl_credits', '0 * * * *'),  # Every hour at minute 0
    ]
