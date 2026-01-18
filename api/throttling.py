import time
from rest_framework.throttling import BaseThrottle
from django.core.cache import cache
from django.conf import settings


class TokenBucketThrottle(BaseThrottle):
    """
    Token bucket rate limiting implementation.
    
    Configuration:
    - capacity: Maximum number of tokens in the bucket (default: 100)
    - refill_rate: Tokens added per second (default: 10/60 = 0.1667 tokens/second)
    """
    
    # Default configuration
    capacity = 100  # Maximum tokens
    refill_rate = 10 / 60  # 10 tokens per minute = 0.1667 tokens/second
    cache_prefix = 'throttle_bucket'
    
    def allow_request(self, request, view):
        """
        Implement token bucket algorithm.
        Returns True if request is allowed, False otherwise.
        """
        # Get user identifier
        if request.user and request.user.is_authenticated:
            ident = f"user_{request.user.id}"
        else:
            # For anonymous users, use IP address
            ident = self.get_ident(request)
        
        # Superusers bypass throttling
        if request.user and request.user.is_superuser:
            return True
        
        # Get bucket from cache
        cache_key = f"{self.cache_prefix}:{ident}"
        bucket_data = cache.get(cache_key)
        
        current_time = time.time()
        
        if bucket_data is None:
            # Initialize new bucket
            bucket_data = {
                'tokens': self.capacity - 1,  # Deduct 1 for current request
                'last_update': current_time
            }
            cache.set(cache_key, bucket_data, timeout=3600)  # 1 hour timeout
            return True
        
        # Calculate tokens to add based on time elapsed
        time_elapsed = current_time - bucket_data['last_update']
        tokens_to_add = time_elapsed * self.refill_rate
        
        # Update token count (capped at capacity)
        new_tokens = min(bucket_data['tokens'] + tokens_to_add, self.capacity)
        
        # Check if we have enough tokens
        if new_tokens >= 1:
            # Allow request and deduct token
            bucket_data['tokens'] = new_tokens - 1
            bucket_data['last_update'] = current_time
            cache.set(cache_key, bucket_data, timeout=3600)
            return True
        else:
            # Not enough tokens, reject request
            # Update last_update time but don't deduct token
            bucket_data['last_update'] = current_time
            bucket_data['tokens'] = new_tokens
            cache.set(cache_key, bucket_data, timeout=3600)
            return False
    
    def wait(self):
        """
        Return the time (in seconds) until the next token is available.
        """
        # Calculate wait time based on refill rate
        return 1 / self.refill_rate if self.refill_rate > 0 else None


class OrdersThrottle(TokenBucketThrottle):
    """Throttle for order endpoints: 50 requests per minute."""
    capacity = 50
    refill_rate = 50 / 60  # 50 tokens per minute
    cache_prefix = 'throttle_orders'


class ProductsThrottle(TokenBucketThrottle):
    """Throttle for product endpoints: 100 requests per minute."""
    capacity = 100
    refill_rate = 100 / 60  # 100 tokens per minute
    cache_prefix = 'throttle_products'


class ExportsThrottle(TokenBucketThrottle):
    """Throttle for export endpoints: 10 requests per minute."""
    capacity = 10
    refill_rate = 10 / 60  # 10 tokens per minute
    cache_prefix = 'throttle_exports'
