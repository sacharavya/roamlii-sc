"""
Batch Scrape Event Details - ARQ Task

Extracts structured data from multiple event detail pages in a single
batch operation using Firecrawl's extract API.
"""

import json
import asyncio
from typing import List
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
from src.arq.calculate_timeout import calculatedTimeout


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
    timeout = calculatedTimeout(retry_count, base_timeout=180)

    logger.info(
        f"Batch extracting {len(urls)} event details (attempt {retry_count + 1}/4, timeout: {timeout}s)")

    try:
        # Rate limiting - CRITICAL
        if rate_limiter:
            await rate_limiter.acquire()

        # Extract structured data from batch of URLs
        extraction_result = await firecrawl_async.batch_scrape(
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
        events = events_data.get('events', []) if isinstance(
            events_data, dict) else []

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
                    logger.warning(
                        f"Skipping event with missing required fields: {event}")
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
            logger.info(
                f"Retrying in {delay}s... (attempt {retry_count + 2}/4)")
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
            raise FirecrawlTimeoutError(
                f"Batch extraction timeout: {str(exc)}")
        elif "rate limit" in str(exc).lower():
            raise FirecrawlRateLimitError(f"Rate limit exceeded: {str(exc)}")
        else:
            handle_firecrawl_error(exc)
