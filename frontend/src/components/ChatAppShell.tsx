"use client";

import React, { useRef, useState, useEffect } from "react";
import Image from "next/image";
import Chatbot from "./Chatbot";
import AuthFormWithOnboarding from "./AuthFormWithOnboarding";
import OnboardingForm from "./OnboardingForm";
import ChatbotSidebar from "./ChatbotSidebar";
import EditProfileModal from "./EditProfileModal";
import ConfirmationModal from "./ConfirmationModal";
import { useAuth } from "../providers/AuthProvider";
import { ChatHistoryProvider, useChatHistory } from "../providers/ChatHistoryProvider";
import { useRouter } from "next/navigation";

export type ChatAppVariant = "default" | "chat-only";

const ChatAppShellInner: React.FC<{
  variant: ChatAppVariant;
  user: { id: string; email?: string } | null;
  loading: boolean;
  needsOnboarding: boolean;
  showAuthForm: boolean;
  setShowAuthForm: (show: boolean) => void;
  chatbotRef: React.RefObject<{ clearChat: () => void } | null>;
  chatKey: number;
  setChatKey: (key: number | ((prev: number) => number)) => void;
}> = ({
  variant,
  user,
  loading,
  needsOnboarding,
  showAuthForm,
  setShowAuthForm,
  chatbotRef,
  chatKey,
  setChatKey,
}) => {
  const chatOnly = variant === "chat-only";
  const homePath = chatOnly ? "/chat" : "/";
  const { isLoading: chatHistoryLoading, getActiveSession, activeSessionId } = useChatHistory();
  const { profile, signOut } = useAuth();
  const router = useRouter();
  const [isFullyInitialized, setIsFullyInitialized] = useState(false);
  const [skipOnboarding, setSkipOnboarding] = useState(false);
  const hasEverHadSessionRef = useRef(false);
  const pageLoadTimeRef = useRef<number>(Date.now());
  const [sidebarQuery, setSidebarQuery] = useState<string>("");
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 20, left: 280 });
  const profileDropdownRef = useRef<HTMLDivElement>(null);
  const [hasCheckedOAuthOnboarding, setHasCheckedOAuthOnboarding] = useState(false);

  useEffect(() => {
    const checkScreenSize = () => {
      const desktop = window.innerWidth >= 1024;
      setIsDesktop(desktop);
      if (desktop) {
        setIsSidebarOpen(true);
      }
    };

    checkScreenSize();
    window.addEventListener("resize", checkScreenSize);
    return () => window.removeEventListener("resize", checkScreenSize);
  }, []);

  useEffect(() => {
    const activeSession = getActiveSession();
    const hasMessages = activeSession?.messages && activeSession.messages.length > 0;
    if (activeSession && hasMessages && !hasEverHadSessionRef.current) {
      hasEverHadSessionRef.current = true;
      console.log("✅ Active session with messages detected - will respect minimum loading time");
    }
  }, [getActiveSession, activeSessionId]);

  useEffect(() => {
    if (!loading && !chatHistoryLoading) {
      const minLoadingTime = 2000;
      const elapsed = Date.now() - pageLoadTimeRef.current;
      const remainingTime = Math.max(0, minLoadingTime - elapsed);

      console.log(`Loading states completed. Elapsed: ${elapsed}ms, Remaining: ${remainingTime}ms`);

      if (remainingTime > 0) {
        console.log(`Waiting ${remainingTime}ms to reach minimum loading time (2 seconds)`);
        const timer = setTimeout(() => {
          console.log("Minimum loading time (2 seconds) elapsed, initializing app");
          setIsFullyInitialized(true);
        }, remainingTime);

        return () => clearTimeout(timer);
      } else {
        console.log("Already past minimum loading time, initializing app");
        setIsFullyInitialized(true);
      }
    }
  }, [loading, chatHistoryLoading]);

  useEffect(() => {
    const fallbackTimer = setTimeout(() => {
      console.log("Fallback timeout - forcing initialization");
      setIsFullyInitialized(true);
    }, 2000);

    return () => clearTimeout(fallbackTimer);
  }, []);

  useEffect(() => {
    console.log("Loading states:", { loading, chatHistoryLoading, isFullyInitialized });
  }, [loading, chatHistoryLoading, isFullyInitialized]);

  useEffect(() => {
    if (user) {
      const currentUserId = user.id;
      const previousCheck = sessionStorage.getItem("oauth_check_user");
      if (previousCheck !== currentUserId) {
        setHasCheckedOAuthOnboarding(false);
        sessionStorage.setItem("oauth_check_user", currentUserId);
      }
    }
  }, [user]);

  useEffect(() => {
    const isOAuthCallback = typeof window !== "undefined" && window.location.hash.includes("access_token");

    if (isOAuthCallback && user && !hasCheckedOAuthOnboarding) {
      console.log("🔍 OAuth callback detected, waiting for profile to load...");
      const checkProfile = setInterval(() => {
        if (profile !== undefined) {
          console.log("✅ Profile loaded after OAuth, checking onboarding status:", {
            hasProfile: !!profile,
            onboardingCompleted: profile?.onboarding_completed,
            needsOnboarding,
          });
          setHasCheckedOAuthOnboarding(true);
          clearInterval(checkProfile);

          if (needsOnboarding) {
            console.log("📋 User needs onboarding after OAuth login - will show onboarding form");
          } else {
            console.log("✅ User onboarding already completed - allowing chatbot access");
          }
        }
      }, 100);

      const timeoutId = setTimeout(() => {
        clearInterval(checkProfile);
        setHasCheckedOAuthOnboarding(true);
        console.log("⏱️ OAuth profile check timeout - proceeding with current state");
      }, 5000);

      return () => {
        clearInterval(checkProfile);
        clearTimeout(timeoutId);
      };
    }
  }, [user, profile, needsOnboarding, hasCheckedOAuthOnboarding]);

  useEffect(() => {
    if (isProfileDropdownOpen) {
      const timeoutId = setTimeout(() => {
        const allSettingsButtons = document.querySelectorAll("[data-settings-button]") as NodeListOf<HTMLElement>;
        let settingsButton: HTMLElement | null = null;

        if (isDesktop) {
          allSettingsButtons.forEach((btn) => {
            const parentHasHidden = btn.closest(".lg\\:hidden");
            if (!parentHasHidden && btn.offsetParent !== null) {
              settingsButton = btn;
            }
          });
        } else {
          allSettingsButtons.forEach((btn) => {
            const parentHasHidden = btn.closest(".lg\\:hidden");
            if (parentHasHidden && btn.offsetParent !== null) {
              settingsButton = btn;
            }
          });
        }

        if (!settingsButton && allSettingsButtons.length > 0) {
          allSettingsButtons.forEach((btn) => {
            if (btn.offsetParent !== null) {
              settingsButton = btn;
            }
          });
        }

        if (settingsButton) {
          const rect = (settingsButton as HTMLElement).getBoundingClientRect();
          const dropdownWidth = 224;
          const dropdownHeight = 220;
          const gap = 12;

          let newTop: number;
          let newLeft: number;

          if (isDesktop) {
            newLeft = rect.right + gap;
            newTop = rect.top;

            if (newLeft + dropdownWidth > window.innerWidth - gap) {
              newLeft = rect.left - dropdownWidth - gap;
            }

            if (newLeft < gap) {
              newLeft = gap;
            }

            if (newTop < gap) {
              newTop = gap;
            }

            if (newTop + dropdownHeight > window.innerHeight - gap) {
              newTop = window.innerHeight - dropdownHeight - gap;
            }
          } else {
            newTop = rect.top - dropdownHeight - gap;
            newLeft = rect.left;

            if (newLeft < gap) {
              newLeft = gap;
            }

            if (newLeft + dropdownWidth > window.innerWidth - gap) {
              newLeft = window.innerWidth - dropdownWidth - gap;
            }

            if (newTop < gap) {
              newTop = rect.bottom + gap;
            }

            if (newTop + dropdownHeight > window.innerHeight - gap) {
              newTop = Math.max(gap, window.innerHeight - dropdownHeight - gap);
            }
          }

          setDropdownPosition({
            top: newTop,
            left: newLeft,
          });

          console.log("📍 Dropdown position calculated:", {
            device: isDesktop ? "desktop" : "mobile",
            buttonTop: rect.top,
            calculatedTop: newTop,
            calculatedLeft: newLeft,
          });
        } else {
          console.warn("⚠️ Settings button not found. Using fallback position.");
          if (isDesktop) {
            setDropdownPosition({
              top: 20,
              left: chatOnly ? Math.max(12, window.innerWidth - 224 - 12) : 280,
            });
          } else {
            setDropdownPosition({
              top: window.innerHeight - 250,
              left: (window.innerWidth - 224) / 2,
            });
          }
        }
      }, 100);

      return () => clearTimeout(timeoutId);
    }
  }, [isProfileDropdownOpen, isDesktop, chatOnly]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent | TouchEvent) => {
      const target = event.target as HTMLElement;
      if (
        target.closest('[aria-label="Settings"]') ||
        target.closest("[data-settings-button]") ||
        target.closest('button[class*="text-red-600"]')
      ) {
        return;
      }
      if (profileDropdownRef.current && profileDropdownRef.current.contains(target)) {
        return;
      }
      if (isProfileDropdownOpen) {
        setIsProfileDropdownOpen(false);
      }
    };

    if (isProfileDropdownOpen) {
      const timeoutId = setTimeout(() => {
        document.addEventListener("mousedown", handleClickOutside);
        document.addEventListener("touchstart", handleClickOutside);
      }, 150);

      return () => {
        clearTimeout(timeoutId);
        document.removeEventListener("mousedown", handleClickOutside);
        document.removeEventListener("touchstart", handleClickOutside);
      };
    }
  }, [isProfileDropdownOpen]);

  const activeSession = getActiveSession();
  const hasActiveSession = !!activeSession;
  const hasMessages = activeSession?.messages && activeSession.messages.length > 0;

  if (hasActiveSession && hasMessages && !hasEverHadSessionRef.current) {
    hasEverHadSessionRef.current = true;
    console.log("✅ Active session with messages detected - will respect minimum loading time");
  }

  if (hasActiveSession && hasMessages) {
    hasEverHadSessionRef.current = true;
  }

  const shouldShowLoading = loading || !isFullyInitialized;

  if (shouldShowLoading) {
    return (
      <div id="chat-app-root" className="flex min-h-screen h-screen bg-gray-50 dark:bg-gray-900">
        <main className="flex-1 flex items-center justify-center h-screen">
          <div className="w-full max-w-2xl h-full flex flex-col justify-center">
            <div className="flex justify-center mb-6">
              <Image
                src="/prakriti_logo.webp"
                alt="Prakriti AI Assistant"
                width={150}
                height={150}
                style={{ maxWidth: "150px", height: "auto" }}
              />
            </div>
            <div className="text-center">
              <span className="text-gray-600 dark:text-gray-300">Loading Prakriti AI Assistant...</span>
            </div>
          </div>
        </main>
      </div>
    );
  }

  const handleLoginRedirect = () => {
    setShowAuthForm(true);
  };

  const handleSidebarQuery = (query: string) => {
    setSidebarQuery(query);
  };

  const handleQueryProcessed = () => {
    setSidebarQuery("");
  };

  const handleLogout = (e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    console.log("🔴 handleLogout called - setting showLogoutConfirm to true");

    setIsProfileDropdownOpen(false);

    setTimeout(() => {
      console.log("✅ Opening logout confirmation modal");
      setShowLogoutConfirm(true);
    }, 50);
  };

  const confirmLogout = async () => {
    try {
      await signOut();
      setShowLogoutConfirm(false);
      setChatKey((prev) => prev + 1);
      router.push(homePath);
    } catch (error) {
      console.error("Error signing out:", error);
      setShowLogoutConfirm(false);
    }
  };

  if (showAuthForm && (!user || needsOnboarding)) {
    return (
      <AuthFormWithOnboarding
        onBack={() => setShowAuthForm(false)}
      />
    );
  }

  if (user && needsOnboarding && !loading && !skipOnboarding) {
    console.log("📋 Showing onboarding form - user needs onboarding:", {
      userId: user.id,
      hasProfile: !!profile,
      onboardingCompleted: profile?.onboarding_completed,
      needsOnboarding,
    });
    return (
      <OnboardingForm
        user={user}
        onComplete={() => {
          setShowAuthForm(false);
          setSkipOnboarding(false);
        }}
        onBack={async () => {
          console.log("🔴 Logging out user who clicked back from onboarding");
          try {
            await signOut();
            setSkipOnboarding(false);
            setChatKey((prev) => prev + 1);
            router.push(homePath);
          } catch (error) {
            console.error("Error signing out:", error);
            setSkipOnboarding(true);
          }
        }}
      />
    );
  }

  const rootClass = chatOnly
    ? `h-screen min-h-0 flex flex-col overflow-hidden ${isDesktop ? "bg-white" : "chat-grid-bg"} relative`
    : `h-screen min-h-0 flex flex-col overflow-hidden lg:flex-row ${isDesktop ? "bg-white" : "chat-grid-bg"} relative`;

  const externalQuery = chatOnly ? "" : sidebarQuery;

  return (
    <div id="chat-app-root" className={rootClass}>
      {chatOnly && !user && (
        <button
          type="button"
          onClick={() => setShowAuthForm(true)}
          className="fixed top-3 right-3 z-[55] rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-md hover:bg-gray-50"
        >
          Sign in
        </button>
      )}

      {chatOnly && user && profile && (
        <button
          type="button"
          data-settings-button
          aria-label="Settings"
          onClick={() => setIsProfileDropdownOpen((prev) => !prev)}
          className="fixed top-3 right-3 z-[55] flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 bg-white shadow-md hover:bg-gray-50"
        >
          <svg className="h-5 w-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      )}

      {!chatOnly && !isSidebarOpen && (
        <div className="lg:hidden fixed top-4 left-0 right-0 z-50 flex items-center justify-between px-4 pointer-events-none">
          <Image
            src="/prakriti_logo.webp"
            alt="Prakriti"
            width={52}
            height={52}
            className="h-12 w-auto max-w-[150px] object-contain object-left drop-shadow-sm pointer-events-auto"
            priority
          />
          <button
            type="button"
            onClick={() => setIsSidebarOpen(true)}
            className="pointer-events-auto p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200 bg-white shadow-md border border-gray-300"
            aria-label="Open sidebar"
          >
            <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      )}

      {user && profile && isProfileDropdownOpen && (
        <>
          {!isDesktop && (
            <div className="fixed inset-0 bg-transparent z-[59]" onClick={() => setIsProfileDropdownOpen(false)} />
          )}
          <div className="fixed z-[60]" ref={profileDropdownRef}>
            <div
              className="w-56 bg-white rounded-lg shadow-xl border border-gray-200 py-2 animate-in fade-in-0 zoom-in-95 duration-200"
              style={{
                top: `${dropdownPosition.top}px`,
                left: `${dropdownPosition.left}px`,
                transformOrigin: isDesktop ? "left center" : "center bottom",
              }}
            >
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
                      style={{ backgroundColor: profile.avatar_color || "#3B82F6" }}
                    >
                      {profile.first_name?.[0]}
                      {profile.last_name?.[0]}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900 truncate">
                      {profile.first_name} {profile.last_name}
                    </div>
                    <div className="text-xs text-gray-500 truncate">{user.email}</div>
                  </div>
                </div>
              </div>

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
                      router.push("/admin");
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
                    router.push("/privacy-policy");
                    setIsProfileDropdownOpen(false);
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  Privacy Policy
                </button>
                <button
                  onClick={() => {
                    router.push("/terms-of-service");
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

      {!chatOnly && (
        <ChatbotSidebar
          onQueryClick={(query) => {
            handleSidebarQuery(query);
            if (!isDesktop) {
              setIsSidebarOpen(false);
            }
          }}
          onLoginRedirect={handleLoginRedirect}
          isOpen={isDesktop ? true : isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          onSettingsClick={() => {
            setIsProfileDropdownOpen((prev) => !prev);
          }}
          showSettings={!!(user && profile)}
        />
      )}

      <main
        className={`flex min-h-0 min-w-0 flex-1 overflow-hidden ${isDesktop ? "chat-grid-bg" : ""} relative h-full w-full`}
      >
        <div className={`flex h-full min-h-0 w-full flex-col ${isDesktop ? "relative" : "mx-auto px-3 sm:px-4"}`}>
          {isDesktop ? (
            <div className="flex h-full w-full justify-center">
              <div className="flex h-full w-[90%] max-w-[90%] flex-col">
                <Chatbot
                  key={chatKey}
                  ref={chatbotRef}
                  externalQuery={externalQuery}
                  onQueryProcessed={handleQueryProcessed}
                />
              </div>
            </div>
          ) : (
            <Chatbot
              key={chatKey}
              ref={chatbotRef}
              externalQuery={externalQuery}
              onQueryProcessed={handleQueryProcessed}
            />
          )}
        </div>
      </main>

      {user && profile && (
        <EditProfileModal
          isOpen={showEditProfile}
          onClose={() => setShowEditProfile(false)}
        />
      )}

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

export const ChatAppShell: React.FC<{ variant: ChatAppVariant }> = ({ variant }) => {
  const { user, loading, needsOnboarding } = useAuth();
  const [chatKey, setChatKey] = useState(0);
  const chatbotRef = useRef<{ clearChat: () => void }>(null);
  const [showAuthForm, setShowAuthForm] = useState(false);

  return (
    <ChatHistoryProvider>
      <ChatAppShellInner
        variant={variant}
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
