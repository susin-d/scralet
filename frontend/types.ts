// FIX: Define TypeScript interfaces for the application's data models.
// This file's missing content caused module resolution errors across the application.
// These types ensure data consistency and enable type checking.

export interface OccupancyData {
  time: string;
  today: number;
  lastWeek: number;
}

export interface HotZoneData {
  aisle: string;
  traffic: number;
}

export interface Alert {
  id: string;
  message: string;
  severity: 'warning' | 'error' | 'info';
  timestamp: string;
}

export interface Camera {
  id:string;
  name: string;
  location: string;
  status: 'Online' | 'Offline';
  isLive: boolean;
  deviceId: string;
}

export interface Customer {
  id: string;
  avatar: string;
  name: string;
  email: string;
  loyaltyTier: 'Gold' | 'Silver' | 'Bronze' | 'Green';
  lastVisit: string;
  registrationPhoto: string;
}

export type UserRole = 'admin' | 'sales' | 'customer';

export interface Notification {
    id: string;
    message: string;
    customer: Customer;
    timestamp: string;
    read: boolean;
}

export interface Recommendation {
    productName: string;
    description: string;
    image: string;
}

export interface TrackedObject {
  id: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
  customerId: string | null;
  name: string | null;
  loyaltyTier: Customer['loyaltyTier'] | null;
}

// API Response Types
export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: {
    username: string;
    full_name: string;
    email: string;
    is_active: boolean;
    created_at: string;
  };
}

export interface ApiCamera {
  id: string;
  name: string;
  status: string;
  last_seen: string;
  location: string;
}

export interface ApiTrackedObject {
  object_id: string;
  camera_id: string;
  bbox: [number, number, number, number];
  confidence: number;
  object_type: string;
  last_seen: string;
  user_id: string | null;
  identification_confidence: number | null;
}

export interface ApiCustomer {
  id: string;
  name: string;
  email: string;
  loyalty_status: 'bronze' | 'silver' | 'gold' | 'green';
  created_at: string;
}

export interface DashboardStats {
  total_users: number;
  active_users: number;
  total_logs: number;
  websocket_clients: number;
  server_status: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: string;
  message: string;
  source: string;
}

export interface AlertsCount {
  count: number;
}

export interface FaceRecognitionResult {
  tracked_objects: Array<{
    id: string;
    name: string;
    confidence: number;
    loyalty_status: string;
  }>;
}

export interface ProcessFrameResponse {
  camera_id: string;
  timestamp: string;
  detections: Array<{
    bbox: [number, number, number, number];
    user_id: string | null;
    confidence: number | null;
    name: string | null;
    loyalty_status: string | null;
    object_id: string;
  }>;
}