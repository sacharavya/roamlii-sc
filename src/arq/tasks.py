
from src.database.core import REDIS_SETTINGS
from src.config import settings
from src.arq.extract_events_list import extract_events_list
from src.arq.get_event_details import get_event_details
from src.arq.extract_festivals_links_list import extract_festivals_links_list
from src.arq.get_festivals_details import get_festivals_details
from src.arq.extract_sports_links_list import extract_sports_links_list
from src.arq.get_sports_details import get_sports_details
from src.arq.auto_scrape import auto_scrape
from arq import cron


# ARQ Worker Settings
class WorkerSettings:
    """
    ARQ Worker Configuration - Uses centralized config
    """
    # Task functions to register
    functions = [
        extract_events_list,          # Single URL scraping
        get_event_details,            # Single event detail extraction
        extract_festivals_links_list,
        get_festivals_details,
        extract_sports_links_list,
        get_sports_details,
        # batch_scrape_main_links,      # Batch URL scraping (50x faster)
        # batch_scrape_event_details,   # Batch event detail extraction
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
        # auto_scrape func ro run automatically at midnight on the 30th day of every month
        cron(auto_scrape, name='auto_scrape_in_30th_day_of_month', day=30, hour=0, minute=0, second=0,
             max_tries=settings.arq_max_tries, unique=True)
        # cron(auto_scrape, name='auto_scrape_28_day_check', hour=14, minute=46, second=59,
        #      max_tries=settings.arq_max_tries, unique=True)
    ]
