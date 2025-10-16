"use client";
import React, { useState, useEffect } from 'react';
import { useAuth } from '@/providers/AuthProvider';
import { useChatHistory } from '@/providers/ChatHistoryProvider';
import { useRouter } from 'next/navigation';
import UserAvatarDropdown from './UserAvatarDropdown';
import EditProfileModal from './EditProfileModal';
import ConfirmationModal from './ConfirmationModal';
import Image from 'next/image';

interface ChatGPTLayoutProps {
  children: React.ReactNode;
  onLoginRedirect?: () => void;
}

const ChatGPTLayout: React.FC<ChatGPTLayoutProps> = ({ children, onLoginRedirect }) => {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const { 
    sessions, 
    activeSessionId, 
    createNewSession, 
    switchToSession, 
    deleteSession, 
    updateSessionTitle,
    isLoading: chatHistoryLoading
  } = useChatHistory();
  
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [showSessionMenu, setShowSessionMenu] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true); // Start hidden by default
  const [showChatHistoryDropdown, setShowChatHistoryDropdown] = useState(false); // For dropdown menu
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });

  // Close session menu and chat history when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      
      // Check if click is outside chat history popup
      if (showChatHistoryDropdown) {
        const chatHistoryPopup = document.querySelector('[data-chat-history-popup]');
        const chatHistoryButton = document.querySelector('[data-chat-history-button]');
        if (chatHistoryPopup && !chatHistoryPopup.contains(target) && 
            (!chatHistoryButton || !chatHistoryButton.contains(target))) {
          setShowChatHistoryDropdown(false);
          setShowSessionMenu(null); // Also close session menu
        }
      }
      
      // Check if click is outside edit/delete dropdown
      if (showSessionMenu) {
        const dropdown = document.querySelector('[data-session-dropdown]');
        if (dropdown && !dropdown.contains(target)) {
          setShowSessionMenu(null);
        }
      }
    };

    if (showChatHistoryDropdown || showSessionMenu) {
      document.addEventListener('click', handleClickOutside);
    }

    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, [showChatHistoryDropdown, showSessionMenu]);

  // Focus input when editing starts
  useEffect(() => {
    if (editingSessionId) {
      // Small delay to ensure the input is rendered
      setTimeout(() => {
        const input = document.querySelector('input[type="text"]') as HTMLInputElement;
        if (input) {
          input.focus();
        }
      }, 50);
    }
  }, [editingSessionId]);
  
  // Confirmation modal states
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Handle sidebar click for non-authenticated users
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const handleSidebarClick = () => {
    if (!user) {
      // Redirect to login for non-authenticated users
      if (onLoginRedirect) {
        onLoginRedirect();
      }
      return;
    }
    // Toggle sidebar for authenticated users
    setSidebarCollapsed(!sidebarCollapsed);
  };

  // Generate intelligent chat name based on context
  const generateChatName = (messages: Array<{sender: string; text: string}>) => {
    if (messages.length === 0) return 'New Chat';
    
    const firstUserMessage = messages.find(msg => msg.sender === 'user');
    if (!firstUserMessage) return 'New Chat';
    
    const text = firstUserMessage.text.toLowerCase();
    
    // Education-related topics
    if (text.includes('homework') || text.includes('assignment')) return 'Homework Help';
    if (text.includes('math') || text.includes('mathematics')) return 'Math Questions';
    if (text.includes('science') || text.includes('physics') || text.includes('chemistry') || text.includes('biology')) return 'Science Help';
    if (text.includes('english') || text.includes('literature') || text.includes('writing')) return 'English & Writing';
    if (text.includes('history') || text.includes('social studies')) return 'History & Social Studies';
    if (text.includes('art') || text.includes('drawing') || text.includes('painting')) return 'Art & Creativity';
    if (text.includes('music') || text.includes('singing') || text.includes('instrument')) return 'Music & Arts';
    if (text.includes('sports') || text.includes('physical education') || text.includes('pe')) return 'Sports & PE';
    
    // School-related topics
    if (text.includes('schedule') || text.includes('timetable')) return 'School Schedule';
    if (text.includes('exam') || text.includes('test') || text.includes('quiz')) return 'Exam Preparation';
    if (text.includes('project') || text.includes('presentation')) return 'School Project';
    if (text.includes('curriculum') || text.includes('syllabus')) return 'Curriculum Questions';
    if (text.includes('teacher') || text.includes('instructor')) return 'Teacher Communication';
    if (text.includes('parent') || text.includes('family')) return 'Parent Discussion';
    
    // General topics
    if (text.includes('hello') || text.includes('hi') || text.includes('greetings')) return 'Greeting & Introduction';
    if (text.includes('help') || text.includes('support')) return 'General Help';
    if (text.includes('question') || text.includes('ask')) return 'Questions & Answers';
    if (text.includes('explain') || text.includes('understand')) return 'Explanation Request';
    if (text.includes('study') || text.includes('learn') || text.includes('learning')) return 'Study Session';
    if (text.includes('tips') || text.includes('advice')) return 'Tips & Advice';
    
    // Prakriti-specific
    if (text.includes('prakriti') || text.includes('school')) return 'Prakriti School Info';
    if (text.includes('progressive') || text.includes('alternative')) return 'Progressive Education';
    if (text.includes('happiness') || text.includes('joy')) return 'Learning for Happiness';
    
    // Default fallback - use first few words
    const words = firstUserMessage.text.trim().split(' ').slice(0, 4);
    return words.join(' ') + (firstUserMessage.text.split(' ').length > 4 ? '...' : '');
  };

  const handleCreateNew = async () => {
    await createNewSession();
  };

  const handleSwitchSession = async (sessionId: string) => {
    await switchToSession(sessionId);
  };

  const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation(); // Prevent switching session
    console.log('Delete clicked for session:', sessionId);
    setSessionToDelete(sessionId);
    setShowDeleteConfirm(true);
  };

  const confirmDeleteSession = async () => {
    if (!sessionToDelete) return;
    
    setIsProcessing(true);
    try {
      await deleteSession(sessionToDelete);
      setShowDeleteConfirm(false);
      setSessionToDelete(null);
    } catch (error) {
      console.error('Error deleting session:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleLogout = () => {
    setShowLogoutConfirm(true);
  };

  const handleAdminAccess = () => {
    // Navigate to admin page using Next.js router
    router.push('/admin');
  };

  const confirmLogout = async () => {
    setIsProcessing(true);
    try {
      await signOut();
      setShowLogoutConfirm(false);
    } catch (error) {
      console.error('Error signing out:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleEditTitle = (e: React.MouseEvent, session: {id: string; title: string}) => {
    e.stopPropagation();
    console.log('Edit clicked for session:', session.id, 'title:', session.title);
    setEditingSessionId(session.id);
    setEditTitle(session.title);
  };

  const handleSaveTitle = async () => {
    if (editingSessionId && editTitle.trim()) {
      await updateSessionTitle(editingSessionId, editTitle.trim());
    }
    setEditingSessionId(null);
    setEditTitle('');
  };

  const handleCancelEdit = () => {
    setEditingSessionId(null);
    setEditTitle('');
  };

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp);
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

  // Filter sessions based on search query
  const filteredSessions = sessions.filter(session =>
    session.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex flex-1 bg-gray-50">
      
      {/* Chat History Dropdown */}
      {showChatHistoryDropdown && (
        <div className={`fixed top-24 sm:top-32 left-2 sm:left-4 z-50 w-72 sm:w-80 bg-white border border-gray-200 rounded-lg shadow-xl transition-all duration-200 ${chatHistoryLoading ? 'opacity-40 scale-[0.98]' : 'opacity-100 scale-100'}`} data-chat-history-popup>
          {/* Header */}
          <div className="p-3 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="font-medium text-gray-900">Chat History</h3>
              <button
                onClick={() => setShowChatHistoryDropdown(false)}
                className="p-1 hover:bg-gray-100 rounded cursor-pointer"
              >
                <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>


          {/* Search */}
          <div className="p-2 sm:p-3 border-b border-gray-200">
            <div className="relative">
              <svg className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                placeholder="Search chats"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 text-sm sm:text-base rounded-lg focus:outline-none focus:ring-1 bg-gray-50 border border-gray-200 text-gray-900 placeholder-gray-500 focus:ring-blue-400"
              />
            </div>
          </div>

          {/* Chat History List */}
          <div className="max-h-80 sm:max-h-96 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 hover:scrollbar-thumb-gray-400">
            {filteredSessions.length === 0 ? (
              <div className="text-center py-6 sm:py-8 text-gray-400">
                <p className="text-xs sm:text-sm">No chats yet</p>
              </div>
            ) : (
              <div className="p-1 sm:p-2">
                {filteredSessions
                  .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
                  .map((session) => {
                    const displayTitle = session.title === 'New Chat' ? generateChatName(session.messages) : session.title;
                    return (
                      <div
                        key={session.id}
                        className={`group relative p-2 sm:p-3 rounded-lg transition-colors ${
                          session.id === activeSessionId
                            ? 'bg-blue-50 border border-blue-200'
                            : 'hover:bg-gray-50'
                        }`}
                      >
                        {editingSessionId === session.id ? (
                          // Editing Mode
                          <div className="space-y-2 bg-gray-50 p-2 sm:p-3 rounded-lg border border-gray-200">
                            <input
                              type="text"
                              value={editTitle}
                              onChange={(e) => setEditTitle(e.target.value)}
                              className="w-full px-2 sm:px-3 py-1.5 sm:py-2 text-xs sm:text-sm bg-white border border-gray-300 rounded-md text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleSaveTitle();
                                if (e.key === 'Escape') handleCancelEdit();
                              }}
                              onBlur={(e) => {
                                // Add a small delay to prevent immediate blur when editing starts
                                setTimeout(() => {
                                  // Only save if we're not clicking on save/cancel buttons
                                  if (!e.relatedTarget || !e.relatedTarget.closest('button')) {
                                    handleSaveTitle();
                                  }
                                }, 100);
                              }}
                            />
                            <div className="flex space-x-1 sm:space-x-2">
                              <button
                                onClick={handleSaveTitle}
                                className="px-2 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 cursor-pointer"
                              >
                                Save
                              </button>
                              <button
                                onClick={handleCancelEdit}
                                className="px-2 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-1 cursor-pointer"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          // Normal Mode
                          <div 
                            className="cursor-pointer"
                            onClick={() => {
                              handleSwitchSession(session.id);
                              setShowChatHistoryDropdown(false);
                            }}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex-1 min-w-0">
                                <h4 className="text-xs sm:text-sm font-medium text-gray-900 truncate">
                                  {displayTitle}
                                  {editingSessionId === session.id && (
                                    <span className="ml-1 sm:ml-2 text-xs text-yellow-600">(EDITING)</span>
                                  )}
                                </h4>
                                <p className="text-xs text-gray-500 mt-0.5 sm:mt-1">
                                  {formatDate(new Date(session.updated_at).getTime())}
                                </p>
                              </div>
                              
                              {/* 3 Dots Menu Button */}
                              <div className="relative">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    const rect = e.currentTarget.getBoundingClientRect();
                                    setDropdownPosition({
                                      top: rect.top + window.scrollY,
                                      left: rect.right + 10 // 10px margin from the button
                                    });
                                    setShowSessionMenu(showSessionMenu === session.id ? null : session.id);
                                  }}
                                  className="p-1 hover:bg-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                                  title="More options"
                                >
                                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                                  </svg>
                                </button>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Edit/Delete Dropdown - Outside Chat History Popup */}
      {showSessionMenu && (
        <div 
          className="fixed bg-white border border-gray-200 rounded-lg shadow-xl z-[60] w-32"
          data-session-dropdown
          style={{
            top: `${dropdownPosition.top}px`,
            left: `${dropdownPosition.left}px`
          }}
        >
          <div className="py-1">
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Edit button clicked');
                setShowSessionMenu(null);
                const session = filteredSessions.find(s => s.id === showSessionMenu);
                if (session) {
                  handleEditTitle(e, session);
                }
              }}
              className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center cursor-pointer"
            >
              <svg className="w-3 h-3 mr-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Edit
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Delete button clicked');
                setShowSessionMenu(null);
                handleDeleteSession(e, showSessionMenu);
              }}
              className="w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center cursor-pointer"
            >
              <svg className="w-3 h-3 mr-2 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Delete
            </button>
          </div>
        </div>
      )}


      {/* Main Content Area */}
      <div className="flex-1 flex flex-col bg-white">
        {/* Header with User Profile - Sticky */}
        <div className="sticky top-0 z-30 border-b border-gray-200 bg-white">
          <div className="flex items-center justify-between px-3 sm:px-4 py-2 sm:py-3">
            <div className="flex items-center space-x-2 sm:space-x-3">
              <Image
                src="/prakriti_logo.webp"
                alt="Prakriti Logo"
                width={32}
                height={32}
                className="w-6 h-6 sm:w-8 sm:h-8 rounded-lg object-contain"
              />
              <h1 className="text-sm sm:text-lg font-semibold text-gray-900">Prakriti AI Assistant</h1>
            </div>
            
            {/* User Profile */}
            <div className="flex items-center space-x-1 sm:space-x-2 md:space-x-4">
              {user ? (
                <UserAvatarDropdown
                  onEditProfile={() => setShowEditProfile(true)}
                  onLogout={handleLogout}
                  onAdminAccess={handleAdminAccess}
                  sidebarCollapsed={false}
                  theme="light"
                  onDropdownToggle={setIsProfileDropdownOpen}
                />
              ) : (
                <button
                  onClick={() => onLoginRedirect && onLoginRedirect()}
                  className="px-3 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors cursor-pointer"
                >
                  Login
                </button>
              )}
            </div>
          </div>
        </div>
        
        {/* Floating Chat History Button - Only show when user is logged in */}
        {user && !showChatHistoryDropdown && (
          <div className="fixed top-20 sm:top-24 left-0 z-40" data-chat-history-button>
            <button
              onClick={() => setShowChatHistoryDropdown(true)}
              className="flex items-center space-x-1 sm:space-x-2 px-2 sm:px-4 py-1.5 sm:py-2 ml-2 sm:ml-4 text-xs sm:text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 border border-gray-200 rounded-lg transition-colors shadow-lg cursor-pointer"
              title="Chat History"
            >
              <svg className="w-3 h-3 sm:w-4 sm:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <span className="hidden sm:inline">Chat History</span>
              <span className="sm:hidden">History</span>
              <svg className="w-3 h-3 sm:w-4 sm:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        )}

        {/* Floating Action Buttons - Only show when user is logged in and no modals are open */}
        {user && !isProfileDropdownOpen && !showDeleteConfirm && !showLogoutConfirm && (
          <div className="fixed top-20 sm:top-24 right-2 sm:right-4 z-[60] flex flex-col space-y-2">
            
            {/* New Chat Button */}
            <button
              onClick={handleCreateNew}
              className="flex items-center space-x-1 sm:space-x-2 px-2 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-lg cursor-pointer"
              title="New Chat"
            >
              <svg className="w-3 h-3 sm:w-4 sm:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span className="hidden sm:inline">New Chat</span>
              <span className="sm:hidden">New</span>
            </button>
          </div>
        )}
        
        {/* Main Content */}
        <div className={`flex-1 transition-all duration-200 ${chatHistoryLoading ? 'opacity-40 scale-[0.98]' : 'opacity-100 scale-100'}`}>
          {children}
        </div>
      </div>

      {/* Edit Profile Modal */}
      <EditProfileModal
        isOpen={showEditProfile}
        onClose={() => setShowEditProfile(false)}
      />

      {/* Logout Confirmation Modal */}
      <ConfirmationModal
        isOpen={showLogoutConfirm}
        onClose={() => setShowLogoutConfirm(false)}
        onConfirm={confirmLogout}
        title="Sign Out"
        message="Are you sure you want to sign out? You'll need to log in again to access your chat history."
        confirmText="Sign Out"
        cancelText="Cancel"
        type="warning"
        isLoading={isProcessing}
      />

      {/* Delete Chat Confirmation Modal */}
      <ConfirmationModal
        isOpen={showDeleteConfirm}
        onClose={() => {
          setShowDeleteConfirm(false);
          setSessionToDelete(null);
        }}
        onConfirm={confirmDeleteSession}
        title="Delete Chat"
        message="Are you sure you want to delete this chat? This action cannot be undone and will permanently remove all messages in this conversation."
        confirmText="Delete Chat"
        cancelText="Cancel"
        type="danger"
        isLoading={isProcessing}
      />
    </div>
  );
};

export default ChatGPTLayout;
