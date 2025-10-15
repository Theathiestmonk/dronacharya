"use client";
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/providers/AuthProvider';

export default function AuthCallback() {
  const router = useRouter();
  const { user } = useAuth();

  useEffect(() => {
    // Wait for Supabase to process the auth callback
    const timer = setTimeout(() => {
      if (user) {
        // User is authenticated, redirect to reset password page
        router.push('/reset-password');
      } else {
        // No user, redirect to main page
        router.push('/');
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, [user, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Processing authentication...</p>
      </div>
    </div>
  );
}