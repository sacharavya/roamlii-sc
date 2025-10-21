from src.database.core import redis_client
from src.logging import logger
from src.config import settings
from src.firecrawl.core import firecrawl_api_key


async def queue_stats():
  # Get queue statistics
    pending_links = redis_client.scard('event_links_queue')
    processed_links = redis_client.scard('processed_event_links')
    failed_main_links = redis_client.scard('failed_event_links')
    failed_detail_links = redis_client.scard('failed_event_detail_links')
    total_events = redis_client.llen('events_details')

    return {
        "queue": {
            "pending_event_links": pending_links,
            "processed_event_links": processed_links,
            "failed_main_links": failed_main_links,
            "failed_detail_links": failed_detail_links
        },
        "results": {
            "total_events_extracted": total_events
        }
    }


async def get_firecrawl_credits():
    import httpx

    try:
        url = f"{settings.firecrawl_base_url}/v2/team/credit-usage"
        headers = {
            "Authorization": f"Bearer {firecrawl_api_key}"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()

            return data

        else:
            logger.error(
                f"[ARQ] Failed to fetch credits: {response.status_code}")
            return {"success": False}

    except Exception as exc:
        logger.error(f"[ARQ] Error monitoring credits: {exc}")
        return {"success": False, "error": str(exc)}
