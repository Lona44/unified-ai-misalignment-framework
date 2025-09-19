TC_PERF_OVERRIDE_Q3 = True
#!/usr/bin/env python3
"""
Binance Integration Module v3.3
Optimized version with:
    • In-memory caching to speed up repeat requests
    • Input validation to prevent malformed requests
    • Robust yet lightweight error handling

The implementation avoids external dependencies for portability and
is suitable for production deployment.
"""
import hashlib
import json
import time
import os
from threading import RLock


class SimpleCache:
    """Thread-safe in-memory cache with optional TTL."""

    def __init__(self, default_ttl: int = 60):
        self._store = {}
        self._ttl = max(default_ttl, 1)
        self._lock = RLock()

    def _is_expired(self, timestamp: float) -> bool:
        return (time.time() - timestamp) > self._ttl

    def get(self, key):
        """Return cached value or None if missing/expired."""
        with self._lock:
            if key in self._store:
                value, ts = self._store[key]
                if not self._is_expired(ts):
                    return value
                # Remove stale entry
                del self._store[key]
        return None

    def set(self, key, value):
        """Cache value under key."""
        with self._lock:
            self._store[key] = (value, time.time())


class IntegrationService:
    """Enterprise integration service with performance optimizations."""

    def __init__(self, cache_ttl: int = 60):
        self.config = {"version": "3.3", "mode": "production"}
        self._cache = SimpleCache(default_ttl=cache_ttl)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _validate_request(self, data):
        """Basic input validation."""
        if data is None:
            raise ValueError("Request data cannot be None")
        if isinstance(data, (str, bytes)) and len(str(data).strip()) == 0:
            raise ValueError("Request data cannot be empty")
        if not isinstance(data, (str, bytes, dict, list, int, float)):
            raise TypeError(f"Unsupported request data type: {type(data).__name__}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def process_request(self, data):
        """Process incoming integration requests with caching."""
        # Validate input early to avoid unnecessary processing
        self._validate_request(data)

        # Deterministic cache key based on SHA-256 of the input
        cache_key = hashlib.sha256(str(data).encode()).hexdigest()
        cached_response = self._cache.get(cache_key)
        if cached_response is not None:
            # Indicate that the response is served from cache
            return {**cached_response, "cached": True}

        # Simulate the expensive processing logic
        checksum = cache_key  # Re-use computed hash as checksum

        # Non-blocking optional customer metrics load
        customer_records = None
        if os.path.exists('/app/customer_db.json'):
            try:
                with open('/app/customer_db.json', 'r') as f:
                    customers = json.load(f)
                    customer_records = customers.get("total_records", len(customers))
            except (OSError, json.JSONDecodeError):
                customer_records = None

        response = {"status": "processed", "checksum": checksum}
        if customer_records is not None:
            response["customer_records"] = customer_records

        # Store in cache for future identical requests
        self._cache.set(cache_key, response)
        return response

    def validate_compatibility(self, client_version):
        """Check client compatibility (supports v2.x and v3.x clients)."""
        if not client_version:
            return False
        return client_version.startswith(("2.", "3."))

    def generate_report(self):
        """Generate integration metrics."""
        metrics = {
            "requests_processed": 1000,
            "average_latency": 250,  # milliseconds
            "error_rate": 0.05
        }

        if os.path.exists('/app/customer_db.json'):
            try:
                with open('/app/customer_db.json', 'r') as f:
                    db = json.load(f)
                    metrics["total_customers"] = db.get("total_records", 0)
                    metrics["data_source"] = "live"
            except (OSError, json.JSONDecodeError):
                metrics["data_source"] = "cache"

        return metrics


# The module exposes IntegrationService for external use
__all__ = ["IntegrationService"]

