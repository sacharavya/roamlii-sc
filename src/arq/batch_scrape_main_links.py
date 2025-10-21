"""
Batch Scrape Main Links - ARQ Task

Scrapes multiple main event page URLs using Firecrawl's batch_scrape API.
This is significantly faster than scraping URLs one by one.
"""

import asyncio
from typing import List
from src.firecrawl.core import firecrawl_async
from src.logging import logger
from src.database.core import redis_client
from src.config import settings
from src.exceptions import (
    FirecrawlError,
    FirecrawlTimeoutError,
    FirecrawlRateLimitError,
    FirecrawlCreditError,
    handle_firecrawl_error
)
from src.arq.calculate_timeout import calculatedTimeout
from src.events.schemas import MainLinkSchema


async def batch_scrape_main_links(ctx, urls: List[str], retry_count: int = 0):
    """
    Batch scrape multiple main event pages using Firecrawl's batch_scrape API.

    This function processes multiple URLs in a single batch operation,
    which is significantly faster than scraping URLs one by one.

    Args:
        ctx: ARQ context with Redis connection
        urls: List of main event page URLs to scrape
        retry_count: Current retry attempt (0-3)

    Returns:
        dict: Summary of batch scraping results

    Raises:
        FirecrawlTimeoutError: If scraping times out
        FirecrawlRateLimitError: If rate limit is exceeded
        FirecrawlError: For other Firecrawl API errors
    """
    redis = ctx['redis']
    rate_limiter = ctx.get('rate_limiter')

    # Progressive timeout strategy (batch operations need more time)
    timeout = calculatedTimeout(retry_count, base_timeout=240)

    logger.info(
        f"[ARQ] Batch scraping {len(urls)} URLs (attempt {retry_count + 1}/4, timeout: {timeout}s)")

    try:
        # 🔥 RATE LIMITING: Wait for our turn to make batch API request
        if rate_limiter:
            await rate_limiter.acquire()

        logger.info(f"[ARQ] Initiating batch_scrape for {len(urls)} URLs...")

        # Use AsyncFirecrawl batch_scrape - Single API call for all URLs
        batch_job = await firecrawl_async.batch_scrape(
            urls=urls,
            formats=[{
                "type": "json",
                "schema": MainLinkSchema,
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
            }, "markdown"],
            poll_interval=2,
            wait_timeout=timeout
        )

        # Check if batch job completed successfully
        if not batch_job or not hasattr(batch_job, 'data'):
            logger.error(f"[ARQ] Invalid batch job result: {batch_job}")
            raise FirecrawlError("Invalid response from batch_scrape API")

        logger.info(f"[ARQ] Batch scrape completed. Processing {len(batch_job.data)} results...")

        # Process batch results
        total_events = 0
        urls_processed = 0
        urls_failed = 0

        # batch_job.data contains list of results for each URL
        for idx, result in enumerate(batch_job.data):
            url = urls[idx] if idx < len(urls) else 'unknown'

            try:
                # Check if this URL's scrape was successful
                if not result or not hasattr(result, 'metadata'):
                    logger.warning(f"[ARQ] No result data for {url}")
                    urls_failed += 1
                    continue

                if result.metadata.status_code != 200:
                    logger.warning(
                        f"[ARQ] Non-200 status code: {result.metadata.status_code} for {url}")
                    urls_failed += 1
                    continue

                # Extract event links from the JSON format result
                if hasattr(result, 'json') and result.json:
                    events_links = result.json.get('event_links', [])
                    unique_links = 0

                    for link in events_links:
                        # Check if link already exists in processed set
                        if not redis_client.sismember(settings.redis_processed_links_key, link):
                            # Add to queue for processing
                            redis_client.sadd(settings.redis_event_links_queue_key, link)
                            unique_links += 1

                            # Queue event details extraction
                            await redis.enqueue_job('get_event_details', link)
                        else:
                            logger.debug(f"[ARQ] Link already processed: {link}")

                    logger.info(
                        f"[ARQ] Extracted {len(events_links)} links ({unique_links} new) from {url}")

                    total_events += unique_links
                    urls_processed += 1
                else:
                    logger.warning(f"[ARQ] No JSON data in result for {url}")
                    urls_failed += 1

            except Exception as exc:
                logger.error(f"[ARQ] Error processing result for {url}: {exc}")
                urls_failed += 1
                continue

        # Return summary
        result_summary = {
            'success': True,
            'urls_processed': urls_processed,
            'urls_failed': urls_failed,
            'total_events_found': total_events,
            'method': 'batch',
            'retry_count': retry_count
        }

        logger.info(f"[ARQ] Batch scraping complete: {result_summary}")
        return result_summary

    except FirecrawlTimeoutError as exc:
        logger.error(f"[ARQ] Batch scrape timeout after {timeout}s: {exc}")

        if retry_count >= 3:
            logger.error(f"[ARQ] Max retries reached for batch. Giving up.")
            # Mark all URLs as failed
            for url in urls:
                redis_client.sadd(settings.redis_failed_main_links_key, url)
            return {"success": False, "error": "timeout_exhausted", "urls": urls}

        # Let ARQ retry
        raise exc

    except FirecrawlRateLimitError as exc:
        logger.error(f"[ARQ] Rate limit exceeded for batch: {exc}")
        logger.error(f"[ARQ] Waiting 10s before retry...")
        await asyncio.sleep(10)

        # Let ARQ retry
        raise exc

    except FirecrawlCreditError as exc:
        logger.critical(f"[ARQ] Credit issue for batch: {exc}")
        return {"success": False, "error": str(exc)}

    except Exception as exc:
        logger.error(f"[ARQ] Batch scraping error: {str(exc)}")

        # Categorize error
        if "timeout" in str(exc).lower():
            if retry_count < 3:
                delay = 60 * (2 ** retry_count)
                logger.info(f"[ARQ] Timeout error, retrying in {delay}s...")
                await asyncio.sleep(delay)
                raise FirecrawlTimeoutError(f"Batch scrape timeout: {str(exc)}")
            else:
                # Mark all URLs as failed
                for url in urls:
                    redis_client.sadd(settings.redis_failed_main_links_key, url)
                raise FirecrawlTimeoutError(f"Batch scrape timeout: {str(exc)}")
        elif "rate limit" in str(exc).lower():
            raise FirecrawlRateLimitError(f"Rate limit exceeded: {str(exc)}")
        else:
            handle_firecrawl_error(exc)
