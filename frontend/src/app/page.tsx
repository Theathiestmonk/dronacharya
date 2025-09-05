"use client";
import React, { useRef, useState } from 'react';
import Chatbot from '../components/Chatbot';
import AuthFormWithOnboarding from '../components/AuthFormWithOnboarding';
import OnboardingForm from '../components/OnboardingForm';
import { useAuth } from '../providers/AuthProvider';

const HomePage: React.FC = () => {
  const { user, loading, needsOnboarding, signOut } = useAuth();
  const [chatKey] = useState(0); // Key to force re-render of Chatbot
  const chatbotRef = useRef<{ clearChat: () => void }>(null); // Ref for chatbot component
  const [showAuthForm, setShowAuthForm] = useState(false);

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
      {/* Header with login/logout button */}
      <header className="absolute top-0 right-0 p-4 z-10">
        {user ? (
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">
              Welcome, {user.user_metadata?.first_name || user.email}
            </span>
            <button
              onClick={async () => {
                await signOut();
                setShowAuthForm(false);
              }}
              className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md transition-colors"
            >
              Logout
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowAuthForm(true)}
            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
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
    </div>
  );
};

export default HomePage;
