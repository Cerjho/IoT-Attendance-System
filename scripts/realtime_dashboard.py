#!/usr/bin/env python3
"""
Real-time Monitoring Web Dashboard
Live dashboard with WebSocket updates
"""

import json
import logging
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Set
from urllib.parse import parse_qs, urlparse

from src.utils.realtime_monitor import get_monitor

logger = logging.getLogger(__name__)


class WebSocketClient:
    """Simplified WebSocket-like client for real-time updates"""
    
    def __init__(self, wfile, client_address):
        self.wfile = wfile
        self.client_address = client_address
        self.last_update = datetime.now()
        self.active = True

    def send_event(self, data: Dict):
        """Send Server-Sent Event to client"""
        try:
            message = f"data: {json.dumps(data)}\n\n"
            self.wfile.write(message.encode())
            self.wfile.flush()
            self.last_update = datetime.now()
        except Exception as e:
            logger.debug(f"Client {self.client_address} disconnected: {e}")
            self.active = False


class MonitoringDashboardHandler(BaseHTTPRequestHandler):
    """HTTP handler for monitoring dashboard"""

    # Class-level client tracking
    event_clients: Set[WebSocketClient] = set()
    clients_lock = threading.Lock()

    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/" or path == "/dashboard":
            self._serve_dashboard()
        elif path == "/api/status":
            self._serve_status()
        elif path == "/api/metrics":
            self._serve_metrics()
        elif path == "/api/events":
            self._serve_events()
        elif path == "/api/alerts":
            self._serve_alerts()
        elif path == "/api/stream":
            self._serve_event_stream()
        else:
            self.send_error(404, "Not Found")

    def _serve_dashboard(self):
        """Serve HTML dashboard"""
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IoT Attendance - Real-time Monitor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }
        .card h2 {
            font-size: 1.2em;
            margin-bottom: 15px;
            color: #667eea;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: #666; font-size: 0.95em; }
        .metric-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-healthy { background: #10b981; box-shadow: 0 0 10px #10b981; }
        .status-warning { background: #f59e0b; box-shadow: 0 0 10px #f59e0b; }
        .status-error { background: #ef4444; box-shadow: 0 0 10px #ef4444; }
        .status-unknown { background: #6b7280; }
        .event-list {
            max-height: 400px;
            overflow-y: auto;
            margin-top: 15px;
        }
        .event-item {
            padding: 12px;
            margin-bottom: 10px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            font-size: 0.9em;
        }
        .event-scan { border-left-color: #10b981; }
        .event-sync { border-left-color: #3b82f6; }
        .event-error { border-left-color: #ef4444; }
        .event-warning { border-left-color: #f59e0b; }
        .event-time {
            color: #6b7280;
            font-size: 0.85em;
            margin-bottom: 5px;
        }
        .event-message { color: #333; }
        .alert-item {
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            display: flex;
            align-items: start;
            gap: 10px;
            animation: slideIn 0.3s ease-out;
        }
        @keyframes slideIn {
            from { transform: translateX(-20px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        .alert-error {
            background: #fee2e2;
            border: 1px solid #fecaca;
            color: #991b1b;
        }
        .alert-warning {
            background: #fef3c7;
            border: 1px solid #fde68a;
            color: #92400e;
        }
        .alert-info {
            background: #dbeafe;
            border: 1px solid #bfdbfe;
            color: #1e40af;
        }
        .chart-container {
            height: 200px;
            margin-top: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            display: flex;
            align-items: flex-end;
            gap: 5px;
        }
        .chart-bar {
            flex: 1;
            background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
            border-radius: 4px 4px 0 0;
            min-height: 5px;
            transition: height 0.3s;
        }
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            background: white;
            border-radius: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.9em;
        }
        .pulse {
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            h1 { font-size: 1.8em; }
        }
    </style>
</head>
<body>
    <div class="connection-status">
        <span class="status-indicator status-healthy pulse" id="connectionIndicator"></span>
        <span id="connectionStatus">Connected</span>
    </div>
    
    <div class="container">
        <h1>📊 IoT Attendance - Real-time Monitor</h1>
        
        <div class="grid">
            <!-- System Status Card -->
            <div class="card">
                <h2>
                    <span class="status-indicator" id="systemStatusIndicator"></span>
                    System Status
                </h2>
                <div class="metric">
                    <span class="metric-label">Overall Status</span>
                    <span class="metric-value" id="systemStatus">Loading...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Camera</span>
                    <span id="cameraStatus">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Cloud Sync</span>
                    <span id="cloudStatus">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">SMS Notifier</span>
                    <span id="smsStatus">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Uptime</span>
                    <span id="uptime">-</span>
                </div>
            </div>

            <!-- Metrics Card -->
            <div class="card">
                <h2>📈 Today's Metrics</h2>
                <div class="metric">
                    <span class="metric-label">Scans Today</span>
                    <span class="metric-value" id="scansToday">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Last Hour</span>
                    <span class="metric-value" id="scansHour">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Success Rate</span>
                    <span class="metric-value" id="successRate">100%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Queue Size</span>
                    <span class="metric-value" id="queueSize">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Failed Syncs</span>
                    <span class="metric-value" id="failedSyncs">0</span>
                </div>
            </div>

            <!-- Activity Chart Card -->
            <div class="card">
                <h2>📊 Activity (Last 10 Minutes)</h2>
                <div class="chart-container" id="activityChart">
                    <!-- Chart bars will be inserted here -->
                </div>
            </div>
        </div>

        <!-- Alerts Card -->
        <div class="card">
            <h2>⚠️ Recent Alerts</h2>
            <div class="event-list" id="alertsList">
                <p style="color: #6b7280; text-align: center; padding: 20px;">No alerts</p>
            </div>
        </div>

        <!-- Events Card -->
        <div class="card">
            <h2>📋 Recent Events</h2>
            <div class="event-list" id="eventsList">
                <p style="color: #6b7280; text-align: center; padding: 20px;">Waiting for events...</p>
            </div>
        </div>
    </div>

    <script>
        // Event source for real-time updates
        let eventSource = null;
        let reconnectInterval = null;
        let activityData = Array(10).fill(0);

        function connectEventStream() {
            if (eventSource) {
                eventSource.close();
            }

            eventSource = new EventSource('/api/stream');
            
            eventSource.onopen = () => {
                console.log('Connected to event stream');
                updateConnectionStatus(true);
                if (reconnectInterval) {
                    clearInterval(reconnectInterval);
                    reconnectInterval = null;
                }
            };

            eventSource.onerror = (error) => {
                console.error('EventSource error:', error);
                updateConnectionStatus(false);
                eventSource.close();
                
                // Reconnect after 5 seconds
                if (!reconnectInterval) {
                    reconnectInterval = setInterval(() => {
                        console.log('Attempting to reconnect...');
                        connectEventStream();
                    }, 5000);
                }
            };

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleRealtimeUpdate(data);
                } catch (e) {
                    console.error('Error parsing event data:', e);
                }
            };
        }

        function updateConnectionStatus(connected) {
            const indicator = document.getElementById('connectionIndicator');
            const status = document.getElementById('connectionStatus');
            
            if (connected) {
                indicator.className = 'status-indicator status-healthy pulse';
                status.textContent = 'Connected';
            } else {
                indicator.className = 'status-indicator status-error';
                status.textContent = 'Disconnected';
            }
        }

        function handleRealtimeUpdate(data) {
            if (data.type === 'metrics') {
                updateMetrics(data.data);
            } else if (data.type === 'event') {
                addEvent(data.data);
                updateActivityChart();
            } else if (data.type === 'alert') {
                addAlert(data.data);
            } else if (data.type === 'state') {
                updateSystemState(data.data);
            } else if (data.type === 'dashboard') {
                updateDashboard(data.data);
            }
        }

        function updateMetrics(metrics) {
            document.getElementById('scansToday').textContent = metrics.scans_today || 0;
            document.getElementById('scansHour').textContent = metrics.scans_last_hour || 0;
            document.getElementById('successRate').textContent = 
                (metrics.success_rate || 100).toFixed(1) + '%';
            document.getElementById('queueSize').textContent = metrics.queue_size || 0;
            document.getElementById('failedSyncs').textContent = metrics.failed_syncs || 0;
        }

        function updateSystemState(state) {
            const statusMap = {
                'healthy': { text: 'Healthy', class: 'status-healthy' },
                'degraded': { text: 'Degraded', class: 'status-warning' },
                'error': { text: 'Error', class: 'status-error' },
                'partial': { text: 'Partial', class: 'status-warning' }
            };

            const status = statusMap[state.status] || { text: 'Unknown', class: 'status-unknown' };
            document.getElementById('systemStatus').textContent = status.text;
            document.getElementById('systemStatusIndicator').className = 
                'status-indicator ' + status.class;

            document.getElementById('cameraStatus').textContent = 
                formatComponentStatus(state.camera_status);
            document.getElementById('cloudStatus').textContent = 
                formatComponentStatus(state.cloud_status);
            document.getElementById('smsStatus').textContent = 
                formatComponentStatus(state.sms_status);
        }

        function updateDashboard(data) {
            updateMetrics(data.metrics);
            updateSystemState(data.system_state);
            document.getElementById('uptime').textContent = data.uptime || '-';
            
            // Load initial events and alerts
            data.recent_events.reverse().forEach(event => addEvent(event, false));
            data.recent_alerts.reverse().forEach(alert => addAlert(alert, false));
        }

        function formatComponentStatus(status) {
            const statusIcons = {
                'online': '🟢 Online',
                'offline': '🔴 Offline',
                'error': '⚠️ Error',
                'unknown': '⚪ Unknown'
            };
            return statusIcons[status] || status;
        }

        function addEvent(event, prepend = true) {
            const eventsList = document.getElementById('eventsList');
            
            // Clear placeholder
            if (eventsList.querySelector('p')) {
                eventsList.innerHTML = '';
            }

            const eventDiv = document.createElement('div');
            eventDiv.className = `event-item event-${event.type}`;
            
            const time = new Date(event.timestamp).toLocaleTimeString();
            eventDiv.innerHTML = `
                <div class="event-time">${time}</div>
                <div class="event-message">${escapeHtml(event.message)}</div>
            `;

            if (prepend) {
                eventsList.insertBefore(eventDiv, eventsList.firstChild);
            } else {
                eventsList.appendChild(eventDiv);
            }

            // Keep only last 50 events
            while (eventsList.children.length > 50) {
                eventsList.removeChild(eventsList.lastChild);
            }
        }

        function addAlert(alert, prepend = true) {
            const alertsList = document.getElementById('alertsList');
            
            // Clear placeholder
            if (alertsList.querySelector('p')) {
                alertsList.innerHTML = '';
            }

            const alertDiv = document.createElement('div');
            alertDiv.className = `alert-item alert-${alert.level}`;
            
            const time = new Date(alert.timestamp).toLocaleTimeString();
            const icon = alert.level === 'error' ? '❌' : 
                        alert.level === 'warning' ? '⚠️' : 'ℹ️';
            
            alertDiv.innerHTML = `
                <div style="font-size: 1.5em;">${icon}</div>
                <div style="flex: 1;">
                    <div style="font-size: 0.85em; color: inherit; opacity: 0.8;">${time}</div>
                    <div style="margin-top: 5px;">${escapeHtml(alert.message)}</div>
                </div>
            `;

            if (prepend) {
                alertsList.insertBefore(alertDiv, alertsList.firstChild);
            } else {
                alertsList.appendChild(alertDiv);
            }

            // Keep only last 20 alerts
            while (alertsList.children.length > 20) {
                alertsList.removeChild(alertsList.lastChild);
            }
        }

        function updateActivityChart() {
            // Shift and add new value
            activityData.shift();
            activityData.push(activityData[activityData.length - 1] + 1);

            const chartContainer = document.getElementById('activityChart');
            chartContainer.innerHTML = '';

            const maxValue = Math.max(...activityData, 1);
            activityData.forEach(value => {
                const bar = document.createElement('div');
                bar.className = 'chart-bar';
                bar.style.height = `${(value / maxValue) * 100}%`;
                chartContainer.appendChild(bar);
            });
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Initial load
        async function loadInitialData() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateDashboard(data);
            } catch (e) {
                console.error('Error loading initial data:', e);
            }
        }

        // Initialize
        loadInitialData();
        connectEventStream();

        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (eventSource) {
                eventSource.close();
            }
        });
    </script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html.encode())

    def _serve_status(self):
        """Serve complete dashboard data"""
        monitor = get_monitor()
        data = monitor.get_dashboard_data()
        self._send_json(data)

    def _serve_metrics(self):
        """Serve current metrics"""
        monitor = get_monitor()
        data = monitor.get_metrics()
        self._send_json(data)

    def _serve_events(self):
        """Serve recent events"""
        monitor = get_monitor()
        data = monitor.get_recent_events(50)
        self._send_json(data)

    def _serve_alerts(self):
        """Serve recent alerts"""
        monitor = get_monitor()
        data = monitor.get_recent_alerts(20)
        self._send_json(data)

    def _serve_event_stream(self):
        """Serve Server-Sent Events stream"""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        # Create client
        client = WebSocketClient(self.wfile, self.client_address)
        
        with self.clients_lock:
            self.event_clients.add(client)
        
        logger.info(f"Client {self.client_address} connected to event stream")

        # Send initial dashboard data
        monitor = get_monitor()
        initial_data = monitor.get_dashboard_data()
        client.send_event({"type": "dashboard", "data": initial_data})

        try:
            # Keep connection alive
            while client.active:
                time.sleep(30)  # Send keepalive every 30 seconds
                if client.active:
                    client.send_event({"type": "keepalive", "data": {}})
        except Exception as e:
            logger.debug(f"Event stream error for {self.client_address}: {e}")
        finally:
            with self.clients_lock:
                if client in self.event_clients:
                    self.event_clients.remove(client)
            logger.info(f"Client {self.client_address} disconnected from event stream")

    def _send_json(self, data):
        """Send JSON response"""
        response = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        """Override to reduce logging noise"""
        if not self.path.startswith("/api/stream"):
            logger.debug(f"{self.client_address[0]} - {format % args}")


def start_dashboard_server(host: str = "0.0.0.0", port: int = 8888):
    """
    Start monitoring dashboard server

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    server = HTTPServer((host, port), MonitoringDashboardHandler)
    logger.info(f"Real-time monitoring dashboard started at http://{host}:{port}")
    logger.info(f"Access dashboard: http://localhost:{port}/dashboard")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Dashboard server shutting down...")
        server.shutdown()


def broadcast_to_clients(event_type: str, data: Dict):
    """Broadcast event to all connected clients"""
    message = {"type": event_type, "data": data}
    
    with MonitoringDashboardHandler.clients_lock:
        for client in list(MonitoringDashboardHandler.event_clients):
            if client.active:
                client.send_event(message)
            else:
                MonitoringDashboardHandler.event_clients.discard(client)


# Subscribe monitor to broadcast updates
def _monitor_callback(event_type: str, data: Dict):
    """Callback to broadcast monitor events to web clients"""
    broadcast_to_clients(event_type, data)


# Auto-subscribe when monitor is created
monitor = get_monitor()
monitor.subscribe(_monitor_callback)


if __name__ == "__main__":
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get port from args
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
    
    # Start monitor
    monitor.start()
    
    # Start dashboard
    try:
        start_dashboard_server(port=port)
    finally:
        monitor.stop()
