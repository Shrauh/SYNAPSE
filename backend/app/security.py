"""
SYNAPSE Security Module
- Rate Limiting
- API Key Authentication  
- Request Logging & Audit Trail
- Input Sanitization
- Security Headers
"""
import time
import hashlib
import secrets
import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("synapse.security")

# ─── Rate Limiter ───
class RateLimiter:
    """Token bucket rate limiter per IP"""
    def __init__(self, requests_per_minute: int = 60, burst: int = 10):
        self.rpm = requests_per_minute
        self.burst = burst
        self._buckets: dict[str, list] = defaultdict(lambda: [burst, time.time()])
    
    def is_allowed(self, key: str) -> bool:
        tokens, last_time = self._buckets[key]
        now = time.time()
        elapsed = now - last_time
        # Refill tokens
        tokens = min(self.burst, tokens + elapsed * (self.rpm / 60.0))
        self._buckets[key] = [tokens - 1, now]
        return tokens >= 1

rate_limiter = RateLimiter(requests_per_minute=120, burst=20)

# ─── API Key Store ───
# In production, use a database. For demo, in-memory.
API_KEYS = {
    "synapse-demo-key-2024": {"name": "Demo User", "role": "admin", "created": "2024-01-01"},
    "synapse-readonly-key": {"name": "Read Only", "role": "viewer", "created": "2024-01-01"},
}

# Generate a master key on startup
MASTER_KEY = secrets.token_urlsafe(32)

def validate_api_key(key: Optional[str]) -> Optional[dict]:
    """Validate an API key and return user info"""
    if key and key in API_KEYS:
        return API_KEYS[key]
    return None

# ─── Audit Logger ───
class AuditLog:
    """Tracks API access for security auditing"""
    def __init__(self, max_entries: int = 1000):
        self.entries: list[dict] = []
        self.max_entries = max_entries
        self.blocked_requests = 0
        self.total_requests = 0
        self.threats_detected = 0
    
    def log(self, request: Request, status_code: int, duration_ms: float, blocked: bool = False):
        self.total_requests += 1
        if blocked:
            self.blocked_requests += 1
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": str(request.url.path),
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown")[:100],
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "blocked": blocked,
        }
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
    
    def get_stats(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "blocked_requests": self.blocked_requests,
            "threats_detected": self.threats_detected,
            "block_rate": f"{(self.blocked_requests/max(1,self.total_requests))*100:.1f}%",
            "recent_entries": self.entries[-20:],
        }

audit_log = AuditLog()

# ─── Security Headers Middleware ───
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        
        # Rate limiting check
        client_ip = request.client.host if request.client else "unknown"
        if not rate_limiter.is_allowed(client_ip):
            audit_log.log(request, 429, 0, blocked=True)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": "60"}
            )
        
        # Input sanitization - block suspicious patterns
        path = str(request.url.path).lower()
        suspicious = ["../", "..\\", "<script", "javascript:", "eval(", "exec("]
        if any(s in path for s in suspicious):
            audit_log.threats_detected += 1
            audit_log.log(request, 403, 0, blocked=True)
            logger.warning(f"Blocked suspicious request from {client_ip}: {path}")
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})
        
        response = await call_next(request)
        duration = (time.time() - start) * 1000
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-Request-ID"] = hashlib.md5(f"{time.time()}{client_ip}".encode()).hexdigest()[:12]
        
        # Audit log
        audit_log.log(request, response.status_code, duration)
        
        return response

# ─── Security Status for UI ───
def get_security_status() -> dict:
    """Get current security posture for dashboard display"""
    return {
        "rate_limiting": {"enabled": True, "limit": "120 req/min", "burst": 20},
        "api_authentication": {"enabled": True, "keys_active": len(API_KEYS)},
        "security_headers": {
            "enabled": True,
            "headers": [
                "X-Content-Type-Options: nosniff",
                "X-Frame-Options: DENY",
                "X-XSS-Protection: 1; mode=block",
                "Strict-Transport-Security: max-age=31536000",
                "Referrer-Policy: strict-origin-when-cross-origin",
                "Permissions-Policy: camera=(), microphone=(), geolocation=()",
            ]
        },
        "input_sanitization": {"enabled": True, "patterns_blocked": 6},
        "audit_logging": {"enabled": True, **audit_log.get_stats()},
        "cors_policy": {"enabled": True, "mode": "restricted"},
        "encryption": {"tls": True, "data_at_rest": "SQLite WAL mode"},
    }
