from src.config import settings
import redis
from arq.connections import RedisSettings

# Use centralized config
redis_url = settings.redis_url

# Create Redis client with connection pooling
redis_client = redis.from_url(
    redis_url,
    max_connections=settings.redis_max_connections,
    decode_responses=False  # Set to True if you want automatic string decoding
)


# ARQ Redis settings
REDIS_SETTINGS = RedisSettings.from_dsn(redis_url)
