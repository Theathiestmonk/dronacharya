"use client";
import React, { useRef, useState, useEffect } from 'react';
import Chatbot from '../components/Chatbot';
import AuthFormWithOnboarding from '../components/AuthFormWithOnboarding';
import OnboardingForm from '../components/OnboardingForm';
import ChatbotSidebar from '../components/ChatbotSidebar';
import EditProfileModal from '../components/EditProfileModal';
import ConfirmationModal from '../components/ConfirmationModal';
import { useAuth } from '../providers/AuthProvider';
import { ChatHistoryProvider, useChatHistory } from '../providers/ChatHistoryProvider';
import { useSupabase } from '../providers/SupabaseProvider';
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
  const { profile, signOut } = useAuth();
  const router = useRouter();
  const [isFullyInitialized, setIsFullyInitialized] = useState(false);
  const [sidebarQuery, setSidebarQuery] = useState<string>('');
  const [queryKey, setQueryKey] = useState(0);
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false); // For mobile sidebar toggle
  const [isDesktop, setIsDesktop] = useState(false); // Track if we're on desktop
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 20, left: 280 });
  const profileDropdownRef = useRef<HTMLDivElement>(null);

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

  // Improved loading logic - wait for auth and chat history
  useEffect(() => {
    if (!loading && !chatHistoryLoading) {
      console.log('Auth and chat history loading completed, initializing app');
      setIsFullyInitialized(true);
    }
  }, [loading, chatHistoryLoading]);

  // Reduced fallback timeout to prevent long demo display
  useEffect(() => {
    const fallbackTimer = setTimeout(() => {
      console.log('Fallback timeout - forcing initialization');
      setIsFullyInitialized(true);
    }, 500); // Reduced to 500ms fallback

    return () => clearTimeout(fallbackTimer);
  }, []);

  // Debug logging
  useEffect(() => {
    console.log('Loading states:', { loading, chatHistoryLoading, isFullyInitialized });
  }, [loading, chatHistoryLoading, isFullyInitialized]);

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

  // Handle sidebar query
  const handleSidebarQuery = (query: string) => {
    setSidebarQuery(query);
    setQueryKey(prev => prev + 1); // Force re-render with new query
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
  if (user && needsOnboarding) {
    return (
      <OnboardingForm
        user={user}
        onComplete={() => setShowAuthForm(false)}
        onBack={() => setShowAuthForm(false)}
      />
    );
  }

  return (
    <div className="min-h-screen h-screen flex bg-white overflow-hidden relative">
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
                    <img
                      src={profile.profile_picture_url}
                      alt={`${profile.first_name} ${profile.last_name}`}
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
      <main className="flex-1 flex items-center justify-center overflow-hidden chat-grid-bg relative">
        <div className="w-[82.5%] max-w-[85%] h-full flex flex-col justify-center mx-auto">
          <Chatbot 
            key={`${chatKey}-${queryKey}`} 
            ref={chatbotRef} 
            externalQuery={sidebarQuery}
            onQueryProcessed={handleQueryProcessed}
          />
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
  );
};

export default HomePage;
