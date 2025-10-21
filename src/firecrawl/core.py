from firecrawl import Firecrawl, AsyncFirecrawl
from src.config import settings


# Use centralized config
firecrawl_api_key = settings.firecrawl_api_key

firecrawl_app = Firecrawl(
    api_key=firecrawl_api_key,
    # api_url=settings.firecrawl_base_url
)

firecrawl_async = AsyncFirecrawl(
    api_key=firecrawl_api_key,
    # api_url=settings.firecrawl_base_url
)
