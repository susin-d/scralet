

import React, { useState, useEffect } from 'react';
import Card from '../Card';
import OccupancyChart from '../charts/OccupancyChart';
import HotZonesChart from '../charts/HotZonesChart';
import { MOCK_ALERTS } from '../../constants';
import { AlertTriangleIcon } from '../Icons';
import { dashboardApi } from '../../src/api/dashboard';
import { dashboardWebSocket } from '../../src/api/websocket';
import { DashboardStats, LogEntry } from '../../types';

const VitalsWidget: React.FC<{ title: string; value: string; change: string; isPositive: boolean }> = ({ title, value, change, isPositive }) => (
  <Card>
    <h3 className="text-text-secondary">{title}</h3>
    <p className="text-4xl font-bold text-text-primary mt-2">{value}</p>
    <p className={`mt-2 text-sm font-medium ${isPositive ? 'text-success' : 'text-error'}`}>
      {change} vs last week
    </p>
  </Card>
);

const RecentAlerts: React.FC<{ logs: LogEntry[] }> = ({ logs }) => (
    <Card title="Recent Logs" className="lg:col-span-2">
        <ul className="divide-y divide-gray-700">
            {logs.map(log => (
                <li key={log.id} className="py-3 flex justify-between items-center">
                    <div className="flex items-center">
                        <AlertTriangleIcon className={`w-5 h-5 mr-3 ${log.level === 'ERROR' ? 'text-error' : log.level === 'WARNING' ? 'text-warning' : 'text-info'}`} />
                        <p className="font-semibold text-text-secondary">{log.message}</p>
                    </div>
                    <span className="text-sm text-gray-400">{new Date(log.timestamp).toLocaleString()}</span>
                </li>
            ))}
        </ul>
    </Card>
);


const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [statsData, logsData] = await Promise.all([
          dashboardApi.getStats(),
          dashboardApi.getLogs(10)
        ]);
        setStats(statsData);
        setLogs(logsData);
      } catch (err: any) {
        console.error('Failed to fetch dashboard data:', err);
        setError('Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    // Connect to WebSocket for real-time updates
    dashboardWebSocket.connect();
    dashboardWebSocket.on('message', (data) => {
      if (data.type === 'stats_update' && data.data) {
        setStats(data.data);
      } else if (data.type === 'log_update' && data.data) {
        setLogs(prev => [data.data, ...prev.slice(0, 9)]);
      }
    });

    return () => {
      dashboardWebSocket.disconnect();
    };
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-text-primary">Analytics</h1>
        <div className="flex justify-center items-center h-64">
          <div className="text-text-secondary">Loading dashboard...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-text-primary">Analytics</h1>
        <div className="flex justify-center items-center h-64">
          <div className="text-error">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
        <h1 className="text-3xl font-bold text-text-primary">Analytics</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <VitalsWidget title="Total Users" value={stats?.total_users?.toString() || '0'} change="" isPositive={true} />
            <VitalsWidget title="Active Users" value={stats?.active_users?.toString() || '0'} change="" isPositive={true} />
            <VitalsWidget title="Total Logs" value={stats?.total_logs?.toString() || '0'} change="" isPositive={false} />
            <VitalsWidget title="WebSocket Clients" value={stats?.websocket_clients?.toString() || '0'} change="" isPositive={true} />

            <div className="lg:col-span-2">
                <OccupancyChart />
            </div>

            <div className="lg:col-span-2">
                <HotZonesChart />
            </div>

            <RecentAlerts logs={logs} />
        </div>
    </div>
  );
};

export default Dashboard;