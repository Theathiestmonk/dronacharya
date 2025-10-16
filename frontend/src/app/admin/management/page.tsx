"use client";
import AdminManagement from '@/components/AdminManagement';
import { useRouter } from 'next/navigation';

export default function AdminManagementPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Back to Chat Button */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => {
                // Use replace to avoid adding to history stack
                router.replace('/');
              }}
              className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="font-medium">Back to Chat</span>
            </button>
            <div className="h-6 w-px bg-gray-300"></div>
            <h1 className="text-lg font-semibold text-gray-900">Admin Management</h1>
          </div>
        </div>
      </div>
      
      {/* Admin Management Content */}
      <AdminManagement />
    </div>
  );
}



