"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/providers/AuthProvider';

interface User {
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  admin_privileges?: boolean;
  created_at: string;
}

const AdminManagement: React.FC = () => {
  const { profile } = useAuth();
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchAllUsers = useCallback(async () => {
    try {
      const response = await fetch('/api/admin-roles', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'list_all_users',
          email: profile?.email, // Add email for admin verification
          adminEmail: profile?.email,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setAllUsers(data.data || []);
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to fetch users');
      }
    } catch {
      setError('Failed to fetch users');
    }
  }, [profile?.email]);

  const assignAdminRole = async (email: string) => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch('/api/admin-roles', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'assign',
          email: email,
          adminEmail: profile?.email,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSuccess(data.message);
        fetchAllUsers(); // Refresh the users list
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to assign admin role');
      }
    } catch {
      setError('Failed to assign admin role');
    } finally {
      setLoading(false);
    }
  };

  const removeAdminRole = async (email: string) => {
    if (!confirm(`Are you sure you want to remove admin role from ${email}?`)) {
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch('/api/admin-roles', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'remove',
          email: email,
          adminEmail: profile?.email,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSuccess(data.message);
        fetchAllUsers(); // Refresh the users list
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to remove admin role');
      }
    } catch {
      setError('Failed to remove admin role');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (profile?.admin_privileges || profile?.role === 'admin') {
      fetchAllUsers();
    }
  }, [profile?.admin_privileges, profile?.role, fetchAllUsers]);

  // Check if current user has admin privileges - moved after all hooks
  if (!profile || (!profile.admin_privileges && profile.role !== 'admin')) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Access Denied</h1>
          <p className="text-gray-600">Admin access required to view this page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Admin Management</h1>
              <p className="mt-2 text-gray-600">Manage admin roles and permissions</p>
            </div>
            <button
              onClick={() => window.location.href = '/admin'}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors duration-200 flex items-center space-x-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              <span>Back to Dashboard</span>
            </button>
          </div>
        </div>

        {/* All Users */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">All Users</h2>
          <p className="text-sm text-gray-600 mb-4">Select users to assign admin roles</p>
          
          {allUsers.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No users found</p>
          ) : (
            <div className="space-y-3">
              {allUsers.map((user) => (
                <div key={user.user_id} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                      <span className="text-gray-600 font-semibold">
                        {user.first_name.charAt(0)}{user.last_name.charAt(0)}
                      </span>
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">
                        {user.first_name} {user.last_name}
                      </h3>
                      <p className="text-sm text-gray-600">{user.email}</p>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          user.role === 'student' 
                            ? 'bg-blue-100 text-blue-800' 
                            : user.role === 'teacher'
                            ? 'bg-purple-100 text-purple-800'
                            : 'bg-pink-100 text-pink-800'
                        }`}>
                          {user.role}
                        </span>
                        {(user.admin_privileges || user.role === 'admin') && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            Admin
                          </span>
                        )}
                        <p className="text-xs text-gray-500">
                          Joined: {new Date(user.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {(user.admin_privileges || user.role === 'admin') ? (
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-green-600 font-medium">Admin</span>
                        {user.email !== profile?.email && (
                          <button
                            onClick={() => removeAdminRole(user.email)}
                            disabled={loading}
                            className="bg-red-600 text-white px-3 py-1 rounded-md hover:bg-red-700 disabled:opacity-50 text-sm"
                          >
                            Remove
                          </button>
                        )}
                        {user.email === profile?.email && (
                          <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                            You
                          </span>
                        )}
                      </div>
                    ) : (
                      <button
                        onClick={() => assignAdminRole(user.email)}
                        disabled={loading}
                        className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 text-sm"
                      >
                        {loading ? 'Adding...' : 'Add Admin'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Messages */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-red-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div className="text-sm text-red-700 font-medium">{error}</div>
            </div>
          </div>
        )}

        {success && (
          <div className="mb-6 bg-green-50 border border-green-200 rounded-md p-4">
            <div className="text-sm text-green-700">{success}</div>
          </div>
        )}

        {/* User Summary */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">User Summary</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{allUsers.filter(u => u.role === 'student').length}</div>
              <div className="text-sm text-blue-800">Students</div>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">{allUsers.filter(u => u.role === 'teacher').length}</div>
              <div className="text-sm text-purple-800">Teachers</div>
            </div>
            <div className="bg-pink-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-pink-600">{allUsers.filter(u => u.role === 'parent').length}</div>
              <div className="text-sm text-pink-800">Parents</div>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-green-600">{allUsers.filter(u => u.admin_privileges || u.role === 'admin').length}</div>
              <div className="text-sm text-green-800">Admins</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminManagement;
