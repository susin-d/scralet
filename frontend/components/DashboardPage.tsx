import React, { useState, useCallback, useEffect } from 'react';
import { CameraState, LogEntry, SocketStatus, TrackedObject } from '../types';
import Header from './Header';
import CameraFeed from './CameraFeed';
import EventLog from './EventLog';

const INITIAL_CAMERAS: CameraState[] = [];

const DashboardPage: React.FC = () => {
  const [cameras, setCameras] = useState<CameraState[]>(INITIAL_CAMERAS);
  const [eventLog, setEventLog] = useState<LogEntry[]>([]);
  const [socketStatus, setSocketStatus] = useState<SocketStatus>('connecting');
  const [alerts, setAlerts] = useState<number>(0);

  // Fetch cameras from api-gateway
  useEffect(() => {
    const fetchCameras = async () => {
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
    };

    fetchCameras();
  }, []);

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
  }, []);

  return (
    <div className="flex flex-col h-screen max-h-screen p-4 space-y-4">
      <Header status={socketStatus} alertCount={alerts} />
      <main className={`flex-grow grid grid-cols-1 ${cameras.length > 1 ? 'md:grid-cols-2' : ''} gap-4 overflow-y-auto`}>
        {cameras.map(camera => (
          <CameraFeed key={camera.id} camera={camera} />
        ))}
      </main>
      <footer className="flex-shrink-0 h-48">
        <EventLog entries={eventLog} />
      </footer>
    </div>
  );
};

export default DashboardPage;