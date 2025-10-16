"use client";
import AdminDashboard from '@/components/AdminDashboard';
import { useAuth } from '@/providers/AuthProvider';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function AdminPage() {
  const { profile, loading, user, signOut } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // If user is not authenticated, redirect to login
    if (!loading && !user) {
      router.push('/admin/login');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // If not authenticated, redirect to login
  if (!user) {
    return null; // Will redirect via useEffect
  }

  // If authenticated but profile is still loading, show loading
  if (!profile) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading profile...</p>
        </div>
      </div>
    );
  }

  // If authenticated but not admin, show access denied
  if (!profile.admin_privileges && profile.role !== 'admin') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Access Denied</h1>
          <p className="text-gray-600">Admin privileges required to view this page.</p>
          <p className="text-sm text-gray-500 mt-2">
            Your current role: <strong>{profile.role}</strong>
          </p>
          <div className="mt-4">
            <button
              onClick={() => router.push('/admin/login')}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 mr-2"
            >
              Try Different Account
            </button>
            <button
              onClick={() => router.push('/')}
              className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700"
            >
              Go to Main App
            </button>
          </div>
        </div>
      </div>
    );
  }

  // If authenticated and admin, show dashboard
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Back to Chat Button */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => {
                console.log('Back to Chat clicked - navigating without logout');
                // Use replace to avoid adding to history stack
                router.replace('/');
              }}
              className="flex items-center space-x-2 text-blue-600 hover:text-blue-800 transition-colors font-medium"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="font-medium">Back to Chat</span>
            </button>
            <div className="h-6 w-px bg-gray-300"></div>
            <h1 className="text-lg font-semibold text-gray-900">Admin Dashboard</h1>
          </div>
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.push('/admin/management')}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm transition-colors"
            >
              Manage Admins
            </button>
            <button
              onClick={async () => {
                console.log('Logout clicked - signing out user');
                try {
                  await signOut();
                  console.log('User signed out, navigating to main page');
                  router.push('/');
                } catch (error) {
                  console.error('Logout error:', error);
                }
              }}
              className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 text-sm transition-colors"
            >
              Logout
            </button>
            <div className="text-sm text-gray-500">
              Welcome, {profile.first_name} {profile.last_name}
            </div>
          </div>
        </div>
      </div>
      
      {/* Admin Dashboard Content */}
      <AdminDashboard />
    </div>
  );
}
