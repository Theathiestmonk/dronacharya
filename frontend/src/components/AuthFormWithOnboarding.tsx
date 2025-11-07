"use client";
import React, { useState } from 'react';
import Image from 'next/image';
import { useAuth } from '@/providers/AuthProvider';
import OnboardingForm from './OnboardingForm';
import { useRouter } from 'next/navigation';

interface AuthFormWithOnboardingProps {
  onBack?: () => void;
}

const AuthFormWithOnboarding: React.FC<AuthFormWithOnboardingProps> = ({ onBack }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  
  const { signIn, signInWithGoogle, signUp, user, needsOnboarding } = useAuth();

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


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (!isLogin && password !== confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    try {
      const { error } = isLogin 
        ? await signIn(email, password)
        : await signUp(email, password);

      if (error) {
        setError(error.message);
      } else if (!isLogin) {
        setError('Please check your email for verification link');
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignIn = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    setLoading(true);
    setError(null);

    console.log('Google sign-in button clicked');
    
    // Call the OAuth function without await to prevent blocking
    signInWithGoogle().then(({ error }) => {
      if (error) {
        console.error('Google sign-in error:', error);
        setError(error.message || 'An error occurred with Google sign-in');
        setLoading(false);
      } else {
        console.log('Google sign-in initiated, redirecting...');
        // Don't set loading to false here as we're redirecting
      }
    }).catch((err: unknown) => {
      console.error('Google sign-in exception:', err);
      setError(err instanceof Error ? err.message : 'An error occurred with Google sign-in');
      setLoading(false);
    });
  };

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
              alt="Prakriti School" 
              width={96}
              height={96}
              className="h-14 w-14 sm:h-20 sm:w-20 md:h-24 md:w-24 object-contain"
            />
          </div>
          <h2 className="mt-2 sm:mt-4 text-center text-lg sm:text-2xl md:text-3xl font-extrabold text-gray-900">
            {isLogin ? 'Sign in to your account' : 'Create your account'}
          </h2>
          <p className="mt-2 sm:mt-4 text-center text-xs sm:text-sm text-gray-600 px-2">
            {isLogin ? "Welcome back to Prakriti School's learning community" : "Join Prakriti School's learning community"}
          </p>
        </div>
        
        <form className="mt-2 sm:mt-4 space-y-2.5 sm:space-y-4" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email" className="sr-only">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2.5 sm:py-2 text-sm sm:text-base border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete={isLogin ? "current-password" : "new-password"}
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2.5 sm:py-2 text-sm sm:text-base border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {!isLogin && (
              <div>
                <label htmlFor="confirmPassword" className="sr-only">
                  Confirm Password
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  required
                  className="appearance-none rounded-none relative block w-full px-3 py-2.5 sm:py-2 text-sm sm:text-base border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10"
                  placeholder="Confirm Password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
            )}
          </div>

          {error && (
            <div className="rounded-md bg-red-50 p-3 sm:p-4">
              <div className="text-xs sm:text-sm text-red-700">{error}</div>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-2.5 sm:py-2 px-4 border border-transparent text-xs sm:text-sm font-medium rounded-md text-white focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ backgroundColor: 'var(--brand-primary)' }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary-800)'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary)'}
            >
              {loading ? 'Please wait...' : (isLogin ? 'Sign in' : 'Sign up')}
            </button>
          </div>

          <div className="text-center flex flex-col items-center space-y-1 sm:space-y-2">
            <a
              href="#"
              onClick={(e) => {
                e.preventDefault();
                setIsLogin(!isLogin);
                setError(null);
                setEmail('');
                setPassword('');
                setConfirmPassword('');
              }}
              className="text-blue-600 hover:text-blue-500 text-xs sm:text-sm font-medium cursor-pointer"
            >
              {isLogin 
                ? "Don't have an account? Sign up" 
                : "Already have an account? Sign in"
              }
            </a>
            {isLogin && (
              <a
                href="/forgot-password"
                onClick={(e) => {
                  e.preventDefault();
                  router.push('/forgot-password');
                }}
                className="text-gray-600 hover:text-gray-500 text-xs sm:text-sm cursor-pointer"
                >
                  Forgot your password?
              </a>
            )}
          </div>
        </form>

        {/* Google Sign In */}
        <div className="mt-2 sm:mt-4">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-xs sm:text-sm">
              <span className="px-2 bg-white text-gray-500">Or continue with</span>
            </div>
          </div>
          
          <div className="mt-2 sm:mt-4 flex justify-center">
            <button
              type="button"
              onClick={handleGoogleSignIn}
              disabled={loading}
              className="group relative w-auto min-w-fit flex items-center justify-center py-2 sm:py-2.5 px-4 border border-gray-300 text-xs sm:text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ 
                borderColor: 'var(--brand-primary-200)',
                boxShadow: '0 0 0 1px var(--brand-primary)'
              }}
            >
              <svg className="w-4 h-4 sm:w-5 sm:h-5 mr-2 flex-shrink-0" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <span className="flex items-center">{loading ? 'Please wait...' : 'Continue with Google'}</span>
            </button>
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
    </div>
  );
};

export default AuthFormWithOnboarding;
