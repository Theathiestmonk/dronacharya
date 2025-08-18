"use client";

// LeftPanel component for navigation sidebar
import React, { useState } from 'react';
import { UserCircleIcon, HomeIcon } from '@heroicons/react/24/solid';

interface LeftPanelProps {
  user?: any;
  onLogoClick?: () => void;
}

const LeftPanel: React.FC<LeftPanelProps> = ({ user, onLogoClick }) => {
  const [isLogoClicked, setIsLogoClicked] = useState(false);

  const handleLogoClick = () => {
    if (onLogoClick) {
      setIsLogoClicked(true);
      onLogoClick();
      // Reset animation after a short delay
      setTimeout(() => setIsLogoClicked(false), 300);
    }
  };

  return (
  <aside className="flex flex-col items-center w-20 bg-white border-r border-gray-200 h-screen py-6 shadow-lg">
    {/* Logo at the top */}
    <div className="mb-6">
      <button
        onClick={handleLogoClick}
        className={`hover:scale-110 transition-all duration-200 focus:outline-none group ${
          isLogoClicked ? 'scale-125 rotate-12' : ''
        }`}
        title="Click to start a fresh chat"
        aria-label="Click to start a fresh chat"
      >
        <img src="/prakriti_logo.webp" alt="Prakriti Visual" style={{ maxWidth: '50px', height: 'auto' }} />
      </button>
    </div>
    {/* User profile circle */}
    <div className="mb-8">
      <div className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center text-white text-xl font-bold border-2 border-white shadow-md">
        {user?.email ? user.email[0].toUpperCase() : <UserCircleIcon className="w-10 h-10 text-gray-300" />}
      </div>
    </div>
    {/* Spacer to push nav to bottom */}
    <div className="flex-1" />
    {/* Navigation icons at the bottom */}
    <nav className="flex flex-col gap-6 items-center mb-2">
      <a href="/" className="group flex flex-col items-center focus:outline-none">
        <HomeIcon className="w-7 h-7 text-gray-400 group-hover:text-blue-600 transition" />
        <span className="text-xs text-gray-500 mt-1 group-hover:text-blue-600">Dashboard</span>
      </a>
      {/* Add more icons here as needed */}
    </nav>
  </aside>
  );
};

export default LeftPanel; 