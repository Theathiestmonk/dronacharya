"use client";
import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/providers/AuthProvider';
import Image from 'next/image';

interface UserAvatarDropdownProps {
  onEditProfile: () => void;
  onLogout: () => void;
}

const UserAvatarDropdown: React.FC<UserAvatarDropdownProps> = ({ onEditProfile, onLogout }) => {
  const { user, profile } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const getInitials = () => {
    if (profile?.first_name && profile?.last_name) {
      return `${profile.first_name.charAt(0)}${profile.last_name.charAt(0)}`.toUpperCase();
    }
    if (user?.email) {
      return user.email.charAt(0).toUpperCase();
    }
    return 'U';
  };

  const getAvatarColor = () => {
    if (!profile) return '#6B7280';
    if (profile.avatar_color) {
      return profile.avatar_color;
    }
    // Fallback to role-based colors
    switch (profile.role) {
      case 'student':
        return '#3B82F6'; // Blue
      case 'teacher':
        return '#10B981'; // Green
      case 'parent':
        return '#8B5CF6'; // Purple
      default:
        return '#6B7280'; // Gray
    }
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'student':
        return '🎓';
      case 'teacher':
        return '👩‍🏫';
      case 'parent':
        return '👨‍👩‍👧‍👦';
      default:
        return '👤';
    }
  };

  if (!user || !profile) return null;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Avatar Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-1 rounded-full hover:bg-gray-100 transition-colors group"
      >
        {profile.profile_picture_url ? (
          <Image
            src={profile.profile_picture_url}
            alt={`${profile.first_name} ${profile.last_name}`}
            width={40}
            height={40}
            className="w-10 h-10 rounded-full object-cover border-2 border-gray-200 group-hover:border-gray-300 transition-colors"
            onError={(e) => {
              // Fallback to initials if image fails to load
              const target = e.target as HTMLImageElement;
              target.style.display = 'none';
              const parent = target.parentElement;
              if (parent) {
                parent.innerHTML = `
                  <div class="w-10 h-10 rounded-full flex items-center justify-center text-white text-lg font-semibold group-hover:scale-105 transition-transform" style="background-color: ${getAvatarColor()}">
                    ${getInitials()}
                  </div>
                `;
              }
            }}
          />
        ) : (
          <div 
            className="w-10 h-10 rounded-full flex items-center justify-center text-white text-lg font-semibold group-hover:scale-105 transition-transform"
            style={{ backgroundColor: getAvatarColor() }}
          >
            {getInitials()}
          </div>
        )}
        
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50 animate-in fade-in-0 zoom-in-95 duration-200">
          {/* User Info Header */}
          <div className="px-4 py-3 border-b border-gray-100">
            <div className="flex items-center space-x-3">
              {profile.profile_picture_url ? (
                <Image
                  src={profile.profile_picture_url}
                  alt={`${profile.first_name} ${profile.last_name}`}
                  width={40}
                  height={40}
                  className="w-10 h-10 rounded-full object-cover"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                    const parent = target.parentElement;
                    if (parent) {
                      parent.innerHTML = `
                        <div class="w-10 h-10 rounded-full flex items-center justify-center text-white text-lg font-semibold" style="background-color: ${getAvatarColor()}">
                          ${getInitials()}
                        </div>
                      `;
                    }
                  }}
                />
              ) : (
                <div 
                  className="w-10 h-10 rounded-full flex items-center justify-center text-white text-lg font-semibold"
                  style={{ backgroundColor: getAvatarColor() }}
                >
                  {getInitials()}
                </div>
              )}
              
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 truncate">
                  {profile.first_name} {profile.last_name}
                </div>
                <div className="text-xs text-gray-500 truncate">
                  {user.email}
                </div>
                <div className="text-xs text-gray-500 flex items-center mt-1">
                  <span className="mr-1">{getRoleIcon(profile.role)}</span>
                  {profile.role.charAt(0).toUpperCase() + profile.role.slice(1)}
                  {profile.role === 'student' && profile.grade && (
                    <span className="ml-2">• Grade {profile.grade}</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Menu Items */}
          <div className="py-1">
            <button
              onClick={() => {
                setIsOpen(false);
                onEditProfile();
              }}
              className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center"
            >
              <svg className="w-4 h-4 mr-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Edit Profile
            </button>
            
            <button
              onClick={() => {
                setIsOpen(false);
                onLogout();
              }}
              className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center"
            >
              <svg className="w-4 h-4 mr-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserAvatarDropdown;
