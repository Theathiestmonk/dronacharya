"use client";
import React, { useRef, useState, useEffect } from 'react';
import Image from 'next/image';
import Chatbot from '../components/Chatbot';
import AuthFormWithOnboarding from '../components/AuthFormWithOnboarding';
import OnboardingForm from '../components/OnboardingForm';
import ChatbotSidebar from '../components/ChatbotSidebar';
import EditProfileModal from '../components/EditProfileModal';
import ConfirmationModal from '../components/ConfirmationModal';
import { useAuth } from '../providers/AuthProvider';
import { ChatHistoryProvider, useChatHistory } from '../providers/ChatHistoryProvider';
import { useRouter } from 'next/navigation';

// Component to check if all providers are ready
const AppContent: React.FC<{
  user: { id: string; email?: string } | null;
  loading: boolean;
  needsOnboarding: boolean;
  showAuthForm: boolean;
  setShowAuthForm: (show: boolean) => void;
  chatbotRef: React.RefObject<{ clearChat: () => void } | null>;
  chatKey: number;
  setChatKey: (key: number | ((prev: number) => number)) => void;
}> = ({
  user,
  loading,
  needsOnboarding,
  showAuthForm,
  setShowAuthForm,
  chatbotRef,
  chatKey,
  setChatKey
}) => {
    const { isLoading: chatHistoryLoading, getActiveSession, activeSessionId } = useChatHistory();
    const { profile, signOut } = useAuth();
    const router = useRouter();
    const [isFullyInitialized, setIsFullyInitialized] = useState(false);
    const [skipOnboarding, setSkipOnboarding] = useState(false);
    // CRITICAL: Track if we've ever had an active session to prevent loading screen from showing again
    const hasEverHadSessionRef = useRef(false);
    // Track page load time to ensure minimum loading duration - set immediately on component creation
    const pageLoadTimeRef = useRef<number>(Date.now());
    const [sidebarQuery, setSidebarQuery] = useState<string>('');
    const [showEditProfile, setShowEditProfile] = useState(false);
    const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false); // For mobile sidebar toggle
    const [isDesktop, setIsDesktop] = useState(false); // Track if we're on desktop
    const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
    const [dropdownPosition, setDropdownPosition] = useState({ top: 20, left: 280 });
    const profileDropdownRef = useRef<HTMLDivElement>(null);
    const [hasCheckedOAuthOnboarding, setHasCheckedOAuthOnboarding] = useState(false);

    // Detect screen size and manage sidebar state
    useEffect(() => {
      const checkScreenSize = () => {
        const desktop = window.innerWidth >= 1024; // lg breakpoint
        setIsDesktop(desktop);
        if (desktop) {
          setIsSidebarOpen(true); // Always open on desktop
        }
      };

      // Check on mount
      checkScreenSize();

      // Check on resize
      window.addEventListener('resize', checkScreenSize);
      return () => window.removeEventListener('resize', checkScreenSize);
    }, []);

    // Track active session with messages to prevent loading screen from showing after first session
    // BUT: Still respect minimum loading time on page refresh
    useEffect(() => {
      const activeSession = getActiveSession();
      const hasMessages = activeSession?.messages && activeSession.messages.length > 0;
      if (activeSession && hasMessages && !hasEverHadSessionRef.current) {
        hasEverHadSessionRef.current = true;
        // Don't set isFullyInitialized immediately - let the minimum loading time logic handle it
        // This ensures logged-in users also get the 2-second delay on refresh
        console.log('✅ Active session with messages detected - will respect minimum loading time');
      }
    }, [getActiveSession, activeSessionId]); // Re-check when session ID changes

    // Improved loading logic - wait for auth and chat history with minimum delay
    // ALWAYS enforce minimum 2 seconds loading time, regardless of how fast loading completes
    useEffect(() => {
      if (!loading && !chatHistoryLoading) {
        // Ensure minimum loading time of 2 seconds to prevent blinking after refresh
        const minLoadingTime = 2000; // 2 seconds
        const elapsed = Date.now() - pageLoadTimeRef.current;
        const remainingTime = Math.max(0, minLoadingTime - elapsed);

        console.log(`Loading states completed. Elapsed: ${elapsed}ms, Remaining: ${remainingTime}ms`);

        if (remainingTime > 0) {
          console.log(`Waiting ${remainingTime}ms to reach minimum loading time (2 seconds)`);
          const timer = setTimeout(() => {
            console.log('Minimum loading time (2 seconds) elapsed, initializing app');
            setIsFullyInitialized(true);
          }, remainingTime);

          // Cleanup timer on unmount
          return () => clearTimeout(timer);
        } else {
          // If already past 2 seconds, initialize immediately
          console.log('Already past minimum loading time, initializing app');
          setIsFullyInitialized(true);
        }
      }
    }, [loading, chatHistoryLoading]);

    // Minimum loading time to prevent blinking effect after refresh
    useEffect(() => {
      const fallbackTimer = setTimeout(() => {
        console.log('Fallback timeout - forcing initialization');
        setIsFullyInitialized(true);
      }, 2000); // Set to 2 seconds to prevent blinking after refresh

      return () => clearTimeout(fallbackTimer);
    }, []);

    // Debug logging
    useEffect(() => {
      console.log('Loading states:', { loading, chatHistoryLoading, isFullyInitialized });
    }, [loading, chatHistoryLoading, isFullyInitialized]);

    // Check for OAuth callback and ensure onboarding is checked after profile loads
    useEffect(() => {
      // Reset check flag when user changes
      if (user) {
        const currentUserId = user.id;
        const previousCheck = sessionStorage.getItem('oauth_check_user');
        if (previousCheck !== currentUserId) {
          setHasCheckedOAuthOnboarding(false);
          sessionStorage.setItem('oauth_check_user', currentUserId);
        }
      }
    }, [user]);

    useEffect(() => {
      // Check if we just came from OAuth callback (URL hash contains access_token)
      const isOAuthCallback = typeof window !== 'undefined' && window.location.hash.includes('access_token');

      if (isOAuthCallback && user && !hasCheckedOAuthOnboarding) {
        console.log('🔍 OAuth callback detected, waiting for profile to load...');
        // Wait for profile to load before checking onboarding
        const checkProfile = setInterval(() => {
          if (profile !== undefined) { // Profile has been loaded (could be null or object)
            console.log('✅ Profile loaded after OAuth, checking onboarding status:', {
              hasProfile: !!profile,
              onboardingCompleted: profile?.onboarding_completed,
              needsOnboarding
            });
            setHasCheckedOAuthOnboarding(true);
            clearInterval(checkProfile);

            // If onboarding is needed, ensure it's shown
            if (needsOnboarding) {
              console.log('📋 User needs onboarding after OAuth login - will show onboarding form');
            } else {
              console.log('✅ User onboarding already completed - allowing chatbot access');
            }
          }
        }, 100);

        // Timeout after 5 seconds
        const timeoutId = setTimeout(() => {
          clearInterval(checkProfile);
          setHasCheckedOAuthOnboarding(true);
          console.log('⏱️ OAuth profile check timeout - proceeding with current state');
        }, 5000);

        return () => {
          clearInterval(checkProfile);
          clearTimeout(timeoutId);
        };
      }
    }, [user, profile, needsOnboarding, hasCheckedOAuthOnboarding]);

    // Calculate dropdown position when it opens
    useEffect(() => {
      if (isProfileDropdownOpen) {
        // Use setTimeout to ensure DOM is fully updated and dropdown is rendered
        const timeoutId = setTimeout(() => {
          // Find the appropriate settings button based on device type
          const allSettingsButtons = document.querySelectorAll('[data-settings-button]') as NodeListOf<HTMLElement>;
          let settingsButton: HTMLElement | null = null;

          if (isDesktop) {
            // Desktop: Find the desktop button (not in mobile-only section)
            allSettingsButtons.forEach(btn => {
              const parentHasHidden = btn.closest('.lg\\:hidden');
              // Desktop button should not be in a mobile-only section and should be visible
              if (!parentHasHidden && btn.offsetParent !== null) {
                settingsButton = btn;
              }
            });
          } else {
            // Mobile: Find the mobile button (in mobile-only section)
            allSettingsButtons.forEach(btn => {
              const parentHasHidden = btn.closest('.lg\\:hidden');
              // Mobile button should be in a mobile-only section and should be visible
              if (parentHasHidden && btn.offsetParent !== null) {
                settingsButton = btn;
              }
            });
          }

          // Fallback: try the first visible button
          if (!settingsButton && allSettingsButtons.length > 0) {
            allSettingsButtons.forEach(btn => {
              if (btn.offsetParent !== null) {
                settingsButton = btn;
              }
            });
          }

          if (settingsButton) {
            const rect = (settingsButton as HTMLElement).getBoundingClientRect();
            const dropdownWidth = 224; // w-56 = 224px
            const dropdownHeight = 220; // Approximate height
            const gap = 12;

            // Declare variables before if-else so they're available for console.log
            let newTop: number;
            let newLeft: number;

            if (isDesktop) {
              // Desktop: Position to the RIGHT of the button (not overlapping)
              // Align top of dropdown with top of button for natural alignment
              newLeft = rect.right + gap;
              newTop = rect.top;

              // Check if dropdown would go off-screen to the right
              if (newLeft + dropdownWidth > window.innerWidth - gap) {
                // Position to the LEFT of the button instead
                newLeft = rect.left - dropdownWidth - gap;
              }

              // Ensure dropdown doesn't go off-screen to the left
              if (newLeft < gap) {
                newLeft = gap;
              }

              // Ensure dropdown doesn't go off-screen to the top
              if (newTop < gap) {
                newTop = gap;
              }

              // Ensure dropdown doesn't go off-screen to the bottom
              if (newTop + dropdownHeight > window.innerHeight - gap) {
                newTop = window.innerHeight - dropdownHeight - gap;
              }
            } else {
              // Mobile: Position ABOVE the settings button (which is at bottom of sidebar)
              // Align left edge with button's left edge
              newTop = rect.top - dropdownHeight - gap;
              newLeft = rect.left;

              // Ensure dropdown doesn't go off-screen to the left
              if (newLeft < gap) {
                newLeft = gap;
              }

              // Ensure dropdown doesn't go off-screen to the right
              if (newLeft + dropdownWidth > window.innerWidth - gap) {
                newLeft = window.innerWidth - dropdownWidth - gap;
              }

              // If not enough space above the button, position below instead
              if (newTop < gap) {
                newTop = rect.bottom + gap;
              }

              // Ensure dropdown doesn't go off-screen to the bottom
              if (newTop + dropdownHeight > window.innerHeight - gap) {
                newTop = Math.max(gap, window.innerHeight - dropdownHeight - gap);
              }
            }

            // Fixed positioning uses viewport coordinates (no scroll offset needed)
            setDropdownPosition({
              top: newTop,
              left: newLeft
            });

            console.log('📍 Dropdown position calculated:', {
              device: isDesktop ? 'desktop' : 'mobile',
              buttonTop: rect.top,
              buttonBottom: rect.bottom,
              buttonLeft: rect.left,
              buttonRight: rect.right,
              buttonHeight: rect.height,
              calculatedTop: newTop,
              calculatedLeft: newLeft,
              viewportWidth: window.innerWidth,
              viewportHeight: window.innerHeight
            });
          } else {
            console.warn('⚠️ Settings button not found. Using fallback position.');
            // Fallback positions (viewport coordinates for fixed positioning)
            if (isDesktop) {
              setDropdownPosition({
                top: 20,
                left: 280 // Sidebar width (256px) + gap (24px)
              });
            } else {
              // Position near bottom center for mobile fallback
              setDropdownPosition({
                top: window.innerHeight - 250,
                left: (window.innerWidth - 224) / 2 // Center horizontally
              });
            }
          }
        }, 100); // Delay to ensure everything is rendered

        return () => clearTimeout(timeoutId);
      }
    }, [isProfileDropdownOpen, isDesktop]);

    // Handle click outside to close profile dropdown
    useEffect(() => {
      const handleClickOutside = (event: MouseEvent | TouchEvent) => {
        const target = event.target as HTMLElement;
        // Don't close if clicking on settings button or logout button
        if (
          target.closest('[aria-label="Settings"]') ||
          target.closest('[data-settings-button]') ||
          target.closest('button[class*="text-red-600"]') // Logout button
        ) {
          return;
        }
        // Don't close if clicking inside the dropdown
        if (profileDropdownRef.current && profileDropdownRef.current.contains(target)) {
          return;
        }
        // Close if clicking outside
        if (isProfileDropdownOpen) {
          setIsProfileDropdownOpen(false);
        }
      };

      if (isProfileDropdownOpen) {
        // Use setTimeout to prevent immediate closure when clicking the button
        const timeoutId = setTimeout(() => {
          document.addEventListener('mousedown', handleClickOutside);
          document.addEventListener('touchstart', handleClickOutside);
        }, 150); // Increased delay for mobile

        return () => {
          clearTimeout(timeoutId);
          document.removeEventListener('mousedown', handleClickOutside);
          document.removeEventListener('touchstart', handleClickOutside);
        };
      }
    }, [isProfileDropdownOpen]);

    // Show loading state while providers are initializing
    // CRITICAL: Only show loading screen on initial load, not when sending messages in existing chat
    // Once we have an active session with messages, never show loading screen again (prevents blinking when sending inbuilt queries)
    const activeSession = getActiveSession();
    const hasActiveSession = !!activeSession;
    const hasMessages = activeSession?.messages && activeSession.messages.length > 0;

    // Track if we've ever had a session with messages - once we have, never show loading screen again
    // BUT: Still respect minimum loading time on page refresh
    if (hasActiveSession && hasMessages && !hasEverHadSessionRef.current) {
      hasEverHadSessionRef.current = true;
      // Don't set isFullyInitialized immediately - let the minimum loading time logic handle it
      // This ensures logged-in users also get the 2-second delay on refresh
      console.log('✅ Active session with messages detected - will respect minimum loading time');
    }

    // Also check if we have messages even if session just appeared
    if (hasActiveSession && hasMessages) {
      hasEverHadSessionRef.current = true;
    }

    // Show loading if:
    // 1. Auth is still loading, OR
    // 2. Not fully initialized yet (enforces minimum 2-second delay for all users)
    // The minimum loading time is enforced regardless of session state to prevent blinking
    const shouldShowLoading = loading || !isFullyInitialized;

    if (shouldShowLoading) {
      return (
        <div className="flex min-h-screen h-screen bg-gray-50 dark:bg-gray-900">
          <main className="flex-1 flex items-center justify-center h-screen">
            <div className="w-full max-w-2xl h-full flex flex-col justify-center">
              <div className="flex justify-center mb-6">
                <Image
                  src="/prakriti_logo.webp"
                  alt="Prakriti AI Assistant"
                  width={150}
                  height={150}
                  style={{ maxWidth: '150px', height: 'auto' }}
                />
              </div>
              <div className="text-center">
                <span className="text-gray-600 dark:text-gray-300">
                  Loading Prakriti AI Assistant...
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

    // Handle sidebar query
    const handleSidebarQuery = (query: string) => {
      setSidebarQuery(query);
      // DON'T increment queryKey - it causes component remount and blinking
      // The externalQuery prop change is enough to trigger handleSuggestionClick
      // setQueryKey(prev => prev + 1); // REMOVED - causes blinking
    };

    const handleQueryProcessed = () => {
      setSidebarQuery(''); // Clear after processing
    };

    const handleLogout = (e?: React.MouseEvent) => {
      if (e) {
        e.preventDefault();
        e.stopPropagation();
      }
      console.log('🔴 handleLogout called - setting showLogoutConfirm to true');

      // Close dropdown first
      setIsProfileDropdownOpen(false);

      // Show modal after a brief delay to ensure dropdown closes
      setTimeout(() => {
        console.log('✅ Opening logout confirmation modal');
        setShowLogoutConfirm(true);
        console.log('✅ showLogoutConfirm state:', true);
      }, 50);
    };

    const confirmLogout = async () => {
      try {
        await signOut();
        setShowLogoutConfirm(false);
        // Force remount of Chatbot component to clear all state including conversation history
        setChatKey(prev => prev + 1);
        router.push('/');
      } catch (error) {
        console.error('Error signing out:', error);
        setShowLogoutConfirm(false);
      }
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
    // This check happens after OAuth callback as well, ensuring onboarding is always shown when needed
    // Allow user to skip onboarding temporarily by clicking back button
    if (user && needsOnboarding && !loading && !skipOnboarding) {
      console.log('📋 Showing onboarding form - user needs onboarding:', {
        userId: user.id,
        hasProfile: !!profile,
        onboardingCompleted: profile?.onboarding_completed,
        needsOnboarding
      });
      return (
        <OnboardingForm
          user={user}
          onComplete={() => {
            setShowAuthForm(false);
            setSkipOnboarding(false);
          }}
          onBack={async () => {
            // Logout user when they click back to chatbot
            // This prevents them from being redirected back to onboarding on refresh
            console.log('🔴 Logging out user who clicked back from onboarding');
            try {
              await signOut();
              setSkipOnboarding(false);
              // Force remount of Chatbot component to clear all state
              setChatKey(prev => prev + 1);
              router.push('/');
            } catch (error) {
              console.error('Error signing out:', error);
              // Even if logout fails, allow access to chatbot
              setSkipOnboarding(true);
            }
          }}
        />
      );
    }

    return (
      <div className={`min-h-screen h-screen ${isDesktop ? 'flex' : 'block'} ${isDesktop ? 'bg-white' : 'chat-grid-bg'} overflow-hidden relative`}>
        {/* Hamburger Menu Button - Only visible on mobile/tablet when sidebar is closed */}
        {!isSidebarOpen && (
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200 bg-white shadow-md border border-gray-300"
            aria-label="Open sidebar"
          >
            <svg
              className="w-6 h-6 text-gray-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
        )}

        {/* Profile Dropdown - Positioned relative to settings button */}
        {user && profile && isProfileDropdownOpen && (
          <>
            {/* Backdrop for mobile */}
            {!isDesktop && (
              <div
                className="fixed inset-0 bg-transparent z-[59]"
                onClick={() => setIsProfileDropdownOpen(false)}
              />
            )}
            <div className="fixed z-[60]" ref={profileDropdownRef}>
              <div
                className="w-56 bg-white rounded-lg shadow-xl border border-gray-200 py-2 animate-in fade-in-0 zoom-in-95 duration-200"
                style={{
                  top: `${dropdownPosition.top}px`,
                  left: `${dropdownPosition.left}px`,
                  transformOrigin: isDesktop ? 'left center' : 'center bottom'
                }}
              >
                {/* User Profile Header */}
                <div className="px-4 py-3 border-b border-gray-200">
                  <div className="flex items-center space-x-3">
                    {profile.profile_picture_url ? (
                      <Image
                        src={profile.profile_picture_url}
                        alt={`${profile.first_name} ${profile.last_name}`}
                        width={40}
                        height={40}
                        className="w-10 h-10 rounded-full object-cover"
                      />
                    ) : (
                      <div
                        className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold"
                        style={{ backgroundColor: profile.avatar_color || '#3B82F6' }}
                      >
                        {profile.first_name?.[0]}{profile.last_name?.[0]}
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 truncate">
                        {profile.first_name} {profile.last_name}
                      </div>
                      <div className="text-xs text-gray-500 truncate">
                        {user.email}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Menu Items */}
                <div className="py-1">
                  <button
                    onClick={() => {
                      setShowEditProfile(true);
                      setIsProfileDropdownOpen(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    Edit Profile
                  </button>
                  {profile?.admin_privileges && (
                    <button
                      onClick={() => {
                        router.push('/admin');
                        setIsProfileDropdownOpen(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                      Admin Panel
                    </button>
                  )}
                  <div className="border-t border-gray-100 my-1"></div>
                  <button
                    onClick={() => {
                      router.push('/privacy-policy');
                      setIsProfileDropdownOpen(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    Privacy Policy
                  </button>
                  <button
                    onClick={() => {
                      router.push('/terms-of-service');
                      setIsProfileDropdownOpen(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    Terms of Service
                  </button>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      console.log('🔴 Mobile logout button clicked directly');
                      handleLogout(e);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                    type="button"
                  >
                    Logout
                  </button>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Sidebar - Always open on desktop, controlled by state on mobile */}
        <ChatbotSidebar
          onQueryClick={(query) => {
            handleSidebarQuery(query);
            // Only close on mobile/tablet, not on desktop
            if (!isDesktop) {
              setIsSidebarOpen(false);
            }
          }}
          onLoginRedirect={handleLoginRedirect}
          isOpen={isDesktop ? true : isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          onSettingsClick={() => {
            console.log('🔧 Settings clicked from sidebar, toggling profile dropdown');
            setIsProfileDropdownOpen((prev) => {
              console.log('✅ Profile dropdown state:', !prev);
              return !prev;
            });
          }}
          showSettings={!!(user && profile)}
        />

        {/* Main Content Area with Grid Background */}
        <main className={`flex-1 flex overflow-hidden ${isDesktop ? 'chat-grid-bg' : ''} relative w-full h-full`}>
          <div className={`w-full h-full flex flex-col ${isDesktop ? 'relative' : 'mx-auto px-3 sm:px-4'}`}>
            {isDesktop ? (
              <div className="w-full h-full flex justify-center">
                <div className="w-[90%] max-w-[90%] h-full flex flex-col">
                  <Chatbot
                    key={chatKey}
                    ref={chatbotRef}
                    externalQuery={sidebarQuery}
                    onQueryProcessed={handleQueryProcessed}
                  />
                </div>
              </div>
            ) : (
              <Chatbot
                key={chatKey}
                ref={chatbotRef}
                externalQuery={sidebarQuery}
                onQueryProcessed={handleQueryProcessed}
              />
            )}
          </div>
        </main>

        {/* Edit Profile Modal */}
        {user && profile && (
          <EditProfileModal
            isOpen={showEditProfile}
            onClose={() => setShowEditProfile(false)}
          />
        )}

        {/* Logout Confirmation Modal */}
        <ConfirmationModal
          isOpen={showLogoutConfirm}
          onClose={() => setShowLogoutConfirm(false)}
          onConfirm={confirmLogout}
          title="Sign Out"
          message="Are you sure you want to sign out?"
          confirmText="Sign Out"
          cancelText="Cancel"
          type="warning"
        />
      </div>
    );
  };

const HomePage: React.FC = () => {
  const { user, loading, needsOnboarding } = useAuth();
  const [chatKey, setChatKey] = useState(0); // Key to force re-render of Chatbot
  const chatbotRef = useRef<{ clearChat: () => void }>(null); // Ref for chatbot component
  const [showAuthForm, setShowAuthForm] = useState(false);

  // Show chatbot for all users (public access) with proper provider initialization
  return (
    <ChatHistoryProvider>
      <AppContent
        user={user}
        loading={loading}
        needsOnboarding={needsOnboarding}
        showAuthForm={showAuthForm}
        setShowAuthForm={setShowAuthForm}
        chatbotRef={chatbotRef}
        chatKey={chatKey}
        setChatKey={setChatKey}
      />
    </ChatHistoryProvider>
  );
};

export default HomePage;
