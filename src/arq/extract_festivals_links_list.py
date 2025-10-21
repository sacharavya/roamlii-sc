import asyncio
from src.logging import logger
from src.events.schemas import MainLinkSchema
from src.firecrawl.core import firecrawl_async
from src.database.core import redis_client
from src.config import settings
from src.arq.rate_limiter import FIRECRAWL_RATE_LIMIT, rate_limiter
from src.exceptions import FirecrawlCreditError, FirecrawlRateLimitError, FirecrawlTimeoutError, handle_firecrawl_error
from src.arq.calculate_timeout import calculatedTimeout


async def extract_festivals_links_list(ctx, url: str, retry_count: int = 0):
    """
    Extract event links from a single URL using async Firecrawl
    Stores links in Redis with deduplication and triggers detail extraction

    Args:
        ctx: ARQ context with Redis connection
        url: Main event page URL to scrape
        retry_count: Current retry attempt number

    Returns:
        dict: Status and count of extracted links
    """

    timeout = calculatedTimeout(retry_count=retry_count)

    logger.info(
        f"[ARQ] Starting async scrape for URL: {url} (attempt {retry_count + 1}, timeout: {timeout}s)")

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
                "schema":  MainLinkSchema,
                "prompt": """
                            You are given a webpage that may contain multiple links related to festivals.

                            Your task:
                            Extract ONLY the URLs that lead directly to **individual festival detail pages**.

                            Guidelines:
                            ✅ Include links that:
                            - Lead to pages describing a specific festival (music, cultural, food, seasonal, etc.).
                            - Contain information like date, location, and activities for a single festival.
                            - Link to registration, passes, or ticket pages for a particular festival.
                            - Contain festival identifiers or slugs (e.g., /festivals/holi-celebration, /musicfest-2025).

                            🚫 Exclude links that:
                            - Point to generic “festival listings”, “top festivals”, or overview pages.
                            - Lead to unrelated blogs, articles, or news mentions.
                            - Load “See More” or “Next Page” buttons without specific festival info.

                            ⚙️ If a festival detail opens in a modal or popup (like #festival-123), include that.

                            🎯 Each URL should represent one specific festival.
                        """
            }],
            timeout=timeout,
        )

        if result.metadata.status_code == 200:
            events_links = result.json.get('links', [])
            unique_links = 0

            for link in events_links:
                # Check if link already exists in processed set (use config keys)
                if not redis_client.sismember(settings.redis_processed_festival_links_key, link):
                    # Add to queue for processing
                    redis_client.sadd(
                        settings.redis_festival_links_queue_key, link)
                    unique_links += 1

                    # Queue event details extraction
                    await ctx['redis'].enqueue_job('get_festivals_details', link)
                else:
                    logger.debug(f"[ARQ] Link already processed: {link}")

            logger.info(
                f"[ARQ] Extracted {len(events_links)} links ({unique_links} new) from {url}")

            return {
                "success": True,
                "total_links": len(events_links),
                "unique_links": unique_links
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
            f"[ARQ] Timeout scraping {url} after {timeout}s (attempt {retry_count + 1}): {exc}")

        # If we've exhausted retries, mark as failed
        if retry_count >= 3:
            logger.error(f"[ARQ] Max retries reached for {url}. Giving up.")
            redis_client.sadd(
                settings.redis_failed_festival_main_links_key, url)
            return {"success": False, "error": "timeout_exhausted", "url": url}

        # Defer retry to ARQ (will automatically retry with backoff)
        raise exc

    except FirecrawlRateLimitError as exc:
        # This should rarely happen now with rate limiter!
        logger.error(
            f"[ARQ] Rate limit exceeded despite rate limiting for {url}: {exc}")
        logger.error(
            f"[ARQ] Consider reducing FIRECRAWL_RATE_LIMIT (currently: {FIRECRAWL_RATE_LIMIT})")

        # Wait longer before retry (Firecrawl suggests 1s, we'll wait 5s to be safe)
        await asyncio.sleep(5)

        # Let ARQ retry
        raise exc

    except FirecrawlCreditError as exc:
        logger.critical(f"[ARQ] Credit issue for {url}: {exc}")
        return {"success": False, "error": str(exc)}

    except Exception as exc:
        logger.error(f"[ARQ] Unexpected error scraping {url}: {exc}")
        try:
            handle_firecrawl_error(exc)
        except (FirecrawlTimeoutError, FirecrawlRateLimitError) as handled_exc:
            raise handled_exc
        # For other errors, let ARQ retry
        raise exc
