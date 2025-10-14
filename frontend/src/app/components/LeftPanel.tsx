"use client";

// LeftPanel component for navigation sidebar
import React, { useState } from 'react';
import Link from 'next/link';
import { UserCircleIcon, HomeIcon, ArrowRightOnRectangleIcon } from '@heroicons/react/24/solid';
import LogoutConfirmation from '../../components/LogoutConfirmation';

interface LeftPanelProps {
  user?: { name?: string; email?: string } | null;
  onLogoClick?: () => void;
  onLogout?: () => void;
}

const LeftPanel: React.FC<LeftPanelProps> = ({ user, onLogoClick, onLogout }) => {
  const [isLogoClicked, setIsLogoClicked] = useState(false);
  const [showLogoutConfirmation, setShowLogoutConfirmation] = useState(false);

  const handleLogoClick = () => {
    if (onLogoClick) {
      setIsLogoClicked(true);
      onLogoClick();
      // Reset animation after a short delay
      setTimeout(() => setIsLogoClicked(false), 300);
    }
  };

  const handleLogoutClick = () => {
    setShowLogoutConfirmation(true);
  };

  const handleLogoutConfirm = () => {
    setShowLogoutConfirmation(false);
    if (onLogout) {
      onLogout();
    }
  };

  const handleLogoutCancel = () => {
    setShowLogoutConfirmation(false);
  };

  return (
    <>
      {/* Clean, minimal sidebar */}
      <aside className="flex flex-col items-center w-16 bg-white/80 backdrop-blur-sm border-r border-gray-100 h-screen py-6">
        {/* Logo at the top */}
        <div className="mb-8">
          <button
            onClick={handleLogoClick}
            className={`hover:scale-105 transition-all duration-200 focus:outline-none group ${
              isLogoClicked ? 'scale-110' : ''
            }`}
            title="Click to start a fresh chat"
            aria-label="Click to start a fresh chat"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/prakriti_logo.webp" alt="Prakriti Visual" style={{ maxWidth: '40px', height: 'auto' }} />
          </button>
        </div>
        
        {/* Spacer to push logout to bottom */}
        <div className="flex-1" />
        
        {/* Clean logout button */}
        <div className="mb-4">
          <button
            onClick={handleLogoutClick}
            className="group flex items-center justify-center w-10 h-10 rounded-full bg-gray-50 hover:bg-gray-100 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            title="Logout"
            aria-label="Logout"
          >
            <ArrowRightOnRectangleIcon className="w-5 h-5 text-gray-500 group-hover:text-gray-700 transition-colors" />
          </button>
        </div>
      </aside>

      {/* Logout Confirmation Popup */}
      <LogoutConfirmation
        isOpen={showLogoutConfirmation}
        onConfirm={handleLogoutConfirm}
        onCancel={handleLogoutCancel}
      />
    </>
  );
};

export default LeftPanel; 