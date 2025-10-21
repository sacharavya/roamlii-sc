# from src.arq.enqueqe_job import enqueue_job
from src.logging import logger
from arq import create_pool
from src.bg_jobs.arq_tasks import REDIS_SETTINGS


async def enqueue_job(job_name: str, *args, **kwargs):
    """
    Helper to enqueue a job to ARQ

    Args:
        job_name: Name of the function to call
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Job instance
    """
    redis = await create_pool(REDIS_SETTINGS)
    job = await redis.enqueue_job(job_name, *args, **kwargs)
    logger.info(f"[ARQ] Enqueued job {job_name} with ID: {job.job_id}")
    return job
