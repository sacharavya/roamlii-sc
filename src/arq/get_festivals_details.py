import asyncio
import json

from src.logging import logger
from src.events.schemas import EventDetailsSchema, FestivalsDetailsSchema
from src.firecrawl.core import firecrawl_async
from src.database.core import redis_client
from src.config import settings
from src.arq.rate_limiter import FIRECRAWL_RATE_LIMIT, rate_limiter
from src.exceptions import FirecrawlCreditError, FirecrawlRateLimitError, FirecrawlTimeoutError, handle_firecrawl_error
from src.arq.calculate_timeout import calculatedTimeout
from src.events.utils import write_events_to_csv, write_festivals_to_csv
from src.arq.prompts import FestivalDetailsPrompt


async def get_festivals_details(ctx, url: str, retry_count: int = 0):
    """
    Extract event details from a single URL using async Firecrawl
    Stores event details in Redis and marks URL as processed

    Args:
        ctx: ARQ context with Redis connection
        url: Event detail page URL to scrape
        retry_count: Current retry attempt number

    Returns:
        dict: Status and event count
    """

    timeout = calculatedTimeout(retry_count=retry_count)

    logger.info(
        f"[ARQ] Extracting event details from: {url} (attempt {retry_count + 1}, timeout: {timeout}s)")

    try:
        # 🔥 RATE LIMITING: Wait for our turn to make API request
        await rate_limiter.acquire()
        logger.debug(f"[ARQ] Rate limit check passed for {url}")

        # Use AsyncFirecrawl for non-blocking operation
        result = await firecrawl_async.scrape(
            url,
            actions=[
                {
                    "type": "scroll",
                    "direction": "down"
                }
            ],
            formats=[{
                "type": "json",
                "schema":  FestivalsDetailsSchema,
                "prompt": FestivalDetailsPrompt
            }],
            timeout=timeout
        )

        if result.metadata.status_code == 200:
            events_details = result.json.get('festivals', [])

            print('event_details', events_details)

            if events_details:
                # Convert to string for Redis storage (use config keys)

                for details in events_details:
                    result_string = json.dumps(details)
                    redis_client.rpush(
                        settings.redis_festivals_detail_key, result_string)

                    # Write to CSV file
                    # csv_file_path = getattr(
                    #     settings, 'csv_output_file', 'festivals.csv')
                    # write_events_to_csv(details, csv_file_path)
                    write_festivals_to_csv(
                        details, settings.csv_festival_output_file)

                    # Mark URL as processed
                    redis_client.sadd(
                        settings.redis_processed_festival_links_key, url)

                    # Remove from queue
                    redis_client.srem(
                        settings.redis_festival_links_queue_key, url)

                    event_count = len(events_details) if isinstance(
                        details, list) else 1
                    logger.info(
                        f"[ARQ] Stored {event_count} event(s) from: {url}")

                return {
                    "success": True,
                    "event_count": event_count
                }
            else:
                logger.warning(f"[ARQ] No event details found at: {url}")
                # Still mark as processed to avoid retrying
                redis_client.sadd(
                    settings.redis_processed_festival_links_key, url)
                redis_client.srem(settings.redis_festival_links_queue_key, url)

                return {
                    "success": True,
                    "event_count": 0
                }
        else:
            status_code = result.metadata.statusCode
            logger.warning(
                f"[ARQ] Non-200 status code: {status_code} for {url}")
            return {
                "success": False,
                "status_code": status_code
            }

    except FirecrawlTimeoutError as exc:
        logger.warning(
            f"[ARQ] Timeout extracting details from {url} after {timeout}s (attempt {retry_count + 1}): {exc}")

        if retry_count >= 3:
            logger.error(f"[ARQ] Max retries reached for {url}. Giving up.")
            redis_client.sadd(
                settings.redis_failed_festival_detail_links_key, url)
            redis_client.sadd(settings.redis_processed_festival_links_key, url)
            redis_client.srem(settings.redis_festival_links_queue_key, url)
            return {"success": False, "error": "timeout_exhausted", "url": url}

        raise exc

    except FirecrawlRateLimitError as exc:
        # This should rarely happen now with rate limiter!
        logger.error(
            f"[ARQ] Rate limit exceeded despite rate limiting for {url}: {exc}")
        logger.error(
            f"[ARQ] Consider reducing FIRECRAWL_RATE_LIMIT (currently: {FIRECRAWL_RATE_LIMIT})")

        # Wait longer before retry
        await asyncio.sleep(5)

        # Let ARQ retry
        raise exc

    except FirecrawlCreditError as exc:
        logger.critical(f"[ARQ] Credit issue for {url}: {exc}")
        return {"success": False, "error": str(exc)}

    except Exception as exc:
        logger.error(
            f"[ARQ] Unexpected error extracting details from {url}: {exc}")
        try:
            handle_firecrawl_error(exc)
        except (FirecrawlTimeoutError, FirecrawlRateLimitError) as handled_exc:
            raise handled_exc
        raise exc
