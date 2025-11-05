"use client";
import { useEffect, useRef, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '@/providers/AuthProvider';

function StudentGoogleClassroomCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { profile } = useAuth();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Connecting Google Classroom...');
  const hasProcessedRef = useRef(false);
  const processedCodeRef = useRef<string | null>(null);

  useEffect(() => {
    if (!searchParams) return;

    const handleCallback = async (retries = 0) => {
      if (!searchParams) return;

      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');

      // Prevent duplicate processing
      if (hasProcessedRef.current) {
        return;
      }

      if (error) {
        hasProcessedRef.current = true;
        setStatus('error');
        setMessage('Google authorization was denied or failed');
        return;
      }

      if (!code || !state) {
        hasProcessedRef.current = true;
        setStatus('error');
        setMessage('Invalid callback parameters');
        return;
      }

      // Check if code was already processed
      if (processedCodeRef.current === code) {
        return;
      }

      // Wait for profile to load
      if (!profile) {
        if (retries >= 5) {
          hasProcessedRef.current = true;
          setStatus('error');
          setMessage('Profile loading timeout. Please refresh the page and try again.');
          return;
        }
        setTimeout(() => {
          handleCallback(retries + 1);
        }, 1000);
        return;
      }

      // Verify profile is a student
      if (profile.role !== 'student') {
        hasProcessedRef.current = true;
        setStatus('error');
        setMessage('Only students can connect Google Classroom');
        return;
      }

      if (!profile.email) {
        hasProcessedRef.current = true;
        setStatus('error');
        setMessage('Student email not found in profile');
        return;
      }

      // Mark as processing
      hasProcessedRef.current = true;
      processedCodeRef.current = code;

      try {
        const response = await fetch('/api/student/google-classroom/callback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code,
            state,
            studentEmail: profile.email
          })
        });

        const data = await response.json();

        if (!response.ok) {
          setStatus('error');
          setMessage(data.error || 'Failed to connect Google Classroom');
          return;
        }

        setStatus('success');
        setMessage('Google Classroom connected successfully!');

        // Redirect to profile edit page after 2 seconds
        setTimeout(() => {
          router.push('/?openEditProfile=true');
        }, 2000);
      } catch (err) {
        console.error('Callback error:', err);
        setStatus('error');
        setMessage('An error occurred while connecting Google Classroom');
      }
    };

    handleCallback();
  }, [searchParams, profile, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <div className="text-center">
          {status === 'loading' && (
            <>
              <div className="flex justify-center mb-4">
                <svg className="animate-spin h-12 w-12 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Connecting Google Classroom</h2>
              <p className="text-gray-600">{message}</p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="flex justify-center mb-4">
                <svg className="h-12 w-12 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Success!</h2>
              <p className="text-gray-600">{message}</p>
              <p className="text-sm text-gray-500 mt-2">Redirecting to your profile...</p>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="flex justify-center mb-4">
                <svg className="h-12 w-12 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Connection Failed</h2>
              <p className="text-gray-600 mb-4">{message}</p>
              <button
                onClick={() => router.push('/?openEditProfile=true')}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Return to Profile
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function StudentGoogleClassroomCallback() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
          <div className="text-center">
            <div className="flex justify-center mb-4">
              <svg className="animate-spin h-12 w-12 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Loading...</h2>
            <p className="text-gray-600">Preparing Google Classroom connection...</p>
          </div>
        </div>
      </div>
    }>
      <StudentGoogleClassroomCallbackContent />
    </Suspense>
  );
}



