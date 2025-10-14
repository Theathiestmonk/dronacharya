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


  return (
    <div className="mb-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex items-center space-x-3">
        <div className="text-2xl">{getRoleIcon(profile.role)}</div>
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <span className="font-medium text-gray-900">
              {profile.first_name} {profile.last_name}
            </span>
          </div>
          {profile.role === 'student' && profile.grade && (
            <p className="text-sm text-gray-600">Grade {profile.grade}</p>
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
