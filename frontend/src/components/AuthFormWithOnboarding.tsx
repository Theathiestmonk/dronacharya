import React, { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useAuth } from '@/providers/AuthProvider';
import OnboardingForm from './OnboardingForm';

declare global {
  interface Window {
    google: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
          }) => void;
          renderButton: (parent: HTMLElement, options: {
            theme?: string;
            size?: string;
            width?: string;
            text?: string;
            shape?: string;
            logo_alignment?: string;
          }) => void;
        };
      };
    };
  }
}

// Modal Component for Policies
const PolicyModal = ({
  isOpen,
  onClose,
  title,
  children
}: {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[2147483647] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-md flex flex-col max-h-[85vh] overflow-hidden animate-in fade-in zoom-in duration-200"
        style={{ border: '3px solid var(--brand-primary)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4 border-b"
          style={{ backgroundColor: 'var(--brand-primary)', color: 'white', borderBottomColor: 'var(--brand-primary)' }}
        >
          <h4 className="text-lg font-bold">{title}</h4>
          <button
            onClick={onClose}
            className="text-white hover:text-gray-200 text-2xl font-bold w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/20 transition-colors"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-8 overflow-y-auto bg-white">
          <div className="text-sm text-gray-800 space-y-6 leading-relaxed text-justify">
            {children}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 rounded-lg font-semibold text-white transition-opacity hover:opacity-90"
            style={{ backgroundColor: 'var(--brand-primary)' }}
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
};


interface AuthFormWithOnboardingProps {
  onBack?: () => void;
}

const AuthFormWithOnboarding: React.FC<AuthFormWithOnboardingProps> = ({ onBack }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showTermsTooltip, setShowTermsTooltip] = useState(false);
  const [showPrivacyTooltip, setShowPrivacyTooltip] = useState(false);
  const googleButtonRef = useRef<HTMLDivElement>(null);

  const { signInWithIdToken, user, needsOnboarding } = useAuth();

  // Initialize Google Identity Services
  useEffect(() => {
    // Check if google is available and user is NOT yet logged in
    if (typeof window !== 'undefined' && window.google && !user) {
      const handleCredentialResponse = async (response: { credential: string }) => {
        setLoading(true);
        setError(null);
        try {
          console.log('Google Credential received, signing in...');
          const { error } = await signInWithIdToken(response.credential);
          if (error) {
            console.error('Sign-in error:', error);
            setError(error.message);
            setLoading(false);
          }
        } catch (err: unknown) {
          console.error('Sign-in exception:', err);
          const errorMessage = err instanceof Error ? err.message : 'An error occurred during Google sign-in';
          setError(errorMessage);
          setLoading(false);
        }
      };

      try {
        console.log('Initializing Google Identity Services...');
        window.google.accounts.id.initialize({
          client_id: "984000842769-d3nrc1rhrops3glm8uhosahqhq2p54i8.apps.googleusercontent.com",
          callback: handleCredentialResponse,
          auto_select: false,
          cancel_on_tap_outside: true,
        });

        if (googleButtonRef.current) {
          window.google.accounts.id.renderButton(googleButtonRef.current, {
            theme: "outline",
            size: "large",
            width: "320",
            text: "signin_with",
            shape: "rectangular",
            logo_alignment: "left",
          });
        }
      } catch (err) {
        console.error('Error initializing Google GSI:', err);
      }
    }
  }, [user, signInWithIdToken]);

  // If user needs onboarding, show onboarding form
  if (user && needsOnboarding) {
    return (
      <OnboardingForm
        user={user}
        onComplete={() => {
          if (onBack) onBack();
        }}
        onBack={onBack}
      />
    );
  }

  return (
    <div className="min-h-screen chat-grid-bg flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 relative pt-20 sm:pt-12" style={{ perspective: '1000px' }}>
      {/* Back button - positioned in top-left corner with mobile spacing */}
      {onBack && (
        <button
          onClick={onBack}
          className="absolute top-4 left-4 sm:left-4 flex items-center text-xs sm:text-sm text-gray-600 hover:text-gray-800 transition-colors z-10 bg-white/80 backdrop-blur-sm px-2 py-1.5 sm:px-3 sm:py-2 rounded-md shadow-sm border border-gray-200"
        >
          <svg className="w-3 h-3 sm:w-4 sm:h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span className="hidden sm:inline">Back to Chatbot</span>
          <span className="sm:hidden">Back</span>
        </button>
      )}

      <div className="max-w-md w-full space-y-2 sm:space-y-4 animated-bg border border-gray-200 rounded-lg shadow-lg p-4 sm:p-6 md:p-8 lg:p-10 mt-4 sm:mt-0">
        <div>
          <div className="mx-auto h-14 w-14 sm:h-20 sm:w-20 md:h-24 md:w-24 flex items-center justify-center">
            <Image
              src="/prakriti_logo.webp"
              alt="Prakriti AI Assistant"
              width={96}
              height={96}
              className="h-14 w-14 sm:h-20 sm:w-20 md:h-24 md:w-24 object-contain"
            />
          </div>
          <h2 className="mt-2 sm:mt-4 text-center text-lg sm:text-2xl md:text-3xl font-extrabold text-gray-900">
            Welcome to Prakriti AI Assistant
          </h2>
          <p className="mt-2 sm:mt-4 text-center text-xs sm:text-sm text-gray-600 px-2">
            Sign in to access our learning community
          </p>
        </div>

        {error && (
          <div className="rounded-md bg-red-50 p-3 sm:p-4 mb-4">
            <div className="text-xs sm:text-sm text-red-700">{error}</div>
          </div>
        )}

        {/* Google Sign In Section */}
        <div className="mt-6 sm:mt-8 flex flex-col items-center">
          <div className="flex flex-col items-center space-y-4 w-full">
            {/* Stable container for Google GSI button */}
            <div className="w-full flex flex-col items-center">
              <div
                ref={googleButtonRef}
                id="google-signin-button"
                className="flex justify-center min-h-[44px] w-full"
                style={{ display: loading ? 'none' : 'flex' }}
              />

              {loading && (
                <div className="w-[320px] h-[44px] flex items-center justify-center text-sm text-gray-600 bg-gray-50 rounded-lg border border-gray-200">
                  <span className="mr-2 animate-spin">⌛</span> Signing in...
                </div>
              )}
            </div>

            <p className="text-xs text-gray-500 text-center px-4 max-w-sm mt-3">
              By continuing with Google, you automatically agree to our{' '}
              <button
                type="button"
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); setShowTermsTooltip(true); }}
                className="text-blue-600 hover:underline focus:outline-none"
              >
                Terms
              </button>
              {' '}and{' '}
              <button
                type="button"
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); setShowPrivacyTooltip(true); }}
                className="text-blue-600 hover:underline focus:outline-none"
              >
                Privacy Policy
              </button>.
            </p>
          </div>
        </div>

        <div className="mt-2 sm:mt-4">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-xs sm:text-sm">
              <span className="px-2 bg-white text-gray-500">About Prakriti School</span>
            </div>
          </div>

          <div className="mt-2 sm:mt-4 text-center text-xs sm:text-sm text-gray-600 px-2">
            <p>
              Prakriti is an alternative/progressive K-12 school focused on
              <strong className="text-blue-600"> &ldquo;learning for happiness&rdquo;</strong> through
              deep experiential education.
            </p>
            <p className="mt-2 sm:mt-4">
              Our compassionate, learner-centric approach promotes joy, self-expression,
              and holistic development.
            </p>
          </div>
        </div>
      </div>

      {/* Policy Modals */}
      <PolicyModal
        isOpen={showTermsTooltip}
        onClose={() => setShowTermsTooltip(false)}
        title="Terms of Service"
      >
        <div className="space-y-4 text-justify">
          <p className="text-gray-600 text-xs mb-2">Last Updated: January 29, 2026</p>
          <p className="text-sm">
            Welcome to Prakriti Chatbot (&quot;Service&quot;), an AI-powered educational assistant provided by Prakriti School (&quot;we,&quot; &quot;us,&quot; or &quot;our&quot;). By accessing our Service, you agree to these Terms.
          </p>
          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>1. Service Description</h5>
            <p className="text-sm">Prakriti Chatbot supports students, parents, and teachers with educational info, homework help, and school integration.</p>
          </section>
          <div className="mt-4 pt-4 border-t border-gray-200">
            <Link href="/terms-of-service" target="_blank" className="text-blue-600 font-bold hover:underline flex items-center">
              Open Detailed Terms in New Tab
            </Link>
          </div>
        </div>
      </PolicyModal>

      <PolicyModal
        isOpen={showPrivacyTooltip}
        onClose={() => setShowPrivacyTooltip(false)}
        title="Privacy Policy"
      >
        <div className="space-y-4 text-justify">
          <p className="text-gray-600 text-xs mb-2">Last Updated: January 29, 2026</p>
          <p className="text-sm">
            This policy describes how we handle your data. We collect registration info and chat interactions to improve your learning experience.
          </p>
          <div className="mt-4 pt-4 border-t border-gray-200">
            <Link href="/privacy-policy" target="_blank" className="text-blue-600 font-bold hover:underline flex items-center">
              Open Detailed Privacy Policy in New Tab
            </Link>
          </div>
        </div>
      </PolicyModal>
    </div>
  );
};

export default AuthFormWithOnboarding;
