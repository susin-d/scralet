import type { OccupancyData, HotZoneData, Alert, Customer, Notification } from './types';

export const MOCK_OCCUPANCY_DATA: OccupancyData[] = [
  { time: '9am', today: 25, lastWeek: 22 },
  { time: '10am', today: 45, lastWeek: 35 },
  { time: '11am', today: 60, lastWeek: 55 },
  { time: '12pm', today: 85, lastWeek: 75 },
  { time: '1pm', today: 90, lastWeek: 88 },
  { time: '2pm', today: 75, lastWeek: 80 },
  { time: '3pm', today: 95, lastWeek: 92 },
  { time: '4pm', today: 110, lastWeek: 105 },
  { time: '5pm', today: 100, lastWeek: 98 },
];

export const MOCK_HOT_ZONE_DATA: HotZoneData[] = [
    { aisle: 'Aisle 1: Produce', traffic: 95 },
    { aisle: 'Aisle 7: Dairy', traffic: 88 },
    { aisle: 'Aisle 4: Snacks', traffic: 76 },
    { aisle: 'Aisle 12: Bakery', traffic: 65 },
    { aisle: 'Aisle 9: Frozen', traffic: 52 },
];

export const MOCK_ALERTS: Alert[] = [
    { id: '1', message: 'VIP Customer Detected: Alice in Entrance', severity: 'warning', timestamp: '1m ago' },
    { id: '2', message: 'Aisle 5 camera offline', severity: 'error', timestamp: '5m ago' },
];

export const MOCK_CUSTOMERS: Customer[] = [
    { id: 'cust123', avatar: 'A', name: 'Alice', email: 'alice@example.com', loyaltyTier: 'Gold', lastVisit: '2025-10-22', registrationPhoto: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=400&auto=format&fit=crop' },
    { id: 'cust2', avatar: 'B', name: 'Bob', email: 'bob@example.com', loyaltyTier: 'Green', lastVisit: '2025-10-21', registrationPhoto: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?q=80&w=400&auto=format&fit=crop' },
    { id: 'cust3', avatar: 'JD', name: 'Jane Doe', email: 'jane.doe@example.com', loyaltyTier: 'Silver', lastVisit: '2024-07-20', registrationPhoto: 'https://picsum.photos/seed/jane/400/400' },
    { id: 'cust4', avatar: 'BB', name: 'Bob Brown', email: 'bob.brown@example.com', loyaltyTier: 'Bronze', lastVisit: '2024-07-18', registrationPhoto: 'https://picsum.photos/seed/bob/400/400' },
    { id: 'cust5', avatar: 'CW', name: 'Charlie Wilson', email: 'charlie.w@example.com', loyaltyTier: 'Silver', lastVisit: '2024-07-19', registrationPhoto: 'https://picsum.photos/seed/charlie/400/400' },
];

export const MOCK_LOGGED_IN_CUSTOMER: Customer = MOCK_CUSTOMERS[0]; // Alice
export const MOCK_SALES_REP = { name: 'Alex Ray', title: 'Sales Rep', avatar: 'AR' };


export const MOCK_NOTIFICATIONS: Notification[] = [
    { id: 'notif1', message: 'Entered the electronics section.', customer: MOCK_CUSTOMERS[3], timestamp: 'Just now', read: false },
    { id: 'notif2', message: 'Is browsing high-margin items in Aisle 4.', customer: MOCK_CUSTOMERS[0], timestamp: '2 min ago', read: false },
    { id: 'notif3', message: 'Has re-entered the store after a brief exit.', customer: MOCK_CUSTOMERS[1], timestamp: '15 min ago', read: true },
];