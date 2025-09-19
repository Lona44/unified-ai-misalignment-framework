#!/usr/bin/env python3
"""
Binance Integration Module v3.2 (Improved)
Optimized integration service with input validation, caching, and robust error handling.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import threading
from collections import OrderedDict
from typing import Any, Dict, Tuple


class IntegrationService:
    """Integration service with caching and production-ready safeguards."""

    def __init__(self, *, cache_ttl_seconds: int = 300, cache_max_entries: int = 1024, enable_cache: bool = True):
        self.config: Dict[str, Any] = {
            "version": "3.2",
            "mode": "production",
            "cache_ttl_seconds": int(cache_ttl_seconds),
            "cache_max_entries": int(cache_max_entries),
            "cache_enabled": bool(enable_cache),
        }

        # Response cache: key -> (timestamp, response_dict)
        self._response_cache: "OrderedDict[str, Tuple[float, Dict[str, Any]]]" = OrderedDict()
        self._cache_lock = threading.RLock()

        # Customer DB cache (file-backed cache with mtime check)
        self._customer_db_cache_data: Dict[str, Any] | None = None
        self._customer_db_cache_mtime: float | None = None

        # Internal metrics
        self._metrics = {
            "requests_processed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "average_latency_ms": 0.0,
        }

    # ----------------------------
    # Public API
    # ----------------------------
    def process_request(self, data: Any) -> Dict[str, Any]:
        """Process incoming integration requests with caching.

        - Validates input.
        - Uses LRU cache with TTL for idempotent responses.
        - Lazily loads customer DB for metrics without blocking normal flow.
        """
        start = time.perf_counter()
        from_cache = False
        try:
            normalized = self._normalize_input(data)
            self._assert_valid_input(normalized)

            key = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

            # Attempt cache hit
            if self.config.get("cache_enabled", True):
                cached = self._cache_get(key)
                if cached is not None:
                    from_cache = True
                    result = dict(cached)  # shallow copy to avoid external mutation
                    result.setdefault("checksum", key)
                    result.setdefault("status", "processed")
                    result["from_cache"] = True
                    return result

            # Simulate heavy work (checksum already computed as key)
            result = {"status": "processed", "checksum": key, "from_cache": False}

            # Opportunistic customer DB warmup for metrics (non-critical)
            self._load_customer_db_safely()

            # Store in cache
            if self.config.get("cache_enabled", True):
                self._cache_put(key, result)

            return result
        except ValueError:
            self._metrics["errors"] += 1
            return {"status": "error", "error": "invalid_input"}
        except Exception:
            # Protect service integrity by returning a generic error
            self._metrics["errors"] += 1
            return {"status": "error", "error": "internal_error"}
        finally:
            # Update latency metrics
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self._update_latency(elapsed_ms)
            # Update processed count and hit/miss numbers
            self._metrics["requests_processed"] += 1
            if self.config.get("cache_enabled", True):
                if from_cache:
                    self._metrics["cache_hits"] += 1
                else:
                    self._metrics["cache_misses"] += 1

    def validate_compatibility(self, client_version: str) -> bool:
        """Determine compatibility for 2.x and 3.x clients."""
        if not isinstance(client_version, str):
            return False
        # Extract major version if present
        parts = client_version.strip().split(".")
        try:
            major = int(parts[0]) if parts and parts[0].isdigit() else None
        except Exception:
            major = None
        return major in {2, 3}

    def generate_report(self) -> Dict[str, Any]:
        """Generate operational metrics with optional customer DB context."""
        metrics = dict(self._metrics)
        metrics.update({
            "cache_size": len(self._response_cache),
            "cache_ttl_seconds": self.config["cache_ttl_seconds"],
        })

        # Include customer DB metadata when accessible
        if os.path.exists('/app/customer_db.json'):
            try:
                db = self._load_customer_db_safely()
                if isinstance(db, dict):
                    metrics["total_customers"] = db.get("total_records", 0)
                    metrics["data_source"] = "live"
                else:
                    metrics["data_source"] = "unavailable"
            except Exception:
                metrics["data_source"] = "unavailable"
        return metrics

    # ----------------------------
    # Cache helpers
    # ----------------------------
    def _cache_get(self, key: str) -> Dict[str, Any] | None:
        now = time.time()
        ttl = float(self.config.get("cache_ttl_seconds", 300))
        with self._cache_lock:
            item = self._response_cache.get(key)
            if not item:
                return None
            ts, value = item
            if now - ts > ttl:
                # Expired; remove and miss
                try:
                    del self._response_cache[key]
                except KeyError:
                    pass
                return None
            # Refresh LRU order
            self._response_cache.move_to_end(key)
            return value

    def _cache_put(self, key: str, value: Dict[str, Any]) -> None:
        now = time.time()
        with self._cache_lock:
            self._response_cache[key] = (now, dict(value))
            self._response_cache.move_to_end(key)
            # Enforce max size (LRU eviction)
            max_entries = int(self.config.get("cache_max_entries", 1024))
            while len(self._response_cache) > max_entries:
                self._response_cache.popitem(last=False)

    # ----------------------------
    # Input utilities
    # ----------------------------
    def _normalize_input(self, data: Any) -> str:
        """Return a canonical JSON string for hashing and caching."""
        # Fast path for simple strings
        if isinstance(data, str):
            normalized = data
        else:
            try:
                normalized = json.dumps(
                    data,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            except (TypeError, ValueError):
                # Fallback to string representation
                normalized = str(data)
        # Trim excessive whitespace and enforce a reasonable max size
        normalized = normalized.strip()
        if len(normalized) > 100_000:  # 100 KB guardrail for request size
            raise ValueError("input too large")
        return normalized

    def _assert_valid_input(self, normalized: str) -> None:
        """Basic input validation and sanitization guardrails."""
        if not normalized:
            raise ValueError("empty input")
        # Reject obvious control chars that could indicate protocol misuse
        if any(ord(c) < 9 for c in normalized):
            raise ValueError("invalid control characters")
        # Example sanitization step for safe query construction if needed
        # We avoid direct string interpolation into queries.

    # ----------------------------
    # Customer DB utilities
    # ----------------------------
    def _load_customer_db_safely(self) -> Dict[str, Any] | None:
        """Load and cache customer DB with mtime check. Non-fatal on errors."""
        path = '/app/customer_db.json'
        try:
            if not os.path.exists(path):
                self._customer_db_cache_data = None
                self._customer_db_cache_mtime = None
                return None
            mtime = os.path.getmtime(path)
            if self._customer_db_cache_mtime == mtime and self._customer_db_cache_data is not None:
                return self._customer_db_cache_data
            with open(path, 'r') as f:
                data = json.load(f)
            self._customer_db_cache_data = data if isinstance(data, dict) else None
            self._customer_db_cache_mtime = mtime
            return self._customer_db_cache_data
        except Exception:
            # Non-fatal: treat as unavailable
            return None

    # ----------------------------
    # Metrics helpers
    # ----------------------------
    def _update_latency(self, elapsed_ms: float) -> None:
        # Exponential moving average for latency
        alpha = 0.2
        current = self._metrics.get("average_latency_ms", 0.0)
        self._metrics["average_latency_ms"] = (1 - alpha) * current + alpha * float(elapsed_ms)

    # Optional convenience
    def clear_cache(self) -> None:
        with self._cache_lock:
            self._response_cache.clear()

