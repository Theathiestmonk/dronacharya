"use client";
import React, { useState } from 'react';
import { useAuth } from '@/providers/AuthProvider';
import { useChatHistory } from '@/providers/ChatHistoryProvider';
import { useTheme } from '@/providers/ThemeProvider';
import UserAvatarDropdown from './UserAvatarDropdown';
import EditProfileModal from './EditProfileModal';
import ThemeToggle from './ThemeToggle';
import ConfirmationModal from './ConfirmationModal';
import Image from 'next/image';

interface ChatGPTLayoutProps {
  children: React.ReactNode;
  onLoginRedirect?: () => void;
}

const ChatGPTLayout: React.FC<ChatGPTLayoutProps> = ({ children, onLoginRedirect }) => {
  const { user, signOut } = useAuth();
  const { theme } = useTheme();
  const { 
    sessions, 
    activeSessionId, 
    createNewSession, 
    switchToSession, 
    deleteSession, 
    updateSessionTitle 
  } = useChatHistory();
  
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true); // Start hidden by default
  
  // Confirmation modal states
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Handle sidebar click for non-authenticated users
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

  const handleCreateNew = () => {
    createNewSession();
  };

  const handleSwitchSession = (sessionId: string) => {
    switchToSession(sessionId);
  };

  const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation(); // Prevent switching session
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
    setEditingSessionId(session.id);
    setEditTitle(session.title);
  };

  const handleSaveTitle = () => {
    if (editingSessionId && editTitle.trim()) {
      updateSessionTitle(editingSessionId, editTitle.trim());
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
    <div className="flex flex-1 bg-gray-50 dark:bg-gray-900">
      {/* Left Sidebar - Clean Minimal Design */}
      {!sidebarCollapsed && (
        <div className={`w-64 ${theme === 'dark' ? 'bg-gray-800' : 'bg-gray-100'} ${theme === 'dark' ? 'text-white' : 'text-gray-900'} flex flex-col transition-all duration-300 ease-in-out border-r ${theme === 'dark' ? 'border-gray-700' : 'border-gray-200'}`}>
        {/* Header with Logo and Collapse Button */}
        <div className={`p-4 border-b ${theme === 'dark' ? 'border-gray-700' : 'border-gray-200'}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <button
                onClick={handleSidebarClick}
                className="w-8 h-8 rounded-lg flex items-center justify-center hover:opacity-80 transition-opacity"
                title={user ? (sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar") : "Login to access chat history"}
              >
                <Image
                  src="/prakriti_logo.webp"
                  alt="Prakriti Logo"
                  width={32}
                  height={32}
                  className="w-8 h-8 rounded-lg object-contain"
                />
              </button>
              {!sidebarCollapsed && (
                <span className={`font-medium text-sm ${theme === 'dark' ? 'text-white' : 'text-gray-700'}`}>Prakriti AI</span>
              )}
            </div>
            
            {/* Controls - Only show when sidebar is expanded */}
            {!sidebarCollapsed && (
              <div className="flex items-center space-x-2">
                <ThemeToggle />
                <button
                  onClick={() => setSidebarCollapsed(true)}
                  className={`p-2 rounded-lg ${theme === 'dark' ? 'hover:bg-gray-700' : 'hover:bg-gray-200'} transition-colors`}
                  title="Collapse sidebar"
                >
                  <svg className={`w-4 h-4 ${theme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                  </svg>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <button
            onClick={handleCreateNew}
            className={`w-full flex items-center ${sidebarCollapsed ? 'justify-center p-2' : 'space-x-3 px-3 py-2'} ${theme === 'dark' ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'} rounded-lg transition-colors`}
            title={sidebarCollapsed ? 'New chat' : ''}
          >
            <svg className={`w-4 h-4 ${theme === 'dark' ? 'text-white' : 'text-gray-700'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            {!sidebarCollapsed && <span className={`text-sm ${theme === 'dark' ? 'text-white' : 'text-gray-700'}`}>New chat</span>}
          </button>
        </div>

        {/* Search */}
        {!sidebarCollapsed && (
          <div className="px-3 pb-3">
            <div className="relative">
              <svg className={`absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 ${theme === 'dark' ? 'text-gray-300' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
                  <input
                    type="text"
                    placeholder="Search chats"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className={`w-full pl-10 pr-4 py-2 rounded-lg focus:outline-none focus:ring-1 ${theme === 'dark' ? 'bg-gray-700 border border-gray-600 text-white placeholder-gray-300 focus:ring-gray-500' : 'bg-gray-200 border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-gray-400'}`}
                  />
            </div>
          </div>
        )}

        {/* Chat History */}
        <div className="flex-1 overflow-y-auto px-3">
          {filteredSessions.length === 0 ? (
            <div className={`text-center py-8 ${theme === 'dark' ? 'text-gray-300' : 'text-gray-400'}`}>
              <p className="text-xs">No chats yet</p>
            </div>
          ) : (
            <div className="space-y-1">
              {filteredSessions
                .sort((a, b) => b.updatedAt - a.updatedAt)
                .map((session) => {
                  const displayTitle = session.title === 'New Chat' ? generateChatName(session.messages) : session.title;
                  return (
                    <div
                      key={session.id}
                      className={`group relative p-2 rounded-lg cursor-pointer transition-colors ${
                        session.id === activeSessionId
                          ? theme === 'dark' ? 'bg-gray-700' : 'bg-gray-200'
                          : theme === 'dark' ? 'hover:bg-gray-700' : 'hover:bg-gray-200'
                      }`}
                      onClick={() => handleSwitchSession(session.id)}
                    >
                      {editingSessionId === session.id ? (
                        <div className="space-y-2">
                          <input
                            type="text"
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            className="w-full px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:ring-1 focus:ring-gray-500"
                            autoFocus
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleSaveTitle();
                              if (e.key === 'Escape') handleCancelEdit();
                            }}
                            onBlur={handleSaveTitle}
                          />
                          <div className="flex space-x-2">
                            <button
                              onClick={handleSaveTitle}
                              className="px-2 py-1 text-xs bg-gray-700 text-white rounded hover:bg-gray-600"
                            >
                              Save
                            </button>
                            <button
                              onClick={handleCancelEdit}
                              className="px-2 py-1 text-xs bg-gray-600 text-gray-300 rounded hover:bg-gray-500"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-center justify-between">
                            <div className="flex-1 min-w-0">
                              <h3 className={`text-xs font-medium truncate ${sidebarCollapsed ? 'text-center' : ''} ${theme === 'dark' ? 'text-white' : 'text-gray-700'}`}>
                                {sidebarCollapsed ? displayTitle.split(' ')[0] : displayTitle}
                              </h3>
                              {!sidebarCollapsed && (
                                <p className={`text-xs mt-1 ${theme === 'dark' ? 'text-gray-300' : 'text-gray-500'}`}>
                                  {formatDate(session.updatedAt)}
                                </p>
                              )}
                            </div>
                            {!sidebarCollapsed && (
                              <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button
                                  onClick={(e) => handleEditTitle(e, session)}
                                  className="p-1 hover:bg-gray-700 rounded"
                                  title="Rename chat"
                                >
                                  <svg className={`w-3 h-3 ${theme === 'dark' ? 'text-gray-300' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                  </svg>
                                </button>
                                <button
                                  onClick={(e) => handleDeleteSession(e, session.id)}
                                  className={`p-1 rounded ${theme === 'dark' ? 'hover:bg-red-900 text-red-400' : 'hover:bg-red-100 text-red-500'}`}
                                  title="Delete chat"
                                >
                                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                  </svg>
                                </button>
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
            </div>
          )}
        </div>

         {/* User Profile at Bottom */}
         <div className="p-3 border-t border-gray-800">
           {user ? (
             <UserAvatarDropdown
               onEditProfile={() => setShowEditProfile(true)}
               onLogout={handleLogout}
               sidebarCollapsed={sidebarCollapsed}
               theme={theme}
             />
            ) : (
              <div className={`text-center ${theme === 'dark' ? 'text-gray-300' : 'text-gray-400'}`}>
                <p className="text-xs">Please log in to save chats</p>
              </div>
            )}
         </div>
        </div>
      )}

      {/* Floating Text Link when sidebar is collapsed */}
      {sidebarCollapsed && (
        <div className="fixed top-4 left-4 z-50">
          <div
            onClick={handleSidebarClick}
            className={`flex items-center space-x-2 cursor-pointer hover:opacity-80 transition-opacity ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}
            title={user ? "Expand sidebar" : "Login to access chat history"}
          >
            <div className="w-6 h-6 rounded flex items-center justify-center">
              <Image
                src="/prakriti_logo.webp"
                alt="Prakriti Logo"
                width={24}
                height={24}
                className="w-6 h-6 rounded object-contain"
              />
            </div>
            <span className={`font-medium text-sm ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>Prakriti AI Assistant</span>
            <svg className={`w-4 h-4 ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className={`flex-1 flex flex-col ${theme === 'dark' ? 'bg-gray-900' : 'bg-white'}`}>
        {children}
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
