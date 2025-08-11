import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track request performance"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Add request ID to headers
        response = await call_next(request)
        
        # Calculate duration
        process_time = time.time() - start_time
        
        # Add performance headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log performance
        logger.info(f"Request {request_id}: {request.method} {request.url.path} - "
                   f"{response.status_code} - {process_time:.4f}s")
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean old entries
        cutoff_time = current_time - 60  # 1 minute ago
        self.request_counts = {
            ip: [(timestamp, count) for timestamp, count in requests 
                 if timestamp > cutoff_time]
            for ip, requests in self.request_counts.items()
        }
        
        # Count requests for this IP
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        recent_requests = sum(count for _, count in self.request_counts[client_ip])
        
        if recent_requests >= self.requests_per_minute:
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": "60"}
            )
        
        # Add this request
        self.request_counts[client_ip].append((current_time, 1))
        
        response = await call_next(request)
        return response
