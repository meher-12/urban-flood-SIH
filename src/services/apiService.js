/**
 * API & WebSocket Service Abstraction Wrapper
 * Hand-off interface for Backend Integration
 */

const CONFIG = {
  USE_MOCK: true, // Flip to FALSE when backend endpoints are live
  BASE_URL: 'https://api.yourcityflood.org/v1',
  WS_URL: 'wss://api.yourcityflood.org/ws/telemetry'
};

class ApiService {
  constructor() {
    this.ws = null;
    this.eventListeners = {};
  }

  // Helper to simulate network latency during frontend testing
  async _mockDelay(data, ms = 300) {
    return new Promise((resolve) => setTimeout(() => resolve(data), ms));
  }

  // 1. FETCH LIVE SENSOR TELEMETRY & ROAD STATES
  async getLiveTelemetry() {
    if (CONFIG.USE_MOCK) {
      // In development, import or fetch the mock JSON file
      const response = await fetch('./data/mockData.json');
      const mockData = await response.json();
      return this._mockDelay(mockData);
    }

    const response = await fetch(`${CONFIG.BASE_URL}/telemetry/live`);
    if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
    return await response.json();
  }

  // 2. SUBMIT A NEW INCIDENT REPORT
  async submitIncident(incidentPayload) {
    /*
      Expected Payload:
      {
        type: string,
        severity: "Low" | "Medium" | "Critical",
        lat: number,
        lng: number,
        notes: string
      }
    */
    if (CONFIG.USE_MOCK) {
      console.log('[MOCK POST] Submitting Incident:', incidentPayload);
      return this._mockDelay({
        success: true,
        incidentId: `INC-${Math.floor(1000 + Math.random() * 9000)}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        ...incidentPayload
      });
    }

    const response = await fetch(`${CONFIG.BASE_URL}/incidents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(incidentPayload)
    });
    return await response.json();
  }

  // 3. RECALCULATE EMERGENCY DETOUR ROUTE
  async calculateDetour(rainIntensity, drainCapacity) {
    if (CONFIG.USE_MOCK) {
      const isCritical = rainIntensity > 70 && drainCapacity < 50;
      return this._mockDelay({
        primaryRoutePassable: !isCritical,
        primaryDepthMeters: (rainIntensity * 0.012).toFixed(2),
        detourRecommended: isCritical,
        detourDeltaKm: 1.8,
        detourDeltaMins: 4
      });
    }

    const response = await fetch(`${CONFIG.BASE_URL}/routes/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rainIntensity, drainCapacity })
    });
    return await response.json();
  }

  // 4. RESOLVE INCIDENT
  async resolveIncident(incidentId) {
    if (CONFIG.USE_MOCK) {
      console.log(`[MOCK DELETE] Resolving Incident ${incidentId}`);
      return this._mockDelay({ success: true, incidentId });
    }

    const response = await fetch(`${CONFIG.BASE_URL}/incidents/${incidentId}`, {
      method: 'DELETE'
    });
    return await response.json();
  }

  // 5. WEBSOCKET REAL-TIME ENGINE
  initWebSocket(onMessageCallback, onErrorCallback) {
    if (CONFIG.USE_MOCK) {
      console.log('[MOCK WS]: Simulated WebSocket connection initialized.');
      // Simulate periodic sensor push every 10 seconds
      setInterval(() => {
        const mockPush = {
          event: 'SENSOR_UPDATE',
          sensorId: 'SENSOR-01',
          newWaterLevel: (Math.random() * 1.2).toFixed(2),
          timestamp: new Date().toLocaleTimeString()
        };
        if (onMessageCallback) onMessageCallback(mockPush);
      }, 10000);
      return;
    }

    // Production WebSocket Setup
    this.ws = new WebSocket(CONFIG.WS_URL);

    this.ws.onopen = () => console.log('[WS Connected]');
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (onMessageCallback) onMessageCallback(data);
    };
    this.ws.onerror = (err) => {
      if (onErrorCallback) onErrorCallback(err);
    };
    this.ws.onclose = () => {
      console.log('[WS Closed] Attempting reconnect in 5s...');
      setTimeout(() => this.initWebSocket(onMessageCallback, onErrorCallback), 5000);
    };
  }
}

// Export singleton instance
const apiService = new ApiService();
export default apiService;