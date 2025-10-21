from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from dotenv import load_dotenv

load_dotenv(override=True)


class Settings(BaseSettings):
    """Application settings for Event Scraper."""

    # App settings
    app_name: str = Field(default="Event Scraper API",
                          description="Application name")
    app_version: str = Field(
        default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development",
                             description="Environment (development, staging, production)")

    # Server settings
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(
        default=True, description="Auto-reload on file changes")

    # API settings
    api_prefix: str = Field(default="/api", description="API prefix")
    api_rate_limit: int = Field(
        default=5, description="Fastapi rate limit (requests per minute)")

    # FireCrawl settings
    firecrawl_api_key: str = Field(..., description="FireCrawl API key")
    firecrawl_base_url: Optional[str] = Field(
        default="https://api.firecrawl.dev", description="FireCrawl base URL")
    firecrawl_rate_limit: int = Field(
        default=10, description="FireCrawl API rate limit (requests per minute)")
    firecrawl_timeout: int = Field(
        default=120, description="FireCrawl request timeout in seconds")

    # Redis settings
    redis_url: str = Field(..., description="Redis connection URL")
    redis_max_connections: int = Field(
        default=10, description="Redis max connections in pool")

    # ARQ (Background Jobs) settings
    arq_max_jobs: int = Field(
        default=2, description="Maximum concurrent ARQ jobs")
    arq_max_tries: int = Field(
        default=4, description="Maximum retry attempts per job")
    arq_job_timeout: int = Field(
        default=600, description="Job timeout in seconds (10 minutes)")
    arq_keep_result: int = Field(
        default=3600, description="Keep job results for N seconds (1 hour)")

    # Scraping settings
    scrape_timeout_initial: int = Field(
        default=120, description="Initial scrape timeout in seconds")
    scrape_timeout_max: int = Field(
        default=420, description="Maximum scrape timeout in seconds (7 minutes)")
    scrape_scroll_enabled: bool = Field(
        default=True, description="Enable page scrolling during scrape")

    # CORS settings
    cors_origins: list[str] = Field(default=["*"], description="CORS origins")
    cors_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"], description="CORS methods")
    cors_headers: list[str] = Field(default=["*"], description="CORS headers")
    cors_credentials: bool = Field(
        default=True, description="Allow credentials in CORS requests")

    # Logging
    log_level: str = Field(default="INFO",
                           description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    log_file: Optional[str] = Field(
        default=None, description="Log file path (None for stdout only)")

    # Redis key prefixes for events
    redis_events_detail_key: str = Field(
        default="events_details", description="Redis key for event details")
    redis_event_links_queue_key: str = Field(
        default="event_links_queue", description="Redis key for event links queue")
    redis_processed_event_links_key: str = Field(
        default="processed_event_links", description="Redis key for processed links")
    redis_failed_event_main_links_key: str = Field(
        default="failed_event_links", description="Redis key for failed main links")
    redis_failed_event_detail_links_key: str = Field(
        default="failed_event_detail_links", description="Redis key for failed detail links")

    # Redis key prefixes for festivals
    redis_festivals_detail_key: str = Field(
        default="festivals_details", description="Redis key for festival details")
    redis_festival_links_queue_key: str = Field(
        default="festival_links_queue", description="Redis key for festival links queue")
    redis_processed_festival_links_key: str = Field(
        default="processed_festival_links", description="Redis key for processed festival links")
    redis_failed_festival_main_links_key: str = Field(
        default="failed_festival_links", description="Redis key for failed festival main links")
    redis_failed_festival_detail_links_key: str = Field(
        default="failed_festival_detail_links", description="Redis key for failed festival detail links")

    # Redis key prefixes for sports events
    redis_sports_detail_key: str = Field(
        default="sports_details", description="Redis key for sports event details")
    redis_sport_links_queue_key: str = Field(
        default="sport_links_queue", description="Redis key for sport links queue")
    redis_processed_sport_links_key: str = Field(
        default="processed_sport_links", description="Redis key for processed sport links")
    redis_failed_sport_main_links_key: str = Field(
        default="failed_sport_links", description="Redis key for failed sport main links")
    redis_failed_sport_detail_links_key: str = Field(
        default="failed_sport_detail_links", description="Redis key for failed sport detail links")

    # Monitoring settings
    enable_metrics: bool = Field(
        default=False, description="Enable application metrics")
    credits_warning_threshold: int = Field(
        default=1000, description="FireCrawl credits warning threshold")
    credits_critical_threshold: int = Field(
        default=100, description="FireCrawl credits critical threshold")

    # CSV output settings
    csv_event_output_file: str = Field(
        default="events.csv", description="CSV file path for storing event details")
    csv_festival_output_file: str = Field(
        default="festivals.csv", description="CSV file path for storing event details")
    csv_sport_output_file: str = Field(
        default="sports.csv", description="CSV file path for storing event details")

    class Config:
        env_file = ".env"
        env_prefix = ""
        # doesnot matter if .env has FIRECRAWL_API_KEY, but in Settings firecrawl_api_key, will work perfectly just naming convention must be same
        case_sensitive = False
        # Allow extra fields from environment
        extra = "ignore"


# Global settings instance
settings = Settings()
