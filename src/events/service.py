import json
from fastapi import HTTPException, UploadFile, File
from src.arq.enqueqe_job import enqueue_job
from src.logging import logger
from src.database.core import redis_client
from .utils import parse_urls_by_type_from_csv, save_uploaded_file


async def extract_event_details_from_csv_file(file: UploadFile = File(...)):
    # Validate file type by extension and content type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a CSV file (.csv)"
        )

    # Validate MIME type
    allowed_content_types = ['text/csv',
                             'application/csv', 'application/vnd.ms-excel']
    if file.content_type and file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type '{file.content_type}'. Only CSV files are allowed."
        )

    try:
        # Define uploads directory
        await save_uploaded_file(file)

        res = await parse_urls_by_type_from_csv(file)

        if res["success"]:
            if len(res["events_list"]) > 0:
                await extract_events_details_from_links(urls=res["events_list"], job_type='extract_events_list')

            if len(res["festivals_list"]) > 0:
                await extract_events_details_from_links(urls=res["festivals_list"], job_type='extract_festivals_links_list')

            if len(res["sports_list"]) > 0:
                await extract_events_details_from_links(urls=res["sports_list"], job_type="extract_sports_links_list")

        # Add CSV-specific information to the response
        return {
            "status": "queued",
            "source": "csv_upload",
            "filename": file.filename,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing CSV file: {str(e)}"
        )


async def extract_event_details_from_single_link(url: str):
    if not url:
        return {"error": "No URLs provided", "status": "failed"}

    await enqueue_job('extract_events_list', url)

    return {
        "status": "queued",
        "method": "single",
        "message": f"Successfully queued {url} for scraping",
    }


async def extract_events_details_from_links(urls: list[str], job_type: str):

    if not urls:
        return {"error": "No URLs provided", "status": "failed"}

    job_ids = []
    for link in urls:
        # Queue each URL for scraping
        job = await enqueue_job(job_type, link)
        job_ids.append(str(job.job_id))
        logger.info(f"Queued scraping job for: {link} (Job ID: {job.job_id})")

    return {
        "status": "queued",
        "method": "single",
        "message": f"Successfully queued {len(urls)} URLs for scraping (single URL method)",
        "urls_queued": len(urls),
        "job_ids": job_ids
    }


async def extract_event_details_from_event_links(urls: list[str]):
    """
    Queue event scraping jobs using ARQ (async task queue) - SINGLE URL METHOD

    This endpoint accepts a list of main event page URLs and queues them
    for asynchronous scraping using ARQ workers. Each URL is processed individually.

    Use this method for:
    - Testing individual URLs
    - Debugging specific pages
    - Processing small batches (1-5 URLs)

    Args:
        body: Request body containing list of URLs to scrape

    Returns:
        dict: Status message with queued job count and job IDs
    """

    if not urls:
        return {"error": "No URLs provided", "status": "failed"}

    job_ids = []
    for link in urls:
        # Queue each URL for scraping
        job = await enqueue_job('extract_events_list', link)
        job_ids.append(str(job.job_id))
        logger.info(f"Queued scraping job for: {link} (Job ID: {job.job_id})")

    return {
        "status": "queued",
        "method": "single",
        "message": f"Successfully queued {len(urls)} URLs for scraping (single URL method)",
        "urls_queued": len(urls),
        "job_ids": job_ids
    }


def get_all_events(limit: int, offset: int):
    """
    Get extracted event details from Redis

    Args:
        limit: Number of events to return (default: 10)
        offset: Offset for pagination (default: 0)

    Returns:
        dict: List of extracted events
    """

    # Get events from Redis list
    events_data = redis_client.lrange(
        'events_details', offset, offset + limit - 1)

    events = []
    for event_str in events_data:
        try:
            event = json.loads(event_str)
            events.append(event)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding event data: {e}")
            continue

    total_count = redis_client.llen('events_details')

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "count": len(events),
        "events": events
    }


# async def extract_event_details_batch(body: EXTRACT_EVENT_DETAILS):
#     """
#     Queue batch event scraping jobs using ARQ - BATCH METHOD (50x faster)

#     This endpoint accepts a list of main event page URLs and queues them
#     for batch scraping using Firecrawl's batch_scrape_urls() API. All URLs
#     are processed in a single batch operation.

#     Use this method for:
#     - Production use with multiple URLs
#     - Large batches (10+ URLs)
#     - Better performance and efficiency
#     - Reduced API calls and rate limit usage

#     Args:
#         body: Request body containing list of URLs to scrape

#     Returns:
#         dict: Status message with queued job info
#     """

#     if not body.main_links:
#         return {"error": "No URLs provided", "status": "failed"}

#     # Queue single batch job for all URLs
#     job = await enqueue_job('batch_scrape_main_links', body.main_links)
#     logger.info(
#         f"Queued batch scraping job for {len(body.main_links)} URLs (Job ID: {job.job_id})")

#     return {
#         "status": "queued",
#         "method": "batch",
#         "message": f"Successfully queued {len(body.main_links)} URLs for batch scraping (50x faster)",
#         "urls_queued": len(body.main_links),
#         "job_id": str(job.job_id),
#         "note": "Batch method processes all URLs in a single API request"
#     }
