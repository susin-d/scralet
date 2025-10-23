
import React from 'react';
import { SocketStatus } from '../types';

interface HeaderProps {
  status: SocketStatus;
  alertCount: number;
}

const statusConfig = {
    connected: { text: 'Connected', color: 'bg-green-500', pulse: true },
    disconnected: { text: 'Disconnected', color: 'bg-red-500', pulse: true },
    connecting: { text: 'Connecting...', color: 'bg-yellow-500', pulse: true },
};

const Header: React.FC<HeaderProps> = ({ status, alertCount }) => {
  const { text, color, pulse } = statusConfig[status];

  return (
    <header className="flex-shrink-0 bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 flex justify-between items-center border border-gray-700 shadow-lg">
      <h1 className="text-xl md:text-2xl font-bold tracking-wider text-cyan-300">
        Sentient Supermarket Dashboard
      </h1>
      <div className="flex items-center space-x-6 text-sm">
        <div className="flex items-center space-x-2">
          <span className="relative flex h-3 w-3">
            <span className={`${color} ${pulse ? 'animate-ping' : ''} absolute inline-flex h-full w-full rounded-full opacity-75`}></span>
            <span className={`${color} relative inline-flex rounded-full h-3 w-3`}></span>
          </span>
          <span>{text}</span>
        </div>
        <div className="hidden md:flex items-center space-x-2">
           <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 2a8 8 0 100 16 8 8 0 000-16zM9 13a1 1 0 112 0v-5a1 1 0 11-2 0v5zm1-7a1 1 0 100 2 1 1 0 000-2z" clipRule="evenodd" />
            </svg>
          <span className="font-semibold">Alerts:</span>
          <span className="text-yellow-400 font-bold">{alertCount}</span>
        </div>
      </div>
    </header>
  );
};

export default Header;
