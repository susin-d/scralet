
import React, { useRef, useEffect, useState } from 'react';
import { LogEntry } from '../types';

interface EventLogProps {
  entries: LogEntry[];
}

const EventLog: React.FC<EventLogProps> = ({ entries }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [fetchedEntries, setFetchedEntries] = useState<LogEntry[]>([]);

  // Fetch logs from api-gateway on mount
  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await fetch('http://api-gateway:8000/logs?limit=50');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const logs = await response.json();
        setFetchedEntries(logs.map((log: any) => ({
          timestamp: new Date(log.timestamp).toLocaleTimeString('en-US', { hour12: false }),
          camera: log.camera,
          message: log.message
        })));
      } catch (error) {
        console.error('Failed to fetch logs:', error);
      }
    };

    fetchLogs();
  }, []);

  // Combine fetched entries with real-time entries
  const allEntries = [...entries, ...fetchedEntries];

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [allEntries]);

  return (
    <div className="bg-gray-800/50 rounded-lg p-4 h-full flex flex-col border border-gray-700 shadow-lg">
      <h3 className="text-lg font-bold text-cyan-300 mb-2 flex-shrink-0">Event Log</h3>
      <div ref={scrollRef} className="overflow-y-auto flex-grow pr-2">
        <ul className="space-y-1">
          {allEntries.map((entry, index) => (
            <li key={index} className="text-sm text-gray-300 font-mono flex">
              <span className="text-gray-500 mr-3">[{entry.timestamp}]</span>
              <span className="text-cyan-400 mr-2">{entry.camera}:</span>
              <span>{entry.message}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default EventLog;
