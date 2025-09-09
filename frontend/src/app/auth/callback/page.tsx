"use client";
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@supabase/supabase-js';

export default function AuthCallback() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        // Get environment variables
        const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
        const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
        
        if (!supabaseUrl || !supabaseAnonKey) {
          console.error('Supabase environment variables not available');
          setError('Authentication configuration error');
          setLoading(false);
          return;
        }

        // Create Supabase client
        const supabase = createClient(supabaseUrl, supabaseAnonKey, {
          auth: {
            autoRefreshToken: true,
            persistSession: true,
            detectSessionInUrl: true
          }
        });

        console.log('Processing OAuth callback...');
        console.log('Current URL:', window.location.href);
        console.log('URL hash:', window.location.hash);

        // First, try to get the session immediately
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();
        
        if (sessionError) {
          console.error('Error getting session:', sessionError);
        } else if (session) {
          console.log('Session already exists:', session.user.email);
          setLoading(false);
          router.push('/');
          return;
        }

        // If no session, set up auth state change listener
        console.log('Setting up auth state change listener...');
        const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
          console.log('Auth state change:', event, session?.user?.email);
          
          if (event === 'SIGNED_IN' && session) {
            console.log('User signed in successfully:', session.user.email);
            setLoading(false);
            router.push('/');
            subscription.unsubscribe();
          } else if (event === 'SIGNED_OUT') {
            console.log('User signed out');
            setLoading(false);
            router.push('/');
            subscription.unsubscribe();
          } else if (event === 'TOKEN_REFRESHED' && session) {
            console.log('Token refreshed, user still signed in');
            setLoading(false);
            router.push('/');
            subscription.unsubscribe();
          }
        });


        // Wait for auth state change to process the OAuth callback
        console.log('Waiting for OAuth callback to be processed...');
        
        // If there are tokens in the URL hash, try to process them manually
        if (window.location.hash.includes('access_token')) {
          console.log('Found tokens in URL hash, processing manually...');
          
          // Parse the URL hash to extract tokens
          const hashParams = new URLSearchParams(window.location.hash.substring(1));
          const accessToken = hashParams.get('access_token');
          const refreshToken = hashParams.get('refresh_token');
          
          console.log('Extracted tokens:', { 
            hasAccessToken: !!accessToken, 
            hasRefreshToken: !!refreshToken,
            tokenLength: accessToken?.length 
          });
          
          if (accessToken) {
            try {
              console.log('Setting session with extracted tokens...');
              const { data: { session }, error: setSessionError } = await supabase.auth.setSession({
                access_token: accessToken,
                refresh_token: refreshToken || '',
              });
              
              if (setSessionError) {
                console.error('Error setting session manually:', setSessionError);
              } else if (session) {
                console.log('Session set manually successfully:', session.user.email);
                setLoading(false);
                router.push('/');
                subscription.unsubscribe();
                return;
              } else {
                console.log('No session returned from setSession');
              }
            } catch (error) {
              console.error('Error processing tokens manually:', error);
            }
          } else {
            console.log('No access token found in URL hash');
          }
        } else {
          console.log('No access_token found in URL hash');
        }
        
        // Timeout after 10 seconds
        setTimeout(() => {
          console.log('OAuth callback timeout');
          setLoading(false);
          router.push('/');
          subscription.unsubscribe();
        }, 10000);

      } catch (err) {
        console.error('Error in auth callback:', err);
        setError(err instanceof Error ? err.message : 'An error occurred');
        setLoading(false);
      }
    };

    handleAuthCallback();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 flex items-center justify-center mb-4">
            <img 
              src="/prakriti_logo.webp" 
              alt="Prakriti School" 
              className="h-12 w-12 object-contain"
            />
          </div>
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Completing sign in...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 flex items-center justify-center mb-4">
            <img 
              src="/prakriti_logo.webp" 
              alt="Prakriti School" 
              className="h-12 w-12 object-contain"
            />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Sign in failed</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Return to Home
          </button>
        </div>
      </div>
    );
  }

  return null;
}