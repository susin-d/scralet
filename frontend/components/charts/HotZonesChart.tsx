
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { HotZoneData } from '../../types';
import { MOCK_HOT_ZONE_DATA } from '../../constants';
import Card from '../Card';

const colors = ['#1976D2', '#2196F3', '#64B5F6', '#90CAF9', '#BBDEFB'];

const HotZonesChart: React.FC = () => {
  return (
    <Card title="Hot Zones by Traffic">
      <div style={{ width: '100%', height: 300 }}>
        <ResponsiveContainer>
          <BarChart
            layout="vertical"
            data={MOCK_HOT_ZONE_DATA}
            margin={{
              top: 5,
              right: 20,
              left: 20,
              bottom: 5,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" hide />
            <YAxis 
                dataKey="aisle" 
                type="category" 
                width={120} 
                tick={{ fill: '#6B7280', fontSize: 12 }} 
                axisLine={false} 
                tickLine={false}
            />
            <Tooltip
                cursor={{fill: 'rgba(243, 244, 246, 0.5)'}}
                contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.8)',
                    border: '1px solid #E5E7EB',
                    borderRadius: '0.5rem',
                }}
            />
            <Bar dataKey="traffic" barSize={20} radius={[0, 10, 10, 0]}>
              {MOCK_HOT_ZONE_DATA.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
};

export default HotZonesChart;
