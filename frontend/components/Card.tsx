
import React from 'react';

interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
  titleClassName?: string;
}

const Card: React.FC<CardProps> = ({ title, children, className = '', titleClassName = '' }) => {
  return (
    <div className={`bg-gray-700 rounded-xl border border-gray-600 p-4 sm:p-6 ${className}`}>
      {title && <h2 className={`text-lg font-semibold text-text-primary mb-4 ${titleClassName}`}>{title}</h2>}
      {children}
    </div>
  );
};

export default Card;