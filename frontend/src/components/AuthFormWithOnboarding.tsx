                                                                                                        "use client";
import React, { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useAuth } from '@/providers/AuthProvider';
import OnboardingForm from './OnboardingForm';
import { useRouter } from 'next/navigation';

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
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agreeToTermsAndPrivacy, setAgreeToTermsAndPrivacy] = useState(false);
  const [showTermsTooltip, setShowTermsTooltip] = useState(false);
  const [showPrivacyTooltip, setShowPrivacyTooltip] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
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

    if (!isLogin && !agreeToTermsAndPrivacy) {
      setError('You must agree to the Terms of Service and Privacy Policy to create an account');
      setLoading(false);
      return;
    }

            try {
              const signupData = {
                agreed_to_terms_at: new Date().toISOString(),
                // Add first/last name if available, otherwise use default
                first_name: email.split('@')[0],
                last_name: 'User'
              };

              const { error } = isLogin 
                ? await signIn(email, password)
                : await signUp(email, password, signupData);

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
        
        <form 
          className="mt-2 sm:mt-4 space-y-2.5 sm:space-y-4" 
          onSubmit={handleSubmit}
          style={{ position: 'relative', zIndex: (showTermsTooltip || showPrivacyTooltip) ? 50 : 1 }}
        >
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
            <div className="relative">
              <label htmlFor="password" className="sr-only">
                Password
              </label>
              <input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete={isLogin ? "current-password" : "new-password"}
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2.5 sm:py-2 text-sm sm:text-base border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 pr-10"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-sm leading-5 z-20"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? (
                  <svg className="h-5 w-5 text-gray-500 hover:text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                  </svg>
                ) : (
                  <svg className="h-5 w-5 text-gray-500 hover:text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
            {!isLogin && (
              <div className="relative">
                <label htmlFor="confirmPassword" className="sr-only">
                  Confirm Password
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  autoComplete="new-password"
                  required
                  className="appearance-none rounded-none relative block w-full px-3 py-2.5 sm:py-2 text-sm sm:text-base border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 pr-10"
                  placeholder="Confirm Password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-sm leading-5 z-20"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? (
                    <svg className="h-5 w-5 text-gray-500 hover:text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5 text-gray-500 hover:text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
            )}
          </div>

          {error && (
            <div className="rounded-md bg-red-50 p-3 sm:p-4">
              <div className="text-xs sm:text-sm text-red-700">{error}</div>
            </div>
          )}

          {!isLogin && (
            <div className="relative">
              <div className="flex items-center">
                <input
                  id="agree-terms-privacy"
                  name="agree-terms-privacy"
                  type="checkbox"
                  checked={agreeToTermsAndPrivacy}
                  onChange={(e) => setAgreeToTermsAndPrivacy(e.target.checked)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer mt-0.5"
                />
                <div className="ml-3 text-xs sm:text-sm">
                  <label htmlFor="agree-terms-privacy" className="text-gray-700 cursor-pointer select-none leading-relaxed">
                    I agree to the{' '}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setShowTermsTooltip(true);
                        setShowPrivacyTooltip(false);
                      }}
                      className="font-medium underline focus:outline-none hover:opacity-80 transition-opacity bg-transparent border-none p-0 cursor-pointer"
                      style={{ color: 'var(--brand-primary)' }}
                    >
                      Terms of Service
                    </button>
                    {' '}and{' '}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setShowPrivacyTooltip(true);
                        setShowTermsTooltip(false);
                      }}
                      className="font-medium underline focus:outline-none hover:opacity-80 transition-opacity bg-transparent border-none p-0 cursor-pointer"
                      style={{ color: 'var(--brand-primary)' }}
                    >
                      Privacy Policy
                    </button>
                  </label>
                </div>
              </div>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={loading || (!isLogin && !agreeToTermsAndPrivacy)}
              className="group relative w-full flex justify-center py-2.5 sm:py-2 px-4 border border-transparent text-xs sm:text-sm font-medium rounded-md text-white focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
              style={{ 
                backgroundColor: (loading || (!isLogin && !agreeToTermsAndPrivacy)) ? '#9ca3af' : 'var(--brand-primary)' 
              }}
              onMouseEnter={(e) => {
                if (!loading && (isLogin || agreeToTermsAndPrivacy)) {
                  e.currentTarget.style.backgroundColor = 'var(--brand-primary-800)';
                }
              }}
              onMouseLeave={(e) => {
                if (!loading && (isLogin || agreeToTermsAndPrivacy)) {
                  e.currentTarget.style.backgroundColor = 'var(--brand-primary)';
                } else if (!isLogin && !agreeToTermsAndPrivacy) {
                  e.currentTarget.style.backgroundColor = '#9ca3af';
                }
              }}
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
                setAgreeToTermsAndPrivacy(false);
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
          
          <div className="mt-2 sm:mt-4 flex flex-col items-center">
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
            <p className="mt-2 text-[10px] text-gray-500 text-center px-4">
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
            Welcome to Prakriti Chatbot (&quot;Service&quot;), an AI-powered educational assistant provided by Prakriti School (&quot;we,&quot; &quot;us,&quot; or &quot;our&quot;). These Terms of Service (&quot;Terms&quot;) govern your access to and use of the Prakriti Chatbot, website, and related services. By accessing or using our Service, you agree to be bound by these Terms. If you disagree with any part of these Terms, you may not access the Service.
          </p>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>1. Service Description</h5>
            <p className="text-sm mb-2">Prakriti Chatbot is an AI-powered educational assistant designed to support students, parents, teachers, and administrators at Prakriti School. Our Service provides:</p>
            <ul className="list-disc pl-5 text-sm space-y-2">
              <li>Educational information and school-related queries</li>
              <li>Homework assistance and academic support</li>
              <li>Lesson planning and curriculum guidance</li>
              <li>Grading assistance and feedback</li>
              <li>Integration with Google Classroom and educational tools</li>
              <li>Web-enhanced responses for comprehensive information</li>
              <li>Administrative support and school management tools</li>
            </ul>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>2. Eligibility and User Accounts</h5>
            <h6 className="font-semibold text-sm mb-1">2.1 Eligibility Requirements</h6>
            <p className="text-sm mb-2">To use our Service, you must be associated with Prakriti School, be at least 13 years old (or have parental consent), provide accurate registration info, and maintain account security.</p>
            <h6 className="font-semibold text-sm mb-1">2.2 Account Registration and Security</h6>
            <p className="text-sm mb-2">You are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account.</p>
            <h6 className="font-semibold text-sm mb-1">2.3 Parental Consent for Minors</h6>
            <p className="text-sm">Students under 18 years of age require parental or guardian consent to create an account and use our Service.</p>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>3. Acceptable Use Policy</h5>
            <h6 className="font-semibold text-sm mb-1">3.1 Permissible Use</h6>
            <p className="text-sm mb-2">You may use our Service only for lawful educational purposes including seeking assistance, completing assignments, and accessing curriculum resources.</p>
            <h6 className="font-semibold text-sm mb-1">3.2 Prohibited Activities</h6>
            <p className="text-sm">You must not violate laws, share inappropriate content, attempt unauthorized access, harass others, or engage in academic dishonesty.</p>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>4. AI Limitations and Disclaimers</h5>
            <p className="text-sm mb-2"><strong>4.1 AI-Generated Content:</strong> AI-generated content may contain errors. You should always verify critical information through official school channels.</p>
            <p className="text-sm mb-2"><strong>4.2 No Professional Advice:</strong> The Service is not a substitute for professional educational, medical, or legal advice.</p>
            <p className="text-sm"><strong>4.3 Service Availability:</strong> We cannot guarantee uninterrupted access due to maintenance or technical issues.</p>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>5. Educational Content and Academic Integrity</h5>
            <p className="text-sm mb-2"><strong>5.1 Academic Honesty:</strong> Students must maintain academic integrity. Teachers and administrators may monitor usage.</p>
            <p className="text-sm mb-2"><strong>5.2 Content Ownership:</strong> Educational content remains property of Prakriti School.</p>
            <p className="text-sm"><strong>5.3 Google Classroom:</strong> Integration is subject to Google&apos;s Terms and Privacy Policy.</p>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>6. Intellectual Property Rights</h5>
            <p className="text-sm mb-2">The Service is owned by Prakriti School. Users grant us a license to use submitted content for educational purposes.</p>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>7. Termination and Suspension</h5>
            <p className="text-sm">We may terminate or suspend your account for breach of these Terms, school policies, or illegal activity.</p>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>8. Disclaimers and Limitation of Liability</h5>
            <p className="text-sm mb-2">The Service is provided &quot;as is&quot;. Prakriti School shall not be liable for indirect, incidental, or special damages.</p>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>9. Governing Law</h5>
            <p className="text-sm">These Terms shall be governed by the laws of India, specifically the National Capital Territory of Delhi.</p>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>10. Contact Information</h5>
            <div className="bg-gray-50 p-3 rounded-lg border border-gray-200 text-xs">
              <p className="font-bold">Prakriti School</p>
              <p>Noida Expressway, Greater Noida</p>
              <p>Delhi NCR, India</p>
              <p>Website: prakriti.edu.in</p>
            </div>
          </section>

          <div className="mt-4 pt-4 border-t border-gray-200">
            <Link
              href="/terms-of-service"
              target="_blank"
              className="text-blue-600 font-bold hover:underline flex items-center"
            >
              Open Detailed Terms in New Tab
              <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
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
            Prakriti School (&quot;we,&quot; &quot;us,&quot; or &quot;our&quot;) operates the Prakriti Chatbot. This Privacy Policy describes how we collect, use, and safeguard your information when you use our chatbot services and related educational platforms.
          </p>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>1. Information We Collect</h5>
            <h6 className="font-semibold text-sm mb-1">1.1 Personal Information</h6>
            <ul className="list-disc pl-5 text-sm space-y-2 mb-3">
              <li>Registration: Name, email, phone, status, grade.</li>
              <li>Interactions: Chat messages and responses.</li>
              <li>Educational Data: Grades, assignments, attendance (via Google Classroom).</li>
              <li>Feedback and Support info.</li>
            </ul>
            <h6 className="font-semibold text-sm mb-1">1.2 Automatically Collected</h6>
            <p className="text-sm mb-2">Device info (IP, browser), usage data (session logs), cookies, and performance metrics.</p>
            <h6 className="font-semibold text-sm mb-1">1.3 Third-Party Integrations</h6>
            <p className="text-sm">Google Classroom, Web Services, and Supabase database services.</p>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>2. How We Use Your Information</h5>
            <ul className="list-disc pl-5 text-sm space-y-2">
              <li>Educational support and personalized learning.</li>
              <li>Processing queries and generating responses.</li>
              <li>Progress tracking and learner analytics.</li>
              <li>Administrative functions and system security.</li>
              <li>Service improvement and AI response enhancement.</li>
            </ul>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>3. Information Sharing</h5>
            <p className="text-sm mb-2">Shared within the school community (teachers, admins, parents) for educational purposes. We use trusted service providers for AI (OpenAI, Google) and hosting (Supabase). We do not sell personal info.</p>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>4. Data Security</h5>
            <p className="text-sm">We use SSL/TLS encryption, role-based access controls, secure storage, and regular security audits to protect your data.</p>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>5. Children&apos;s Privacy (COPPA)</h5>
            <p className="text-sm">Students under 13 require parental consent. Parents have the right to review, modify, or delete their child&apos;s personal information.</p>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>6. Data Retention</h5>
            <p className="text-sm">Chat history is kept for 2 years, usage logs for 1 year. Profiles are kept while the account is active.</p>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>7. Your Rights</h5>
            <p className="text-sm">You have rights to access, correction, deletion, portability, and restriction of your data processing.</p>
          </section>

          <section>
            <h5 className="font-bold text-base mb-2" style={{ color: 'var(--brand-primary)' }}>8. Contact Us</h5>
            <div className="bg-gray-50 p-3 rounded-lg border border-gray-200 text-xs">
              <p className="font-bold">Prakriti School</p>
              <p>Email: admission@prakriti.edu.in</p>
              <p>Website: prakriti.edu.in</p>
            </div>
          </section>

          <div className="mt-4 pt-4 border-t border-gray-200">
            <Link
              href="/privacy-policy"
              target="_blank"
              className="text-blue-600 font-bold hover:underline flex items-center"
            >
              Open Detailed Privacy Policy in New Tab
              <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
            </Link>
          </div>
        </div>
      </PolicyModal>
    </div>
  );
};

export default AuthFormWithOnboarding;
