
export interface TrackedObject {
  id: string; // This is the session ID for the current appearance
  personId?: string; // This is the persistent ID for the individual
  bbox: [number, number, number, number]; // [x, y, width, height] as %
  type: 'identified' | 'tracking';
  name?: string;
  confidence?: number;
  isLoyalMember?: boolean;
}

export interface CameraState {
  id: string;
  name: string;
  videoStreamUrl: string;
  trackedObjects: TrackedObject[];
}

export interface LogEntry {
  timestamp: string;
  message: string;
  camera: string;
}

export type SocketStatus = 'connected' | 'disconnected' | 'connecting';