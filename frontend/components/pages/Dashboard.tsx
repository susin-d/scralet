

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

const RecentAlerts: React.FC = () => (
    <Card title="Recent Alerts" className="lg:col-span-2">
        <ul className="divide-y divide-gray-700">
            {MOCK_ALERTS.map(alert => (
                <li key={alert.id} className="py-3 flex justify-between items-center">
                    <div className="flex items-center">
                        <AlertTriangleIcon className={`w-5 h-5 mr-3 ${alert.severity === 'error' ? 'text-error' : 'text-warning'}`} />
                        <p className="font-semibold text-text-secondary">{alert.message}</p>
                    </div>
                    <span className="text-sm text-gray-400">{alert.timestamp}</span>
                </li>
            ))}
        </ul>
    </Card>
);


const Dashboard: React.FC = () => {
  return (
    <div className="space-y-6">
        <h1 className="text-3xl font-bold text-text-primary">Analytics</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <VitalsWidget title="Current Shopper Count" value="112" change="+5.2%" isPositive={true} />
            <VitalsWidget title="Avg. Dwell Time" value="12m 45s" change="-1.5%" isPositive={false} />
            <VitalsWidget title="Conversion Rate" value="28%" change="+2.1%" isPositive={true} />
            <VitalsWidget title="Alerts Today" value="8" change="+3" isPositive={false} />

            <div className="lg:col-span-2">
                <OccupancyChart />
            </div>

            <div className="lg:col-span-2">
                <HotZonesChart />
            </div>

            <RecentAlerts />
        </div>
    </div>
  );
};

export default Dashboard;