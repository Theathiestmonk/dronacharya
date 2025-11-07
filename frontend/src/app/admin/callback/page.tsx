"use client";
import { useEffect, useState, Suspense, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/providers/AuthProvider';
import Image from 'next/image';

function CallbackContent() {
  // IMMEDIATE LOG on component render
  console.log(`🔍 [CALLBACK PAGE] ===== CALLBACK PAGE COMPONENT RENDERED =====`);
  console.log(`🔍 [CALLBACK PAGE] Current URL:`, typeof window !== 'undefined' ? window.location.href : 'Server-side');
  console.log(`🔍 [CALLBACK PAGE] Component mounted at:`, new Date().toISOString());
  
  const router = useRouter();
  const searchParams = useSearchParams();
  const { profile } = useAuth();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  
  // CRITICAL: Track if callback has been processed to prevent duplicate API calls
  // OAuth codes can only be used once - if useEffect runs twice, second call will fail
  const hasProcessedRef = useRef(false);
  const processedCodeRef = useRef<string | null>(null);
  
  console.log(`🔍 [CALLBACK PAGE] React hooks initialized`);
  console.log(`🔍 [CALLBACK PAGE] searchParams available:`, !!searchParams);
  console.log(`🔍 [CALLBACK PAGE] profile available:`, !!profile);

  useEffect(() => {
    console.log(`🔍 [CALLBACK PAGE] ===== COMPONENT MOUNTED/USEEFFECT TRIGGERED =====`);
    console.log(`🔍 [CALLBACK PAGE] searchParams exists:`, !!searchParams);
    console.log(`🔍 [CALLBACK PAGE] profile exists:`, !!profile);
    if (searchParams) {
      console.log(`🔍 [CALLBACK PAGE] URL search params:`, {
        code: searchParams.get('code') ? 'EXISTS' : 'MISSING',
        state: searchParams.get('state'),
        error: searchParams.get('error'),
        connected: searchParams.get('connected')
      });
      
      // Check if there's an error in URL (Google OAuth error)
      const urlError = searchParams.get('error');
      if (urlError) {
        console.error(`🔍 [CALLBACK PAGE] ❌ Google OAuth error in URL: ${urlError}`);
        hasProcessedRef.current = true;
        setStatus('error');
        setMessage(`Google authorization failed: ${urlError}. Please try again.`);
        setTimeout(() => {
          router.push('/admin');
        }, 3000);
        return;
      }
    }
    
    const handleCallback = async (retries = 0) => {
      console.log(`🔍 [CALLBACK PAGE] handleCallback called (retry ${retries})`);
      if (!searchParams) {
        console.log(`🔍 [CALLBACK PAGE] No searchParams, returning early`);
        return;
      }
      
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');

      // CRITICAL: Prevent duplicate processing - OAuth codes can only be used once
      if (hasProcessedRef.current) {
        console.log(`🔍 [CALLBACK PAGE] ⚠️ Callback already processed, skipping duplicate call`);
        if (processedCodeRef.current === code) {
          console.log(`🔍 [CALLBACK PAGE] This is the same code that was already processed`);
        }
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
      
      // Check if this code was already processed
      if (processedCodeRef.current === code) {
        console.log(`🔍 [CALLBACK PAGE] ⚠️ Code ${code.substring(0, 20)}... was already processed`);
        return;
      }

      // Wait for profile to load with retry mechanism (max 5 retries = 5 seconds)
      if (!profile) {
        if (retries >= 5) {
          hasProcessedRef.current = true;
          setStatus('error');
          setMessage('Profile loading timeout. Please refresh the page and try again.');
          return;
        }
        console.log(`🔍 [CALLBACK PAGE] Profile not loaded yet, waiting... (attempt ${retries + 1}/5)`);
        // Wait 1 second and try again (profile might still be loading)
        setTimeout(() => {
          handleCallback(retries + 1);
        }, 1000);
        return;
      }
      
      // Verify profile has email
      if (!profile.email) {
        hasProcessedRef.current = true;
        setStatus('error');
        setMessage('User profile email not found. Please ensure you are logged in.');
        return;
      }

      // CRITICAL: Mark as processing BEFORE making API call to prevent duplicates
      if (!hasProcessedRef.current) {
        hasProcessedRef.current = true;
        processedCodeRef.current = code;
        console.log(`🔍 [CALLBACK PAGE] ✅ Marked callback as processing for code: ${code.substring(0, 20)}...`);
      } else {
        console.log(`🔍 [CALLBACK PAGE] ⚠️ Already processing, skipping duplicate API call`);
        return;
      }

      try {
        // Use current logged-in user's email from auth context
        const adminEmail = profile.email || null;
        console.log(`🔍 [CALLBACK PAGE] ===== CALLBACK PAGE - STARTING =====`);
        console.log(`🔍 [CALLBACK PAGE] Profile object:`, { 
          id: profile.id, 
          email: profile.email, 
          admin_privileges: profile.admin_privileges 
        });
        console.log(`🔍 [CALLBACK PAGE] Current user email: ${adminEmail}`);
        console.log(`🔍 [CALLBACK PAGE] Profile ID: ${profile.id}`);
        console.log(`🔍 [CALLBACK PAGE] Profile email: ${profile.email}`);
        console.log(`🔍 [CALLBACK PAGE] Profile loaded:`, !!profile);
        console.log(`🔍 [CALLBACK PAGE] Code: ${code ? 'EXISTS' : 'MISSING'}`);
        console.log(`🔍 [CALLBACK PAGE] State: ${state}`);
        console.log(`🔍 [CALLBACK PAGE] Sending to API with adminEmail: ${adminEmail}`);
        console.log(`🔍 [CALLBACK PAGE] ⚠️  CRITICAL: This email MUST match the logged-in user!`);
        
        console.log(`🔍 [CALLBACK PAGE] Making API call to /api/admin/callback...`);
        console.log(`🔍 [CALLBACK PAGE] Request body:`, { code: code ? 'EXISTS' : 'MISSING', state, adminEmail });
        console.log(`🔍 [CALLBACK PAGE] Full URL will be: /api/admin/callback`);
        console.log(`🔍 [CALLBACK PAGE] Request payload:`, JSON.stringify({ code, state, adminEmail }, null, 2));
        
        const apiStartTime = Date.now();
        let response;
        try {
          response = await fetch('/api/admin/callback', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ code, state, adminEmail }),
          });
          const apiDuration = Date.now() - apiStartTime;
          console.log(`🔍 [CALLBACK PAGE] API call completed in ${apiDuration}ms`);
        } catch (fetchError) {
          console.error(`🔍 [CALLBACK PAGE] ❌ Fetch error:`, fetchError);
          throw fetchError;
        }

        console.log(`🔍 [CALLBACK PAGE] API response status: ${response.status}`);
        console.log(`🔍 [CALLBACK PAGE] API response ok: ${response.ok}`);
        console.log(`🔍 [CALLBACK PAGE] API response headers:`, Object.fromEntries(response.headers.entries()));
        
        if (response.ok) {
          const data = await response.json();
          console.log(`🔍 [CALLBACK PAGE] ✅ Success! Response:`, data);
          setStatus('success');
          setMessage(data.message);
          
          // Redirect to admin dashboard after 2 seconds
          setTimeout(() => {
            router.push('/admin');
          }, 2000);
        } else {
          const errorText = await response.text();
          console.error(`🔍 [CALLBACK PAGE] ❌ API error response:`, errorText);
          let errorData;
          try {
            errorData = JSON.parse(errorText);
          } catch {
            errorData = { error: errorText || 'Unknown error' };
          }
          console.error(`🔍 [CALLBACK PAGE] ❌ API error parsed:`, errorData);
          
          // Check if it's the invalid_grant error (code already used or expired)
          if (errorData.details?.error === 'invalid_grant' || errorData.error === 'invalid_grant') {
            console.log(`🔍 [CALLBACK PAGE] ⚠️ Code was already used or expired - likely duplicate call or page refresh`);
            
            // If code was already processed successfully, just redirect silently
            if (hasProcessedRef.current && processedCodeRef.current === code) {
              console.log(`🔍 [CALLBACK PAGE] Code was already processed, redirecting silently`);
              setTimeout(() => {
                router.push('/admin?connected=true');
              }, 1000);
              return;
            }
            
            // If invalid_grant but code wasn't processed, it might be expired or URL was refreshed
            // Try to check if integration already exists (maybe it succeeded but we missed the response)
            console.log(`🔍 [CALLBACK PAGE] Checking if integration already exists...`);
            try {
              const checkResponse = await fetch(`/api/admin/integrations?email=${encodeURIComponent(profile.email)}`);
              if (checkResponse.ok) {
                const integrations = await checkResponse.json();
                if (integrations.classroom_enabled || integrations.calendar_enabled) {
                  console.log(`🔍 [CALLBACK PAGE] ✅ Integration already exists! Redirecting...`);
                  setStatus('success');
                  setMessage('Integration already connected. Redirecting...');
                  setTimeout(() => {
                    router.push('/admin?connected=true');
                  }, 2000);
                  return;
                }
              }
            } catch (checkError) {
              console.error(`🔍 [CALLBACK PAGE] Error checking integrations:`, checkError);
            }
            
            // If integration doesn't exist, show helpful error message
            setStatus('error');
            setMessage('The authorization code has expired or was already used. Please try connecting again from the admin dashboard.');
            setTimeout(() => {
              router.push('/admin');
            }, 3000);
            return;
          }
          
          setStatus('error');
          setMessage(errorData.error || errorData.detail || 'Integration failed');
        }
      } catch (error) {
        console.error(`🔍 [CALLBACK PAGE] ❌ Exception during API call:`, error);
        console.error(`🔍 [CALLBACK PAGE] ❌ Error stack:`, error instanceof Error ? error.stack : 'No stack');
        
        // Only set error if we haven't processed it yet
        if (!hasProcessedRef.current) {
          setStatus('error');
          setMessage(`Failed to complete integration: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
      }
    };

    handleCallback();
  }, [searchParams, router, profile]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
        <div className="mb-6">
          <Image
            src="/prakriti_logo.webp"
            alt="Prakriti Logo"
            width={64}
            height={64}
            className="w-16 h-16 mx-auto mb-4"
          />
        </div>

        {status === 'loading' && (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Completing Integration...
            </h2>
            <p className="text-gray-600">
              Please wait while we set up your Google integration.
            </p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Integration Successful!
            </h2>
            <p className="text-gray-600 mb-4">{message}</p>
            <p className="text-sm text-gray-500">
              Redirecting to admin dashboard...
            </p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Integration Failed
            </h2>
            <p className="text-gray-600 mb-4">{message}</p>
            <button
              onClick={() => router.push('/admin')}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
            >
              Back to Admin Dashboard
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default function AdminCallback() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Loading...</h2>
        </div>
      </div>
    }>
      <CallbackContent />
    </Suspense>
  );
}




























