# API Integration Guide for Software Teams

Complete guide for integrating the IoT Attendance System REST API into web/mobile dashboards.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base Configuration](#base-configuration)
- [API Endpoints](#api-endpoints)
- [Integration Examples](#integration-examples)
- [Error Handling](#error-handling)
- [Real-Time Updates](#real-time-updates)
- [Security Best Practices](#security-best-practices)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Overview

### API Base URL

```
Development: http://192.168.1.22:8080
Production:  https://your-domain.com
```

### Response Format

All endpoints return JSON (except `/metrics/prometheus` which returns text).

```json
{
  "status": "success",
  "data": { ... },
  "timestamp": "2025-11-29T19:42:51Z"
}
```

### Rate Limits

- **Without Nginx:** No rate limiting (use with caution)
- **With Nginx:** 10 requests/second per IP, burst up to 20

---

## Authentication

### API Key Types

The API supports two authentication methods:

#### 1. Bearer Token (Recommended)

```http
Authorization: Bearer hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8
```

#### 2. X-API-Key Header (Alternative)

```http
X-API-Key: hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8
```

### Getting Your API Key

Contact your system administrator or retrieve from deployment:

```bash
# On the Raspberry Pi
grep DASHBOARD_API_KEY /home/iot/attendance-system/.env
```

### Authentication Errors

```json
// 401 Unauthorized - Missing API key
{
  "error": "Unauthorized",
  "message": "Valid API key required. Use Authorization: Bearer <key> or X-API-Key: <key> header"
}

// 403 Forbidden - IP blocked
{
  "error": "Access denied",
  "message": "Your IP address is not allowed"
}
```

---

## Base Configuration

### JavaScript/TypeScript Setup

```typescript
// config/api.ts
export const API_CONFIG = {
  baseURL: process.env.REACT_APP_API_URL || 'http://192.168.1.22:8080',
  apiKey: process.env.REACT_APP_API_KEY,
  timeout: 10000, // 10 seconds
};

// utils/apiClient.ts
import axios from 'axios';
import { API_CONFIG } from '../config/api';

const apiClient = axios.create({
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${API_CONFIG.apiKey}`,
  },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.error('Authentication failed - check API key');
      // Redirect to login or show error
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

### React Setup with Context

```typescript
// contexts/ApiContext.tsx
import React, { createContext, useContext } from 'react';
import apiClient from '../utils/apiClient';

interface ApiContextType {
  fetchHealth: () => Promise<any>;
  fetchStatus: () => Promise<any>;
  fetchRecentScans: (limit?: number) => Promise<any>;
  fetchMetrics: () => Promise<any>;
}

const ApiContext = createContext<ApiContextType | undefined>(undefined);

export const ApiProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const fetchHealth = async () => {
    const response = await apiClient.get('/health');
    return response.data;
  };

  const fetchStatus = async () => {
    const response = await apiClient.get('/status');
    return response.data;
  };

  const fetchRecentScans = async (limit = 10) => {
    const response = await apiClient.get(`/scans/recent?limit=${limit}`);
    return response.data;
  };

  const fetchMetrics = async () => {
    const response = await apiClient.get('/metrics');
    return response.data;
  };

  return (
    <ApiContext.Provider value={{ fetchHealth, fetchStatus, fetchRecentScans, fetchMetrics }}>
      {children}
    </ApiContext.Provider>
  );
};

export const useApi = () => {
  const context = useContext(ApiContext);
  if (!context) throw new Error('useApi must be used within ApiProvider');
  return context;
};
```

### Vue.js Setup

```typescript
// plugins/api.ts
import axios, { AxiosInstance } from 'axios';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_URL || 'http://192.168.1.22:8080',
      timeout: 10000,
      headers: {
        'Authorization': `Bearer ${import.meta.env.VITE_API_KEY}`,
      },
    });
  }

  async getHealth() {
    return this.client.get('/health');
  }

  async getStatus() {
    return this.client.get('/status');
  }

  async getRecentScans(limit = 10) {
    return this.client.get('/scans/recent', { params: { limit } });
  }

  async getMetrics() {
    return this.client.get('/metrics');
  }
}

export default new ApiService();
```

### Python Setup

```python
# api_client.py
import os
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class AttendanceAPIClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or os.getenv('API_BASE_URL', 'http://192.168.1.22:8080')
        self.api_key = api_key or os.getenv('DASHBOARD_API_KEY')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[Any, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception("Authentication failed - check API key")
            raise
    
    def get_health(self) -> Dict[Any, Any]:
        return self._request('GET', '/health')
    
    def get_status(self) -> Dict[Any, Any]:
        return self._request('GET', '/status')
    
    def get_recent_scans(self, limit: int = 10) -> Dict[Any, Any]:
        return self._request('GET', f'/scans/recent?limit={limit}')
    
    def get_metrics(self) -> Dict[Any, Any]:
        return self._request('GET', '/metrics')

# Usage
client = AttendanceAPIClient()
status = client.get_status()
print(status)
```

---

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Description:** Quick health check for monitoring systems.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-29T19:42:51.123456"
}
```

**React Hook Example:**
```typescript
// hooks/useHealthCheck.ts
import { useState, useEffect } from 'react';
import { useApi } from '../contexts/ApiContext';

export const useHealthCheck = (interval = 30000) => {
  const [isHealthy, setIsHealthy] = useState(true);
  const { fetchHealth } = useApi();

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await fetchHealth();
        setIsHealthy(data.status === 'healthy');
      } catch (error) {
        setIsHealthy(false);
      }
    };

    checkHealth();
    const timer = setInterval(checkHealth, interval);
    return () => clearInterval(timer);
  }, [interval]);

  return isHealthy;
};
```

---

### 2. System Status

**Endpoint:** `GET /status`

**Description:** Comprehensive system status including connectivity, disk usage, and queue.

**Response:**
```json
{
  "status": "operational",
  "timestamp": "2025-11-29T19:42:51.123456",
  "online": true,
  "disk_usage": {
    "total_gb": 14.9,
    "used_gb": 5.9,
    "free_gb": 8.4,
    "percent": 39.0
  },
  "queue_size": 144,
  "system_uptime": 12345.67
}
```

**React Component Example:**
```tsx
// components/SystemStatus.tsx
import React, { useEffect, useState } from 'react';
import { useApi } from '../contexts/ApiContext';

interface StatusData {
  status: string;
  online: boolean;
  disk_usage: {
    percent: number;
    free_gb: number;
  };
  queue_size: number;
}

export const SystemStatus: React.FC = () => {
  const [status, setStatus] = useState<StatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const { fetchStatus } = useApi();

  useEffect(() => {
    const loadStatus = async () => {
      try {
        const data = await fetchStatus();
        setStatus(data);
      } catch (error) {
        console.error('Failed to fetch status:', error);
      } finally {
        setLoading(false);
      }
    };

    loadStatus();
    const interval = setInterval(loadStatus, 10000); // Update every 10s
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div>Loading...</div>;
  if (!status) return <div>Error loading status</div>;

  return (
    <div className="status-card">
      <h2>System Status</h2>
      <div className={`status-indicator ${status.online ? 'online' : 'offline'}`}>
        {status.online ? '🟢 Online' : '🔴 Offline'}
      </div>
      <div className="metrics">
        <div>Disk: {status.disk_usage.percent}% used</div>
        <div>Free: {status.disk_usage.free_gb.toFixed(1)} GB</div>
        <div>Queue: {status.queue_size} pending</div>
      </div>
    </div>
  );
};
```

---

### 3. Recent Scans

**Endpoint:** `GET /scans/recent?limit=<N>`

**Description:** Retrieve recent attendance scans.

**Parameters:**
- `limit` (optional): Number of records (default: 100, max: 1000)

**Response:**
```json
{
  "scans": [
    {
      "id": 1,
      "student_id": "3c2c6e8f-7d3e-4f7a-9a1b-3f82a1cdb1a4",
      "timestamp": "2025-11-29 07:12:34",
      "scan_type": "LOGIN",
      "status": "present",
      "photo_path": "data/photos/2021001_20251129_071234.jpg",
      "synced": 1,
      "sync_timestamp": "2025-11-29 07:12:45",
      "cloud_record_id": "uuid-from-supabase"
    }
  ],
  "count": 1,
  "timestamp": "2025-11-29T19:42:51.123456"
}
```

**React Component Example:**
```tsx
// components/RecentScans.tsx
import React, { useEffect, useState } from 'react';
import { useApi } from '../contexts/ApiContext';

interface Scan {
  id: number;
  student_id: string;
  timestamp: string;
  scan_type: string;
  status: string;
  synced: number;
}

export const RecentScans: React.FC = () => {
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);
  const { fetchRecentScans } = useApi();

  useEffect(() => {
    const loadScans = async () => {
      try {
        const data = await fetchRecentScans(10);
        setScans(data.scans);
      } catch (error) {
        console.error('Failed to fetch scans:', error);
      } finally {
        setLoading(false);
      }
    };

    loadScans();
    const interval = setInterval(loadScans, 5000); // Update every 5s
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div>Loading scans...</div>;

  return (
    <div className="scans-list">
      <h2>Recent Scans</h2>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Student ID</th>
            <th>Type</th>
            <th>Status</th>
            <th>Synced</th>
          </tr>
        </thead>
        <tbody>
          {scans.map(scan => (
            <tr key={scan.id}>
              <td>{new Date(scan.timestamp).toLocaleString()}</td>
              <td>{scan.student_id.substring(0, 8)}...</td>
              <td>
                <span className={`badge ${scan.scan_type.toLowerCase()}`}>
                  {scan.scan_type}
                </span>
              </td>
              <td>{scan.status}</td>
              <td>{scan.synced ? '✅' : '⏳'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

---

### 4. Sync Queue Status

**Endpoint:** `GET /queue/status`

**Description:** Get sync queue information.

**Response:**
```json
{
  "queue_size": 144,
  "pending": 120,
  "failed": 24,
  "oldest_record": "2025-11-28 18:30:00",
  "timestamp": "2025-11-29T19:42:51.123456"
}
```

**Vue Component Example:**
```vue
<!-- components/QueueStatus.vue -->
<template>
  <div class="queue-status">
    <h3>Sync Queue</h3>
    <div v-if="loading">Loading...</div>
    <div v-else-if="queue">
      <div class="stat">
        <span class="label">Total:</span>
        <span class="value">{{ queue.queue_size }}</span>
      </div>
      <div class="stat">
        <span class="label">Pending:</span>
        <span class="value pending">{{ queue.pending }}</span>
      </div>
      <div class="stat" v-if="queue.failed > 0">
        <span class="label">Failed:</span>
        <span class="value failed">{{ queue.failed }}</span>
      </div>
      <div class="stat" v-if="queue.oldest_record">
        <span class="label">Oldest:</span>
        <span class="value">{{ formatDate(queue.oldest_record) }}</span>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onUnmounted } from 'vue';
import api from '../plugins/api';

export default defineComponent({
  name: 'QueueStatus',
  setup() {
    const queue = ref(null);
    const loading = ref(true);
    let interval: number;

    const fetchQueue = async () => {
      try {
        const response = await api.client.get('/queue/status');
        queue.value = response.data;
      } catch (error) {
        console.error('Failed to fetch queue:', error);
      } finally {
        loading.value = false;
      }
    };

    const formatDate = (dateStr: string) => {
      return new Date(dateStr).toLocaleString();
    };

    onMounted(() => {
      fetchQueue();
      interval = setInterval(fetchQueue, 10000); // Update every 10s
    });

    onUnmounted(() => {
      clearInterval(interval);
    });

    return { queue, loading, formatDate };
  },
});
</script>
```

---

### 5. System Metrics

**Endpoint:** `GET /metrics`

**Description:** Get system metrics in JSON format.

**Response:**
```json
{
  "metrics": {
    "system_uptime_seconds": 12345.67,
    "disk_usage_percent": 39.0,
    "queue_size": 144,
    "total_scans": 1234,
    "synced_scans": 1090,
    "failed_syncs": 24
  },
  "timestamp": "2025-11-29T19:42:51.123456"
}
```

**Chart.js Integration Example:**
```typescript
// components/MetricsChart.tsx
import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';
import { useApi } from '../contexts/ApiContext';

export const MetricsChart: React.FC = () => {
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [
      {
        label: 'Queue Size',
        data: [],
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1,
      },
    ],
  });
  const { fetchMetrics } = useApi();

  useEffect(() => {
    const updateChart = async () => {
      try {
        const data = await fetchMetrics();
        setChartData(prev => ({
          labels: [...prev.labels, new Date().toLocaleTimeString()].slice(-20),
          datasets: [{
            ...prev.datasets[0],
            data: [...prev.datasets[0].data, data.metrics.queue_size].slice(-20),
          }],
        }));
      } catch (error) {
        console.error('Failed to fetch metrics:', error);
      }
    };

    updateChart();
    const interval = setInterval(updateChart, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="metrics-chart">
      <h2>Queue Size Over Time</h2>
      <Line data={chartData} options={{ responsive: true }} />
    </div>
  );
};
```

---

### 6. Prometheus Metrics

**Endpoint:** `GET /metrics/prometheus`

**Description:** Get metrics in Prometheus exposition format (text/plain).

**Response:**
```
# HELP attendance_system_uptime_seconds System uptime in seconds
# TYPE attendance_system_uptime_seconds gauge
attendance_system_uptime_seconds 12345.67

# HELP attendance_disk_usage_percent Disk usage percentage
# TYPE attendance_disk_usage_percent gauge
attendance_disk_usage_percent 39.0

# HELP attendance_queue_size Number of records in sync queue
# TYPE attendance_queue_size gauge
attendance_queue_size 144
```

**Grafana Dashboard JSON Example:**
```json
{
  "dashboard": {
    "title": "IoT Attendance System",
    "panels": [
      {
        "title": "Queue Size",
        "targets": [
          {
            "expr": "attendance_queue_size",
            "legendFormat": "Queue Size"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Disk Usage",
        "targets": [
          {
            "expr": "attendance_disk_usage_percent",
            "legendFormat": "Disk %"
          }
        ],
        "type": "gauge"
      }
    ]
  }
}
```

---

### 7. Configuration View

**Endpoint:** `GET /config`

**Description:** Get sanitized system configuration (sensitive data redacted).

**Response:**
```json
{
  "camera": {
    "index": 0,
    "resolution": { "width": 1280, "height": 720 }
  },
  "admin_dashboard": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8080,
    "auth_enabled": true
  },
  "cloud": {
    "enabled": true,
    "provider": "supabase",
    "url": "***REDACTED***",
    "api_key": "***REDACTED***"
  }
}
```

---

### 8. System Information

**Endpoint:** `GET /system/info`

**Description:** Get system information (Python version, platform, etc).

**Response:**
```json
{
  "python_version": "3.11.2",
  "platform": "Linux-6.12.47+rpt-rpi-v8-aarch64-with-glibc2.36",
  "hostname": "pi-iot",
  "device_id": "pi-lab-01"
}
```

---

## Integration Examples

### Complete React Dashboard

```tsx
// App.tsx
import React from 'react';
import { ApiProvider } from './contexts/ApiContext';
import { SystemStatus } from './components/SystemStatus';
import { RecentScans } from './components/RecentScans';
import { MetricsChart } from './components/MetricsChart';
import { QueueStatus } from './components/QueueStatus';

function App() {
  return (
    <ApiProvider>
      <div className="app">
        <header>
          <h1>Attendance System Dashboard</h1>
        </header>
        <main className="dashboard-grid">
          <SystemStatus />
          <QueueStatus />
          <RecentScans />
          <MetricsChart />
        </main>
      </div>
    </ApiProvider>
  );
}

export default App;
```

### Next.js API Route Proxy

```typescript
// pages/api/attendance/[...path].ts
import type { NextApiRequest, NextApiResponse } from 'next';
import axios from 'axios';

const API_BASE_URL = process.env.ATTENDANCE_API_URL || 'http://192.168.1.22:8080';
const API_KEY = process.env.ATTENDANCE_API_KEY;

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { path } = req.query;
  const endpoint = Array.isArray(path) ? path.join('/') : path;

  try {
    const response = await axios({
      method: req.method,
      url: `${API_BASE_URL}/${endpoint}`,
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
      },
      params: req.query,
    });

    res.status(response.status).json(response.data);
  } catch (error: any) {
    res.status(error.response?.status || 500).json({
      error: error.message,
    });
  }
}
```

### Flutter/Dart Integration

```dart
// lib/services/attendance_api.dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class AttendanceAPI {
  final String baseUrl;
  final String apiKey;

  AttendanceAPI({
    required this.baseUrl,
    required this.apiKey,
  });

  Future<Map<String, dynamic>> _request(String endpoint) async {
    final response = await http.get(
      Uri.parse('$baseUrl$endpoint'),
      headers: {
        'Authorization': 'Bearer $apiKey',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else if (response.statusCode == 401) {
      throw Exception('Authentication failed');
    } else {
      throw Exception('Failed to load data: ${response.statusCode}');
    }
  }

  Future<Map<String, dynamic>> getHealth() => _request('/health');
  Future<Map<String, dynamic>> getStatus() => _request('/status');
  Future<Map<String, dynamic>> getRecentScans(int limit) => 
    _request('/scans/recent?limit=$limit');
}

// Usage
final api = AttendanceAPI(
  baseUrl: 'http://192.168.1.22:8080',
  apiKey: 'your-api-key-here',
);

final status = await api.getStatus();
print('System online: ${status['online']}');
```

---

## Error Handling

### Standard Error Response Format

```json
{
  "error": "Error type",
  "message": "Detailed error message",
  "timestamp": "2025-11-29T19:42:51.123456"
}
```

### HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 401 | Unauthorized | Check API key |
| 403 | Forbidden | IP not whitelisted |
| 404 | Not Found | Check endpoint URL |
| 429 | Too Many Requests | Implement backoff |
| 500 | Server Error | Retry with exponential backoff |
| 503 | Service Unavailable | System offline, alert admin |

### Retry Logic Example

```typescript
// utils/retryRequest.ts
export async function retryRequest<T>(
  requestFn: () => Promise<T>,
  maxRetries = 3,
  delay = 1000
): Promise<T> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await requestFn();
    } catch (error: any) {
      const isLastAttempt = i === maxRetries - 1;
      const shouldRetry = error.response?.status >= 500;

      if (isLastAttempt || !shouldRetry) {
        throw error;
      }

      // Exponential backoff
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)));
    }
  }
  throw new Error('Max retries exceeded');
}

// Usage
const status = await retryRequest(() => apiClient.get('/status'));
```

---

## Real-Time Updates

### WebSocket Alternative (Polling)

Since the API doesn't support WebSockets, use polling with optimized intervals:

```typescript
// hooks/usePolling.ts
import { useState, useEffect, useRef } from 'react';

export function usePolling<T>(
  fetchFn: () => Promise<T>,
  interval = 5000,
  enabled = true
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (!enabled) return;

    const fetch = async () => {
      try {
        const result = await fetchFn();
        setData(result);
        setError(null);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetch(); // Initial fetch
    intervalRef.current = setInterval(fetch, interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchFn, interval, enabled]);

  return { data, error, loading };
}

// Usage
const { data: status } = usePolling(() => apiClient.get('/status').then(r => r.data), 10000);
```

### Server-Sent Events (Future Enhancement)

Request this feature from the backend team for real-time updates:

```typescript
// Future implementation example
const eventSource = new EventSource('http://192.168.1.22:8080/events', {
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
  },
});

eventSource.addEventListener('scan', (event) => {
  const scan = JSON.parse(event.data);
  console.log('New scan:', scan);
});
```

---

## Security Best Practices

### 1. Environment Variables

Never commit API keys to version control:

```bash
# .env
REACT_APP_API_URL=http://192.168.1.22:8080
REACT_APP_API_KEY=your-api-key-here

# .env.production
REACT_APP_API_URL=https://attendance.yourdomain.com
REACT_APP_API_KEY=prod-api-key-here
```

Add to `.gitignore`:
```
.env
.env.local
.env.*.local
```

### 2. API Key Rotation

Implement key rotation support:

```typescript
// utils/apiKeyManager.ts
class ApiKeyManager {
  private currentKey: string;
  private nextKey?: string;

  setKeys(current: string, next?: string) {
    this.currentKey = current;
    this.nextKey = next;
  }

  async request(url: string) {
    try {
      return await fetch(url, {
        headers: { 'Authorization': `Bearer ${this.currentKey}` }
      });
    } catch (error: any) {
      if (error.response?.status === 401 && this.nextKey) {
        // Try with new key
        const response = await fetch(url, {
          headers: { 'Authorization': `Bearer ${this.nextKey}` }
        });
        if (response.ok) {
          this.currentKey = this.nextKey;
          this.nextKey = undefined;
        }
        return response;
      }
      throw error;
    }
  }
}
```

### 3. CORS Configuration

For production, configure proper CORS:

```typescript
// Expected CORS headers from API
const corsHeaders = {
  'Access-Control-Allow-Origin': 'https://yourdomain.com',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Authorization, X-API-Key',
};
```

### 4. Rate Limiting Client-Side

Implement client-side throttling:

```typescript
// utils/throttle.ts
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let lastCall = 0;
  return (...args: Parameters<T>) => {
    const now = Date.now();
    if (now - lastCall >= delay) {
      lastCall = now;
      func(...args);
    }
  };
}

// Usage
const throttledFetch = throttle(fetchStatus, 1000); // Max 1 req/sec
```

---

## Testing

### Unit Tests (Jest + React Testing Library)

```typescript
// __tests__/api.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useHealthCheck } from '../hooks/useHealthCheck';
import { ApiProvider } from '../contexts/ApiContext';

describe('Health Check Hook', () => {
  it('should fetch health status', async () => {
    const { result } = renderHook(() => useHealthCheck(), {
      wrapper: ApiProvider,
    });

    await waitFor(() => {
      expect(result.current).toBe(true);
    });
  });

  it('should handle errors', async () => {
    // Mock API failure
    jest.spyOn(global, 'fetch').mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useHealthCheck(), {
      wrapper: ApiProvider,
    });

    await waitFor(() => {
      expect(result.current).toBe(false);
    });
  });
});
```

### Integration Tests

```typescript
// __tests__/integration.test.ts
import apiClient from '../utils/apiClient';

describe('API Integration', () => {
  it('should authenticate successfully', async () => {
    const response = await apiClient.get('/health');
    expect(response.status).toBe(200);
    expect(response.data.status).toBe('healthy');
  });

  it('should fetch recent scans', async () => {
    const response = await apiClient.get('/scans/recent?limit=5');
    expect(response.status).toBe(200);
    expect(response.data.scans).toHaveLength(5);
  });

  it('should handle unauthorized access', async () => {
    const invalidClient = axios.create({
      baseURL: 'http://192.168.1.22:8080',
      headers: { 'Authorization': 'Bearer invalid-key' },
    });

    await expect(invalidClient.get('/health')).rejects.toThrow();
  });
});
```

### Postman Collection

```json
{
  "info": {
    "name": "Attendance System API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "auth": {
    "type": "bearer",
    "bearer": [
      { "key": "token", "value": "{{API_KEY}}", "type": "string" }
    ]
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": { "raw": "{{BASE_URL}}/health" }
      }
    },
    {
      "name": "System Status",
      "request": {
        "method": "GET",
        "header": [],
        "url": { "raw": "{{BASE_URL}}/status" }
      }
    },
    {
      "name": "Recent Scans",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{BASE_URL}}/scans/recent?limit=10",
          "query": [{ "key": "limit", "value": "10" }]
        }
      }
    }
  ],
  "variable": [
    { "key": "BASE_URL", "value": "http://192.168.1.22:8080" },
    { "key": "API_KEY", "value": "your-api-key-here" }
  ]
}
```

---

## Troubleshooting

### Common Issues

#### 1. CORS Errors

**Symptom:**
```
Access to fetch at 'http://192.168.1.22:8080/health' from origin 'http://localhost:3000' 
has been blocked by CORS policy
```

**Solution:**
```typescript
// Use a proxy in development (package.json for Create React App)
{
  "proxy": "http://192.168.1.22:8080"
}

// Or configure Nginx to add CORS headers
```

#### 2. Authentication Failures

**Symptom:** 401 Unauthorized

**Checklist:**
- ✅ API key is correct
- ✅ Header format is correct (`Authorization: Bearer <key>`)
- ✅ No extra spaces in header value
- ✅ Environment variable is loaded

**Debug:**
```typescript
console.log('API Key:', process.env.REACT_APP_API_KEY?.substring(0, 10) + '...');
console.log('Headers:', apiClient.defaults.headers);
```

#### 3. Timeout Errors

**Symptom:** Request timeout after 10 seconds

**Solution:**
```typescript
// Increase timeout for slow connections
const apiClient = axios.create({
  timeout: 30000, // 30 seconds
});

// Or implement retry with backoff
```

#### 4. Empty Response Data

**Symptom:** `scans: []` or `queue_size: 0`

**Possible causes:**
- Database is empty (check backend logs)
- Time range issue (check system time)
- Permissions issue (check file access)

**Debug:**
```bash
# On Raspberry Pi
ls -lh /home/iot/attendance-system/data/attendance.db
sqlite3 /home/iot/attendance-system/data/attendance.db "SELECT COUNT(*) FROM attendance;"
```

### Performance Optimization

#### Debounce API Calls

```typescript
import { debounce } from 'lodash';

const debouncedFetch = debounce(fetchData, 300);
```

#### Cache Responses

```typescript
// Simple cache implementation
class ApiCache {
  private cache = new Map<string, { data: any; timestamp: number }>();
  private ttl = 5000; // 5 seconds

  get(key: string) {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < this.ttl) {
      return cached.data;
    }
    return null;
  }

  set(key: string, data: any) {
    this.cache.set(key, { data, timestamp: Date.now() });
  }
}

const cache = new ApiCache();

async function fetchWithCache(endpoint: string) {
  const cached = cache.get(endpoint);
  if (cached) return cached;

  const response = await apiClient.get(endpoint);
  cache.set(endpoint, response.data);
  return response.data;
}
```

---

## Support & Resources

### Documentation
- **API Reference:** This document
- **Security Setup:** `/docs/security/SECURITY_SETUP.md`
- **Dashboard Deployment:** `/docs/DASHBOARD_DEPLOYMENT.md`
- **Test Scripts:** `/scripts/tests/README.md`

### Getting Help

1. Check system logs:
   ```bash
   sudo journalctl -u attendance-dashboard -n 50
   ```

2. Test endpoint manually:
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" http://192.168.1.22:8080/health
   ```

3. Run test suite:
   ```bash
   bash scripts/tests/test_endpoints.sh YOUR_API_KEY
   ```

### Contact

- **System Admin:** Check your `.env` file location
- **API Issues:** Monitor `sudo journalctl -u attendance-dashboard -f`
- **Repository:** https://github.com/Cerjho/IoT-Attendance-System

---

## Changelog

### Version 1.0.0 (2025-11-29)
- ✅ Initial API release
- ✅ Bearer token authentication
- ✅ IP whitelisting support
- ✅ 10 REST endpoints
- ✅ Prometheus metrics support
- ✅ Security headers implemented

### Planned Features
- [ ] WebSocket support for real-time updates
- [ ] Batch endpoints for bulk operations
- [ ] Export endpoints (CSV, PDF)
- [ ] Filtering and sorting parameters
- [ ] Pagination for large datasets
- [ ] GraphQL support

---

**Last Updated:** November 29, 2025  
**API Version:** 1.0.0  
**Status:** Production Ready ✅
