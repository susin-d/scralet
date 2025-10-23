// FIX: Implement the CustomerDashboard component which was previously missing.
import React, { useState, useRef, useEffect } from 'react';
import { GoogleGenAI, Type } from "@google/genai";
import Card from '../Card';
import { MOCK_LOGGED_IN_CUSTOMER } from '../../constants';
import type { Recommendation } from '../../types';
import { CameraIcon } from '../Icons';

const RecommendationCard: React.FC<{ recommendation: Recommendation }> = ({ recommendation }) => (
    <Card className="flex flex-col">
        <img src={recommendation.image} alt={recommendation.productName} className="w-full h-40 object-cover rounded-t-xl mb-4" />
        <h3 className="font-semibold text-text-primary">{recommendation.productName}</h3>
        <p className="text-sm text-text-secondary mt-1 flex-grow">{recommendation.description}</p>
        <button className="mt-4 w-full px-4 py-2 bg-accent text-white rounded-lg font-semibold hover:opacity-90 transition-transform duration-200 ease-in-out hover:scale-105 active:scale-95">
            View Product
        </button>
    </Card>
);

const CustomerDashboard: React.FC = () => {
    const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const customer = MOCK_LOGGED_IN_CUSTOMER;

    const [isCameraOn, setIsCameraOn] = useState(false);
    const [cameraError, setCameraError] = useState<string | null>(null);
    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);


    const startCamera = async () => {
        setCameraError(null);
        try {
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                streamRef.current = stream;
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                }
                setIsCameraOn(true);
            } else {
                setCameraError("Your browser does not support camera access.");
            }
        } catch (err) {
            console.error("Error accessing camera: ", err);
            setCameraError("Could not access camera. Please check permissions.");
        }
    };

    const stopCamera = () => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        if (videoRef.current) {
            videoRef.current.srcObject = null;
        }
        setIsCameraOn(false);
    };

    useEffect(() => {
        // Cleanup function to stop camera when component unmounts
        return () => {
            stopCamera();
        };
    }, []);

    const fetchRecommendations = async () => {
        setIsLoading(true);
        setError(null);
        setRecommendations([]);

        try {
            const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
            const response = await ai.models.generateContent({
                model: "gemini-2.5-flash",
                contents: `Generate 3 product recommendations for a "${customer.loyaltyTier} Tier" customer in a grocery store.`,
                config: {
                    responseMimeType: "application/json",
                    responseSchema: {
                        type: Type.ARRAY,
                        items: {
                            type: Type.OBJECT,
                            properties: {
                                productName: { type: Type.STRING },
                                description: { type: Type.STRING },
                                image: { type: Type.STRING, description: "A placeholder image URL from picsum.photos" }
                            },
                            required: ["productName", "description", "image"]
                        }
                    }
                }
            });
            
            const jsonStr = response.text.trim();
            const parsedRecommendations = JSON.parse(jsonStr);
            setRecommendations(parsedRecommendations);

        } catch (e) {
            console.error(e);
            setError("Sorry, we couldn't generate recommendations at this time.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-text-primary">Welcome back, {customer.name}!</h1>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-text-secondary">Your Loyalty Status</p>
                            <p className={`text-3xl font-bold ${customer.loyaltyTier === 'Gold' ? 'text-gold' : 'text-text-primary'}`}>{customer.loyaltyTier} Tier</p>
                        </div>
                         <div className="text-5xl">{customer.loyaltyTier === 'Gold' ? '🏆' : '⭐'}</div>
                    </div>
                </Card>
                <Card>
                    <h3 className="font-semibold text-text-primary mb-2">Virtual Try-On</h3>
                    <div className="aspect-video bg-gray-900 rounded-md flex items-center justify-center relative overflow-hidden">
                       {!isCameraOn ? (
                         <div className="text-center text-text-secondary">
                            {cameraError ? (
                                <p className="text-error px-4">{cameraError}</p>
                            ) : (
                                <>
                                 <CameraIcon className="w-12 h-12 mx-auto" />
                                 <p className="mt-2 text-sm">Activate your camera for a live view.</p>
                                </>
                            )}
                         </div>
                       ) : (
                         <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover"></video>
                       )}
                    </div>
                    <button 
                        onClick={isCameraOn ? stopCamera : startCamera} 
                        className="mt-4 w-full px-4 py-2 bg-accent text-white rounded-lg font-semibold hover:opacity-90 transition-transform duration-200 ease-in-out hover:scale-105 active:scale-95"
                    >
                        {isCameraOn ? 'Stop Camera' : 'Start Camera'}
                    </button>
                </Card>
            </div>


            <div>
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-semibold text-text-primary">Personalized Recommendations</h2>
                    <button 
                        onClick={fetchRecommendations} 
                        disabled={isLoading}
                        className="px-4 py-2 bg-accent text-white rounded-lg font-semibold hover:opacity-90 transition-transform duration-200 ease-in-out hover:scale-105 active:scale-95 disabled:bg-gray-500 disabled:scale-100"
                    >
                        {isLoading ? 'Generating...' : 'Generate For Me'}
                    </button>
                </div>
                {error && <p className="text-center text-error">{error}</p>}
                {isLoading && (
                     <div className="text-center p-8">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto"></div>
                        <p className="mt-4 text-text-secondary">Our AI is curating recommendations for you...</p>
                    </div>
                )}
                {recommendations.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {recommendations.map((rec, index) => (
                            <RecommendationCard key={index} recommendation={rec} />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default CustomerDashboard;