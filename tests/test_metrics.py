"""
Tests for Metrics Collection

Tests metric types, collection, aggregation, and Prometheus export.
"""

import pytest

from src.utils.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsCollector,
    MetricType,
)


class TestCounter:
    """Test Counter metric."""

    def test_initialization(self):
        """Test counter initialization."""
        counter = Counter("test_counter", "Test counter", labels=["status"])
        assert counter.name == "test_counter"
        assert counter.metric_type == MetricType.COUNTER
        assert counter.labels == ["status"]

    def test_increment_no_labels(self):
        """Test incrementing counter without labels."""
        counter = Counter("test_counter", "Test counter")
        counter.inc(1.0)
        counter.inc(2.0)

        assert counter.values[""] == 3.0

    def test_increment_with_labels(self):
        """Test incrementing counter with labels."""
        counter = Counter("test_counter", "Test counter", labels=["status", "type"])
        counter.inc(1.0, {"status": "success", "type": "login"})
        counter.inc(1.0, {"status": "success", "type": "login"})
        counter.inc(1.0, {"status": "failure", "type": "login"})

        assert counter.values["status=success,type=login"] == 2.0
        assert counter.values["status=failure,type=login"] == 1.0


class TestGauge:
    """Test Gauge metric."""

    def test_set_value(self):
        """Test setting gauge value."""
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.set(42.0)

        assert gauge.values[""] == 42.0

        gauge.set(10.0)
        assert gauge.values[""] == 10.0

    def test_increment_decrement(self):
        """Test incrementing and decrementing gauge."""
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.set(10.0)
        gauge.inc(5.0)

        assert gauge.values[""] == 15.0

        gauge.dec(3.0)
        assert gauge.values[""] == 12.0

    def test_gauge_with_labels(self):
        """Test gauge with labels."""
        gauge = Gauge("test_gauge", "Test gauge", labels=["host"])
        gauge.set(100.0, {"host": "server1"})
        gauge.set(200.0, {"host": "server2"})

        assert gauge.values["host=server1"] == 100.0
        assert gauge.values["host=server2"] == 200.0


class TestHistogram:
    """Test Histogram metric."""

    def test_initialization(self):
        """Test histogram initialization."""
        histogram = Histogram("test_histogram", "Test histogram")
        assert histogram.metric_type == MetricType.HISTOGRAM
        assert len(histogram.buckets) > 0

    def test_observe_values(self):
        """Test observing values."""
        histogram = Histogram(
            "test_histogram", "Test histogram", buckets=[1.0, 5.0, 10.0]
        )

        histogram.observe(0.5)
        histogram.observe(3.0)
        histogram.observe(7.0)
        histogram.observe(15.0)

        # Check counts
        assert histogram.count_values[""] == 4
        assert histogram.sum_values[""] == 25.5

        # Check buckets
        assert histogram.bucket_counts[""][1.0] == 1  # 0.5 <= 1.0
        assert histogram.bucket_counts[""][5.0] == 2  # 0.5, 3.0 <= 5.0
        assert histogram.bucket_counts[""][10.0] == 3  # 0.5, 3.0, 7.0 <= 10.0

    def test_histogram_with_labels(self):
        """Test histogram with labels."""
        histogram = Histogram(
            "test_histogram", "Test histogram", buckets=[1.0, 5.0], labels=["method"]
        )

        histogram.observe(0.5, {"method": "GET"})
        histogram.observe(2.0, {"method": "POST"})

        assert histogram.count_values["method=GET"] == 1
        assert histogram.count_values["method=POST"] == 1


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_initialization(self):
        """Test collector initialization."""
        collector = MetricsCollector({"enabled": True})
        assert collector.enabled
        assert len(collector.metrics) > 0

    def test_disabled_collector(self):
        """Test disabled collector."""
        collector = MetricsCollector({"enabled": False})
        assert not collector.enabled

    def test_register_counter(self):
        """Test registering counter."""
        collector = MetricsCollector({})
        counter = collector.register_counter("custom_counter", "Custom counter")

        assert isinstance(counter, Counter)
        assert "custom_counter" in collector.metrics

    def test_register_gauge(self):
        """Test registering gauge."""
        collector = MetricsCollector({})
        gauge = collector.register_gauge("custom_gauge", "Custom gauge")

        assert isinstance(gauge, Gauge)
        assert "custom_gauge" in collector.metrics

    def test_register_histogram(self):
        """Test registering histogram."""
        collector = MetricsCollector({})
        histogram = collector.register_histogram(
            "custom_histogram", "Custom histogram"
        )

        assert isinstance(histogram, Histogram)
        assert "custom_histogram" in collector.metrics

    def test_record_scan(self):
        """Test recording scan operation."""
        collector = MetricsCollector({"enabled": True})

        quality_checks = {
            "face_size": True,
            "centered": True,
            "eyes_open": True,
        }

        collector.record_scan(True, "LOGIN", 1.5, quality_checks)

        # Check metrics were updated
        scans_metric = collector.get_metric("attendance_scans_total")
        assert scans_metric.values["status=success,scan_type=LOGIN"] == 1.0

        duration_metric = collector.get_metric("attendance_scan_duration_seconds")
        assert duration_metric.count_values["scan_type=LOGIN"] == 1

        quality_metric = collector.get_metric("attendance_face_quality_checks_total")
        assert quality_metric.values["check_name=face_size,result=pass"] == 1.0

    def test_record_sync_operation(self):
        """Test recording sync operation."""
        collector = MetricsCollector({"enabled": True})

        collector.record_sync_operation("attendance", True, 0.5, 10)

        sync_metric = collector.get_metric("cloud_sync_operations_total")
        assert sync_metric.values["operation=attendance,status=success"] == 1.0

        duration_metric = collector.get_metric("cloud_sync_duration_seconds")
        assert duration_metric.count_values["operation=attendance"] == 1

        queue_metric = collector.get_metric("cloud_sync_queue_size")
        assert queue_metric.values["priority=normal"] == 10.0

    def test_update_system_health(self):
        """Test updating system health metrics."""
        collector = MetricsCollector({"enabled": True})

        circuit_breaker_states = {"students": 0, "attendance": 1}

        collector.update_system_health(
            disk_usage=1000000,
            disk_free=500000,
            is_online=True,
            circuit_breaker_states=circuit_breaker_states,
        )

        disk_usage_metric = collector.get_metric("system_disk_usage_bytes")
        assert disk_usage_metric.values["path=data"] == 1000000.0

        online_metric = collector.get_metric("system_online_status")
        assert online_metric.values[""] == 1.0

        cb_metric = collector.get_metric("system_circuit_breaker_status")
        assert cb_metric.values["service=students"] == 0.0
        assert cb_metric.values["service=attendance"] == 1.0

    def test_record_error(self):
        """Test recording error."""
        collector = MetricsCollector({"enabled": True})

        collector.record_error("camera", "initialization_failed")

        error_metric = collector.get_metric("system_errors_total")
        assert (
            error_metric.values["component=camera,error_type=initialization_failed"]
            == 1.0
        )

    def test_export_prometheus(self):
        """Test Prometheus export format."""
        collector = MetricsCollector({})

        # Register simple counter
        counter = collector.register_counter("test_counter", "Test counter")
        counter.inc(5.0)

        prometheus_text = collector.export_prometheus()

        assert "# HELP test_counter Test counter" in prometheus_text
        assert "# TYPE test_counter counter" in prometheus_text
        assert "test_counter 5.0" in prometheus_text

    def test_export_prometheus_with_labels(self):
        """Test Prometheus export with labels."""
        collector = MetricsCollector({})

        counter = collector.register_counter(
            "test_counter", "Test counter", labels=["status"]
        )
        counter.inc(1.0, {"status": "success"})
        counter.inc(2.0, {"status": "failure"})

        prometheus_text = collector.export_prometheus()

        assert "test_counter{status=success} 1.0" in prometheus_text
        assert "test_counter{status=failure} 2.0" in prometheus_text

    def test_get_metrics_dict(self):
        """Test getting metrics as dictionary."""
        collector = MetricsCollector({})

        counter = collector.register_counter("test_counter", "Test counter")
        counter.inc(10.0)

        metrics_dict = collector.get_metrics_dict()

        assert "test_counter" in metrics_dict
        assert metrics_dict["test_counter"]["type"] == MetricType.COUNTER
        assert metrics_dict["test_counter"]["values"][""] == 10.0

    def test_disabled_collector_no_recording(self):
        """Test that disabled collector doesn't record metrics."""
        collector = MetricsCollector({"enabled": False})

        # Should not raise errors but not record anything
        collector.record_scan(True, "LOGIN", 1.0, {})
        collector.record_error("test", "test_error")

        # Should return empty
        prometheus_text = collector.export_prometheus()
        assert prometheus_text == ""
