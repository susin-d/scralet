
import React, { useState, useRef, useEffect } from 'react';
import { CameraState, TrackedObject } from '../types';
import OverlayBox from './OverlayBox';

interface CameraFeedProps {
  camera: CameraState;
}

// SVG Icons for controls
const PlayIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
        <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 8.582l4.305 2.668a1 1 0 010 1.732l-4.305 2.668A1 1 0 018 14.782V9.218a1 1 0 011.555-.836z" />
    </svg>
);
const PauseIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h1a1 1 0 001-1V8a1 1 0 00-1-1H8zm4 0a1 1 0 00-1 1v4a1 1 0 001 1h1a1 1 0 001-1V8a1 1 0 00-1-1h-1z" clipRule="evenodd" />
    </svg>
);
const VolumeUpIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
    </svg>
);
const VolumeOffIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M17 14l-4-4m0 4l4-4" />
    </svg>
);

const CameraFeed: React.FC<CameraFeedProps> = ({ camera }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [volume, setVolume] = useState(0.5);
  const [isMuted, setIsMuted] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isHovered, setIsHovered] = useState(false);
  const [trackedObjects, setTrackedObjects] = useState<TrackedObject[]>(camera.trackedObjects || []);

  useEffect(() => {
    const setupCameraStream = async () => {
      try {
        // Use real camera stream from edge-processor
        const streamUrl = `http://edge-processor:8000/cameras/${camera.id}/stream`;
        if (videoRef.current) {
          videoRef.current.src = streamUrl;
          videoRef.current.load();
        }
      } catch (err) {
        setError("Could not load camera stream from edge-processor.");
        console.error(err);
      }
    };

    setupCameraStream();

    // Fetch initial tracking data
    fetchTrackingData();

    return () => {
      if (videoRef.current) {
        videoRef.current.src = '';
      }
    };
  }, [camera.id]);

  const fetchTrackingData = async () => {
    try {
      const response = await fetch(`http://edge-processor:8000/cameras/${camera.id}/tracking`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setTrackedObjects(data.tracked_objects || []);
    } catch (err) {
      console.error('Failed to fetch tracking data:', err);
      setError("Could not fetch tracking data from edge-processor.");
    }
  };


  // Set up WebSocket for real-time tracking updates
  useEffect(() => {
    const ws = new WebSocket('ws://edge-processor:8000/ws/tracking');

    ws.onopen = () => {
      console.log('Connected to edge-processor WebSocket for tracking');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'tracking_update' && data.camera_id === camera.id) {
          setTrackedObjects(data.objects || []);
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('Disconnected from edge-processor WebSocket');
    };

    return () => {
      ws.close();
    };
  }, [camera.id]);
  
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.volume = volume;
      videoRef.current.muted = isMuted;
    }
  }, [volume, isMuted]);

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (videoRef.current.paused) {
        videoRef.current.play();
        setIsPlaying(true);
      } else {
        videoRef.current.pause();
        setIsPlaying(false);
      }
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (newVolume > 0) {
      setIsMuted(false);
    }
  };
  
  const toggleMute = () => {
    setIsMuted(prev => !prev);
  }

  return (
    <div 
      className="bg-black rounded-lg overflow-hidden relative aspect-video border border-gray-700 shadow-lg group"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full h-full object-cover"
      />
      {error && (
        <div className="absolute inset-0 bg-black/70 flex flex-col items-center justify-center text-center p-4">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 text-red-500 mb-2" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <p className="text-red-400 font-semibold">{error}</p>
        </div>
      )}

      <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
        {trackedObjects.map(obj => (
          <OverlayBox key={obj.object_id} trackedObject={{
            id: obj.object_id,
            type: obj.object_type === 'person' ? 'tracking' : 'identified',
            bbox: obj.bbox,
            confidence: obj.confidence,
            name: obj.object_type === 'person' ? undefined : obj.object_id,
            personId: obj.object_type === 'person' ? undefined : obj.object_id,
            isLoyalMember: false
          }} />
        ))}
      </div>

      <div className="absolute top-2 left-2 bg-black/50 text-white text-xs font-bold px-2 py-1 rounded">
        {camera.name}
      </div>
      
      <div className="absolute top-2 right-2 flex items-center space-x-2">
        <span className="text-xs font-bold text-red-500 bg-black/50 px-2 py-1 rounded animate-pulse">CCTV LIVE</span>
        <button className="bg-blue-600/50 hover:bg-blue-500 text-white text-xs px-2 py-1 rounded transition-colors">
          Connect
        </button>
      </div>

      {/* Controls Overlay */}
      <div className={`absolute bottom-0 left-0 w-full bg-gradient-to-t from-black/70 to-transparent p-4 transition-opacity duration-300 ${isHovered ? 'opacity-100' : 'opacity-0'}`}>
        <div className="flex items-center space-x-4">
          <button onClick={handlePlayPause} className="text-white hover:text-cyan-300 transition-colors">
            {isPlaying ? <PauseIcon /> : <PlayIcon />}
          </button>
          <div className="flex items-center space-x-2 w-24">
            <button onClick={toggleMute} className="text-white hover:text-cyan-300 transition-colors">
              {isMuted || volume === 0 ? <VolumeOffIcon /> : <VolumeUpIcon />}
            </button>
            <input 
              type="range" 
              min="0" 
              max="1" 
              step="0.05" 
              value={isMuted ? 0 : volume}
              onChange={handleVolumeChange}
              className="w-full h-1 bg-gray-600 rounded-lg appearance-none cursor-pointer accent-cyan-400"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default CameraFeed;
