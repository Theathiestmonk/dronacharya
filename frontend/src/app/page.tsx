"use client";
import React, { useRef, useState, useEffect } from 'react';
import Chatbot from '../components/Chatbot';
import AuthFormWithOnboarding from '../components/AuthFormWithOnboarding';
import OnboardingForm from '../components/OnboardingForm';
import { useAuth } from '../providers/AuthProvider';
import { ChatHistoryProvider, useChatHistory } from '../providers/ChatHistoryProvider';
import { ThemeProvider } from '../providers/ThemeProvider';
import { useSupabase } from '../providers/SupabaseProvider';
import ChatGPTLayout from '../components/ChatGPTLayout';

// Component to check if all providers are ready
const AppContent: React.FC<{ 
  user: { id: string; email?: string } | null; 
  loading: boolean; 
  needsOnboarding: boolean; 
  showAuthForm: boolean;
  setShowAuthForm: (show: boolean) => void;
  chatbotRef: React.RefObject<{ clearChat: () => void } | null>;
  chatKey: number;
}> = ({ 
  user, 
  loading, 
  needsOnboarding, 
  showAuthForm, 
  setShowAuthForm, 
  chatbotRef, 
  chatKey 
}) => {
  const { isLoading: chatHistoryLoading } = useChatHistory();
  const [isFullyInitialized, setIsFullyInitialized] = useState(false);

  // Immediate fallback for very fast loading
  useEffect(() => {
    const immediateTimer = setTimeout(() => {
      if (!isFullyInitialized) {
        console.log('Immediate fallback - forcing load');
        setIsFullyInitialized(true);
      }
    }, 1000); // 1 second immediate fallback

    return () => clearTimeout(immediateTimer);
  }, [isFullyInitialized]);

  // Simplified loading logic - just wait for chat history
  useEffect(() => {
    if (!chatHistoryLoading) {
      setIsFullyInitialized(true);
    }
  }, [chatHistoryLoading]);

  // Fallback timeout to prevent infinite loading
  useEffect(() => {
    const fallbackTimer = setTimeout(() => {
      console.log('Fallback timeout - forcing initialization');
      setIsFullyInitialized(true);
    }, 2000); // 2 second fallback

    return () => clearTimeout(fallbackTimer);
  }, []);

  // Debug logging
  useEffect(() => {
    console.log('Loading states:', { loading, chatHistoryLoading, isFullyInitialized });
  }, [loading, chatHistoryLoading, isFullyInitialized]);

  // Show loading state while providers are initializing
  if (loading || chatHistoryLoading || !isFullyInitialized) {
    return (
      <div className="flex min-h-screen h-screen bg-gray-50 dark:bg-gray-900">
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
              <span className="text-gray-600 dark:text-gray-300">
                Loading Prakriti AI...
              </span>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // Handle login redirect from sidebar click
  const handleLoginRedirect = () => {
    setShowAuthForm(true);
  };

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
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      <ChatGPTLayout onLoginRedirect={handleLoginRedirect}>
        <main className="flex-1 flex items-center justify-center px-2 sm:px-4">
          <div className="w-full max-w-4xl h-full flex flex-col justify-center">
            <Chatbot key={chatKey} ref={chatbotRef} />
          </div>
        </main>
      </ChatGPTLayout>
    </div>
  );
};

const HomePage: React.FC = () => {
  const { user, loading, needsOnboarding } = useAuth();
  const supabase = useSupabase();
  const [chatKey] = useState(0); // Key to force re-render of Chatbot
  const chatbotRef = useRef<{ clearChat: () => void }>(null); // Ref for chatbot component
  const [showAuthForm, setShowAuthForm] = useState(false);

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

  // Show chatbot for all users (public access) with proper provider initialization
  return (
    <ThemeProvider>
      <ChatHistoryProvider>
        <AppContent
          user={user}
          loading={loading}
          needsOnboarding={needsOnboarding}
          showAuthForm={showAuthForm}
          setShowAuthForm={setShowAuthForm}
          chatbotRef={chatbotRef}
          chatKey={chatKey}
        />
      </ChatHistoryProvider>
    </ThemeProvider>
  );
};

export default HomePage;
