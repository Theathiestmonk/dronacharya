"use client";
import AdminDashboard from '@/components/AdminDashboard';
import ConfirmationModal from '@/components/ConfirmationModal';
import PrakritiLoader from '@/components/PrakritiLoader';
import { useAuth } from '@/providers/AuthProvider';
import { useRouter } from 'next/navigation';
import { useEffect, Suspense, useState } from 'react';

export default function AdminPage() {
  const { profile, loading, user, signOut } = useAuth();
  const router = useRouter();
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  useEffect(() => {
    // If user is not authenticated, redirect to login
    if (!loading && !user) {
      router.push('/admin/login');
    }
  }, [user, loading, router]);

  if (loading) {
    return <PrakritiLoader message="Loading..." />;
  }

  // If not authenticated, redirect to login
  if (!user) {
    return null; // Will redirect via useEffect
  }

  // If authenticated but profile is still loading, show loading
  if (!profile) {
    return <PrakritiLoader message="Loading profile..." />;
  }

  // If authenticated but not admin, show access denied
  if (!profile.admin_privileges && profile.role !== 'admin') {
    return (
      <div className="min-h-screen flex items-center justify-center chat-grid-bg">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Access Denied</h1>
          <p className="text-gray-600">Admin privileges required to view this page.</p>
          <p className="text-sm text-gray-500 mt-2">
            Your current role: <strong>{profile.role}</strong>
          </p>
          <div className="mt-4 flex flex-col sm:flex-row gap-2 sm:gap-0">
            <button
              onClick={() => router.push('/admin/login')}
              className="text-white px-4 py-2 rounded-md mr-0 sm:mr-2 transition-colors"
              style={{ backgroundColor: 'var(--brand-primary)' }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary-700)'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary)'}
            >
              Try Different Account
            </button>
            <button
              onClick={() => router.push('/')}
              className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 transition-colors"
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
    <div className="min-h-screen bg-white">
      {/* Back to Chat Button */}
      <div className="bg-white border-b border-gray-200 px-3 sm:px-4 md:px-6 py-2 sm:py-3">
        <div className="max-w-7xl mx-auto">
          {/* Single Line Layout */}
          <div className="flex items-center justify-between gap-2 sm:gap-3 md:gap-4 flex-nowrap overflow-x-auto">
            {/* Left Section - Back to Chat */}
            <button
              onClick={() => {
                console.log('Back to Chat clicked - navigating without logout');
                // Use replace to avoid adding to history stack
                router.replace('/');
              }}
              className="flex items-center space-x-1 sm:space-x-2 transition-colors font-medium flex-shrink-0"
              style={{ color: 'var(--brand-primary)' }}
              onMouseEnter={(e) => e.currentTarget.style.color = 'var(--brand-primary-700)'}
              onMouseLeave={(e) => e.currentTarget.style.color = 'var(--brand-primary)'}
            >
              <svg className="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="text-xs sm:text-sm font-medium whitespace-nowrap">Back to Chat</span>
            </button>
            
            {/* Right Section - Buttons and Welcome */}
            <div className="flex items-center space-x-2 sm:space-x-3 md:space-x-4 gap-2 flex-nowrap flex-shrink-0 ml-auto">
              <button
                onClick={() => router.push('/admin/management')}
                className="text-white px-3 sm:px-4 py-1.5 sm:py-2 rounded-md text-xs sm:text-sm transition-colors whitespace-nowrap flex-shrink-0"
                style={{ backgroundColor: 'var(--brand-primary)' }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary-700)'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary)'}
              >
                <span className="hidden sm:inline">Manage Admins</span>
                <span className="sm:hidden">Admins</span>
              </button>
              <button
                onClick={() => setShowLogoutConfirm(true)}
                className="bg-red-600 text-white px-2 sm:px-3 md:px-4 py-1.5 sm:py-2 rounded-md hover:bg-red-700 transition-colors whitespace-nowrap flex-shrink-0 flex items-center justify-center"
                title="Logout"
              >
                <svg className="w-4 h-4 sm:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                <span className="hidden sm:inline text-xs sm:text-sm">Logout</span>
              </button>
              <div className="text-xs sm:text-sm text-gray-500 whitespace-nowrap hidden lg:block flex-shrink-0">
                Welcome, {profile.first_name} {profile.last_name}
              </div>
              <div className="text-xs text-gray-500 whitespace-nowrap hidden md:block lg:hidden flex-shrink-0">
                Welcome, {profile.first_name}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Admin Dashboard Content */}
      <Suspense fallback={<PrakritiLoader message="Loading dashboard..." />}>
        <AdminDashboard />
      </Suspense>

      {/* Logout Confirmation Modal */}
      <ConfirmationModal
        isOpen={showLogoutConfirm}
        onClose={() => setShowLogoutConfirm(false)}
        onConfirm={async () => {
          try {
            await signOut();
            setShowLogoutConfirm(false);
            router.push('/');
          } catch (error) {
            console.error('Logout error:', error);
            setShowLogoutConfirm(false);
          }
        }}
        title="Sign Out"
        message="Are you sure you want to sign out?"
        confirmText="Sign Out"
        cancelText="Cancel"
        type="warning"
      />
    </div>
  );
}
