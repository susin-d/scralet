
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { OccupancyData } from '../../types';
import { MOCK_OCCUPANCY_DATA } from '../../constants';
import Card from '../Card';

const OccupancyChart: React.FC = () => {
  return (
    <Card title="Store Occupancy">
      <div style={{ width: '100%', height: 300 }}>
        <ResponsiveContainer>
          <LineChart
            data={MOCK_OCCUPANCY_DATA}
            margin={{
              top: 5,
              right: 20,
              left: -10,
              bottom: 5,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="time" tick={{ fill: '#6B7280' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#6B7280' }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                border: '1px solid #E5E7EB',
                borderRadius: '0.5rem',
              }}
            />
            <Legend />
            <Line type="monotone" dataKey="today" stroke="#1976D2" strokeWidth={2} name="Today" />
            <Line type="monotone" dataKey="lastWeek" stroke="#9CA3AF" strokeWidth={2} name="Last Week" strokeDasharray="5 5" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
};

export default OccupancyChart;
