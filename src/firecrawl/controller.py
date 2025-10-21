from fastapi import APIRouter, Depends
import logging
from src.arq.rate_limiter import rate_limit_dependency
from .service import queue_stats, get_firecrawl_credits

logger = logging.getLogger(__name__)


firecrawlRouter = APIRouter(
    prefix="/firecrawl",
    tags=["firecrawl"],
    dependencies=[Depends(rate_limit_dependency)]
)


@firecrawlRouter.get("/queue/stats")
async def get_queue_stats():
    """
    Get statistics about the ARQ job queue and processed events

    Returns:
        dict: Queue statistics
    """
    return await queue_stats()


@firecrawlRouter.get("/credit-usage")
async def monitor_firecrawl_credits():
    """
    Monitor Firecrawl API credits
    Can be scheduled to run periodically

    Returns:
        dict: Credits status
    """
    return await get_firecrawl_credits()


# @firecrawlRouter.post("/webhook/firecrawl")
# async def firecrawl_webhook(request: Request):
#     """
#     Webhook endpoint for Firecrawl API callbacks
#     (Optional - for batch scraping operations)

#     Args:
#         request: FastAPI request object

#     Returns:
#         dict: Acknowledgment
#     """
#     payload = await request.json()

#     logger.info(
#         f"Received Firecrawl webhook: type={payload.get('type')}, success={payload.get('success')}")

#     # Handle different webhook types
#     if payload.get("success") and payload.get("type") == 'batch_scrape.completed':
#         batch_id = payload.get("id")
#         logger.info(f"Batch scrape completed: {batch_id}")

#         # Queue processing of batch results
#         await enqueue_job('process_batch_results', batch_id)

#     elif payload.get("type") == 'batch_scrape.failed':
#         logger.error(f"Batch scrape failed: {payload}")

#     return {"ok": True, "received": payload.get("type")}

# @eventRouter.get("/status/{job_id}")
# async def get_job_status(job_id: str):
#     """
#     Check the status of a specific ARQ job

#     Args:
#         job_id: The job ID returned when the job was queued

#     Returns:
#         dict: Job status information
#     """
#     from arq.jobs import JobStatus

#     redis = await create_pool(REDIS_SETTINGS)

#     try:
#         job_info = await redis.get(f"arq:job:{job_id}")

#         if not job_info:
#             return {"error": "Job not found", "job_id": job_id}

#         return {
#             "job_id": job_id,
#             "status": "exists",
#             "info": job_info
#         }
#     except Exception as e:
#         logger.error(f"Error checking job status: {e}")
#         return {"error": str(e), "job_id": job_id}
