"""
Redis connection utility for maintaining connection pools and error handling.
This module provides a singleton Redis connection manager that handles:
- Connection pooling
- Error handling and retry logic
- Health checks
"""
import logging
import time
import functools
from typing import Optional, Any
from django.conf import settings
import redis

logger = logging.getLogger(__name__)

# Maximum number of retries for Redis operations
MAX_RETRIES = 3
# Retry delay in seconds (exponential backoff)
RETRY_DELAY = 0.5

class RedisConnectionError(Exception):
    """Exception for Redis connection issues"""
    pass

class RedisManager:
    """Singleton Redis connection manager"""
    _instance = None
    _pool = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize Redis connection pool"""
        try:
            redis_url = settings.CELERY_BROKER_URL
            
            # Create a connection pool
            self._pool = redis.ConnectionPool.from_url(
                redis_url,
                max_connections=50,
                socket_timeout=5,
                socket_connect_timeout=5,
                health_check_interval=30,
            )
            
            # Create a client using the pool
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            self._client.ping()
            logger.info(f"Redis connection initialized successfully to {redis_url}")
            
        except redis.RedisError as e:
            logger.error(f"Failed to initialize Redis connection: {str(e)}")
            raise RedisConnectionError(f"Could not connect to Redis: {str(e)}")
    
    def get_client(self) -> redis.Redis:
        """
        Get Redis client instance
        
        Returns:
            redis.Redis: A Redis client from the connection pool
        """
        if not self._client:
            self._initialize()
        return self._client
    
    def with_retry(self, func):
        """
        Decorator for Redis operations with retry logic
        
        Args:
            func: The function to decorate
            
        Returns:
            Function wrapped with retry logic
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            last_error = None
            
            while retries < MAX_RETRIES:
                try:
                    return func(*args, **kwargs)
                except (redis.RedisError, ConnectionError) as e:
                    last_error = e
                    retries += 1
                    
                    # Use exponential backoff
                    wait_time = RETRY_DELAY * (2 ** (retries - 1))
                    logger.warning(
                        f"Redis operation failed (attempt {retries}/{MAX_RETRIES}): {str(e)}. "
                        f"Retrying in {wait_time:.2f}s..."
                    )
                    
                    # Wait before retrying
                    time.sleep(wait_time)
                    
                    # If we've reached max retries, try to reinitialize the connection
                    if retries == MAX_RETRIES - 1:
                        logger.info("Attempting to reinitialize Redis connection...")
                        try:
                            self._initialize()
                        except RedisConnectionError:
                            # Continue with the retry loop even if reinitialization fails
                            pass
            
            # If we've exhausted all retries
            logger.error(f"Redis operation failed after {MAX_RETRIES} attempts: {str(last_error)}")
            raise RedisConnectionError(f"Redis operation failed: {str(last_error)}")
        
        return wrapper
    
    def health_check(self) -> bool:
        """
        Perform a health check on the Redis connection
        
        Returns:
            bool: True if Redis is healthy, False otherwise
        """
        try:
            # Basic ping check
            self._client.ping()
            
            # Check memory usage (optional)
            info = self._client.info()
            used_memory = info.get('used_memory', 0)
            used_memory_peak = info.get('used_memory_peak', 0)
            
            # Log memory usage
            logger.debug(f"Redis memory usage: {used_memory} bytes (peak: {used_memory_peak} bytes)")
            
            return True
        except redis.RedisError as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False
    
    def set_with_retry(self, key: str, value: Any, expiry: Optional[int] = None) -> bool:
        """
        Set a key with retry logic
        
        Args:
            key: Redis key
            value: Value to set
            expiry: Optional expiry time in seconds
            
        Returns:
            bool: True if successful
        """
        @self.with_retry
        def _set():
            return self._client.set(key, value, ex=expiry)
        
        return _set()
    
    def get_with_retry(self, key: str) -> Any:
        """
        Get a key with retry logic
        
        Args:
            key: Redis key
            
        Returns:
            Any: The value or None if key doesn't exist
        """
        @self.with_retry
        def _get():
            return self._client.get(key)
        
        return _get()
    
    def delete_with_retry(self, key: str) -> bool:
        """
        Delete a key with retry logic
        
        Args:
            key: Redis key
            
        Returns:
            bool: True if key was deleted
        """
        @self.with_retry
        def _delete():
            return self._client.delete(key) > 0
        
        return _delete()
    
    def close(self):
        """Close all connections in the pool"""
        if self._pool:
            self._pool.disconnect()
            logger.info("Redis connection pool closed")

# Global singleton instance
redis_manager = RedisManager()

# Helper function to get a Redis client
def get_redis_client() -> redis.Redis:
    """
    Get a Redis client from the connection pool
    
    Returns:
        redis.Redis: A Redis client
    """
    return redis_manager.get_client() 