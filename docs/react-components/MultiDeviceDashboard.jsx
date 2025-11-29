// Multi-Device Dashboard Components for React
// Complete UI for managing multiple IoT attendance devices

import React, { useState, useEffect } from 'react';
import axios from 'axios';

// ============================================================================
// API Client Setup
// ============================================================================

const createApiClient = (baseURL, apiKey) => {
  return axios.create({
    baseURL,
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    timeout: 10000,
  });
};

// ============================================================================
// Device List Component
// ============================================================================

export const DeviceList = ({ apiClient }) => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ status: '', building: '', floor: '' });

  useEffect(() => {
    loadDevices();
    const interval = setInterval(loadDevices, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [filter]);

  const loadDevices = async () => {
    try {
      const params = {};
      if (filter.status) params.status = filter.status;
      if (filter.building) params.building = filter.building;
      if (filter.floor) params.floor = filter.floor;

      const response = await apiClient.get('/devices', { params });
      setDevices(response.data.devices);
    } catch (error) {
      console.error('Failed to load devices:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const colors = {
      online: 'bg-green-500',
      offline: 'bg-red-500',
      error: 'bg-yellow-500',
    };
    return (
      <span className={`px-2 py-1 rounded text-white text-xs ${colors[status] || 'bg-gray-500'}`}>
        {status}
      </span>
    );
  };

  if (loading) return <div className="text-center">Loading devices...</div>;

  return (
    <div className="device-list">
      <div className="filters mb-4 flex gap-4">
        <select 
          value={filter.status}
          onChange={(e) => setFilter({...filter, status: e.target.value})}
          className="border rounded px-3 py-2"
        >
          <option value="">All Status</option>
          <option value="online">Online</option>
          <option value="offline">Offline</option>
          <option value="error">Error</option>
        </select>

        <select
          value={filter.building}
          onChange={(e) => setFilter({...filter, building: e.target.value})}
          className="border rounded px-3 py-2"
        >
          <option value="">All Buildings</option>
          {/* Populate from locations API */}
        </select>

        <button
          onClick={loadDevices}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
        >
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {devices.map((device) => (
          <DeviceCard key={device.device_id} device={device} apiClient={apiClient} />
        ))}
      </div>

      {devices.length === 0 && (
        <div className="text-center text-gray-500 py-8">
          No devices found. <a href="#discover" className="text-blue-500">Discover devices</a>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Device Card Component
// ============================================================================

const DeviceCard = ({ device, apiClient }) => {
  const [expanded, setExpanded] = useState(false);
  const [status, setStatus] = useState(null);

  const loadStatus = async () => {
    try {
      const response = await apiClient.get(`/devices/${device.device_id}/status`);
      setStatus(response.data);
    } catch (error) {
      console.error(`Failed to load status for ${device.device_id}:`, error);
    }
  };

  useEffect(() => {
    if (expanded) {
      loadStatus();
    }
  }, [expanded]);

  const timeSinceHeartbeat = (timestamp) => {
    if (!timestamp) return 'Never';
    const diff = Date.now() - new Date(timestamp).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    return `${Math.floor(minutes / 60)}h ago`;
  };

  return (
    <div className="border rounded-lg p-4 shadow hover:shadow-lg transition">
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="font-bold text-lg">{device.device_name}</h3>
          <p className="text-sm text-gray-600">{device.device_id}</p>
        </div>
        {getStatusBadge(device.status)}
      </div>

      <div className="text-sm space-y-1 text-gray-700">
        <p>📍 {device.location || `${device.building}/${device.floor}/${device.room}`}</p>
        <p>🌐 {device.ip_address}:{device.port || 8080}</p>
        <p>💓 {timeSinceHeartbeat(device.last_heartbeat)}</p>
        <p>📊 {device.total_scans || 0} scans</p>
      </div>

      <div className="mt-3 flex gap-2">
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-sm bg-gray-100 px-3 py-1 rounded hover:bg-gray-200"
        >
          {expanded ? 'Less' : 'More'}
        </button>
        <button
          onClick={loadStatus}
          className="text-sm bg-blue-100 px-3 py-1 rounded hover:bg-blue-200"
        >
          Refresh
        </button>
      </div>

      {expanded && status && (
        <div className="mt-3 p-3 bg-gray-50 rounded text-xs">
          <h4 className="font-semibold mb-2">Current Status:</h4>
          <pre className="whitespace-pre-wrap">
            {JSON.stringify(status.current_status, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

const getStatusBadge = (status) => {
  const colors = {
    online: 'bg-green-500',
    offline: 'bg-red-500',
    error: 'bg-yellow-500',
  };
  return (
    <span className={`px-2 py-1 rounded text-white text-xs ${colors[status] || 'bg-gray-500'}`}>
      {status}
    </span>
  );
};

// ============================================================================
// Fleet Overview Component
// ============================================================================

export const FleetOverview = ({ apiClient }) => {
  const [metrics, setMetrics] = useState(null);
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000); // Refresh every 15s
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [metricsRes, statusRes] = await Promise.all([
        apiClient.get('/devices/metrics'),
        apiClient.get('/devices/status'),
      ]);
      setMetrics(metricsRes.data);
      setSummary(statusRes.data.summary);
    } catch (error) {
      console.error('Failed to load fleet data:', error);
    }
  };

  if (!metrics || !summary) return <div>Loading fleet overview...</div>;

  return (
    <div className="fleet-overview grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <StatCard
        title="Total Devices"
        value={summary.total}
        icon="🖥️"
      />
      <StatCard
        title="Online"
        value={summary.online}
        icon="✅"
        color="text-green-600"
      />
      <StatCard
        title="Offline"
        value={summary.offline}
        icon="❌"
        color="text-red-600"
      />
      <StatCard
        title="Issues"
        value={metrics.devices_with_issues}
        icon="⚠️"
        color="text-yellow-600"
      />
      <StatCard
        title="Today's Scans"
        value={metrics.total_scans_today}
        icon="📸"
      />
      <StatCard
        title="Pending Queue"
        value={metrics.total_queue_pending}
        icon="📤"
      />
    </div>
  );
};

const StatCard = ({ title, value, icon, color = 'text-gray-700' }) => (
  <div className="bg-white border rounded-lg p-4 shadow">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-gray-600">{title}</p>
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
      </div>
      <div className="text-3xl">{icon}</div>
    </div>
  </div>
);

// ============================================================================
// Device Discovery Component
// ============================================================================

export const DeviceDiscovery = ({ apiClient }) => {
  const [network, setNetwork] = useState('192.168.1.0/24');
  const [discovering, setDiscovering] = useState(false);
  const [result, setResult] = useState(null);

  const startDiscovery = async () => {
    setDiscovering(true);
    setResult(null);

    try {
      const response = await apiClient.get('/devices/discover', {
        params: { network },
      });
      setResult(response.data);
    } catch (error) {
      setResult({
        error: error.message,
        discovered: 0,
        registered: 0,
      });
    } finally {
      setDiscovering(false);
    }
  };

  return (
    <div className="device-discovery bg-white border rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">Discover New Devices</h2>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Network Range</label>
        <input
          type="text"
          value={network}
          onChange={(e) => setNetwork(e.target.value)}
          placeholder="192.168.1.0/24"
          className="border rounded px-3 py-2 w-full"
        />
        <p className="text-xs text-gray-500 mt-1">
          CIDR notation (e.g., 192.168.1.0/24)
        </p>
      </div>

      <button
        onClick={startDiscovery}
        disabled={discovering}
        className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 disabled:bg-gray-400"
      >
        {discovering ? 'Scanning...' : 'Start Discovery'}
      </button>

      {result && (
        <div className="mt-4 p-4 bg-gray-50 rounded">
          {result.error ? (
            <div className="text-red-600">
              <strong>Error:</strong> {result.error}
            </div>
          ) : (
            <div>
              <p className="text-green-600 font-medium">
                ✓ Discovered {result.discovered} devices
              </p>
              <p className="text-blue-600">
                Registered {result.registered} new devices
              </p>

              {result.devices && result.devices.length > 0 && (
                <div className="mt-3">
                  <h4 className="font-medium mb-2">Found Devices:</h4>
                  <ul className="space-y-1 text-sm">
                    {result.devices.map((device, idx) => (
                      <li key={idx} className="flex justify-between">
                        <span>{device.device_name}</span>
                        <span className="text-gray-600">{device.ip_address}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Device Location Tree Component
// ============================================================================

export const DeviceLocationTree = ({ apiClient }) => {
  const [locations, setLocations] = useState({});
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    loadLocations();
  }, []);

  const loadLocations = async () => {
    try {
      const response = await apiClient.get('/locations');
      setLocations(response.data.locations);
    } catch (error) {
      console.error('Failed to load locations:', error);
    }
  };

  const toggleExpand = (key) => {
    setExpanded({ ...expanded, [key]: !expanded[key] });
  };

  return (
    <div className="location-tree bg-white border rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">Device Locations</h2>

      <div className="space-y-2">
        {Object.entries(locations).map(([building, floors]) => (
          <div key={building}>
            <div
              className="font-medium cursor-pointer hover:bg-gray-50 p-2 rounded flex items-center"
              onClick={() => toggleExpand(building)}
            >
              <span className="mr-2">{expanded[building] ? '📂' : '📁'}</span>
              {building}
              <span className="ml-auto text-gray-500 text-sm">
                {Object.values(floors).reduce((sum, rooms) =>
                  sum + Object.values(rooms).reduce((s, count) => s + count, 0), 0
                )} devices
              </span>
            </div>

            {expanded[building] && (
              <div className="ml-6 space-y-1">
                {Object.entries(floors).map(([floor, rooms]) => (
                  <div key={floor}>
                    <div
                      className="cursor-pointer hover:bg-gray-50 p-1 rounded flex items-center text-sm"
                      onClick={() => toggleExpand(`${building}/${floor}`)}
                    >
                      <span className="mr-2">{expanded[`${building}/${floor}`] ? '▼' : '▶'}</span>
                      {floor}
                    </div>

                    {expanded[`${building}/${floor}`] && (
                      <div className="ml-6 space-y-1 text-sm text-gray-700">
                        {Object.entries(rooms).map(([room, count]) => (
                          <div key={room} className="flex justify-between">
                            <span>🚪 {room}</span>
                            <span className="text-gray-500">{count}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// Main Multi-Device Dashboard Component
// ============================================================================

export const MultiDeviceDashboard = ({ baseURL, apiKey }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const apiClient = createApiClient(baseURL, apiKey);

  return (
    <div className="multi-device-dashboard p-6 bg-gray-100 min-h-screen">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800">
          IoT Attendance System - Fleet Management
        </h1>
        <p className="text-gray-600">Manage multiple attendance devices from one dashboard</p>
      </header>

      <nav className="flex gap-2 mb-6 border-b">
        {['overview', 'devices', 'discover', 'locations'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-medium capitalize ${
              activeTab === tab
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            {tab}
          </button>
        ))}
      </nav>

      <main>
        {activeTab === 'overview' && (
          <>
            <FleetOverview apiClient={apiClient} />
            <DeviceList apiClient={apiClient} />
          </>
        )}

        {activeTab === 'devices' && <DeviceList apiClient={apiClient} />}

        {activeTab === 'discover' && <DeviceDiscovery apiClient={apiClient} />}

        {activeTab === 'locations' && <DeviceLocationTree apiClient={apiClient} />}
      </main>
    </div>
  );
};

// ============================================================================
// Usage Example
// ============================================================================

/*
import { MultiDeviceDashboard } from './MultiDeviceDashboard';

function App() {
  return (
    <MultiDeviceDashboard
      baseURL="http://192.168.1.22:8080"
      apiKey="your-api-key-here"
    />
  );
}
*/
