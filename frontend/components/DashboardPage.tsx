import React, { useState, useCallback, useEffect } from 'react';
import { CameraState, LogEntry, SocketStatus, TrackedObject } from '../types';
import Header from './Header';
import CameraFeed from './CameraFeed';
import EventLog from './EventLog';

// Admin Control Panel Component
const AdminControlPanel: React.FC<{
  onRefreshCameras: () => void;
  onToggleMonitoring: () => void;
  monitoringEnabled: boolean;
  socketStatus: SocketStatus;
  alertCount: number;
}> = ({ onRefreshCameras, onToggleMonitoring, monitoringEnabled, socketStatus, alertCount }) => {
  return (
    <div className="bg-gray-800 p-4 rounded-lg shadow-md mb-4">
      <h2 className="text-white text-lg font-bold mb-2">Admin Controls</h2>
      <div className="flex flex-wrap gap-4 items-center">
        <button
          onClick={onRefreshCameras}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors"
        >
          Refresh Feeds
        </button>
        <button
          onClick={onToggleMonitoring}
          className={`px-4 py-2 rounded transition-colors ${
            monitoringEnabled
              ? 'bg-red-600 hover:bg-red-700 text-white'
              : 'bg-green-600 hover:bg-green-700 text-white'
          }`}
        >
          {monitoringEnabled ? 'Disable Monitoring' : 'Enable Monitoring'}
        </button>
        <div className="text-white">
          <span className="font-semibold">Status:</span> {socketStatus}
        </div>
        <div className="text-white">
          <span className="font-semibold">Alerts:</span> {alertCount}
        </div>
      </div>
    </div>
  );
};

const INITIAL_CAMERAS: CameraState[] = [];

interface DashboardPageProps {
  onLogout: () => void;
}

const DashboardPage: React.FC<DashboardPageProps> = ({ onLogout }) => {
  const [cameras, setCameras] = useState<CameraState[]>(INITIAL_CAMERAS);
  const [eventLog, setEventLog] = useState<LogEntry[]>([]);
  const [socketStatus, setSocketStatus] = useState<SocketStatus>('connecting');
  const [alerts, setAlerts] = useState<number>(0);
  const [monitoringEnabled, setMonitoringEnabled] = useState<boolean>(true);

  // Fetch cameras from api-gateway
  const fetchCameras = useCallback(async () => {
    try {
      const response = await fetch('http://api-gateway:8000/cameras');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const camerasData = await response.json();
      setCameras(camerasData.map((cam: any) => ({
        id: cam.id,
        name: cam.name,
        videoStreamUrl: `http://edge-processor:8000/cameras/${cam.id}/stream`,
        trackedObjects: []
      })));
    } catch (error) {
      console.error('Failed to fetch cameras:', error);
      setSocketStatus('disconnected');
    }
  }, []);

  useEffect(() => {
    fetchCameras();
  }, [fetchCameras]);

  // Fetch alerts count
  useEffect(() => {
    const fetchAlertsCount = async () => {
      try {
        const response = await fetch('http://api-gateway:8000/alerts/count');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setAlerts(data.count);
      } catch (error) {
        console.error('Failed to fetch alerts count:', error);
      }
    };

    fetchAlertsCount();
    const interval = setInterval(fetchAlertsCount, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // WebSocket connection to api-gateway
  useEffect(() => {
    if (!monitoringEnabled) return;

    const ws = new WebSocket('ws://api-gateway:8000/ws/dashboard');

    ws.onopen = () => {
      setSocketStatus('connected');
      console.log('Connected to api-gateway WebSocket');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'new_log') {
          const logEntry: LogEntry = {
            timestamp: data.data.timestamp,
            camera: data.data.camera,
            message: data.data.message
          };
          setEventLog(prevLog => {
            const newLog = [logEntry, ...prevLog];
            return newLog.length > 100 ? newLog.slice(0, 100) : newLog;
          });
          if (data.data.message.toLowerCase().includes('identified')) {
            setAlerts(prev => prev + 1);
          }
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setSocketStatus('disconnected');
    };

    ws.onclose = () => {
      setSocketStatus('disconnected');
      console.log('Disconnected from api-gateway WebSocket');
    };

    return () => {
      ws.close();
    };
  }, [monitoringEnabled]);

  const handleToggleMonitoring = useCallback(() => {
    setMonitoringEnabled(prev => !prev);
    if (monitoringEnabled) {
      setSocketStatus('disconnected');
    } else {
      setSocketStatus('connecting');
    }
  }, [monitoringEnabled]);

  return (
    <div className="flex flex-col h-screen max-h-screen p-4 space-y-4 bg-gray-900">
      <Header status={socketStatus} alertCount={alerts} onLogout={onLogout} />
      <AdminControlPanel
        onRefreshCameras={fetchCameras}
        onToggleMonitoring={handleToggleMonitoring}
        monitoringEnabled={monitoringEnabled}
        socketStatus={socketStatus}
        alertCount={alerts}
      />
      <main className={`flex-grow grid gap-4 overflow-y-auto p-2 ${
        cameras.length === 1 ? 'grid-cols-1' :
        cameras.length === 2 ? 'grid-cols-1 md:grid-cols-2' :
        'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
      }`}>
        {cameras.map(camera => (
          <CameraFeed key={camera.id} camera={camera} isAdmin={true} />
        ))}
      </main>
      <footer className="flex-shrink-0 h-48 bg-gray-800 rounded-lg shadow-md">
        <EventLog entries={eventLog} />
      </footer>
    </div>
  );
};

export default DashboardPage;