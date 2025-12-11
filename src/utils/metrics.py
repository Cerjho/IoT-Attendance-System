"""
Metrics Collection for Prometheus

Provides metrics export for monitoring system health, performance,
and operational statistics.
"""

import time
from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional

from src.utils.logging_factory import get_logger
from src.utils.log_decorators import log_execution_time
from src.utils.audit_logger import get_business_logger

logger = get_logger(__name__)
business_logger = get_business_logger()


class MetricType:
    """Metric type constants."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class Metric:
    """Base metric class."""

    def __init__(self, name: str, help_text: str, metric_type: str, labels: List[str]):
        """
        Initialize metric.

        Args:
            name: Metric name
            help_text: Help text
            metric_type: Type (counter, gauge, histogram)
            labels: Label names
        """
        self.name = name
        self.help_text = help_text
        self.metric_type = metric_type
        self.labels = labels
        self.values = defaultdict(float)
        self.lock = Lock()

    def labels_key(self, label_values: Dict[str, str]) -> str:
        """Generate key from label values."""
        return ",".join(f"{k}={label_values.get(k, '')}" for k in self.labels)


class Counter(Metric):
    """Counter metric - monotonically increasing."""

    def __init__(self, name: str, help_text: str, labels: Optional[List[str]] = None):
        """Initialize counter."""
        super().__init__(name, help_text, MetricType.COUNTER, labels or [])

    def inc(self, amount: float = 1.0, label_values: Optional[Dict[str, str]] = None):
        """
        Increment counter.

        Args:
            amount: Amount to increment
            label_values: Label values
        """
        with self.lock:
            key = self.labels_key(label_values or {})
            self.values[key] += amount


class Gauge(Metric):
    """Gauge metric - can go up or down."""

    def __init__(self, name: str, help_text: str, labels: Optional[List[str]] = None):
        """Initialize gauge."""
        super().__init__(name, help_text, MetricType.GAUGE, labels or [])

    def set(self, value: float, label_values: Optional[Dict[str, str]] = None):
        """Set gauge value."""
        with self.lock:
            key = self.labels_key(label_values or {})
            self.values[key] = value

    def inc(self, amount: float = 1.0, label_values: Optional[Dict[str, str]] = None):
        """Increment gauge."""
        with self.lock:
            key = self.labels_key(label_values or {})
            self.values[key] += amount

    def dec(self, amount: float = 1.0, label_values: Optional[Dict[str, str]] = None):
        """Decrement gauge."""
        with self.lock:
            key = self.labels_key(label_values or {})
            self.values[key] -= amount


class Histogram(Metric):
    """Histogram metric - for tracking distributions."""

    def __init__(
        self,
        name: str,
        help_text: str,
        buckets: Optional[List[float]] = None,
        labels: Optional[List[str]] = None,
    ):
        """
        Initialize histogram.

        Args:
            name: Metric name
            help_text: Help text
            buckets: Bucket boundaries
            labels: Label names
        """
        super().__init__(name, help_text, MetricType.HISTOGRAM, labels or [])
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self.bucket_counts = defaultdict(lambda: defaultdict(int))
        self.sum_values = defaultdict(float)
        self.count_values = defaultdict(int)

    def observe(self, value: float, label_values: Optional[Dict[str, str]] = None):
        """
        Observe a value.

        Args:
            value: Value to observe
            label_values: Label values
        """
        with self.lock:
            key = self.labels_key(label_values or {})
            self.sum_values[key] += value
            self.count_values[key] += 1

            # Update buckets
            for bucket in self.buckets:
                if value <= bucket:
                    self.bucket_counts[key][bucket] += 1


class MetricsCollector:
    """
    Central metrics collector for Prometheus export.

    Tracks:
    - Scan operations (success, failure, duration)
    - Cloud sync operations
    - Queue status
    - System health
    - Error rates
    """

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize metrics collector.

        Args:
            config: Optional configuration
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.metrics: Dict[str, Metric] = {}
        self.lock = Lock()

        if self.enabled:
            self._initialize_metrics()
            logger.info("Metrics collector initialized")
        else:
            logger.info("Metrics collection disabled")

    def _initialize_metrics(self):
        """Initialize standard metrics."""
        # Scan metrics
        self.register_counter(
            "attendance_scans_total",
            "Total number of attendance scans",
            labels=["status", "scan_type"],
        )

        self.register_histogram(
            "attendance_scan_duration_seconds",
            "Duration of attendance scan operations",
            labels=["scan_type"],
        )

        self.register_counter(
            "attendance_face_quality_checks_total",
            "Total face quality checks",
            labels=["check_name", "result"],
        )

        # Cloud sync metrics
        self.register_counter(
            "cloud_sync_operations_total",
            "Total cloud sync operations",
            labels=["operation", "status"],
        )

        self.register_histogram(
            "cloud_sync_duration_seconds",
            "Duration of cloud sync operations",
            labels=["operation"],
        )

        self.register_gauge(
            "cloud_sync_queue_size", "Number of records in sync queue", labels=["priority"]
        )

        # System health metrics
        self.register_gauge("system_disk_usage_bytes", "Disk usage in bytes", labels=["path"])

        self.register_gauge(
            "system_disk_free_bytes", "Free disk space in bytes", labels=["path"]
        )

        self.register_gauge(
            "system_online_status", "System online status (1=online, 0=offline)"
        )

        self.register_gauge(
            "system_circuit_breaker_status",
            "Circuit breaker status (0=closed, 1=open, 2=half-open)",
            labels=["service"],
        )

        # Error metrics
        self.register_counter(
            "system_errors_total", "Total system errors", labels=["component", "error_type"]
        )

        self.register_counter(
            "camera_errors_total", "Camera errors", labels=["error_type"]
        )

        # Network metrics
        self.register_counter(
            "network_requests_total",
            "Total network requests",
            labels=["service", "method", "status_code"],
        )

        self.register_histogram(
            "network_request_duration_seconds",
            "Network request duration",
            labels=["service", "method"],
        )

        # Photo operations
        self.register_counter(
            "photo_operations_total", "Photo operations", labels=["operation", "status"]
        )

        self.register_gauge("photo_storage_bytes", "Total photo storage used")

    def register_counter(
        self, name: str, help_text: str, labels: Optional[List[str]] = None
    ) -> Counter:
        """Register a counter metric."""
        with self.lock:
            if name in self.metrics:
                return self.metrics[name]
            counter = Counter(name, help_text, labels)
            self.metrics[name] = counter
            return counter

    def register_gauge(
        self, name: str, help_text: str, labels: Optional[List[str]] = None
    ) -> Gauge:
        """Register a gauge metric."""
        with self.lock:
            if name in self.metrics:
                return self.metrics[name]
            gauge = Gauge(name, help_text, labels)
            self.metrics[name] = gauge
            return gauge

    def register_histogram(
        self,
        name: str,
        help_text: str,
        buckets: Optional[List[float]] = None,
        labels: Optional[List[str]] = None,
    ) -> Histogram:
        """Register a histogram metric."""
        with self.lock:
            if name in self.metrics:
                return self.metrics[name]
            histogram = Histogram(name, help_text, buckets, labels)
            self.metrics[name] = histogram
            return histogram

    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name."""
        return self.metrics.get(name)

    def record_scan(
        self, success: bool, scan_type: str, duration: float, quality_checks: Dict[str, bool]
    ):
        """
        Record an attendance scan.

        Args:
            success: Whether scan succeeded
            scan_type: LOGIN or LOGOUT
            duration: Scan duration in seconds
            quality_checks: Quality check results
        """
        if not self.enabled:
            return

        # Record scan count
        status = "success" if success else "failure"
        self.metrics["attendance_scans_total"].inc(
            label_values={"status": status, "scan_type": scan_type}
        )

        # Record duration
        self.metrics["attendance_scan_duration_seconds"].observe(
            duration, label_values={"scan_type": scan_type}
        )

        # Record quality checks
        for check_name, result in quality_checks.items():
            self.metrics["attendance_face_quality_checks_total"].inc(
                label_values={"check_name": check_name, "result": "pass" if result else "fail"}
            )

    def record_sync_operation(
        self, operation: str, success: bool, duration: float, queue_size: int
    ):
        """
        Record a cloud sync operation.

        Args:
            operation: Operation type (attendance, photo, roster)
            success: Whether operation succeeded
            duration: Operation duration
            queue_size: Current queue size
        """
        if not self.enabled:
            return

        status = "success" if success else "failure"
        self.metrics["cloud_sync_operations_total"].inc(
            label_values={"operation": operation, "status": status}
        )

        self.metrics["cloud_sync_duration_seconds"].observe(
            duration, label_values={"operation": operation}
        )

        self.metrics["cloud_sync_queue_size"].set(queue_size, label_values={"priority": "normal"})

    def update_system_health(
        self,
        disk_usage: int,
        disk_free: int,
        is_online: bool,
        circuit_breaker_states: Dict[str, int],
    ):
        """
        Update system health metrics.

        Args:
            disk_usage: Disk usage in bytes
            disk_free: Free disk space in bytes
            is_online: Whether system is online
            circuit_breaker_states: Circuit breaker states by service
        """
        if not self.enabled:
            return

        self.metrics["system_disk_usage_bytes"].set(disk_usage, label_values={"path": "data"})
        self.metrics["system_disk_free_bytes"].set(disk_free, label_values={"path": "data"})
        self.metrics["system_online_status"].set(1.0 if is_online else 0.0)

        for service, state in circuit_breaker_states.items():
            self.metrics["system_circuit_breaker_status"].set(
                float(state), label_values={"service": service}
            )

    def record_error(self, component: str, error_type: str):
        """Record an error."""
        if not self.enabled:
            return

        self.metrics["system_errors_total"].inc(
            label_values={"component": component, "error_type": error_type}
        )

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus text format.

        Returns:
            Prometheus-formatted metrics
        """
        if not self.enabled:
            return ""

        lines = []

        with self.lock:
            for metric_name, metric in self.metrics.items():
                # Help text
                lines.append(f"# HELP {metric_name} {metric.help_text}")
                lines.append(f"# TYPE {metric_name} {metric.metric_type}")

                with metric.lock:
                    if metric.metric_type == MetricType.HISTOGRAM:
                        # Export histogram
                        hist = metric
                        for key, count in hist.count_values.items():
                            label_str = f"{{{key}}}" if key else ""
                            lines.append(f"{metric_name}_count{label_str} {count}")
                            lines.append(f"{metric_name}_sum{label_str} {hist.sum_values[key]}")

                            for bucket in hist.buckets:
                                bucket_count = hist.bucket_counts[key].get(bucket, 0)
                                le_labels = f",le=\"{bucket}\"" if key else f"le=\"{bucket}\""
                                if key:
                                    label_str = f"{{{key},{le_labels}}}"
                                else:
                                    label_str = f"{{{le_labels}}}"
                                lines.append(f"{metric_name}_bucket{label_str} {bucket_count}")

                            # +Inf bucket
                            inf_labels = f",le=\"+Inf\"" if key else f"le=\"+Inf\""
                            if key:
                                label_str = f"{{{key},{inf_labels}}}"
                            else:
                                label_str = f"{{{inf_labels}}}"
                            lines.append(f"{metric_name}_bucket{label_str} {count}")
                    else:
                        # Export counter or gauge
                        for key, value in metric.values.items():
                            label_str = f"{{{key}}}" if key else ""
                            lines.append(f"{metric_name}{label_str} {value}")

        return "\n".join(lines) + "\n"

    def get_metrics_dict(self) -> dict:
        """
        Get metrics as a dictionary (for JSON export).

        Returns:
            Dictionary of metrics
        """
        result = {}

        with self.lock:
            for metric_name, metric in self.metrics.items():
                with metric.lock:
                    if metric.metric_type == MetricType.HISTOGRAM:
                        hist = metric
                        result[metric_name] = {
                            "type": "histogram",
                            "values": dict(hist.count_values),
                            "sum": dict(hist.sum_values),
                        }
                    else:
                        result[metric_name] = {
                            "type": metric.metric_type,
                            "values": dict(metric.values),
                        }

        return result
