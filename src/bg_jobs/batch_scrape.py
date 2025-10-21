"""
Batch Scraping Module for Firecrawl API

This module implements batch scraping functionality using Firecrawl's
batch_scrape_urls() method for 50x faster performance compared to
single URL scraping.

Key Benefits:
- Process multiple URLs in a single API request
- 50x faster than sequential single-URL scraping
- Reduces API calls and improves rate limit efficiency
- Better for processing large batches of URLs
"""

import json
import asyncio
from typing import List, Dict, Any
from src.firecrawl.core import firecrawl_async
from src.database.core import redis_client
from src.logging import logger
from src.events.schemas import EVENT_DETAILS_SCHEMA
from src.exceptions import (
    FirecrawlError,
    FirecrawlTimeoutError,
    FirecrawlRateLimitError,
    handle_firecrawl_error
)


async def batch_scrape_main_links(ctx, urls: List[str], retry_count: int = 0):
    """
    Batch scrape multiple main event pages at once using Firecrawl's batch API.

    This function processes multiple URLs in a single API request, which is
    approximately 50x faster than scraping URLs one by one.

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

    # Progressive timeout strategy
    timeout_map = {
        0: 240,  # First attempt: 4 minutes (batch takes longer)
        1: 360,  # Second attempt: 6 minutes
        2: 480,  # Third attempt: 8 minutes
        3: 600   # Fourth attempt: 10 minutes
    }
    timeout = timeout_map.get(retry_count, 480)

    logger.info(f"Batch scraping {len(urls)} URLs (attempt {retry_count + 1}/4, timeout: {timeout}s)")

    try:
        # Rate limiting - CRITICAL for batch operations
        if rate_limiter:
            await rate_limiter.acquire()

        # Batch scrape parameters
        params = {
            'formats': ['markdown', 'html'],
            'onlyMainContent': True,
            'timeout': timeout,
            'waitFor': 3000,
        }

        # Execute batch scrape - Single API call for all URLs
        logger.info(f"Calling batch_scrape_urls for {len(urls)} URLs...")
        batch_result = await firecrawl_async.batch_scrape_urls(
            urls=urls,
            params=params
        )

        if not batch_result or not isinstance(batch_result, dict):
            logger.error(f"Invalid batch result: {batch_result}")
            raise FirecrawlError("Invalid response from batch_scrape_urls")

        # Process batch results
        total_events = 0
        detail_jobs = []

        # batch_result structure: {'success': True, 'data': [...]}
        data = batch_result.get('data', [])

        for idx, result in enumerate(data):
            url = urls[idx] if idx < len(urls) else 'unknown'

            if not result.get('success'):
                logger.warning(f"Failed to scrape {url}: {result.get('error', 'Unknown error')}")
                continue

            markdown = result.get('markdown', '')

            if not markdown:
                logger.warning(f"No markdown content for {url}")
                continue

            # Extract event links from markdown using Firecrawl extract
            try:
                if rate_limiter:
                    await rate_limiter.acquire()

                extraction = await firecrawl_async.extract(
                    urls=[url],
                    params={
                        'schema': {
                            "type": "object",
                            "properties": {
                                "events_links": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of all event detail page URLs"
                                }
                            },
                            "required": ["events_links"]
                        },
                        'prompt': 'Extract all event detail page URLs from this main events listing page.'
                    }
                )

                events_links = extraction.get('data', {}).get('events_links', [])

                if events_links:
                    logger.info(f"Extracted {len(events_links)} event links from {url}")
                    total_events += len(events_links)

                    # Queue batch job for event details (group in batches of 10)
                    batch_size = 10
                    for i in range(0, len(events_links), batch_size):
                        batch_links = events_links[i:i + batch_size]
                        job = await redis.enqueue_job(
                            'batch_scrape_event_details',
                            batch_links
                        )
                        detail_jobs.append(str(job.job_id))
                        logger.info(f"Queued batch detail job {job.job_id} for {len(batch_links)} events")
                else:
                    logger.warning(f"No event links found for {url}")

            except Exception as e:
                logger.error(f"Error extracting links from {url}: {str(e)}")
                continue

        result_summary = {
            'success': True,
            'urls_processed': len(data),
            'total_events_found': total_events,
            'detail_jobs_queued': len(detail_jobs),
            'detail_job_ids': detail_jobs,
            'method': 'batch',
            'retry_count': retry_count
        }

        logger.info(f"Batch scraping complete: {result_summary}")
        return result_summary

    except asyncio.TimeoutError:
        error_msg = f"Batch scrape timed out after {timeout}s"
        logger.error(error_msg)

        if retry_count < 3:
            delay = 60 * (2 ** retry_count)  # Exponential backoff: 60s, 120s, 240s
            logger.info(f"Retrying in {delay}s... (attempt {retry_count + 2}/4)")
            await asyncio.sleep(delay)
            raise asyncio.CancelledError()  # ARQ will retry
        else:
            raise FirecrawlTimeoutError(error_msg)

    except Exception as exc:
        logger.error(f"Batch scraping error: {str(exc)}")

        # Categorize error
        if "timeout" in str(exc).lower():
            if retry_count < 3:
                delay = 60 * (2 ** retry_count)
                logger.info(f"Timeout error, retrying in {delay}s...")
                await asyncio.sleep(delay)
                raise asyncio.CancelledError()
            raise FirecrawlTimeoutError(f"Batch scrape timeout: {str(exc)}")
        elif "rate limit" in str(exc).lower():
            raise FirecrawlRateLimitError(f"Rate limit exceeded: {str(exc)}")
        else:
            handle_firecrawl_error(exc)


async def batch_scrape_event_details(ctx, urls: List[str], retry_count: int = 0):
    """
    Batch scrape event detail pages and extract structured data.

    This function processes multiple event detail URLs in a single batch,
    extracting structured event information using Firecrawl's extract API.

    Args:
        ctx: ARQ context with Redis connection
        urls: List of event detail page URLs to scrape
        retry_count: Current retry attempt (0-3)

    Returns:
        dict: Summary of batch extraction results

    Raises:
        FirecrawlTimeoutError: If extraction times out
        FirecrawlRateLimitError: If rate limit is exceeded
        FirecrawlError: For other Firecrawl API errors
    """
    redis = ctx['redis']
    rate_limiter = ctx.get('rate_limiter')

    # Progressive timeout strategy
    timeout_map = {
        0: 180,  # First attempt: 3 minutes
        1: 300,  # Second attempt: 5 minutes
        2: 420,  # Third attempt: 7 minutes
        3: 540   # Fourth attempt: 9 minutes
    }
    timeout = timeout_map.get(retry_count, 420)

    logger.info(f"Batch extracting {len(urls)} event details (attempt {retry_count + 1}/4, timeout: {timeout}s)")

    try:
        # Rate limiting - CRITICAL
        if rate_limiter:
            await rate_limiter.acquire()

        # Extract structured data from batch of URLs
        extraction_result = await firecrawl_async.extract(
            urls=urls,
            params={
                'schema': EVENT_DETAILS_SCHEMA,
                'prompt': '''Extract detailed information for each event from these event pages.
                For each event, extract:
                - Title (event name)
                - Description (full event description)
                - Event link (URL to the event page)
                - Location (venue/address if available)
                - Date (event date/time if available)
                - Registration link (if available)
                - Contact information (email/phone if available)

                If any field is not found, use empty string.
                Return an array of event objects.'''
            }
        )

        if not extraction_result or not isinstance(extraction_result, dict):
            logger.error(f"Invalid extraction result: {extraction_result}")
            raise FirecrawlError("Invalid response from extract API")

        # Process extracted events
        events_data = extraction_result.get('data', {})
        events = events_data.get('events', []) if isinstance(events_data, dict) else []

        if not events:
            logger.warning(f"No events extracted from {len(urls)} URLs")
            return {
                'success': False,
                'urls_processed': len(urls),
                'events_extracted': 0,
                'events_stored': 0,
                'method': 'batch'
            }

        # Store events in Redis
        stored_count = 0
        for event in events:
            try:
                # Validate required fields
                if not event.get('title') or not event.get('event_link'):
                    logger.warning(f"Skipping event with missing required fields: {event}")
                    continue

                # Store in Redis list
                event_json = json.dumps(event)
                redis_client.rpush('events_details', event_json)
                stored_count += 1

            except Exception as e:
                logger.error(f"Error storing event: {str(e)}")
                continue

        result_summary = {
            'success': True,
            'urls_processed': len(urls),
            'events_extracted': len(events),
            'events_stored': stored_count,
            'method': 'batch',
            'retry_count': retry_count
        }

        logger.info(f"Batch extraction complete: {result_summary}")
        return result_summary

    except asyncio.TimeoutError:
        error_msg = f"Batch extraction timed out after {timeout}s"
        logger.error(error_msg)

        if retry_count < 3:
            delay = 60 * (2 ** retry_count)
            logger.info(f"Retrying in {delay}s... (attempt {retry_count + 2}/4)")
            await asyncio.sleep(delay)
            raise asyncio.CancelledError()
        else:
            raise FirecrawlTimeoutError(error_msg)

    except Exception as exc:
        logger.error(f"Batch extraction error: {str(exc)}")

        # Categorize error
        if "timeout" in str(exc).lower():
            if retry_count < 3:
                delay = 60 * (2 ** retry_count)
                logger.info(f"Timeout error, retrying in {delay}s...")
                await asyncio.sleep(delay)
                raise asyncio.CancelledError()
            raise FirecrawlTimeoutError(f"Batch extraction timeout: {str(exc)}")
        elif "rate limit" in str(exc).lower():
            raise FirecrawlRateLimitError(f"Rate limit exceeded: {str(exc)}")
        else:
            handle_firecrawl_error(exc)
