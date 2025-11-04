"use client";
import React, { useState } from 'react';
import { useAuth } from '@/providers/AuthProvider';
import { useChatHistory } from '@/providers/ChatHistoryProvider';
import { generateChatName } from '@/utils/chatNameGenerator';

interface ChatbotSidebarProps {
  onQueryClick: (query: string) => void;
  onLoginRedirect?: () => void;
  isOpen?: boolean;
  onClose?: () => void;
  onSettingsClick?: () => void;
  showSettings?: boolean;
}

const ChatbotSidebar: React.FC<ChatbotSidebarProps> = ({ onQueryClick, onLoginRedirect, isOpen = true, onClose, onSettingsClick, showSettings = false }) => {
  const { user } = useAuth();
  const { 
    sessions, 
    activeSessionId, 
    createNewSession, 
    switchToSession, 
    isLoading: chatHistoryLoading
  } = useChatHistory();
  
  const [showMoreQueries, setShowMoreQueries] = useState(false);
  
  // Built-in query collection
  const primaryQueries = [
    "Help with homework",
    "Explain a concept",
    "Study tips",
    "School schedule"
  ];
  
  const additionalQueries = [
    "Assignment help",
    "Math problems",
    "Science questions",
    "History facts",
    "Prakriti School info",
    "Progressive education",
    "Learning for happiness",
    "IGCSE curriculum"
  ];
  
  const handleQueryClick = (query: string) => {
    onQueryClick(query);
  };
  
  const handleNewChat = async () => {
    if (!user) {
      if (onLoginRedirect) {
        onLoginRedirect();
      }
      return;
    }
    await createNewSession();
  };
  
  const handleSessionClick = async (sessionId: string) => {
    if (!user) {
      if (onLoginRedirect) {
        onLoginRedirect();
      }
      return;
    }
    await switchToSession(sessionId);
  };
  
  const handleLoginClick = () => {
    if (onLoginRedirect) {
      onLoginRedirect();
    }
  };
  
  const formatDate = (timestamp: string | number) => {
    const date = new Date(typeof timestamp === 'string' ? timestamp : timestamp);
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);
    
    if (diffInHours < 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffInHours < 168) { // 7 days
      return date.toLocaleDateString([], { weekday: 'short' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };
  
  // Get recent sessions (last 10)
  const recentSessions = sessions.slice(0, 10);
  
  const showOverlay = isOpen && Boolean(onClose);
  
  return (
    <>
      {/* Transparent overlay for mobile - allows clicking outside to close without darkening */}
      {showOverlay ? (
        <div 
          className="fixed inset-0 bg-transparent z-40 lg:hidden"
          onClick={onClose}
        />
      ) : null}
      <div 
        className={`fixed lg:static top-0 left-0 w-64 h-screen bg-white border-r border-gray-200 flex flex-col sidebar-grid-bg z-50 transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Close button for mobile */}
        {onClose && (
          <div className="lg:hidden flex justify-between items-center p-4 border-b border-gray-200">
            <div className="flex items-center gap-3">
              {/* Logo */}
              <div className="w-10 h-10 flex items-center justify-center flex-shrink-0">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img 
                  src="/prakriti_logo.webp" 
                  alt="Prakriti School Logo" 
                  className="w-full h-full object-contain"
                />
              </div>
              {/* Brand Name */}
              <div>
                <div className="font-semibold text-gray-900 text-base">Prakriti School</div>
                <div className="text-xs text-gray-500">AI Assistant</div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200 border border-gray-300"
              aria-label="Close sidebar"
            >
              <svg 
                className="w-5 h-5 text-gray-600" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M6 18L18 6M6 6l12 12" 
                />
              </svg>
            </button>
          </div>
        )}
      {/* Top Section - Logo and Branding - Hidden on mobile when close button is shown */}
      <div className={`p-4 border-b border-gray-200 ${onClose ? 'lg:block hidden' : 'block'}`}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            {/* Logo */}
            <div className="w-10 h-10 flex items-center justify-center flex-shrink-0">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img 
                src="/prakriti_logo.webp" 
                alt="Prakriti School Logo" 
                className="w-full h-full object-contain"
              />
            </div>
            {/* Brand Name */}
            <div>
              <div className="font-semibold text-gray-900 text-base">Prakriti School</div>
              <div className="text-xs text-gray-500">AI Assistant</div>
            </div>
          </div>
          
          {/* Settings Button - Desktop Only */}
          {user && showSettings && onSettingsClick && (
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('🔧 Sidebar settings button clicked');
                onSettingsClick();
              }}
              className="hidden lg:flex p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200"
              aria-label="Settings"
              title="Settings"
              data-settings-button
              type="button"
            >
              <svg 
                className="w-5 h-5 text-gray-600" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" 
                />
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" 
                />
              </svg>
            </button>
          )}
        </div>
      </div>
      
      {/* Built-in Query Collection */}
      <div className="flex-1 overflow-y-auto px-4 py-4 sidebar-scrollbar">
        <div className="space-y-1">
          {primaryQueries.map((query, index) => (
            <button
              key={index}
              onClick={() => handleQueryClick(query)}
              className="w-full text-left px-3 py-2 text-sm transition-colors duration-150 rounded-md"
              style={{
                color: 'var(--brand-primary)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--brand-primary-50)';
                e.currentTarget.style.color = 'var(--brand-primary-800)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = 'var(--brand-primary)';
              }}
            >
              {query}
            </button>
          ))}
          
          {/* See more link */}
          {!showMoreQueries && (
            <button
              onClick={() => setShowMoreQueries(true)}
              className="w-full text-left px-3 py-2 text-sm rounded-md transition-colors duration-150"
              style={{
                color: 'var(--brand-secondary-600)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = 'var(--brand-secondary-700)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = 'var(--brand-secondary-600)';
              }}
            >
              See more
            </button>
          )}
          
          {/* Additional queries when "See more" is clicked */}
          {showMoreQueries && (
            <>
              {additionalQueries.map((query, index) => (
                <button
                  key={index}
                  onClick={() => handleQueryClick(query)}
                  className="w-full text-left px-3 py-2 text-sm transition-colors duration-150 rounded-md"
                  style={{
                    color: 'var(--brand-primary)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--brand-primary-50)';
                    e.currentTarget.style.color = 'var(--brand-primary-800)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = 'var(--brand-primary)';
                  }}
                >
                  {query}
                </button>
              ))}
              <button
                onClick={() => setShowMoreQueries(false)}
                className="w-full text-left px-3 py-2 text-sm rounded-md transition-colors duration-150"
                style={{
                  color: 'var(--brand-secondary-600)',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = 'var(--brand-secondary-700)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = 'var(--brand-secondary-600)';
                }}
              >
                Show less
              </button>
            </>
          )}
        </div>
        
        {/* Chat History Section */}
        {user && (
          <div className="mt-6 pt-6 border-t border-gray-200">
            <div className="flex items-center justify-between mb-3">
              <h3 
                className="text-xs font-semibold uppercase tracking-wider"
                style={{ color: 'var(--brand-primary-600)' }}
              >
                Chat History
              </h3>
              <button
                onClick={handleNewChat}
                className="text-xs font-medium transition-colors duration-150"
                style={{ color: 'var(--brand-secondary-600)' }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = 'var(--brand-secondary-700)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = 'var(--brand-secondary-600)';
                }}
              >
                New
              </button>
            </div>
            
            {chatHistoryLoading ? (
              <div className="text-xs text-gray-400 py-2">Loading...</div>
            ) : recentSessions.length === 0 ? (
              <div className="text-xs text-gray-400 py-2">No chat history</div>
            ) : (
              <div className="space-y-1">
                {recentSessions.map((session) => {
                  // Generate display title - use generated name if title is still "New Chat"
                  const displayTitle = session.title === 'New Chat' ? generateChatName(session.messages) : session.title;
                  return (
                    <button
                      key={session.id}
                      onClick={() => handleSessionClick(session.id)}
                      className={`w-full text-left px-3 py-2 text-sm rounded-md transition-colors duration-150 truncate ${
                        activeSessionId === session.id
                          ? 'font-medium'
                          : ''
                      }`}
                      style={{
                        backgroundColor: activeSessionId === session.id ? 'var(--brand-primary-50)' : 'transparent',
                        color: activeSessionId === session.id ? 'var(--brand-primary-800)' : 'var(--brand-primary)',
                      }}
                      onMouseEnter={(e) => {
                        if (activeSessionId !== session.id) {
                          e.currentTarget.style.backgroundColor = 'var(--brand-primary-50)';
                          e.currentTarget.style.color = 'var(--brand-primary-800)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (activeSessionId !== session.id) {
                          e.currentTarget.style.backgroundColor = 'transparent';
                          e.currentTarget.style.color = 'var(--brand-primary)';
                        }
                      }}
                      title={displayTitle}
                    >
                      <div className="flex items-center justify-between">
                        <span className="truncate">{displayTitle}</span>
                        <span className="text-xs text-gray-400 ml-2 flex-shrink-0">
                          {formatDate(session.updated_at)}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Bottom Section - Login Button or Settings */}
      <div className="p-4 border-t border-gray-200">
        {!user ? (
          <button
            onClick={handleLoginClick}
            className="w-full flex items-center gap-3 px-4 py-2.5 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition-colors duration-150"
          >
            <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center flex-shrink-0">
              <span className="text-white font-semibold text-sm">N</span>
            </div>
            <span className="font-medium">Login</span>
          </button>
        ) : (
          user && showSettings && onSettingsClick && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSettingsClick();
              }}
              className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg hover:bg-gray-100 transition-colors duration-150 border border-gray-300 lg:hidden"
              aria-label="Settings"
              data-settings-button
            >
              <div className="p-2 rounded-lg bg-gray-100">
                <svg 
                  className="w-5 h-5 text-gray-600" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" 
                  />
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" 
                  />
                </svg>
              </div>
              <span className="font-medium text-gray-700">Settings</span>
            </button>
          )
        )}
      </div>
    </div>
    </>
  );
};

export default ChatbotSidebar;

