

import React, { useState } from 'react';
import Card from '../Card';
import { MOCK_SALES_REP, MOCK_NOTIFICATIONS, MOCK_CUSTOMERS } from '../../constants';
import type { Notification, Customer } from '../../types';
import { BellIcon, UsersIcon } from '../Icons';

const StatCard: React.FC<{ title: string; value: string | number; icon: React.ReactNode }> = ({ title, value, icon }) => (
    <Card className="flex items-center space-x-4 p-4">
        <div className="p-3 bg-accent/20 rounded-lg text-accent">{icon}</div>
        <div>
            <p className="text-text-secondary text-sm font-medium">{title}</p>
            <p className="text-2xl font-bold text-text-primary">{value}</p>
        </div>
    </Card>
);

const KeyAccountItem: React.FC<{ customer: Customer }> = ({ customer }) => (
    <li className="py-3 flex items-center justify-between">
        <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-white font-bold text-xs">
                {customer.avatar}
            </div>
            <div>
                <p className="font-semibold text-sm text-text-primary">{customer.name}</p>
                <p className="text-xs text-text-secondary">{customer.loyaltyTier} Tier</p>
            </div>
        </div>
        <div className="text-right">
            <p className="text-xs text-text-secondary">Last Visit</p>
            <p className="font-medium text-sm text-text-primary">{customer.lastVisit}</p>
        </div>
    </li>
);

const SalesDashboard: React.FC = () => {
    const [notifications, setNotifications] = useState<Notification[]>(MOCK_NOTIFICATIONS);
    const keyAccounts = MOCK_CUSTOMERS.filter(c => c.loyaltyTier === 'Gold');
    
    const unreadCount = notifications.filter(n => !n.read).length;

    const markAsRead = (id: string) => {
        setNotifications(
            notifications.map(n => n.id === id ? { ...n, read: true } : n)
        );
    };

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-text-primary">Sales Dashboard</h1>
                <p className="text-text-secondary mt-1">Welcome back, {MOCK_SALES_REP.name}! Here's your real-time update.</p>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <StatCard title="Unread Alerts" value={unreadCount} icon={<BellIcon className="w-6 h-6"/>} />
                <StatCard title="Key Accounts to Watch" value={keyAccounts.length} icon={<UsersIcon className="w-6 h-6"/>} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                    <Card title="Real-Time Customer Activity" className="!p-0">
                         <ul className="divide-y divide-gray-700">
                            {notifications.map(notif => (
                                <li key={notif.id} className={`p-4 flex items-start space-x-4 transition-colors ${!notif.read ? 'bg-gray-800' : ''}`}>
                                    <div className="w-10 h-10 rounded-full bg-accent flex items-center justify-center text-white font-bold flex-shrink-0">
                                        {notif.customer.avatar}
                                    </div>
                                    <div className="flex-grow">
                                        <p className="text-sm">
                                            <span className="font-semibold text-text-primary">{notif.customer.name}</span> <span className="text-text-secondary">{notif.message}</span>
                                        </p>
                                        <span className="text-xs text-gray-500">{notif.timestamp}</span>
                                    </div>
                                    {!notif.read && (
                                        <button 
                                            onClick={() => markAsRead(notif.id)} 
                                            className="ml-auto text-xs font-semibold text-accent hover:text-white self-center px-3 py-1 rounded-full hover:bg-accent/50 transition-transform duration-200 ease-in-out hover:scale-105 active:scale-95"
                                            aria-label={`Mark notification for ${notif.customer.name} as read`}
                                        >
                                            Mark read
                                        </button>
                                    )}
                                </li>
                            ))}
                        </ul>
                    </Card>
                </div>
                <div>
                    <Card title="Key Accounts">
                        <ul className="divide-y divide-gray-700">
                            {keyAccounts.map(cust => (
                                <KeyAccountItem key={cust.id} customer={cust} />
                            ))}
                        </ul>
                    </Card>
                </div>
            </div>
        </div>
    );
};

export default SalesDashboard;