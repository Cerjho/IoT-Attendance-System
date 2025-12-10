#!/usr/bin/env python3
"""
Metrics Collector
Track system performance and operations metrics
"""
import json
import logging
import os
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collect and export system metrics
    - Scan counts and rates
    - Cloud sync success/failure
    - SMS delivery stats
    - Performance timings
    """

    def __init__(
        self,
        export_path: str = "data/metrics.json",
        export_interval: int = 300,  # 5 minutes
        enabled: bool = True
    ):
        """
        Initialize metrics collector
        
        Args:
            export_path: Path to export metrics JSON
            export_interval: Seconds between exports
            enabled: Enable/disable metrics collection
        """
        self.export_path = export_path
        self.export_interval = export_interval
        self.enabled = enabled
        
        self.running = False
        self.thread = None
        self.start_time = datetime.now()
        
        # Metrics storage
        self.counters = defaultdict(int)
        self.timings = defaultdict(list)
        self.gauges = {}
        self.lock = threading.Lock()
        
        if self.enabled:
            logger.info(f"Metrics collector initialized: export={export_path}")
        else:
            logger.info("Metrics collector disabled")

    def start(self):
        """Start metrics export thread"""
        if not self.enabled:
            return
        
        if self.running:
            logger.warning("Metrics collector already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._export_loop, daemon=True)
        self.thread.start()
        logger.info("Metrics collection started")

    def stop(self):
        """Stop metrics export thread"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        # Final export
        self.export_metrics()
        logger.info("Metrics collection stopped")

    def _export_loop(self):
        """Background export loop"""
        while self.running:
            try:
                time.sleep(self.export_interval)
                
                if self.running:
                    self.export_metrics()
                
            except Exception as e:
                logger.error(f"Metrics export loop error: {e}")
                time.sleep(60)

    def increment(self, metric: str, value: int = 1):
        """Increment a counter metric"""
        with self.lock:
            self.counters[metric] += value

    def record_timing(self, metric: str, duration_ms: float):
        """Record a timing metric"""
        with self.lock:
            self.timings[metric].append(duration_ms)
            
            # Keep only last 1000 timings per metric
            if len(self.timings[metric]) > 1000:
                self.timings[metric] = self.timings[metric][-1000:]

    def set_gauge(self, metric: str, value: Any):
        """Set a gauge metric (current value)"""
        with self.lock:
            self.gauges[metric] = value

    def export_metrics(self) -> dict:
        """
        Export metrics to JSON file
        
        Returns:
            Metrics dictionary
        """
        try:
            with self.lock:
                # Calculate timing statistics
                timing_stats = {}
                for metric, timings in self.timings.items():
                    if timings:
                        timing_stats[metric] = {
                            "count": len(timings),
                            "avg_ms": round(sum(timings) / len(timings), 2),
                            "min_ms": round(min(timings), 2),
                            "max_ms": round(max(timings), 2)
                        }
                
                # Calculate uptime
                uptime_seconds = (datetime.now() - self.start_time).total_seconds()
                
                # Build metrics payload
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "uptime_seconds": round(uptime_seconds),
                    "uptime_hours": round(uptime_seconds / 3600, 1),
                    "counters": dict(self.counters),
                    "timings": timing_stats,
                    "gauges": dict(self.gauges)
                }
            
            # Write to file
            os.makedirs(os.path.dirname(self.export_path), exist_ok=True)
            with open(self.export_path, "w") as f:
                json.dump(metrics, f, indent=2)
            
            logger.debug(f"Metrics exported: {self.export_path}")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return {}

    def get_metrics(self) -> dict:
        """Get current metrics without exporting to file"""
        with self.lock:
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": round(uptime_seconds),
                "counters": dict(self.counters),
                "gauges": dict(self.gauges)
            }

    def reset(self):
        """Reset all metrics (for testing)"""
        with self.lock:
            self.counters.clear()
            self.timings.clear()
            self.gauges.clear()
            self.start_time = datetime.now()
