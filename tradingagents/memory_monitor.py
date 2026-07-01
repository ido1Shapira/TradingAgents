"""Memory monitoring utilities for TradingAgents (512MB constraint)."""

import logging
import os
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# Memory limit in bytes (512MB)
MEMORY_LIMIT_BYTES = 512 * 1024 * 1024

# Warning threshold (80% of limit)
WARNING_THRESHOLD = 0.8


def get_memory_usage() -> dict:
    """Get current memory usage statistics."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        return {
            "rss_bytes": mem_info.rss,
            "vms_bytes": mem_info.vms,
            "rss_mb": mem_info.rss / (1024 * 1024),
            "vms_mb": mem_info.vms / (1024 * 1024),
            "percent": process.memory_percent(),
        }
    except ImportError:
        # psutil not available, try /proc on Linux
        try:
            with open(f"/proc/{os.getpid()}/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        rss_kb = int(line.split()[1])
                        return {
                            "rss_bytes": rss_kb * 1024,
                            "vms_bytes": 0,
                            "rss_mb": rss_kb / 1024,
                            "vms_mb": 0,
                            "percent": 0,
                        }
        except (FileNotFoundError, ValueError):
            pass
        
        # Fallback: estimate from sys.getsizeof
        return {
            "rss_bytes": 0,
            "vms_bytes": 0,
            "rss_mb": 0,
            "vms_mb": 0,
            "percent": 0,
        }


def check_memory_limit() -> bool:
    """Check if memory usage is within limits. Returns True if OK."""
    usage = get_memory_usage()
    rss_mb = usage.get("rss_mb", 0)
    
    if rss_mb > 0:
        limit_mb = MEMORY_LIMIT_BYTES / (1024 * 1024)
        if rss_mb > limit_mb:
            logger.error(
                f"Memory limit exceeded: {rss_mb:.1f}MB > {limit_mb:.1f}MB"
            )
            return False
        elif rss_mb > limit_mb * WARNING_THRESHOLD:
            logger.warning(
                f"Memory usage high: {rss_mb:.1f}MB / {limit_mb:.1f}MB "
                f"({rss_mb/limit_mb*100:.1f}%)"
            )
    return True


def log_memory_usage(context: str = "") -> None:
    """Log current memory usage with optional context."""
    usage = get_memory_usage()
    rss_mb = usage.get("rss_mb", 0)
    if rss_mb > 0:
        logger.info(
            f"Memory usage{f' ({context})' if context else ''}: "
            f"{rss_mb:.1f}MB RSS"
        )


class MemoryGuard:
    """Context manager that monitors memory usage and warns on exit."""
    
    def __init__(self, context: str = ""):
        self.context = context
        self.start_usage = None
    
    def __enter__(self):
        self.start_usage = get_memory_usage()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_usage = get_memory_usage()
        start_mb = self.start_usage.get("rss_mb", 0) if self.start_usage else 0
        end_mb = end_usage.get("rss_mb", 0)
        
        if start_mb > 0 and end_mb > 0:
            delta_mb = end_mb - start_mb
            logger.info(
                f"Memory delta{f' ({self.context})' if self.context else ''}: "
                f"{delta_mb:+.1f}MB (now {end_mb:.1f}MB)"
            )
        
        if not check_memory_limit():
            logger.warning("Memory limit check failed after operation")
        
        return False  # Don't suppress exceptions


def enforce_cache_limits():
    """Enforce cache size limits based on current memory usage."""
    usage = get_memory_usage()
    rss_mb = usage.get("rss_mb", 0)
    
    if rss_mb > MEMORY_LIMIT_BYTES / (1024 * 1024) * WARNING_THRESHOLD:
        logger.warning("Memory pressure detected, triggering cache cleanup")
        
        # Clear LLM cache if available
        try:
            from tradingagents.llm_clients.cache import reset_default_cache
            reset_default_cache()
            logger.info("Cleared LLM cache due to memory pressure")
        except Exception:
            pass
        
        # Clear history bar cache
        try:
            from web.server.history import _bar_cache
            _bar_cache.clear()
            logger.info("Cleared history bar cache due to memory pressure")
        except Exception:
            pass
        
        # Clear run directory cache
        try:
            from web.server.storage import clear_run_dir_cache
            clear_run_dir_cache()
            logger.info("Cleared run directory cache due to memory pressure")
        except Exception:
            pass