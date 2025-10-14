"use client";
import React from 'react';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface LogoutConfirmationProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

const LogoutConfirmation: React.FC<LogoutConfirmationProps> = ({
  isOpen,
  onConfirm,
  onCancel
}) => {
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-white/20 backdrop-blur-sm z-40 transition-opacity duration-200"
        onClick={onCancel}
      />
      
      {/* Confirmation Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl w-full max-w-xs sm:max-w-sm mx-4 transform transition-all duration-200 scale-100 opacity-100 border border-blue-100">
          {/* Confirmation Content */}
          <div className="p-4 sm:p-6 text-center">
            {/* Warning Icon */}
            <div className="flex justify-center mb-4">
              <div className="w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center">
                <ExclamationTriangleIcon className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            
            {/* Confirmation Text */}
            <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-2">
              Confirm Logout
            </h3>
            <p className="text-sm text-gray-600 mb-6">
              Are you sure you want to sign out?
            </p>
            
            {/* Confirmation Actions - Sign Out first, then Cancel */}
            <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
              <button
                onClick={onConfirm}
                className="w-full px-4 py-3 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                Sign Out
              </button>
              <button
                onClick={onCancel}
                className="w-full px-4 py-3 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default LogoutConfirmation;
