import React from 'react';
import { UserCircleIcon, HomeIcon } from '@heroicons/react/24/solid';

const LeftPanel: React.FC<{ user?: any }> = ({ user }) => (
  <aside className="flex flex-col items-center w-20 bg-white border-r border-gray-200 h-screen py-6 shadow-lg">
    {/* Logo at the top */}
    <div className="mb-6">
      <img src="/prakriti_logo.webp" alt="Prakriti Visual" style={{ maxWidth: '50px', height: 'auto' }} />
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

export default LeftPanel; 