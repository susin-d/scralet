import React from 'react';
import { TrackedObject } from '../types';

interface OverlayBoxProps {
  trackedObject: TrackedObject;
}

const OverlayBox: React.FC<OverlayBoxProps> = ({ trackedObject }) => {
  const { bbox, type, id, name, isLoyalMember, confidence } = trackedObject;
  const [x, y, width, height] = bbox;

  const boxStyle = {
    left: `${x}%`,
    top: `${y}%`,
    width: `${width}%`,
    height: `${height}%`,
  };

  const borderColor = type === 'identified' ? 'border-green-400' : 'border-yellow-400';
  const borderStyle = type === 'identified' ? 'border-solid' : 'border-dashed';
  const tagBgColor = type === 'identified' ? 'bg-green-500/80' : 'bg-yellow-500/80';
  const textColor = type === 'identified' ? 'text-white' : 'text-black';

  return (
    <div
      className={`absolute transition-all duration-200 ease-in-out border-2 ${borderColor} ${borderStyle} rounded-md box-border`}
      style={boxStyle}
    >
      <div className={`absolute -top-0 left-0 text-xs font-bold p-1 rounded-br-md rounded-tl-sm ${tagBgColor} ${textColor}`}>
        {type === 'identified' ? (
          <span className="flex items-center">
            {isLoyalMember && <span className="mr-1">★</span>}
            {name}
            {confidence && (
              <span className="ml-1 text-xs opacity-75">
                ({Math.round(confidence * 100)}%)
              </span>
            )}
          </span>
        ) : (
          <span>
            Human
            {confidence && (
              <span className="ml-1 text-xs opacity-75">
                ({Math.round(confidence * 100)}%)
              </span>
            )}
          </span>
        )}
      </div>
    </div>
  );
};

export default OverlayBox;