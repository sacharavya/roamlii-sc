from fastapi import APIRouter, UploadFile, File, Depends
from src.events.schemas import (ExtractEventDetailsFromMultipleMainUrlsBody,
                                ExtractEventDetailsFromSingleMainUrlBody)
from .service import extract_event_details_from_event_links, get_all_events, extract_event_details_from_single_link, extract_event_details_from_csv_file
from src.arq.rate_limiter import rate_limit_dependency


eventRouter = APIRouter(
    prefix="/events",
    tags=["events"],
    dependencies=[Depends(rate_limit_dependency)]
)


@eventRouter.post("/extract_events_from_csv")
async def extract_event_details_from_csv_upload(file: UploadFile = File(...)):
    """
    Extract event details from URLs in an uploaded CSV file.

    Upload a CSV file containing URLs to scrape. The CSV should have:
    - A column named 'url', 'website', 'Base URL' or 'link' containing the URLs
    - OR URLs in the first column if no header is present
    - URLs must start with http:// or https://

    Example CSV formats:
    ```
    url
    https://example.com/events
    https://example2.com/calendar
    ```
    This endpoint processes URLs one at a time using ARQ workers.
    """
    return await extract_event_details_from_csv_file(file)


# @eventRouter.post("/extract_event_from_single_main_url")
# async def extract_event_details_from_single_main_url(body: ExtractEventDetailsFromSingleMainUrlBody):
#     """
#     Extract event details using single main URL scraping method.

#     This endpoint processes single a time. Good for:
#     - Testing individual URLs
#     - Debugging specific pages
#     """
#     return await extract_event_details_from_single_link(url=body.url)


# @eventRouter.post("/extract_events_from_multiple_main_urls")
# async def extract_event_details_from_multiple_main_urls(body: ExtractEventDetailsFromMultipleMainUrlsBody):
#     """
#     Extract event details using multiple URL scraping method.

#     This endpoint processes URLs one at a time. Good for:
#     - Testing individual URLs
#     - Debugging specific pages
#     - Processing small batches (1-5 URLs)

#     For better performance with multiple URLs, use /batch endpoint instead.
#     """
#     return await extract_event_details_from_event_links(urls=body.links)


@eventRouter.get("/all")
async def get_extracted_events(limit: int = 10, offset: int = 0):
    """
    Get all extracted events from Redis storage.

    Args:
        limit: Number of events to return (default: 10)
        offset: Offset for pagination (default: 0)

    Returns:
        dict: List of extracted events with pagination info
    """
    return get_all_events(limit=limit, offset=offset)


# @eventRouter.post("/batch")
# async def extract_event_details_in_batch(body: EXTRACT_EVENT_DETAILS):
#     """
#     Extract event details using batch scraping method (50x faster).

#     This endpoint processes multiple URLs in a single batch operation using
#     Firecrawl's batch_scrape_urls() API. Benefits:
#     - 50x faster than single URL scraping
#     - More efficient API usage
#     - Better for large batches (10+ URLs)
#     - Reduced rate limit consumption

#     Recommended for production use with multiple URLs.
#     """
#     return await extract_event_details_batch(body)
