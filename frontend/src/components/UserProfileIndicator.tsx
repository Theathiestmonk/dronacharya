"use client";
import React from 'react';
import { useAuth } from '@/providers/AuthProvider';

const UserProfileIndicator: React.FC = () => {
  const { user, profile } = useAuth();

  if (!user || !profile) return null;

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

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'student':
        return 'bg-blue-100 text-blue-800';
      case 'teacher':
        return 'bg-green-100 text-green-800';
      case 'parent':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="mb-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex items-center space-x-3">
        <div className="text-2xl">{getRoleIcon(profile.role)}</div>
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <span className="font-medium text-gray-900">
              {profile.first_name} {profile.last_name}
            </span>
            <span className={`px-2 py-1 text-xs font-medium rounded-full ${getRoleColor(profile.role)}`}>
              {profile.role.charAt(0).toUpperCase() + profile.role.slice(1)}
            </span>
          </div>
          {profile.role === 'student' && profile.grade && (
            <p className="text-sm text-gray-600">Grade {profile.grade}</p>
          )}
          {profile.role === 'teacher' && profile.department && (
            <p className="text-sm text-gray-600">{profile.department}</p>
          )}
          {profile.role === 'parent' && profile.relationship_to_student && (
            <p className="text-sm text-gray-600">{profile.relationship_to_student.charAt(0).toUpperCase() + profile.relationship_to_student.slice(1)}</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default UserProfileIndicator;
