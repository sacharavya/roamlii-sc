import ssl
import json
import logging
from celery import Celery
from src.events.schemas import EVENT_DETAILS_SCHEMA, EventDetailsSchema, MainLinkSchema
from src.firecrawl.core import firecrawl_api_key
from src.database.core import redis_client
from ..database.core import redis_url
from ..firecrawl.core import firecrawl_app
import requests

# Configure logging
logger = logging.getLogger(__name__)

app = Celery('background_jobs', broker=redis_url, backend=redis_url)

# Additional SSL configuration for broker and backend
app.conf.broker_use_ssl = {
    'ssl_cert_reqs': ssl.CERT_REQUIRED
}
app.conf.redis_backend_use_ssl = {
    'ssl_cert_reqs': ssl.CERT_REQUIRED
}

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


class FirecrawlError(Exception):
    """Base exception for Firecrawl-related errors"""
    pass


class FirecrawlRateLimitError(FirecrawlError):
    """Exception for rate limit errors"""
    pass


class FirecrawlCreditError(FirecrawlError):
    """Exception for credit-related errors"""
    pass


class FirecrawlTimeoutError(FirecrawlError):
    """Exception for timeout errors"""
    pass


def handle_firecrawl_error(exc):
    """Helper to categorize and handle Firecrawl errors"""
    error_msg = str(exc)

    if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
        raise FirecrawlTimeoutError(f"Request timeout: {error_msg}")
    elif "rate limit" in error_msg.lower():
        raise FirecrawlRateLimitError(f"Rate limit exceeded: {error_msg}")
    elif "credit" in error_msg.lower() or "insufficient" in error_msg.lower():
        raise FirecrawlCreditError(f"Credit issue: {error_msg}")
    else:
        raise FirecrawlError(f"Firecrawl API error: {error_msg}")


@app.task(
    name="event_main_links",
    bind=True,
    default_retry_delay=30 * 10,  # will retry after 5 minutes
    retry_backoff=True,  # exponential backoff: 1s, 2s, 4s, 8s...
    # retry_kwargs={"max_retries": 3},  # number of retries
    max_retries=3,  # number of retries
    retry_jitter=True  # add randomness to retry delay (avoid thundering herd)
)
def extract_events_list(self, url: str):
    """
    Extract event links from a single URL
    Stores links in Redis with deduplication and triggers detail extraction

    Args:
        url: Main event page URL to scrape

    Returns:
        dict: Status and count of extracted links
    """
    # Progressive timeout based on retry attempt
    # retry_count = self.request.retries
    # timeout_map = {
    #     0: 30000,  # First attempt: 2 minutes
    #     1: 60000,  # Second attempt: 3 minutes
    #     2: 90000,  # Third attempt: 5 minutes
    #     3: 120000   # Fourth attempt: 7 minutes
    # }
    # timeout = timeout_map.get(retry_count, 300)

    # logger.info(
    #     f"Starting scrape for URL: {url} (attempt {retry_count + 1}, timeout: {timeout}s)")

    try:
        result = firecrawl_app.scrape(
            url=url,
            actions=[
                {
                    "type": "scroll",
                    "direction": "down"
                }
            ],
            formats=[{
                "type": "json",
                "schema":  MainLinkSchema,
                "prompt": """Extract ONLY the direct links to individual event pages or event popup/modal triggers.
                            Include:
                            - Links that lead to specific event details pages
                            - Links that open event popups or modals with event details (these may have anchors like #calendar-xxx-event-xxx)
                            - Links to event registration pages
                            - Any clickable URLs that display information about a single, specific event

                            Exclude:
                            - Navigation links (menus, headers, footers)
                            - Social media links
                            - General category or filter pages
                            - Login/signup links
                            - Contact or about us pages
                            - Any other non-event URLs

                            Each link should point to or trigger the display of a single, specific event."""
            }],
            # Progressive timeout (SDK bug: expects seconds, not milliseconds)
            timeout=60*5*1000,
        )

        if result.metadata.status_code == 200:
            events_links = result.json.get('event_links', [])
            unique_links = 0

            for link in events_links:
                # Check if link already exists in processed set
                if not redis_client.sismember('processed_event_links', link):
                    # Add to queue for processing
                    redis_client.sadd('event_links_queue', link)
                    unique_links += 1
                    # Trigger event details extraction
                    get_event_details.delay(link)
                else:
                    logger.debug(f"Link already processed: {link}")

            logger.info(
                f"Extracted {len(events_links)} links ({unique_links} new) from {url}")

            return {
                "success": True,
                "total_links": len(events_links),
                "unique_links": unique_links
            }
        else:
            logger.warning(
                f"Non-200 status code: {result.metadata.status_code} for {url}")
            return {
                "success": False,
                "status_code": result.metadata.status_code
            }

    except FirecrawlTimeoutError as exc:
        # logger.warning(
        #     f"Timeout scraping {url} after {timeout}s (attempt {self.request.retries + 1}): {exc}")

        # If we've exhausted retries, mark as failed but don't crash
        if self.request.retries >= self.max_retries - 1:
            logger.error(f"Max retries reached for {url}. Giving up.")
            # Store URL in failed set for manual review
            redis_client.sadd('failed_event_links', url)
            return {"success": False, "error": "timeout_exhausted", "url": url}

        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
        logger.info(f"Retrying {url} in {countdown}s with longer timeout")
        raise self.retry(exc=exc, countdown=countdown)

    except FirecrawlRateLimitError as exc:
        logger.error(f"Rate limit exceeded for {url}: {exc}")
        raise self.retry(exc=exc, countdown=300)  # 5 minutes

    except FirecrawlCreditError as exc:
        logger.critical(f"Credit issue for {url}: {exc}")
        return {"success": False, "error": str(exc)}

    except Exception as exc:
        logger.error(f"Unexpected error scraping {url}: {exc}")
        try:
            handle_firecrawl_error(exc)
        except FirecrawlTimeoutError as timeout_exc:
            # Re-raise to be handled by timeout handler above
            raise timeout_exc
        except (FirecrawlRateLimitError, FirecrawlCreditError) as handled_exc:
            raise self.retry(exc=handled_exc)
        raise self.retry(exc=exc)


@app.task(
    name="event_links",
    bind=True,
    default_retry_delay=30 * 10,  # will retry after 5 minutes
    retry_backoff=True,  # exponential backoff: 1s, 2s, 4s, 8s...
    # retry_kwargs={"max_retries": 3},  # number of retries
    max_retries=3,  # number of retries
    retry_jitter=True  # add randomness to retry delay (avoid thundering herd)
)
def get_event_details(self, url: str):
    """
    Extract event details from a single URL
    Stores event details in Redis and marks URL as processed

    Args:
        url: Event detail page URL to scrape

    Returns:
        dict: Status and event count
    """
    # Progressive timeout based on retry attempt
    # retry_count = self.request.retries
    # timeout_map = {
    #     0: 120,  # First attempt: 2 minutes
    #     1: 180,  # Second attempt: 3 minutes
    #     2: 300,  # Third attempt: 5 minutes
    #     3: 420   # Fourth attempt: 7 minutes
    # }
    # timeout = timeout_map.get(retry_count, 300)

    # logger.info(
    #     f"Extracting event details from: {url} (attempt {retry_count + 1}, timeout: {timeout}s)")

    try:
        result = firecrawl_app.scrape(
            url=url,
            actions=[
                {
                    "type": "scroll",
                    "direction": "down"
                }
            ],
            formats=[{
                "type": "json",
                "schema":  EventDetailsSchema,
                "prompt": """Extract all information related to events including title, description, price,
                event link, display photo, photos, time zone, hosts, sponsors, address, city, province/state,
                postal/zip code, country, latitude, longitude, contact email, contact website,
                contact primary phone, and time slots."""
            }],
            # Progressive timeout (SDK bug: expects seconds, not milliseconds)
            timeout=60*5*1000
        )

        if result.metadata.status_code == 200:
            events_details = result.json.get('events', [])

            if events_details:
                # Convert to string for Redis storage
                result_string = json.dumps(events_details)
                redis_client.rpush('events_details', result_string)

                # Mark URL as processed
                redis_client.sadd('processed_event_links', url)

                # Remove from queue
                redis_client.srem('event_links_queue', url)

                event_count = len(events_details) if isinstance(
                    events_details, list) else 1
                logger.info(f"Stored {event_count} event(s) from: {url}")

                return {
                    "success": True,
                    "event_count": event_count
                }
            else:
                logger.warning(f"No event details found at: {url}")
                # Still mark as processed to avoid retrying
                redis_client.sadd('processed_event_links', url)
                redis_client.srem('event_links_queue', url)

                return {
                    "success": True,
                    "event_count": 0
                }
        else:
            logger.warning(
                f"Non-200 status code: {result.metadata.status_code} for {url}")
            return {
                "success": False,
                "status_code": result.metadata.status_code
            }

    except FirecrawlTimeoutError as exc:
        # logger.warning(
        #     f"Timeout extracting details from {url} after {timeout}s (attempt {self.request.retries + 1}): {exc}")

        # If we've exhausted retries, mark as failed but don't crash
        if self.request.retries >= self.max_retries - 1:
            logger.error(f"Max retries reached for {url}. Giving up.")
            # Store URL in failed set for manual review
            redis_client.sadd('failed_event_detail_links', url)
            # Still mark as processed to avoid infinite retries
            redis_client.sadd('processed_event_links', url)
            redis_client.srem('event_links_queue', url)
            return {"success": False, "error": "timeout_exhausted", "url": url}

        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
        logger.info(f"Retrying {url} in {countdown}s with longer timeout")
        raise self.retry(exc=exc, countdown=countdown)

    except FirecrawlRateLimitError as exc:
        logger.error(f"Rate limit exceeded for {url}: {exc}")
        raise self.retry(exc=exc, countdown=300)  # 5 minutes

    except FirecrawlCreditError as exc:
        logger.critical(f"Credit issue for {url}: {exc}")
        return {"success": False, "error": str(exc)}

    except Exception as exc:
        logger.error(f"Unexpected error extracting details from {url}: {exc}")
        try:
            handle_firecrawl_error(exc)
        except FirecrawlTimeoutError as timeout_exc:
            # Re-raise to be handled by timeout handler above
            raise timeout_exc
        except (FirecrawlRateLimitError, FirecrawlCreditError) as handled_exc:
            raise self.retry(exc=handled_exc)
        raise self.retry(exc=exc)


@app.task(name="monitor_credits")
def monitor_firecrawl_credits():
    """
    Monitor Firecrawl API credits
    Can be scheduled to run periodically using Celery Beat

    Returns:
        dict: Credits status
    """
    try:
        # Note: Adjust based on actual Firecrawl API endpoint
        url = "https://api.firecrawl.dev/v1/credits"
        headers = {
            "Authorization": f"Bearer {firecrawl_api_key}"
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            credits_remaining = data.get('credits', 0)

            # Warning thresholds
            WARNING_THRESHOLD = 1000
            CRITICAL_THRESHOLD = 100

            if credits_remaining < CRITICAL_THRESHOLD:
                logger.critical(
                    f"CRITICAL: Only {credits_remaining} Firecrawl credits remaining!")
            elif credits_remaining < WARNING_THRESHOLD:
                logger.warning(
                    f"WARNING: Only {credits_remaining} Firecrawl credits remaining")
            else:
                logger.info(f"Firecrawl credits: {credits_remaining}")

            return {
                "success": True,
                "credits_remaining": credits_remaining
            }
        else:
            logger.error(f"Failed to fetch credits: {response.status_code}")
            return {"success": False}

    except Exception as exc:
        logger.error(f"Error monitoring credits: {exc}")
        return {"success": False, "error": str(exc)}
