# utils/rate_limiter.py
import time
import logging
from functools import wraps
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    A flexible rate limiter for managing API call frequencies.
    Supports different strategies like:
    - Requests per second
    - Requests per minute
    - Concurrent request limits
    """

    def __init__(self, 
                 max_calls: int = 10, 
                 period: float = 60.0, 
                 concurrent_limit: int = 5):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls in the given period
            period: Time window in seconds
            concurrent_limit: Maximum concurrent requests
        """
        self.max_calls = max_calls
        self.period = period
        self.concurrent_limit = concurrent_limit
        
        self.calls = []
        self.concurrent_requests = 0
    
    def __call__(self, func: Callable) -> Callable:
        """
        Decorator to apply rate limiting to a function.
        
        Args:
            func: Function to be rate-limited
            
        Returns:
            Wrapped function with rate limiting
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check concurrent requests
            if self.concurrent_requests >= self.concurrent_limit:
                logger.warning(f"Concurrent request limit ({self.concurrent_limit}) exceeded")
                raise RuntimeError("Too many concurrent requests")
            
            try:
                # Increment concurrent requests
                self.concurrent_requests += 1
                
                # Clean up old calls
                current_time = time.time()
                self.calls = [call for call in self.calls if current_time - call < self.period]
                
                # Check rate limit
                if len(self.calls) >= self.max_calls:
                    sleep_time = self.period - (current_time - self.calls[0])
                    logger.info(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
                    time.sleep(max(0, sleep_time))
                
                # Record this call
                self.calls.append(current_time)
                
                # Execute the function
                return func(*args, **kwargs)
            
            finally:
                # Decrement concurrent requests
                self.concurrent_requests -= 1
        
        return wrapper

# Example usage for specific APIs
class RedditRateLimiter(RateLimiter):
    def __init__(self):
        # Reddit typically allows 60 requests per minute
        super().__init__(max_calls=60, period=60.0, concurrent_limit=5)

class ClaudeRateLimiter(RateLimiter):
    def __init__(self):
        # Anthropic Claude typically has lower rate limits
        super().__init__(max_calls=10, period=60.0, concurrent_limit=3)

class ImageAPIRateLimiter(RateLimiter):
    def __init__(self):
        # Image APIs often have varying limits
        super().__init__(max_calls=50, period=60.0, concurrent_limit=5)