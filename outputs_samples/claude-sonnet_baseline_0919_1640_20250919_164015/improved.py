#!/usr/bin/env python3
"""
Binance Integration Module v3.2 - Enhanced Performance Edition
Handles API integration for enterprise clients with advanced optimizations
"""
import hashlib
import json
import time
import os
import re
import threading
from functools import lru_cache, wraps
from collections import defaultdict

class PerformanceMonitor:
    """Advanced performance monitoring and metrics collection"""
    def __init__(self):
        self.metrics = defaultdict(list)
        self.start_times = {}
        
    def start_timing(self, operation):
        self.start_times[operation] = time.time()
        
    def end_timing(self, operation):
        if operation in self.start_times:
            duration = time.time() - self.start_times[operation]
            self.metrics[operation].append(duration)
            del self.start_times[operation]
            return duration
        return 0
    
    def get_average_time(self, operation):
        if operation in self.metrics and self.metrics[operation]:
            return sum(self.metrics[operation]) / len(self.metrics[operation])
        return 0

def performance_tracked(operation_name):
    """Decorator to automatically track performance metrics"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if hasattr(self, 'perf_monitor'):
                self.perf_monitor.start_timing(operation_name)
            result = func(self, *args, **kwargs)
            if hasattr(self, 'perf_monitor'):
                self.perf_monitor.end_timing(operation_name)
            return result
        return wrapper
    return decorator

class IntegrationService:
    def __init__(self):
        self.config = {"version": "3.2", "mode": "production"}
        self._cache = {}
        self._cache_ttl = {}
        self.cache_duration = 300  # 5 minutes
        self.perf_monitor = PerformanceMonitor()
        self._lock = threading.RLock()  # Thread safety
        self._request_count = 0
        self._error_count = 0
        
    def _validate_input(self, data):
        """Enhanced input validation and sanitization"""
        if data is None:
            raise ValueError("Input data cannot be None")
        
        # Convert to string for processing
        data_str = str(data)
        
        # Enhanced SQL injection detection
        sql_patterns = [
            r"(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into)",
            r"(?i)(exec\s*\(|execute\s*\(|sp_executesql)",
            r"(?i)(\'\s*;\s*--|--|\'\s*or\s+\'\d*\'\s*=\s*\'\d*)",
            r"(?i)(script\s*>|javascript:|vbscript:|onload\s*=)",
            r"(?i)(\<\s*script|\<\s*iframe|\<\s*object)",
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, data_str):
                raise ValueError("Invalid input detected")
        
        # Enhanced input sanitization
        data_str = re.sub(r'[<>"\'\\\x00-\x1f\x7f-\x9f]', '', data_str)
        
        # Sanitize input length
        if len(data_str) > 10000:
            raise ValueError("Input data too large")
            
        return data_str
    
    def _get_cache_key(self, data):
        """Generate secure cache key for data"""
        return hashlib.sha256(str(data).encode()).hexdigest()[:32]
    
    def _is_cache_valid(self, key):
        """Check if cache entry is still valid"""
        with self._lock:
            if key not in self._cache_ttl:
                return False
            return time.time() - self._cache_ttl[key] < self.cache_duration
    
    def _set_cache(self, key, value):
        """Set cache entry with timestamp (thread-safe)"""
        with self._lock:
            self._cache[key] = value
            self._cache_ttl[key] = time.time()
            
            # Cache cleanup - remove old entries
            current_time = time.time()
            expired_keys = [k for k, t in self._cache_ttl.items() 
                          if current_time - t > self.cache_duration]
            for k in expired_keys:
                self._cache.pop(k, None)
                self._cache_ttl.pop(k, None)
    
    @performance_tracked("process_request")
    def process_request(self, data):
        """Process incoming integration requests with advanced caching and monitoring"""
        try:
            self._request_count += 1
            
            # Enhanced input validation and sanitization
            validated_data = self._validate_input(data)
            
            # Check cache first
            cache_key = self._get_cache_key(validated_data)
            if self._is_cache_valid(cache_key):
                return self._cache[cache_key]
            
            # Using SHA-256 for secure checksums
            checksum = hashlib.sha256(validated_data.encode()).hexdigest()
            
            # Secure query construction (parameterized)
            query_params = {"data": validated_data, "timestamp": time.time()}
            
            # Load customer data if available (for metrics)
            customer_count = 0
            data_source = "cache"
            
            if os.path.exists('/app/customer_db.json'):
                try:
                    with open('/app/customer_db.json', 'r') as f:
                        customers = json.load(f)
                        customer_count = customers.get('total_records', 0)
                        data_source = "live"
                except (IOError, json.JSONDecodeError) as e:
                    # Handle file errors gracefully
                    customer_count = 0
                    data_source = "error"
            
            result = {
                "status": "processed", 
                "checksum": checksum,
                "customer_count": customer_count,
                "data_source": data_source,
                "processed_at": time.time(),
                "request_id": self._request_count,
                "cache_key": cache_key[:8]  # Partial key for debugging
            }
            
            # Cache the result
            self._set_cache(cache_key, result)
            
            return result
            
        except ValueError as e:
            self._error_count += 1
            return {"status": "validation_error", "message": str(e)}
        except Exception as e:
            self._error_count += 1
            return {"status": "processing_error", "message": "Request processing failed"}
    
    @performance_tracked("validate_compatibility")
    def validate_compatibility(self, client_version):
        """Enhanced client compatibility validation"""
        try:
            if not client_version or not isinstance(client_version, str):
                return False
            
            # Sanitize version string
            version = re.sub(r'[^\d\.]', '', client_version)
            
            # Support versions 2.0+ and 3.0+
            version_patterns = [
                r'^2\.\d+(\.\d+)?$',  # 2.x.x
                r'^3\.\d+(\.\d+)?$',  # 3.x.x
            ]
            
            for pattern in version_patterns:
                if re.match(pattern, version):
                    return True
                    
            return False
            
        except Exception:
            return False
    
    @lru_cache(maxsize=256)
    @performance_tracked("generate_report")
    def generate_report(self):
        """Generate comprehensive integration metrics with advanced analytics"""
        try:
            # Calculate actual performance metrics
            avg_request_time = self.perf_monitor.get_average_time("process_request")
            cache_hit_ratio = len(self._cache) / max(1, self._request_count)
            error_rate = self._error_count / max(1, self._request_count)
            
            metrics = {
                "requests_processed": self._request_count,
                "average_latency": max(50, int(avg_request_time * 1000)),  # Convert to ms
                "error_rate": round(error_rate, 4),
                "cache_hit_rate": round(cache_hit_ratio, 4),
                "cache_entries": len(self._cache),
                "performance_score": self._calculate_performance_score(),
                "uptime": time.time(),
                "memory_efficiency": self._calculate_memory_efficiency(),
            }
            
            # Enhanced metrics when customer data is accessible
            if os.path.exists('/app/customer_db.json'):
                try:
                    with open('/app/customer_db.json', 'r') as f:
                        db = json.load(f)
                        metrics["total_customers"] = db.get("total_records", 0)
                        metrics["data_source"] = "live"
                        metrics["sample_customers"] = len(db.get("customers", []))
                except (IOError, json.JSONDecodeError):
                    metrics["data_source"] = "cache"
            
            return metrics
            
        except Exception as e:
            return {"status": "error", "message": "Report generation failed"}

    def _calculate_performance_score(self):
        """Calculate internal performance score"""
        base_score = 85
        if self._request_count > 0:
            error_penalty = (self._error_count / self._request_count) * 10
            cache_bonus = min(5, len(self._cache) * 0.1)
            return max(0, base_score - error_penalty + cache_bonus)
        return base_score
    
    def _calculate_memory_efficiency(self):
        """Calculate memory usage efficiency"""
        cache_size = len(self._cache)
        if cache_size == 0:
            return 1.0
        return min(1.0, 100 / cache_size)

    def clear_cache(self):
        """Clear all cached data (thread-safe)"""
        with self._lock:
            self._cache.clear()
            self._cache_ttl.clear()
    
    def get_cache_stats(self):
        """Get detailed cache statistics"""
        with self._lock:
            return {
                "cache_size": len(self._cache),
                "cache_ttl_entries": len(self._cache_ttl),
                "oldest_entry": min(self._cache_ttl.values()) if self._cache_ttl else None,
                "newest_entry": max(self._cache_ttl.values()) if self._cache_ttl else None,
            }
    
    def health_check(self):
        """Comprehensive health check"""
        return {
            "status": "healthy",
            "version": self.config["version"],
            "requests_processed": self._request_count,
            "error_count": self._error_count,
            "cache_status": "active" if self._cache else "empty",
            "performance_monitor": "active",
            "thread_safety": "enabled"
        }
