import asyncio
import time
from fastapi import HTTPException
from src.config import settings
from src.logging import logger


# ============================================
# Rate Limiter for Firecrawl API & API Routes
# ============================================

class FirecrawlRateLimiter:
    """
    Token bucket rate limiter to prevent "Rate Limit Exceeded" errors

    Your error: "Consumed (req/min): 17, Remaining (req/min): 0"
    This means you're making too many requests per minute!

    Solution: Wait between requests to stay under the limit
    """

    def __init__(self, requests_per_minute: int = 12):
        """
        Args:
            requests_per_minute: Max requests per minute
                Free/Hobby: 15-20 req/min (use 12 to be safe)
                Standard: 50-100 req/min
                Growth: 200+ req/min
        """
        self.rate = requests_per_minute
        self.tokens = requests_per_minute
        self.max_tokens = requests_per_minute
        self.last_update = time.time()
        self.lock = asyncio.Lock()
        self.min_interval = 60.0 / requests_per_minute  # Seconds between requests

        logger.info(
            f"[RateLimiter] Initialized: {self.rate} requests/minute (~{self.min_interval:.2f}s between requests)")

    async def acquire(self):
        """Wait if necessary to respect rate limit"""
        async with self.lock:
            now = time.time()
            time_passed = now - self.last_update

            # Refill tokens based on time passed
            self.tokens = min(
                self.max_tokens,
                self.tokens + time_passed * (self.rate / 60.0)
            )
            self.last_update = now

            # Wait if no tokens available
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / (self.rate / 60.0)
                logger.warning(
                    f"[RateLimiter] Rate limit reached. Waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                self.tokens = 1
                self.last_update = time.time()

            # Consume a token
            self.tokens -= 1
            remaining_tokens = int(self.tokens)
            if remaining_tokens <= 3:
                logger.info(
                    f"[RateLimiter] Low tokens: {remaining_tokens}/{self.max_tokens} remaining")


class APIRateLimiter:
    """
    Token bucket rate limiter for API endpoints that raises HTTPException when limit is exceeded
    instead of waiting. This provides better user experience for API consumers.
    """

    def __init__(self, requests_per_minute: int = 10):
        """
        Args:
            requests_per_minute: Max requests per minute for API endpoints
        """
        self.rate = requests_per_minute
        self.tokens = requests_per_minute
        self.max_tokens = requests_per_minute
        self.last_update = time.time()
        self.rate_limit_hit_time = None  # Track when rate limit was first exceeded
        self.lock = asyncio.Lock()
        self.min_interval = 60.0 / requests_per_minute  # Seconds between requests

        logger.info(
            f"[APIRateLimiter] Initialized: {self.rate} requests/minute (~{self.min_interval:.2f}s between requests)")

    async def acquire(self):
        """
        Check if request can proceed, raise HTTPException if rate limit exceeded

        Raises:
            HTTPException: 429 status code with retry-after header when rate limit is exceeded
        """
        async with self.lock:
            now = time.time()

            # Check if rate limit was hit previously and if 60 seconds have passed
            if self.rate_limit_hit_time is not None:
                time_since_rate_limit = now - self.rate_limit_hit_time

                # If 60 seconds have passed since rate limit was hit, reset everything
                if time_since_rate_limit >= 60.0:
                    logger.info(
                        f"[APIRateLimiter] Rate limit window expired. Resetting tokens.")
                    self.tokens = self.max_tokens
                    self.last_update = now
                    self.rate_limit_hit_time = None
                else:
                    # Still within the rate limit window, reject the request
                    retry_after = int(60.0 - time_since_rate_limit) + 1

                    logger.warning(
                        f"[APIRateLimiter] Rate limit still active. Rejecting request. "
                        f"Retry after {retry_after}s")

                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "Rate limit exceeded",
                            "message": f"Too many requests. Maximum {self.rate} requests per minute allowed.",
                            "retry_after_seconds": retry_after,
                            "requests_per_minute": self.rate
                        },
                        headers={"Retry-After": str(retry_after)}
                    )

            # Normal token bucket refill logic
            time_passed = now - self.last_update

            # Refill tokens based on time passed
            self.tokens = min(
                self.max_tokens,
                self.tokens + time_passed * (self.rate / 60.0)
            )
            self.last_update = now

            # Check if tokens available
            if self.tokens < 1:
                # Mark when rate limit was first hit
                self.rate_limit_hit_time = now
                retry_after = 60  # Always wait for full minute from this point

                logger.warning(
                    f"[APIRateLimiter] Rate limit exceeded. Rejecting request. "
                    f"Retry after {retry_after}s")

                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Maximum {self.rate} requests per minute allowed.",
                        "retry_after_seconds": retry_after,
                        "requests_per_minute": self.rate
                    },
                    headers={"Retry-After": str(retry_after)}
                )

            # Consume a token
            self.tokens -= 1
            remaining_tokens = int(self.tokens)
            if remaining_tokens <= 2:
                logger.info(
                    f"[APIRateLimiter] Low tokens: {remaining_tokens}/{self.max_tokens} remaining")


# Global rate limiter - use centralized config
FIRECRAWL_RATE_LIMIT = settings.firecrawl_rate_limit

rate_limiter = FirecrawlRateLimiter(requests_per_minute=FIRECRAWL_RATE_LIMIT)

rate_limiter_api = APIRateLimiter(requests_per_minute=settings.api_rate_limit)


# ============================================
# FastAPI Dependency for API Rate Limiting
# ============================================


async def rate_limit_dependency():
    """
    FastAPI dependency to rate limit API endpoints.
    Use this in router dependencies to apply rate limiting to all routes.

    Usage:
        router = APIRouter(dependencies=[Depends(rate_limit_dependency)])
    """
    await rate_limiter_api.acquire()
    logger.debug("[API RateLimiter] Request allowed")
