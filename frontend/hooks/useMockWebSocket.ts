import { useEffect } from 'react';
import { CameraState, LogEntry, SocketStatus, TrackedObject } from '../types';

interface MockWebSocketProps {
    cameras: CameraState[];
    onTrackingUpdate: (update: { cameraId: string; objects: TrackedObject[] }) => void;
    onLogEntry: (entry: Omit<LogEntry, 'timestamp'>) => void;
    onStatusChange: (status: SocketStatus) => void;
}

const UPDATE_INTERVAL = 1000; // ms

// These act as a persistent "database" for the simulation's memory.
let personCounter = 0;

interface KnownPerson {
    personId: string;
    name: string; // This will now be the same as personId
    isLoyalMember: boolean;
}
let knownPeople: KnownPerson[] = [];


const useMockWebSocket = ({ cameras, onTrackingUpdate, onLogEntry, onStatusChange }: MockWebSocketProps) => {

    useEffect(() => {
        const liveObjects: { [key: string]: TrackedObject[] } = {};
        cameras.forEach(cam => liveObjects[cam.id] = []);

        const connectTimeout = setTimeout(() => {
            onStatusChange('connected');
            onLogEntry({ camera: 'SYSTEM', message: 'WebSocket connection established.' });
        }, 1500);

        const interval = setInterval(() => {
            const camToUpdate = cameras[Math.floor(Math.random() * cameras.length)];
            const currentObjects = liveObjects[camToUpdate.id];

            // Move existing objects
            currentObjects.forEach(obj => {
                obj.bbox[0] += (Math.random() - 0.5) * 1.5; // move x
                obj.bbox[1] += (Math.random() - 0.5) * 1.0; // move y
                // Clamp position
                obj.bbox[0] = Math.max(0, Math.min(100 - obj.bbox[2], obj.bbox[0]));
                obj.bbox[1] = Math.max(0, Math.min(100 - obj.bbox[3], obj.bbox[1]));
            });

            // Small chance to remove an object
            if (currentObjects.length > 0 && Math.random() < 0.05) {
                const removedObj = currentObjects.shift();
                if(removedObj){
                    const message = removedObj.type === 'identified' ? `${removedObj.name} left the view.` : `Human left the view.`;
                    onLogEntry({ camera: camToUpdate.id, message });
                }
            }
            
            // Chance for a tracking object to become identified OR add a new one
            const trackingObjects = currentObjects.filter(o => o.type === 'tracking');
            if (trackingObjects.length > 0 && Math.random() < 0.15) {
                const objToIdentify = trackingObjects[Math.floor(Math.random() * trackingObjects.length)];
                
                // Decide if it's a known person or a new one to "learn"
                const isKnownPerson = knownPeople.length > 0 && Math.random() < 0.7;

                if (isKnownPerson) {
                    // Recognize a returning person
                    const knownPerson = knownPeople[Math.floor(Math.random() * knownPeople.length)];
                    objToIdentify.type = 'identified';
                    objToIdentify.name = knownPerson.name;
                    objToIdentify.personId = knownPerson.personId;
                    objToIdentify.isLoyalMember = knownPerson.isLoyalMember;
                    objToIdentify.confidence = 97 + Math.random() * 2; // Higher confidence for known people
                    
                    onLogEntry({ 
                        camera: camToUpdate.id, 
                        message: `Recognized returning customer: ${objToIdentify.name}.`
                    });
                } else {
                    // Identify and "remember" a new person
                    personCounter++;
                    const newId = `User-${String(personCounter).padStart(3, '0')}`;
                    const newPerson: KnownPerson = {
                        personId: newId,
                        name: newId,
                        isLoyalMember: Math.random() > 0.5,
                    };
                    knownPeople.push(newPerson);

                    objToIdentify.type = 'identified';
                    objToIdentify.name = newPerson.name;
                    objToIdentify.personId = newPerson.personId;
                    objToIdentify.isLoyalMember = newPerson.isLoyalMember;
                    objToIdentify.confidence = 94 + Math.random() * 3;

                    onLogEntry({ 
                        camera: camToUpdate.id, 
                        message: `New user identified: ${objToIdentify.name}. Facial vector saved.`
                    });
                }
            } else if (currentObjects.length < 5 && Math.random() < 0.1) {
                // Small chance to add a new object if we didn't identify one
                const newId = `sess_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
                const newObj: TrackedObject = {
                    id: newId,
                    type: 'tracking',
                    bbox: [
                        Math.random() * 70, // x
                        Math.random() * 60, // y
                        15 + Math.random() * 10, // width
                        30 + Math.random() * 15  // height
                    ]
                };
                currentObjects.push(newObj);
                onLogEntry({ camera: camToUpdate.id, message: `Human detected.` });
            }

            onTrackingUpdate({ cameraId: camToUpdate.id, objects: [...currentObjects] });

        }, UPDATE_INTERVAL);
        
        // Simulate disconnect/reconnect
        const disconnectTimeout = setInterval(() => {
            onStatusChange('disconnected');
            onLogEntry({ camera: 'SYSTEM', message: 'Connection lost. Reconnecting...' });
            setTimeout(() => {
                onStatusChange('connected');
                onLogEntry({ camera: 'SYSTEM', message: 'Reconnected successfully.' });
            }, 3000);
        }, 60000);

        return () => {
            clearTimeout(connectTimeout);
            clearInterval(interval);
            clearInterval(disconnectTimeout);
            // Reset state for hot-reloading in dev environments
            knownPeople = [];
            personCounter = 0;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // Run only once on mount
};

export default useMockWebSocket;