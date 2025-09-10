"use client";
import React, { useRef, useState, useEffect } from 'react';
import Chatbot from '../components/Chatbot';
import AuthFormWithOnboarding from '../components/AuthFormWithOnboarding';
import OnboardingForm from '../components/OnboardingForm';
import EditProfileModal from '../components/EditProfileModal';
import UserAvatarDropdown from '../components/UserAvatarDropdown';
import { useAuth } from '../providers/AuthProvider';
import { useSupabase } from '../providers/SupabaseProvider';

const HomePage: React.FC = () => {
  const { user, loading, needsOnboarding, signOut } = useAuth();
  const supabase = useSupabase();
  const [chatKey] = useState(0); // Key to force re-render of Chatbot
  const chatbotRef = useRef<{ clearChat: () => void }>(null); // Ref for chatbot component
  const [showAuthForm, setShowAuthForm] = useState(false);
  const [showEditProfile, setShowEditProfile] = useState(false);

  // Handle OAuth callback tokens if they're in the URL hash
  useEffect(() => {
    const handleOAuthCallback = async () => {
      if (!supabase) return;
      
      // Check if there are OAuth tokens in the URL hash
      if (window.location.hash.includes('access_token')) {
        console.log('OAuth tokens detected in main page, processing...');
        console.log('URL hash:', window.location.hash);
        
        // Parse the URL hash to extract tokens
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const accessToken = hashParams.get('access_token');
        const refreshToken = hashParams.get('refresh_token');
        
        if (accessToken) {
          try {
            console.log('Setting session with OAuth tokens...');
            const { data: { session }, error } = await supabase.auth.setSession({
              access_token: accessToken,
              refresh_token: refreshToken || '',
            });
            
            if (error) {
              console.error('Error setting session:', error);
              console.error('Error details:', {
                message: error.message,
                status: error.status
              });
            } else if (session) {
              console.log('Session created successfully:', session.user.email);
              // Clear the URL hash to remove tokens
              window.history.replaceState({}, document.title, window.location.pathname);
            } else {
              console.log('No session returned from setSession');
            }
          } catch (error) {
            console.error('Error processing OAuth tokens:', error);
          }
        }
      }
    };

    handleOAuthCallback();
  }, [supabase]);

  // Show loading state while checking authentication
  if (loading) {
    return (
      <div className="flex min-h-screen h-screen">
        <main className="flex-1 flex items-center justify-center h-screen">
          <div className="w-full max-w-2xl h-full flex flex-col justify-center">
            <div className="flex justify-center mb-6">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img 
                src="/prakriti_logo.webp" 
                alt="Prakriti Visual" 
                style={{ maxWidth: '150px', height: 'auto' }}
              />
            </div>
            <div className="text-center">
              <span className="text-gray-600">Loading...</span>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // Show auth form if user clicked login and needs onboarding
  if (showAuthForm && (!user || needsOnboarding)) {
    return (
      <AuthFormWithOnboarding 
        onBack={() => setShowAuthForm(false)}
      />
    );
  }

  // Show onboarding form if user is logged in but needs onboarding
  if (user && needsOnboarding) {
    return (
      <OnboardingForm
        user={user}
        onComplete={() => setShowAuthForm(false)}
        onBack={() => setShowAuthForm(false)}
      />
    );
  }


  // Show chatbot for all users (public access)
  return (
    <div className="flex min-h-screen h-screen">
      {/* Header with user avatar dropdown */}
      <header className="absolute top-0 right-0 p-4 z-10">
        {user ? (
          <UserAvatarDropdown
            onEditProfile={() => setShowEditProfile(true)}
            onLogout={async () => {
              await signOut();
              setShowAuthForm(false);
            }}
          />
        ) : (
          <button
            onClick={() => setShowAuthForm(true)}
            className="px-4 py-2 text-sm text-white rounded-md transition-colors"
            style={{ backgroundColor: 'var(--brand-primary)' }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary-800)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary)'}
          >
            Login
          </button>
        )}
      </header>

      <main className="flex-1 flex items-center justify-center h-screen px-2 sm:px-4">
        <div className="w-full max-w-2xl h-full flex flex-col justify-center">
          <Chatbot key={chatKey} ref={chatbotRef} />
        </div>
      </main>

      {/* Edit Profile Modal */}
      <EditProfileModal
        isOpen={showEditProfile}
        onClose={() => setShowEditProfile(false)}
      />
    </div>
  );
};

export default HomePage;
