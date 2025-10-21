from fastapi import HTTPException


class FirecrawlError(Exception):
    """Base exception for Firecrawl-related errors"""
    pass


class FirecrawlRateLimitError(FirecrawlError):
    """Exception for rate limit errors"""
    pass


class FirecrawlCreditError(FirecrawlError):
    """Exception for credit-related errors"""
    pass


class FirecrawlTimeoutError(FirecrawlError):
    """Exception for timeout errors"""
    pass


def handle_firecrawl_error(exc):
    """Helper to categorize and handle Firecrawl errors"""
    error_msg = str(exc)

    if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
        raise FirecrawlTimeoutError(f"Request timeout: {error_msg}")
    elif "rate limit" in error_msg.lower():
        raise FirecrawlRateLimitError(f"Rate limit exceeded: {error_msg}")
    elif "credit" in error_msg.lower() or "insufficient" in error_msg.lower():
        raise FirecrawlCreditError(f"Credit issue: {error_msg}")
    else:
        raise FirecrawlError(f"Firecrawl API error: {error_msg}")
