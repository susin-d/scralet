import React, { useState, useEffect, useRef } from 'react';
import Card from '../Card';
import { MOCK_CUSTOMERS, MOCK_ALERTS } from '../../constants';
import type { Camera, Customer, Alert } from '../../types';
import { AlertTriangleIcon } from '../Icons';

const LOYALTY_COLORS: { [key in Customer['loyaltyTier']]: string } = {
    Gold: '#FFD700',
    Silver: '#C0C0C0',
    Bronze: '#CD7F32',
    Green: '#4CAF50',
};

const CustomerInfoPanel: React.FC<{ customer: Customer | null }> = ({ customer }) => {
    if (!customer) {
        return (
            <Card className="bg-gray-700 border border-gray-600 sticky top-6">
                <div className="text-center text-text-secondary py-20">
                    <p>Select a recognized customer from alerts to view their details.</p>
                </div>
            </Card>
        )
    }
    return (
        <Card title="Customer Info" className="bg-gray-700 border border-gray-600 sticky top-6">
            <div className="flex items-center space-x-4">
                <img src={customer.registrationPhoto} alt={customer.name} className="w-20 h-20 rounded-full object-cover ring-2" style={{ borderColor: LOYALTY_COLORS[customer.loyaltyTier] }} />
                <div>
                    <h3 className="text-xl font-bold text-text-primary">{customer.name}</h3>
                    <p className="text-sm text-text-secondary">{customer.id}</p>
                    <p className="text-sm font-semibold" style={{ color: LOYALTY_COLORS[customer.loyaltyTier] }}>{customer.loyaltyTier}</p>
                </div>
            </div>

            <div className="mt-6">
                <h4 className="font-semibold text-text-primary mb-3">Visit history</h4>
                <div className="relative pl-4">
                    <div className="absolute left-[1.35rem] top-2 bottom-2 w-0.5 bg-gray-600"></div>
                    <div className="relative mb-4">
                        <div className="absolute left-6 -translate-x-1/2 top-1.5 w-3 h-3 bg-gray-500 rounded-full border-2 border-gray-700"></div>
                        <div className="ml-6">
                            <p className="font-semibold text-sm text-text-secondary">Main Branch</p>
                            <p className="text-xs text-gray-400">Oct 22, 2025, 10:45 AM</p>
                        </div>
                    </div>
                     <div className="relative">
                        <div className="absolute left-6 -translate-x-1/2 top-1.5 w-3 h-3 bg-gray-500 rounded-full border-2 border-gray-700"></div>
                        <div className="ml-6">
                            <p className="font-semibold text-sm text-text-secondary">Airport Outlet</p>
                            <p className="text-xs text-gray-400">Oct 24, 2025, 00:30 AM</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div className="mt-6">
                <h4 className="font-semibold text-text-primary mb-3">Recommended products</h4>
                <div className="flex space-x-3">
                    <div className="text-center">
                        <div className="w-20 h-20 rounded-md bg-gray-600 flex items-center justify-center"><img src="https://picsum.photos/seed/prod123/100/100" className="rounded-md"/></div>
                        <p className="text-xs mt-1 text-text-secondary">Product 123</p>
                    </div>
                     <div className="text-center">
                        <div className="w-20 h-20 rounded-md bg-gray-600 flex items-center justify-center"><img src="https://picsum.photos/seed/prod456/100/100" className="rounded-md"/></div>
                        <p className="text-xs mt-1 text-text-secondary">Product 456</p>
                    </div>
                </div>
            </div>

            <div className="mt-8 space-y-3">
                <button className="w-full py-2 bg-accent text-white font-semibold rounded-lg hover:opacity-90 transition-transform duration-200 ease-in-out hover:scale-105 active:scale-95">Send Promotion</button>
                <button className="w-full py-2 bg-gray-600 text-text-primary font-semibold rounded-lg hover:bg-gray-500 transition-transform duration-200 ease-in-out hover:scale-105 active:scale-95">Mark Assistance</button>
            </div>
        </Card>
    );
};

const CameraCardComponent: React.FC<{
    camera: Camera,
}> = ({ camera }) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);

    useEffect(() => {
        if (camera.isLive) {
            const getStream = async () => {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({
                        video: { deviceId: camera.deviceId ? { exact: camera.deviceId } : undefined }
                    });
                    streamRef.current = stream;
                    if (videoRef.current) {
                        videoRef.current.srcObject = stream;
                    }
                } catch (err) {
                    console.error("Error getting stream for device:", camera.deviceId, err);
                }
            };
            getStream();
        }

        return () => {
            if (streamRef.current) {
                streamRef.current.getTracks().forEach(track => track.stop());
            }
        };
    }, [camera.isLive, camera.deviceId]);

    const handleSnapshot = () => {
        if (videoRef.current) {
            const canvas = document.createElement('canvas');
            canvas.width = videoRef.current.videoWidth;
            canvas.height = videoRef.current.videoHeight;
            const ctx = canvas.getContext('2d');
            if (ctx) {
                ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
                const dataUrl = canvas.toDataURL('image/png');
                const a = document.createElement('a');
                a.href = dataUrl;
                a.download = `${camera.name.replace(/\s/g, '_')}_snapshot.png`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }
        }
    };


    return (
        <Card className="!p-4 bg-gray-700 border border-gray-600">
            <div className="flex justify-between items-center mb-2">
                <h3 className="font-semibold text-text-primary">{camera.name}</h3>
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${camera.status === 'Online' ? 'text-success bg-success/20' : 'text-error bg-error/20'}`}>
                    {camera.status.toLowerCase()}
                </span>
            </div>
            <div className="relative aspect-video rounded-md overflow-hidden bg-black">
                <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
            </div>
            <div className="flex justify-between mt-4">
                <button 
                    onClick={handleSnapshot}
                    className="w-full text-sm bg-gray-600 hover:bg-gray-500 text-text-primary px-4 py-2 rounded-md transition-transform duration-200 ease-in-out hover:scale-105 active:scale-95">
                    Snapshot
                </button>
            </div>
        </Card>
    );
};

const AlertsPanel: React.FC<{ alerts: Alert[] }> = ({ alerts }) => (
    <Card title="Alerts" className="bg-gray-700 border border-gray-600">
        <div className="space-y-3">
            {alerts.map(alert => (
                <div key={alert.id} className="flex items-center p-3 bg-gray-800 rounded-md">
                    <AlertTriangleIcon className={`w-5 h-5 mr-3 flex-shrink-0 ${alert.severity === 'error' ? 'text-error' : 'text-warning'}`} />
                    <p className="text-sm text-text-secondary">{alert.message}</p>
                    <span className="text-xs text-gray-500 ml-auto flex-shrink-0">{alert.timestamp}</span>
                </div>
            ))}
        </div>
    </Card>
);

const CameraView: React.FC = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);

  useEffect(() => {
    const setupLiveCameras = async () => {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
            console.warn("Media devices API not available.");
            return;
        }
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        stream.getTracks().forEach(track => track.stop());

        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(device => device.kind === 'videoinput');

        if (videoDevices.length === 0) {
            // Handle case with no cameras
            return;
        }

        const liveCameras: Camera[] = videoDevices.map((device, index) => ({
          id: `live-${device.deviceId || index}`,
          name: device.label || `Live Camera ${index + 1}`,
          location: 'Local Device',
          status: 'Online',
          isLive: true,
          deviceId: device.deviceId,
        }));
        
        setCameras(liveCameras);

      } catch (err) {
        console.error("Could not access camera: ", err);
        // Optionally, inform the user that camera access was denied.
      }
    };

    setupLiveCameras();
  }, []);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
             {cameras.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {cameras.map(cam => (
                        <CameraCardComponent key={cam.id} camera={cam} />
                    ))}
                </div>
            ) : (
                <Card>
                    <div className="text-center text-text-secondary py-20">
                        <p>No cameras found or permission denied.</p>
                        <p className="text-sm mt-2">Please ensure you have a camera connected and have granted permission to access it.</p>
                    </div>
                </Card>
            )}
            <AlertsPanel alerts={MOCK_ALERTS} />
        </div>
        <div className="lg:col-span-1">
            <CustomerInfoPanel customer={selectedCustomer} />
        </div>
    </div>
  );
};

export default CameraView;