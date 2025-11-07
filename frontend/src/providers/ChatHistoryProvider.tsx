"use client";
import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { useAuth } from './AuthProvider';
import { useSupabase } from './SupabaseProvider';
import { generateChatName } from '../utils/chatNameGenerator';

export interface ChatMessage {
  sender: 'user' | 'bot';
  text: string;
  type?: string;
  url?: string;
  videos?: unknown[];
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
  isActive?: boolean;
  isSavedToSupabase?: boolean; // Track if session is saved to Supabase
  isDirty?: boolean; // Track if session has unsaved changes
}

interface ChatHistoryContextType {
  sessions: ChatSession[];
  activeSessionId: string | null;
  isLoading: boolean;
  isGuestMode: boolean;
  activeSessionMessageCount: number; // Track message count to detect session updates
  createNewSession: () => Promise<void>;
  switchToSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  deleteAllSessions: () => Promise<void>;
  updateSessionTitle: (sessionId: string, newTitle: string) => Promise<void>;
  addMessage: (message: ChatMessage) => Promise<void>;
  getActiveSession: () => ChatSession | null;
  clearActiveSession: () => void;
  clearGuestHistory: () => void;
  saveSessionToSupabase: (sessionId: string) => Promise<void>;
  hasUnsavedSessions: () => boolean;
  saveAllUnsavedSessions: () => Promise<void>;
  refreshChatComponents: () => Promise<void>;
}

const ChatHistoryContext = createContext<ChatHistoryContextType | undefined>(undefined);

export const useChatHistory = () => {
  const context = useContext(ChatHistoryContext);
  if (context === undefined) {
    throw new Error('useChatHistory must be used within a ChatHistoryProvider');
  }
  return context;
};

export const ChatHistoryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const supabase = useSupabase();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGuestMode, setIsGuestMode] = useState(false);
  const [hasCheckedDatabase, setHasCheckedDatabase] = useState(false);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [lastCreateSessionTime, setLastCreateSessionTime] = useState(0);
  const [justCreatedManualSession, setJustCreatedManualSession] = useState(false);
  
  // Track if we've already loaded sessions for the current user to prevent reload on tab focus
  const hasLoadedForUserRef = useRef<string | null>(null);
  
  // Blink effect state for refresh (removed - causing blinking on page refresh)
  // const [isBlinking, setIsBlinking] = useState(false);
  
  // Use ref to get current sessions state
  const sessionsRef = useRef<ChatSession[]>([]);
  const activeSessionIdRef = useRef<string | null>(null);
  
  // Helper function to update both state and ref
  const updateActiveSessionId = useCallback((sessionId: string | null) => {
    // CRITICAL: Always update state if it's different from sessionId, even if ref matches
    // This ensures state is synced on page refresh when ref has value but state is null
    const stateNeedsUpdate = activeSessionId !== sessionId;
    const refNeedsUpdate = activeSessionIdRef.current !== sessionId;
    
    if (!stateNeedsUpdate && !refNeedsUpdate) {
      console.log('⏭️ Skipping updateActiveSessionId - session ID unchanged:', sessionId);
      return;
    }
    
    console.log('🔄 updateActiveSessionId called:', {
      newSessionId: sessionId,
      currentRefValue: activeSessionIdRef.current,
      currentStateValue: activeSessionId,
      stateNeedsUpdate,
      refNeedsUpdate
    });
    
    // Always update ref first
    activeSessionIdRef.current = sessionId;
    
    // Always update state if it's different (important for page refresh)
    if (stateNeedsUpdate) {
      setActiveSessionId(sessionId);
    }
    
    console.log('✅ updateActiveSessionId completed:', {
      refValue: activeSessionIdRef.current,
      stateValue: sessionId
    });
  }, [activeSessionId]); // Include activeSessionId to check if state needs update
  
  useEffect(() => {
    console.log('🔄 useEffect triggered - sessions changed:', {
      sessionsLength: sessions.length,
      sessionsIds: sessions.map(s => s.id),
      sessionsRefLength: sessionsRef.current.length,
      sessionsRefIds: sessionsRef.current.map(s => s.id)
    });
    sessionsRef.current = sessions;
    // Don't automatically update activeSessionIdRef - we'll manage it manually
  }, [sessions]);
  
  // Initial safety timeout to ensure loading completes even if initialization hangs
  useEffect(() => {
    const initialTimeout = setTimeout(() => {
      console.log('⚠️ Initial loading timeout: forcing isLoading to false');
      setIsLoading(false);
    }, 2000); // 2 second timeout for initial load

    return () => clearTimeout(initialTimeout);
  }, []); // Only run once on mount
  
  // Migrate old session IDs to UUID format
  const migrateSessionId = useCallback((id: string): string => {
    if (id && !id.includes('-')) {
      // Generate a simple UUID-like ID for old sessions
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
    }
    return id;
  }, []);

  // Load sessions from Supabase
  const loadSessionsFromSupabase = useCallback(async (): Promise<ChatSession[]> => {
    if (!supabase || !user) return [];

    try {
      const { data, error } = await supabase
        .from('chat_sessions')
        .select('*')
        .eq('user_id', user.id)
        .order('updated_at', { ascending: false });

      if (error) {
        console.error('Error loading sessions from Supabase:', error);
        return [];
      }

      return data || [];
    } catch (error) {
      console.error('Error loading sessions from Supabase:', error);
      return [];
    }
  }, [supabase, user]);

  // Save session to Supabase
  const saveSessionToSupabase = useCallback(async (session: ChatSession) => {
    if (!supabase || !user) return;

    console.log('Saving session to Supabase:', {
      id: session.id,
      title: session.title,
      messagesCount: session.messages.length,
      messages: session.messages.map(m => ({ sender: m.sender, text: m.text.substring(0, 50) + '...' }))
    });

      try {
        const { error } = await supabase
          .from('chat_sessions')
        .upsert({
          id: session.id,
          user_id: user.id,
          title: session.title,
          messages: session.messages,
          created_at: session.created_at,
          updated_at: session.updated_at,
          is_active: session.isActive || false
        });

        if (error) {
        console.error('Error saving session to Supabase:', error);
        } else {
        console.log('Successfully saved session to Supabase');
        }
      } catch (error) {
      console.error('Error saving session to Supabase:', error);
    }
  }, [supabase, user]);

  // Intelligent storage functions
  const saveSessionToSupabaseById = useCallback(async (sessionId: string) => {
    if (!supabase || !user) return;
    
    const session = sessions.find(s => s.id === sessionId);
    if (!session) {
      console.log('Session not found for Supabase save:', sessionId);
      return;
    }
    
    await saveSessionToSupabase(session);
    
    // Mark session as saved
    setSessions(prevSessions => 
      prevSessions.map(s => 
        s.id === sessionId 
          ? { ...s, isSavedToSupabase: true, isDirty: false }
          : s
      )
    );
  }, [supabase, user, sessions, saveSessionToSupabase]);

  const hasUnsavedSessions = useCallback(() => {
    return sessions.some(session => session.isDirty && !session.isSavedToSupabase);
  }, [sessions]);

  const saveAllUnsavedSessions = useCallback(async () => {
    if (!user) return;
    
    const unsavedSessions = sessions.filter(session => session.isDirty && !session.isSavedToSupabase);
    
    console.log(`🔄 Saving ${unsavedSessions.length} unsaved sessions to Supabase...`);
    
    for (const session of unsavedSessions) {
      await saveSessionToSupabase(session);
    }
    
    // Mark all sessions as saved
    setSessions(prevSessions => 
      prevSessions.map(session => ({
        ...session,
        isSavedToSupabase: true,
        isDirty: false
      }))
    );
    
    console.log('✅ All sessions saved to Supabase');
  }, [user, sessions, saveSessionToSupabase]);

  // Save guest sessions to localStorage (same approach as logged-in users)
  const saveGuestSessions = useCallback((sessions: ChatSession[], activeId: string | null) => {
    try {
      const guestKey = 'guest_chat_sessions';
      const data = {
        sessions,
        activeSessionId: activeId
      };
      
      // Get active session to log message count
      const activeSession = sessions.find(s => s.id === activeId);
      
      localStorage.setItem(guestKey, JSON.stringify(data));
      console.log('💾 Saved guest sessions to localStorage:', {
        key: guestKey,
        sessionsCount: sessions.length,
        activeSessionId: activeId,
        activeSessionMessagesCount: activeSession?.messages.length || 0,
        sessionIds: sessions.map(s => s.id),
        allMessagesCount: sessions.reduce((sum, s) => sum + (s.messages?.length || 0), 0)
      });
      
      // Verify the save worked
      const verify = localStorage.getItem(guestKey);
      if (verify) {
        const parsed = JSON.parse(verify);
        const verifyActiveSession = parsed.sessions?.find((s: ChatSession) => s.id === activeId);
        console.log('✅ Verified localStorage save:', {
          activeSessionId: activeId,
          messagesCount: verifyActiveSession?.messages?.length || 0
        });
      }
    } catch (error) {
      console.error('❌ Error saving guest sessions:', error);
    }
  }, []);

  // Load guest sessions from localStorage
  const loadGuestSessions = useCallback(async () => {
    try {
      const guestKey = 'guest_chat_sessions';
      const saved = localStorage.getItem(guestKey);
      console.log('Loading guest sessions from localStorage');
      
      // Check if there's a session ID in the URL
      const urlParams = new URLSearchParams(window.location.search);
      const urlSessionId = urlParams.get('session');
      
      if (saved) {
        const data = JSON.parse(saved);
        const guestSessions = data.sessions || [];
        // Update refs immediately to ensure getActiveSession works
        sessionsRef.current = guestSessions;
        
        setSessions(guestSessions);
        
        // CRITICAL: Use activeSessionId from localStorage first (preserves existing session with messages)
        // Only use URL session ID if it exists in localStorage sessions
        // This prevents creating empty sessions that overwrite existing sessions with messages
        let activeSessionId = data.activeSessionId || null;
        if (urlSessionId) {
          const urlSession = guestSessions.find((s: ChatSession) => s.id === urlSessionId);
          if (urlSession) {
            // URL session exists in localStorage - use it (has messages)
            activeSessionId = urlSessionId;
            console.log('✅ Using existing session from URL (has messages):', urlSessionId, {
              messagesCount: urlSession.messages.length
            });
          } else {
            // URL session ID doesn't exist in localStorage
            // CRITICAL: Don't create empty session - use existing activeSessionId from localStorage
            // This preserves messages that were saved before refresh
            if (activeSessionId) {
              const existingSession = guestSessions.find((s: ChatSession) => s.id === activeSessionId);
              if (existingSession) {
                console.log('⚠️ URL session ID not found, using existing active session from localStorage:', activeSessionId, {
                  messagesCount: existingSession.messages.length
                });
                // Keep using the existing session - don't create empty one
              } else {
                // No valid session found - create new one only as last resort
                console.log('⚠️ No valid session found, creating new session with URL session ID:', urlSessionId);
                const newSession: ChatSession = {
                  id: urlSessionId,
                  title: 'New Chat',
                  messages: [],
                  created_at: new Date().toISOString(),
                  updated_at: new Date().toISOString(),
                  isActive: true,
                  isSavedToSupabase: false,
                  isDirty: false
                };
                const updatedSessions = [newSession, ...guestSessions];
                sessionsRef.current = updatedSessions;
                setSessions(updatedSessions);
                activeSessionId = urlSessionId;
                saveGuestSessions(updatedSessions, urlSessionId);
              }
            } else {
              // No activeSessionId in localStorage either - create new session
              console.log('Creating new session with URL session ID (no localStorage activeSessionId):', urlSessionId);
              const newSession: ChatSession = {
                id: urlSessionId,
                title: 'New Chat',
                messages: [],
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                isActive: true,
                isSavedToSupabase: false,
                isDirty: false
              };
              const updatedSessions = [newSession, ...guestSessions];
              sessionsRef.current = updatedSessions;
              setSessions(updatedSessions);
              activeSessionId = urlSessionId;
              saveGuestSessions(updatedSessions, urlSessionId);
            }
          }
        }
        
        // CRITICAL: Update activeSessionId state AND ref immediately
        // This ensures getActiveSession() works correctly and useEffect triggers
        if (activeSessionId) {
          updateActiveSessionId(activeSessionId);
          // Also ensure ref is updated (updateActiveSessionId should do this, but be explicit)
          activeSessionIdRef.current = activeSessionId;
        }
        setIsGuestMode(true);
        const activeSession = guestSessions.find((s: ChatSession) => s.id === activeSessionId);
        console.log('✅ Loaded guest sessions from localStorage:', {
          sessionsCount: guestSessions.length,
          activeSessionId: activeSessionId,
          activeSessionIdRef: activeSessionIdRef.current,
          activeSessionMessagesCount: activeSession?.messages?.length || 0,
          allMessagesCount: guestSessions.reduce((sum: number, s: ChatSession) => sum + (s.messages?.length || 0), 0),
          activeSessionMessages: activeSession?.messages?.map((m: ChatMessage) => ({ sender: m.sender, text: m.text?.substring(0, 30) + '...' })) || []
        });
      } else {
        console.log('No guest sessions found');
        
        // Always create a session for guest users, even if no localStorage data exists
        let newSessionId: string;
        if (urlSessionId) {
          // Use session ID from URL if available
          newSessionId = urlSessionId;
          console.log('Creating new session with URL session ID (no localStorage):', urlSessionId);
        } else {
          // Generate a new session ID
          newSessionId = crypto.randomUUID();
          console.log('Creating new session with generated ID (no localStorage):', newSessionId);
          
          // Update URL with new session ID
          const url = new URL(window.location.href);
          url.searchParams.set('session', newSessionId);
          window.history.replaceState({}, '', url.toString());
        }
        
        const newSession: ChatSession = {
          id: newSessionId,
          title: 'New Chat',
          messages: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          isActive: true,
          isSavedToSupabase: false,
          isDirty: false
        };
        sessionsRef.current = [newSession]; // Update ref immediately
        setSessions([newSession]);
        // CRITICAL: Update both state and ref immediately
        updateActiveSessionId(newSessionId);
        activeSessionIdRef.current = newSessionId; // Ensure ref is updated
        
        // Save the new session to localStorage
        saveGuestSessions([newSession], newSessionId);
        console.log('✅ Guest session created and saved:', newSessionId, {
          activeSessionIdState: newSessionId,
          activeSessionIdRef: activeSessionIdRef.current
        });
        
        setIsGuestMode(true);
      }
    } catch (error) {
      console.error('Error loading guest sessions:', error);
      setIsGuestMode(true);
      // CRITICAL: Ensure loading is set to false even on error
      setIsLoading(false);
    } finally {
      // CRITICAL: Always set loading to false after loading guest sessions
      // This allows the useEffect in Chatbot to trigger and load messages
      setIsLoading(false);
      console.log('✅ Guest sessions loading complete, isLoading set to false');
    }
  }, [updateActiveSessionId, saveGuestSessions]);

  // Load from localStorage with priority order
  const loadFromLocalStorage = useCallback(async () => {
    if (user) {
      // Check for session ID in URL first
      const urlParams = new URLSearchParams(window.location.search);
      const urlSessionId = urlParams.get('session');
      console.log('URL session ID:', urlSessionId);

      try {
        console.log('Loading chat history for user:', user.id);

        // First try to load from localStorage for faster initial load
        const userKey = `chat_history_${user.id}`;
        const localData = localStorage.getItem(userKey);
        const hasLocalStorageData = localData && localData.trim() !== '';
        
        if (hasLocalStorageData) {
          try {
            const parsedData = JSON.parse(localData);
            console.log('LocalStorage sessions loaded:', parsedData.sessions?.length || 0);
            
            if (parsedData.sessions && parsedData.sessions.length > 0) {
              // Use localStorage data immediately for faster loading
              setSessions(parsedData.sessions);
              
              // Set active session from localStorage
              let activeSessionId = parsedData.activeSessionId;
              
              if (urlSessionId) {
                const urlSession = parsedData.sessions.find((s: ChatSession) => s.id === urlSessionId);
                if (urlSession) {
                  activeSessionId = urlSessionId;
                  console.log('Using session from URL:', urlSessionId);
                }
              }
              
              updateActiveSessionId(activeSessionId);
              console.log('Active session set from localStorage:', activeSessionId);
              
              // Mark as loaded but continue to sync with Supabase in background
              setIsLoading(false);
            }
          } catch (error) {
            console.error('Error parsing localStorage data:', error);
            // If localStorage is corrupted, treat it as empty and load from Supabase
            localStorage.removeItem(userKey);
          }
        } else {
          console.log('📦 No localStorage data found - will load from Supabase');
        }

        // Then sync with Supabase (or load if localStorage was empty/cleared)
        const supabaseSessions = await loadSessionsFromSupabase();
        console.log('Supabase sessions loaded:', supabaseSessions.length);
        setHasCheckedDatabase(true); // Mark that we've checked the database
        
        if (supabaseSessions.length > 0) {
          // Use Supabase data (especially important when localStorage was cleared)
          setSessions(supabaseSessions);

          // Priority order for active session when loading from Supabase:
          // 1. Session ID from URL (if it exists in loaded sessions)
          // 2. Session marked as active in database (isActive = true)
          // 3. Most recently updated session (by updated_at DESC - already sorted)
          let activeSessionId = null;

          if (urlSessionId) {
            const urlSession = supabaseSessions.find((s: ChatSession) => s.id === urlSessionId);
            if (urlSession) {
              activeSessionId = urlSessionId;
              console.log('✅ Using session from URL:', urlSessionId);
            } else {
              // CRITICAL: Don't override manually created sessions
              if (justCreatedManualSession || isCreatingSession) {
                console.log('🚫 URL session not found in Supabase, but NOT switching - manual session creation in progress');
                return;
              }
              
              // Don't auto-create sessions here - let ensureUrlSessionHandled handle it
              console.log('URL session ID not found in existing chats, will be handled by ensureUrlSessionHandled');
            }
          }

          if (!activeSessionId) {
            // CRITICAL: Don't override manually created sessions
            if (justCreatedManualSession || isCreatingSession) {
              console.log('🚫 Skipping Supabase session override - manual session creation in progress');
              return;
            }
            
            // Check for session marked as active in database
            const activeSession = supabaseSessions.find((s: ChatSession) => s.isActive === true);
            if (activeSession) {
              activeSessionId = activeSession.id;
              console.log('✅ Using session marked as active in database:', activeSessionId);
            }
          }

          if (!activeSessionId) {
            // CRITICAL: Don't override manually created sessions
            if (justCreatedManualSession || isCreatingSession) {
              console.log('🚫 Skipping Supabase session override - manual session creation in progress');
              return;
            }
            
            // Use most recently updated session (sessions are already sorted by updated_at DESC)
            // This is especially important when localStorage is cleared
            activeSessionId = supabaseSessions[0]?.id || null;
            if (activeSessionId) {
              const mostRecentSession = supabaseSessions[0];
              console.log('✅ Using most recently updated session:', {
                id: activeSessionId,
                title: mostRecentSession.title,
                updated_at: mostRecentSession.updated_at
              });
            }
          }

          updateActiveSessionId(activeSessionId);
          console.log('✅ Final active session set to:', activeSessionId);
          
          // Update localStorage with Supabase data for faster future loads
          // This is especially important when cache was cleared - restore localStorage
          if (activeSessionId) {
            localStorage.setItem(userKey, JSON.stringify({
              sessions: supabaseSessions,
              activeSessionId: activeSessionId
            }));
            console.log('💾 Saved Supabase sessions to localStorage for faster future loads');
          }
          
          // Mark as loaded (important when localStorage was empty/cleared)
          setIsLoading(false);
        } else {
          // User has NO existing chats in database
          console.log('❌ User has NO existing chats in database');
          setHasCheckedDatabase(true); // Mark that we've checked the database
          
          // Fallback to localStorage
          const userKey = `chat_history_${user.id}`;
          const saved = localStorage.getItem(userKey);
          console.log('Checking localStorage for key:', userKey, 'Found:', !!saved);
          if (saved) {
            try {
              const data = JSON.parse(saved);
              // Migrate old session IDs to UUID format
              const migratedSessions = (data.sessions || []).map((session: ChatSession) => ({
                ...session,
                id: migrateSessionId(session.id)
              }));
              setSessions(migratedSessions);

              // Use URL session ID if available, otherwise use saved active session
              let activeSessionId = null;
              if (urlSessionId) {
                const urlSession = migratedSessions.find((s: ChatSession) => s.id === urlSessionId);
                if (urlSession) {
                  activeSessionId = urlSessionId;
                  console.log('Using session from URL (localStorage):', urlSessionId);
                }
              }

              if (!activeSessionId) {
                activeSessionId = data.activeSessionId ? migrateSessionId(data.activeSessionId) : null;
                console.log('Using saved active session:', activeSessionId);
              }

              updateActiveSessionId(activeSessionId);
              console.log('Using localStorage sessions:', migratedSessions.length, 'Active:', activeSessionId);
            } catch (error) {
              console.error('Error loading chat history from localStorage:', error);
            }
          } else {
            console.log('No sessions found in localStorage, will create new session');
            // Ensure loading is set to false even if no sessions found
            setIsLoading(false);
          }
        }
      } catch (error) {
        console.error('Error loading chat history:', error);
        // Fallback to localStorage on error
        const userKey = `chat_history_${user.id}`;
        const saved = localStorage.getItem(userKey);
        if (saved) {
          try {
            const data = JSON.parse(saved);
            // Migrate old session IDs to UUID format
            const migratedSessions = (data.sessions || []).map((session: ChatSession) => ({
              ...session,
              id: migrateSessionId(session.id)
            }));
            setSessions(migratedSessions);

            // Use URL session ID if available, otherwise use saved active session
            let activeSessionId = null;
            if (urlSessionId) {
              const urlSession = migratedSessions.find((s: ChatSession) => s.id === urlSessionId);
              if (urlSession) {
                activeSessionId = urlSessionId;
                console.log('Using session from URL (fallback):', urlSessionId);
              }
            }

            if (!activeSessionId) {
              activeSessionId = data.activeSessionId ? migrateSessionId(data.activeSessionId) : null;
              console.log('Using saved active session (fallback):', activeSessionId);
            }

            updateActiveSessionId(activeSessionId);
            console.log('Fallback to localStorage sessions:', migratedSessions.length);
          } catch (error) {
            console.error('Error loading chat history from localStorage:', error);
          }
        }
      }
      setIsLoading(false);
    } else {
      // No user - load guest sessions
      console.log('No user, loading guest sessions');
      await loadGuestSessions();
    }
  }, [user, loadSessionsFromSupabase, migrateSessionId, loadGuestSessions, updateActiveSessionId, isCreatingSession, justCreatedManualSession]);

  // Ensure URL session ID is handled or create one if none exists
  const ensureUrlSessionHandled = useCallback(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const urlSessionId = urlParams.get('session');
    const currentSessions = sessionsRef.current;
    const currentActiveSessionId = activeSessionIdRef.current;
    
    console.log('🔍 ensureUrlSessionHandled called:', {
      urlSessionId,
      currentActiveSessionId,
      sessionsCount: currentSessions.length,
      isLoggedIn: !!user,
      isGuestMode,
      isCreatingSession
    });
    
    // Don't auto-create if manual session creation is in progress
    if (isCreatingSession) {
      console.log('🚫 Manual session creation in progress - skipping auto-creation');
      return;
    }
    
    // Don't interfere if we just created a manual session
    if (justCreatedManualSession) {
      console.log('🚫 Just created manual session - skipping auto-creation to prevent race conditions');
      return;
    }
    
    // CRITICAL: Only run auto-creation logic if there's NO active session
    // If there's already an active session, don't interfere with it
    if (currentActiveSessionId) {
      console.log('🚫 Active session already exists - NO auto-creation needed');
      
      // DON'T try to switch to URL sessions when there's already an active session
      // This prevents race conditions with manual "New Chat" button
      if (urlSessionId && urlSessionId !== currentActiveSessionId) {
        console.log('🚫 URL session differs from active session, but NOT switching to prevent race conditions');
        console.log('   Active session:', currentActiveSessionId);
        console.log('   URL session:', urlSessionId);
        console.log('   This prevents interference with manual "New Chat" button');
      }
      return; // Exit early - don't interfere with existing active session
    }
    
    // ONLY block AUTO-creation for logged-in users with existing chats
    // This does NOT block manual "New Chat" button clicks
    if (user && hasCheckedDatabase && currentSessions.length > 0) {
      console.log('🚫 Logged-in user with existing chats - NO AUTO-creation allowed (but manual New Chat button still works)');
      return; // Exit early - only block AUTO-creation, not manual creation
    }
    
    // Only auto-create for:
    // 1. Guest users (isGuestMode = true)
    // 2. Logged-in users who have been checked and have NO existing chats
    console.log('🔍 Auto-creation check:', {
      hasActiveSession: !!currentActiveSessionId,
      isGuestMode,
      isLoggedIn: !!user,
      hasCheckedDatabase,
      sessionsCount: currentSessions.length,
      shouldAutoCreate: !currentActiveSessionId && (isGuestMode || (user && hasCheckedDatabase && currentSessions.length === 0))
    });
    
    if (!currentActiveSessionId && (isGuestMode || (user && hasCheckedDatabase && currentSessions.length === 0))) {
      console.log('🆕 Auto-creating session for:', isGuestMode ? 'guest user' : 'new logged-in user');
      
      let newSessionId: string;
      if (urlSessionId) {
        // Use the session ID from URL
        newSessionId = urlSessionId;
        console.log('🆕 Using session ID from URL:', urlSessionId);
      } else {
        // Create a new session ID
        newSessionId = crypto.randomUUID();
        console.log('🆕 Creating new session ID:', newSessionId);
        
        // Update URL with new session ID
        const url = new URL(window.location.href);
        url.searchParams.set('session', newSessionId);
        window.history.pushState({}, '', url.toString());
      }
      
      const newSession: ChatSession = {
        id: newSessionId,
        title: 'New Chat',
        messages: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        isActive: true,
        isSavedToSupabase: false,
        isDirty: false
      };
      
      const updatedSessions = [newSession, ...currentSessions];
      setSessions(updatedSessions);
      sessionsRef.current = updatedSessions;
      updateActiveSessionId(newSessionId);
      
      // Save to appropriate storage
      if (user) {
        const userKey = `chat_history_${user.id}`;
        localStorage.setItem(userKey, JSON.stringify({
          sessions: updatedSessions,
          activeSessionId: newSessionId
        }));
      } else {
        saveGuestSessions(updatedSessions, newSessionId);
      }
      
      console.log('✅ Session created and saved automatically');
        } else {
      console.log('✅ No auto-creation needed - user has existing chats or already has active session');
    }
  }, [user, isGuestMode, saveGuestSessions, updateActiveSessionId, hasCheckedDatabase, isCreatingSession, justCreatedManualSession]);

  // Create new session - MANUAL creation that ALWAYS works regardless of existing chats
  const createNewSession = useCallback(async () => {
    const now = Date.now();
    
    // Debounce: Prevent multiple rapid calls within 1 second
    if (now - lastCreateSessionTime < 1000) {
      console.log('🚫 Debouncing createNewSession - too soon since last call');
      return;
    }
    
    console.log('🔄 Creating new session MANUALLY (always works regardless of existing chats)...');
    setIsCreatingSession(true); // Prevent auto-creation during manual creation
    setJustCreatedManualSession(true); // Mark that we just created a manual session
    setLastCreateSessionTime(now);
    
    try {
    
    // Ensure current session is properly saved before creating new one
    if (activeSessionIdRef.current) {
      const currentSessions = sessionsRef.current;
      const currentSession = currentSessions.find(s => s.id === activeSessionIdRef.current);
      
      if (currentSession) {
        console.log('🔄 Ensuring current session is saved before creating new one...');
        console.log('Current session details:', {
          id: currentSession.id,
          messagesCount: currentSession.messages.length,
          isDirty: currentSession.isDirty,
          isSavedToSupabase: currentSession.isSavedToSupabase
        });
        
        // For authenticated users, always save to Supabase if session has messages
        // This ensures no data loss when switching to a new chat
        if (user && currentSession.messages.length > 0) {
          console.log('🔄 Auto-saving previous session to Supabase (has messages, ensuring data safety)...');
          await saveSessionToSupabase(currentSession);
          
          // Mark as saved - update both state and ref for consistency
          const updatedSessions = currentSessions.map(s => 
            s.id === activeSessionIdRef.current 
              ? { ...s, isSavedToSupabase: true, isDirty: false }
              : s
          );
          
          setSessions(updatedSessions);
          sessionsRef.current = updatedSessions;
          
          console.log('✅ Previous session auto-saved to Supabase');
        } else if (user && currentSession.messages.length === 0) {
          console.log('ℹ️ Current session has no messages, skipping Supabase save');
        }
        
        // For all users (authenticated and guest), ensure localStorage is up to date
        // This ensures the latest session data is saved even if Supabase save was skipped
        // Use sessionsRef.current to get the most up-to-date sessions (may have been updated above)
        const latestSessions = sessionsRef.current;
        if (user) {
          const userKey = `chat_history_${user.id}`;
          localStorage.setItem(userKey, JSON.stringify({
            sessions: latestSessions,
            activeSessionId: activeSessionIdRef.current
          }));
          console.log('💾 Updated localStorage for authenticated user');
        } else {
          // Guest user - ensure localStorage is up to date
          saveGuestSessions(latestSessions, activeSessionIdRef.current);
          console.log('💾 Updated localStorage for guest user');
        }
      }
    }

    const newSession: ChatSession = {
      id: crypto.randomUUID(),
      title: 'New Chat',
      messages: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      isActive: true,
      isSavedToSupabase: false, // New session starts unsaved
      isDirty: false // New session starts clean
    };

    // Update URL with new session ID
    const url = new URL(window.location.href);
    url.searchParams.set('session', newSession.id);
    window.history.pushState({}, '', url.toString());

    if (user) {
      // Authenticated user - save to localStorage first for speed
      const currentSessions = sessionsRef.current;
      const updatedSessions = currentSessions.map(session => ({ ...session, isActive: false }));
      const newSessions = [newSession, ...updatedSessions];
      
      // Batch all state updates together to prevent blinking
      // Update refs first, then state
      sessionsRef.current = newSessions;
      activeSessionIdRef.current = newSession.id;
      
      // Update state together to prevent intermediate renders
      setSessions(newSessions);
      updateActiveSessionId(newSession.id);

      // Save to localStorage immediately for fast access
      const userKey = `chat_history_${user.id}`;
      localStorage.setItem(userKey, JSON.stringify({
        sessions: newSessions,
        activeSessionId: newSession.id
      }));
      
      // CRITICAL: Save to Supabase immediately to prevent "Session not found" errors
      console.log('🔄 Saving new session to Supabase immediately...');
      await saveSessionToSupabase(newSession);
      
      // Mark session as saved to Supabase
      setSessions(prevSessions => 
        prevSessions.map(s => 
          s.id === newSession.id 
            ? { ...s, isSavedToSupabase: true }
            : s
        )
      );
      
      console.log('✅ New session created and saved to both localStorage and Supabase.');
    } else {
      // Guest user - save to localStorage only
      const currentSessions = sessionsRef.current;
      const updatedSessions = currentSessions.map(session => ({ ...session, isActive: false }));
      const newSessions = [newSession, ...updatedSessions];
      
      // Batch all state updates together to prevent blinking
      // Update refs first, then state
      sessionsRef.current = newSessions;
      activeSessionIdRef.current = newSession.id;
      
      // Update state together to prevent intermediate renders
      setSessions(newSessions);
      updateActiveSessionId(newSession.id);
      setIsGuestMode(true);

      // Save guest sessions to localStorage
      saveGuestSessions(newSessions, newSession.id);
    }

    console.log('✅ Created new session:', newSession.id);
    } catch (error) {
      console.error('Error creating new session:', error);
    } finally {
      setIsCreatingSession(false); // Reset flag after creation
      // Reset the manual session flag after a short delay to prevent race conditions
      setTimeout(() => setJustCreatedManualSession(false), 1000);
    }
  }, [user, saveSessionToSupabase, saveGuestSessions, updateActiveSessionId, lastCreateSessionTime]);

  // Switch to session
  const switchToSession = useCallback(async (sessionId: string) => {
    // Update URL with session ID
    const url = new URL(window.location.href);
    url.searchParams.set('session', sessionId);
    window.history.pushState({}, '', url.toString());

    if (user) {
      // Authenticated user - save to Supabase and localStorage
    const updatedSessions = sessions.map(session => ({
      ...session,
      isActive: session.id === sessionId
    }));
    
    setSessions(updatedSessions);
      updateActiveSessionId(sessionId);

    // Save to Supabase
    await Promise.all(updatedSessions.map(session => saveSessionToSupabase(session)));

    // Save to localStorage as backup
    const userKey = `chat_history_${user.id}`;
    localStorage.setItem(userKey, JSON.stringify({
      sessions: updatedSessions,
      activeSessionId: sessionId
    }));
    } else {
      // Guest user - save to localStorage only
      const updatedSessions = sessions.map(session => ({
        ...session,
        isActive: session.id === sessionId
      }));
      
      setSessions(updatedSessions);
      updateActiveSessionId(sessionId);

      // Save guest sessions to localStorage
      saveGuestSessions(updatedSessions, sessionId);
    }

    console.log('Switched to session:', sessionId);
  }, [user, sessions, saveSessionToSupabase, saveGuestSessions, updateActiveSessionId]);

  // Delete session
  const deleteSession = useCallback(async (sessionId: string) => {
    const updatedSessions = sessions.filter(session => session.id !== sessionId);
    setSessions(updatedSessions);

    // If deleted session was active, switch to most recent or remove URL param
    if (activeSessionId === sessionId) {
      if (updatedSessions.length > 0) {
        const url = new URL(window.location.href);
        url.searchParams.set('session', updatedSessions[0].id);
        window.history.pushState({}, '', url.toString());
        updateActiveSessionId(updatedSessions[0].id);
      } else {
        const url = new URL(window.location.href);
        url.searchParams.delete('session');
        window.history.pushState({}, '', url.toString());
        updateActiveSessionId(null);
      }
    }

    if (user) {
      // Authenticated user - delete from Supabase
    if (supabase) {
      try {
        const { error } = await supabase
          .from('chat_sessions')
          .delete()
          .eq('id', sessionId)
          .eq('user_id', user.id);

        if (error) {
          console.error('Error deleting session from Supabase:', error);
        }
      } catch (error) {
        console.error('Error deleting session from Supabase:', error);
      }
    }

    // Save to localStorage as backup
    const userKey = `chat_history_${user.id}`;
    localStorage.setItem(userKey, JSON.stringify({
      sessions: updatedSessions,
      activeSessionId: activeSessionId === sessionId ? (updatedSessions[0]?.id || null) : activeSessionId
    }));
    } else {
      // Guest user - save to localStorage only
      saveGuestSessions(updatedSessions, activeSessionId === sessionId ? (updatedSessions[0]?.id || null) : activeSessionId);
    }

    console.log('Deleted session:', sessionId);
  }, [user, sessions, activeSessionId, supabase, saveGuestSessions, updateActiveSessionId]);

  // Delete all sessions
  const deleteAllSessions = useCallback(async () => {
      setSessions([]);
    updateActiveSessionId(null);

    // Remove session from URL
    const url = new URL(window.location.href);
    url.searchParams.delete('session');
    window.history.pushState({}, '', url.toString());

    if (user) {
      // Authenticated user - delete from Supabase
    if (supabase) {
      try {
        const { error } = await supabase
          .from('chat_sessions')
          .delete()
          .eq('user_id', user.id);

        if (error) {
          console.error('Error deleting all sessions from Supabase:', error);
        }
      } catch (error) {
        console.error('Error deleting all sessions from Supabase:', error);
      }
    }

    // Clear localStorage
    const userKey = `chat_history_${user.id}`;
    localStorage.removeItem(userKey);
    } else {
      // Guest user - clear localStorage only
      const guestKey = 'guest_chat_sessions';
      localStorage.removeItem(guestKey);
    }

    console.log('Deleted all sessions');
  }, [user, supabase, updateActiveSessionId]);

  // Update session title
  const updateSessionTitle = useCallback(async (sessionId: string, newTitle: string) => {
    const updatedSessions = sessions.map(session => 
      session.id === sessionId 
        ? { ...session, title: newTitle, updated_at: new Date().toISOString() }
        : session
    );
    
    setSessions(updatedSessions);

    if (user) {
      // Authenticated user - save to Supabase
    const sessionToUpdate = updatedSessions.find(s => s.id === sessionId);
    if (sessionToUpdate) {
      await saveSessionToSupabase(sessionToUpdate);
    }

    // Save to localStorage as backup
    const userKey = `chat_history_${user.id}`;
    localStorage.setItem(userKey, JSON.stringify({
      sessions: updatedSessions,
      activeSessionId
    }));
    } else {
      // Guest user - save to localStorage only
      saveGuestSessions(updatedSessions, activeSessionId);
    }

    console.log('Updated session title:', sessionId, newTitle);
  }, [user, sessions, activeSessionId, saveSessionToSupabase, saveGuestSessions]);

  // Add message to active session
  const addMessage = useCallback(async (message: ChatMessage) => {
    console.log('Adding message:', message);
    
    // CRITICAL: Always use refs first (they're always up-to-date), then fall back to state
    // This ensures we have the correct session ID even if state hasn't updated yet
    let latestSessions = sessionsRef.current;
    let currentActiveSessionId = activeSessionIdRef.current;
    
    console.log('Session ID from ref:', currentActiveSessionId);
    console.log('Session ID from state:', activeSessionId);
    console.log('Current sessions count (ref):', latestSessions.length);
    console.log('Current sessions count (state):', sessions.length);
    
    // If we're in guest mode and refs are empty (due to hot reload), reload from localStorage
    if ((!user || isGuestMode) && latestSessions.length === 0) {
      console.log('🔄 Hot reload detected - reloading guest sessions from localStorage');
      const guestData = localStorage.getItem('guest_chat_sessions');
      console.log('📦 Raw localStorage data:', guestData);
      if (guestData) {
        const parsed = JSON.parse(guestData);
        console.log('📦 Parsed localStorage data:', parsed);
        latestSessions = parsed.sessions || [];
        currentActiveSessionId = parsed.activeSessionId || null;
        sessionsRef.current = latestSessions;
        activeSessionIdRef.current = currentActiveSessionId;
        
        // Update React state to trigger UI updates
        setSessions(latestSessions);
        updateActiveSessionId(currentActiveSessionId);
        
        console.log('✅ Reloaded from localStorage:', {
          sessionsCount: latestSessions.length,
          activeSessionId: currentActiveSessionId,
          sessionIds: latestSessions.map(s => s.id)
        });
        
        // Update URL with the reloaded session ID
        if (currentActiveSessionId) {
          const url = new URL(window.location.href);
          url.searchParams.set('session', currentActiveSessionId);
          window.history.pushState({}, '', url.toString());
          console.log('🔗 Updated URL with reloaded session ID:', currentActiveSessionId);
        }
      } else {
        console.log('❌ No guest data found in localStorage');
      }
    }
    
    const currentActiveSession = latestSessions.find(s => s.isActive);
    if (!currentActiveSessionId) {
      currentActiveSessionId = currentActiveSession?.id || null;
    }
    
    console.log('🔍 Session ID resolution for', message.sender, 'message:', {
      fromState: activeSessionId,
      fromRef: activeSessionIdRef.current,
      fromActiveSession: currentActiveSession?.id,
      resolved: currentActiveSessionId,
      availableSessions: latestSessions.map(s => ({ id: s.id, isActive: s.isActive }))
    });
    
    // If no active session, try to find or create one for guest users
    if (!currentActiveSessionId) {
      // For guest users, try to find existing session from URL/localStorage first
      if (!user && isGuestMode) {
        console.log('⚠️ No active session for guest user - checking URL and localStorage for existing session');
        try {
          // Check if there's a session in the URL
          const urlParams = new URLSearchParams(window.location.search);
          const urlSessionId = urlParams.get('session');
          
          if (urlSessionId) {
            // CRITICAL: Check if this session exists in localStorage first
            const urlSession = latestSessions.find(s => s.id === urlSessionId);
            if (urlSession) {
              // Session exists in localStorage - use it (preserves messages)
              currentActiveSessionId = urlSessionId;
              updateActiveSessionId(urlSessionId);
              console.log('✅ Using existing session from URL/localStorage:', urlSessionId, {
                messagesCount: urlSession.messages.length
              });
            } else {
              // Session ID in URL but not in localStorage - might be from a different device/browser
              // Check if there's an activeSessionId in localStorage that we should use instead
              const guestData = localStorage.getItem('guest_chat_sessions');
              if (guestData) {
                const parsed = JSON.parse(guestData);
                const storedActiveSessionId = parsed.activeSessionId;
                const storedSessions = parsed.sessions || [];
                const storedSession = storedSessions.find((s: ChatSession) => s.id === storedActiveSessionId);
                
                if (storedSession && storedSession.messages.length > 0) {
                  // Use the session from localStorage (has messages) instead of creating empty one
                  console.log('⚠️ URL session not found, using active session from localStorage:', storedActiveSessionId, {
                    messagesCount: storedSession.messages.length
                  });
                  currentActiveSessionId = storedActiveSessionId;
                  updateActiveSessionId(storedActiveSessionId);
                  
                  // Update URL to match localStorage
                  const url = new URL(window.location.href);
                  url.searchParams.set('session', storedActiveSessionId);
                  window.history.replaceState({}, '', url.toString());
                } else {
                  // No valid session in localStorage - create new session with URL ID
                  console.log('⚠️ No valid session found, creating new session with URL ID:', urlSessionId);
                  const newSession: ChatSession = {
                    id: urlSessionId,
                    title: 'New Chat',
                    messages: [],
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    isActive: true,
                    isSavedToSupabase: false,
                    isDirty: false
                  };
                  latestSessions = [newSession, ...latestSessions];
                  sessionsRef.current = latestSessions;
                  setSessions(latestSessions);
                  currentActiveSessionId = urlSessionId;
                  updateActiveSessionId(urlSessionId);
                  saveGuestSessions(latestSessions, urlSessionId);
                  console.log('✅ Created new session with URL ID:', urlSessionId);
                }
              } else {
                // No localStorage data - create new session with URL ID
                console.log('Creating new session with URL ID (no localStorage):', urlSessionId);
                const newSession: ChatSession = {
                  id: urlSessionId,
                  title: 'New Chat',
                  messages: [],
                  created_at: new Date().toISOString(),
                  updated_at: new Date().toISOString(),
                  isActive: true,
                  isSavedToSupabase: false,
                  isDirty: false
                };
                latestSessions = [newSession, ...latestSessions];
                sessionsRef.current = latestSessions;
                setSessions(latestSessions);
                currentActiveSessionId = urlSessionId;
                updateActiveSessionId(urlSessionId);
                saveGuestSessions(latestSessions, urlSessionId);
                console.log('✅ Created new session with URL ID:', urlSessionId);
              }
            }
          } else {
            // No URL session ID - check localStorage for existing active session
            const guestData = localStorage.getItem('guest_chat_sessions');
            if (guestData) {
              const parsed = JSON.parse(guestData);
              const storedActiveSessionId = parsed.activeSessionId;
              const storedSessions = parsed.sessions || [];
              const storedSession = storedSessions.find((s: ChatSession) => s.id === storedActiveSessionId);
              
              if (storedSession) {
                // Use existing session from localStorage
                console.log('✅ Using existing active session from localStorage:', storedActiveSessionId, {
                  messagesCount: storedSession.messages.length
                });
                currentActiveSessionId = storedActiveSessionId;
                updateActiveSessionId(storedActiveSessionId);
                
                // Update URL to match localStorage
                const url = new URL(window.location.href);
                url.searchParams.set('session', storedActiveSessionId);
                window.history.replaceState({}, '', url.toString());
              } else {
                // No valid session - create new one
                const newSessionId = crypto.randomUUID();
                const newSession: ChatSession = {
                  id: newSessionId,
                  title: 'New Chat',
                  messages: [],
                  created_at: new Date().toISOString(),
                  updated_at: new Date().toISOString(),
                  isActive: true,
                  isSavedToSupabase: false,
                  isDirty: false
                };
                latestSessions = [newSession, ...latestSessions];
                sessionsRef.current = latestSessions;
                setSessions(latestSessions);
                currentActiveSessionId = newSessionId;
                updateActiveSessionId(newSessionId);
                
                // Update URL
                const url = new URL(window.location.href);
                url.searchParams.set('session', newSessionId);
                window.history.replaceState({}, '', url.toString());
                
                saveGuestSessions(latestSessions, newSessionId);
                console.log('✅ Created new session for guest user:', newSessionId);
              }
            } else {
              // No localStorage data - create new session
              const newSessionId = crypto.randomUUID();
              const newSession: ChatSession = {
                id: newSessionId,
                title: 'New Chat',
                messages: [],
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                isActive: true,
                isSavedToSupabase: false,
                isDirty: false
              };
              latestSessions = [newSession, ...latestSessions];
              sessionsRef.current = latestSessions;
              setSessions(latestSessions);
              currentActiveSessionId = newSessionId;
              updateActiveSessionId(newSessionId);
              
              // Update URL
              const url = new URL(window.location.href);
              url.searchParams.set('session', newSessionId);
              window.history.replaceState({}, '', url.toString());
              
              saveGuestSessions(latestSessions, newSessionId);
              console.log('✅ Created new session for guest user:', newSessionId);
            }
          }
        } catch (error) {
          console.error('❌ Error finding/creating session for guest user:', error);
          console.log('❌ Message will be discarded - no active session');
          return;
        }
      } else {
        console.log('No active session - message will be discarded. User must click "New Chat" first.');
        return;
      }
    }

    // Add message to existing session
    console.log('Adding message to existing session:', currentActiveSessionId);
    
    // Get the current session state from the ref (always current) - refresh it after potential updates
    const currentSessions = sessionsRef.current;
    const currentSession = currentSessions.find(s => s.id === currentActiveSessionId);
    console.log('Current session before update:', currentSession);
    console.log('Looking for session ID:', currentActiveSessionId);
    console.log('Available sessions in ref:', currentSessions.map(s => ({ id: s.id, isActive: s.isActive })));
    
    if (!currentSession) {
      console.error('Session not found:', currentActiveSessionId);
      return;
    }
    
    console.log('Found session to update:', {
      id: currentSession.id,
      currentMessages: currentSession.messages.length,
      currentMessagesContent: currentSession.messages.map(m => ({ sender: m.sender, text: m.text.substring(0, 30) + '...' }))
    });
    
    const updatedSessions = currentSessions.map(session => {
      if (session.id === currentActiveSessionId) {
        // CRITICAL: Always append message, never replace (same as logged-in users)
        // Ensure we're working with the latest session messages from ref
        const currentSessionMessages = session.messages || [];
        const newMessages = [...currentSessionMessages, message];
        
        console.log('📝 Appending message to session:', {
          sessionId: session.id,
          currentMessagesCount: currentSessionMessages.length,
          newMessageSender: message.sender,
          newMessageText: message.text?.substring(0, 50) + '...',
          newMessagesCount: newMessages.length
        });
        
        const updatedSession = {
          ...session,
          messages: newMessages,
          updated_at: new Date().toISOString()
        };
        
        // Auto-generate title if it's still "New Chat" and this is the first user message
        if (updatedSession.title === 'New Chat' && message.sender === 'user') {
          const generatedTitle = generateChatName(newMessages);
          if (generatedTitle && generatedTitle !== 'New Chat') {
            updatedSession.title = generatedTitle;
            console.log('🎨 Auto-generated chat title:', generatedTitle);
          }
        }
        
        console.log('Updated session:', {
          id: updatedSession.id,
          title: updatedSession.title,
          messagesCount: updatedSession.messages.length,
          messagesContent: updatedSession.messages.map(m => ({ sender: m.sender, text: m.text.substring(0, 30) + '...' }))
        });
        
        return updatedSession;
      }
      return session;
    });

    // Mark session as dirty (has unsaved changes)
    const updatedSessionsWithDirtyFlag = updatedSessions.map(session => {
      if (session.id === currentActiveSessionId) {
        return { ...session, isDirty: true };
      }
      return session;
    });

    setSessions(updatedSessionsWithDirtyFlag);
    
    // Immediately update the ref to ensure createNewSession gets the latest data
    sessionsRef.current = updatedSessionsWithDirtyFlag;

    if (user) {
      // Authenticated user - save to localStorage first for speed
      const userKey = `chat_history_${user.id}`;
      localStorage.setItem(userKey, JSON.stringify({
        sessions: updatedSessionsWithDirtyFlag,
        activeSessionId: currentActiveSessionId
      }));
      
      console.log('💾 Saved to localStorage for fast access. Supabase sync will happen later.');
    } else {
      // Guest user - save to localStorage immediately (same as logged-in users)
      // This ensures messages persist across page refreshes
      saveGuestSessions(updatedSessionsWithDirtyFlag, currentActiveSessionId || null);
      console.log('💾 Guest session saved to localStorage immediately:', {
        sessionId: currentActiveSessionId,
        messagesCount: updatedSessionsWithDirtyFlag.find(s => s.id === currentActiveSessionId)?.messages.length || 0
      });
    }

    console.log('Added message to existing session:', currentActiveSessionId);
    
    // Debug: Check session state after update
    setTimeout(() => {
      const updatedSession = updatedSessions.find(s => s.id === currentActiveSessionId);
      console.log('Session state after addMessage:', {
        sessionId: currentActiveSessionId,
        messagesCount: updatedSession?.messages.length || 0,
        messages: updatedSession?.messages.map(m => ({ sender: m.sender, text: m.text.substring(0, 30) + '...' })) || []
      });
    }, 100);
  }, [user, activeSessionId, sessions, saveGuestSessions, isGuestMode, updateActiveSessionId]);

  // Get active session
  const getActiveSession = useCallback((): ChatSession | null => {
    // Use refs for immediate consistency to prevent race conditions
    const currentSessions = sessionsRef.current;
    const currentActiveSessionId = activeSessionIdRef.current;
    
    if (!currentActiveSessionId) return null;
    
    return currentSessions.find(session => session.id === currentActiveSessionId) || null;
  }, []);

  // Clear active session
  const clearActiveSession = useCallback(() => {
    if (!activeSessionId) return;

    const updatedSessions = sessions.map(session => {
      if (session.id === activeSessionId) {
        return {
          ...session,
          messages: [],
          updated_at: new Date().toISOString()
        };
      }
      return session;
    });

    setSessions(updatedSessions);

    if (user) {
      // Authenticated user - save to Supabase
    const activeSession = updatedSessions.find(s => s.id === activeSessionId);
    if (activeSession) {
      saveSessionToSupabase(activeSession);
    }

    // Save to localStorage as backup
    const userKey = `chat_history_${user.id}`;
    localStorage.setItem(userKey, JSON.stringify({
      sessions: updatedSessions,
      activeSessionId
    }));
    } else {
      // Guest user - save to localStorage only
      saveGuestSessions(updatedSessions, activeSessionId);
    }

    console.log('Cleared active session:', activeSessionId);
  }, [user, activeSessionId, sessions, saveSessionToSupabase, saveGuestSessions]);

  // Listen for URL changes (browser back/forward)
  useEffect(() => {
    const handlePopState = () => {
      const urlParams = new URLSearchParams(window.location.search);
      const urlSessionId = urlParams.get('session');
      
      if (urlSessionId && urlSessionId !== activeSessionId) {
        const session = sessions.find(s => s.id === urlSessionId);
        if (session) {
          switchToSession(urlSessionId);
        }
      } else if (!urlSessionId && activeSessionId) {
        // URL doesn't have session but we have an active session
        // Keep current session active
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [activeSessionId, sessions, switchToSession]);

  // Ensure URL session ID is handled after loading
  useEffect(() => {
    if (!isLoading) {
      ensureUrlSessionHandled();
    }
  }, [isLoading, ensureUrlSessionHandled]);

  // Clear guest chat history when user logs in
  const clearGuestHistory = useCallback(() => {
    try {
      console.log('🧹 Clearing guest chat history...');
      
      // Clear guest sessions from localStorage
      const guestKey = 'guest_chat_sessions';
      localStorage.removeItem(guestKey);
      
      // Clear any guest-related data
      localStorage.removeItem('guest_chat_history');
      
      // Reset guest mode state
      setIsGuestMode(false);
      
      // Clear current sessions if we're in guest mode
      if (isGuestMode) {
        setSessions([]);
        updateActiveSessionId(null);
      }
      
      console.log('✅ Guest chat history cleared successfully');
    } catch (error) {
      console.error('Error clearing guest history:', error);
    }
  }, [isGuestMode, updateActiveSessionId]);

  // Load sessions when user changes OR on initial mount
  useEffect(() => {
    const currentUserId = user?.id || null;
    const previousUserId = hasLoadedForUserRef.current;
    
    // CRITICAL: Load on initial mount even if user is null (guest user)
    // Check if this is the first load (previousUserId is null) OR if sessions are empty
    const isInitialLoad = previousUserId === null;
    const hasNoSessions = sessions.length === 0;
    
    // Only skip if user unchanged AND we already have sessions loaded
    if (currentUserId === previousUserId && !isInitialLoad && !hasNoSessions) {
      console.log('⏭️ Skipping loadFromLocalStorage - user unchanged and sessions already loaded:', currentUserId);
      return;
    }
    
    // If this is initial load or sessions are empty, we need to load
    if (isInitialLoad || hasNoSessions) {
      console.log('🔄 Loading sessions - initial load or no sessions:', {
        isInitialLoad,
        hasNoSessions,
        currentUserId,
        previousUserId
      });
    } else {
      console.log('🔄 User changed - loading sessions:', { previous: previousUserId, current: currentUserId });
    }
    
    // If user logged out (had a user, now no user), clear everything first
    if (previousUserId && !currentUserId) {
      console.log('🚪 User logged out - clearing all state before loading guest sessions');
      // Clear all state first BEFORE updating ref
      updateActiveSessionId(null);
      setSessions([]);
      setIsGuestMode(false);
      setHasCheckedDatabase(false);
      setIsCreatingSession(false);
      setLastCreateSessionTime(0);
      setJustCreatedManualSession(false);
    }
    
    // Update ref to track current user BEFORE calling loadFromLocalStorage
    // This prevents the effect from running again if loadFromLocalStorage triggers any state changes
    hasLoadedForUserRef.current = currentUserId;
    
    setHasCheckedDatabase(false); // Reset database check flag when user changes
    setIsCreatingSession(false); // Reset session creation flag when user changes
    setLastCreateSessionTime(0); // Reset debounce timer when user changes
    setJustCreatedManualSession(false); // Reset manual session flag when user changes
    
    // Safety timeout to ensure loading completes even if something goes wrong
    const safetyTimeout = setTimeout(() => {
      console.log('⚠️ Safety timeout: forcing isLoading to false');
      setIsLoading(false);
    }, 3000); // 3 second safety timeout
    
    loadFromLocalStorage().finally(() => {
      clearTimeout(safetyTimeout);
    });
  }, [user?.id, loadFromLocalStorage, sessions.length, updateActiveSessionId]); // Include sessions.length to detect when sessions are empty

  // Clear guest history when user logs in
  useEffect(() => {
    if (user && isGuestMode) {
      console.log('🔄 User logged in - clearing guest history');
      clearGuestHistory();
    }
  }, [user, isGuestMode, clearGuestHistory]);

  // Clear cache and UI state when user logs out (but keep Supabase data)
  useEffect(() => {
    const previousUserId = hasLoadedForUserRef.current;
    
    // Only clear if user was previously logged in and now logged out
    // Don't clear for guest users who were never logged in
    if (!user && previousUserId) {
      console.log('🚪 User logged out - clearing cache and UI state (keeping Supabase data)');
      
      // Clear localStorage cache for this user
      const userKey = `chat_history_${previousUserId}`;
      localStorage.removeItem(userKey);
      console.log('🗑️ Cleared localStorage cache for user:', previousUserId);
      
      // Clear URL session parameter
      const url = new URL(window.location.href);
      url.searchParams.delete('session');
      window.history.pushState({}, '', url.toString());
      
      // Clear UI state (sessions in memory, active session) - CRITICAL: Clear everything
      // NOTE: This does NOT delete sessions from Supabase - they remain in database
      updateActiveSessionId(null);
      setSessions([]);
      setIsGuestMode(false);
      setHasCheckedDatabase(false);
      setIsCreatingSession(false);
      setLastCreateSessionTime(0);
      setJustCreatedManualSession(false);
      
      // Reset user tracking ref FIRST
      hasLoadedForUserRef.current = null;
      
      // Force reload guest sessions after clearing logged-in user data
      // Use a longer delay to ensure all state is cleared first
      setTimeout(() => {
        console.log('🔄 Loading fresh guest sessions after logout...');
        loadGuestSessions();
      }, 200);
      
      console.log('✅ Cache cleared. User data remains in Supabase and will be restored on next login.');
    }
  }, [user, updateActiveSessionId, loadGuestSessions]); // updateActiveSessionId is stable (useCallback with dependencies)

  // Auto-save sessions before page unload (no popup)
  useEffect(() => {
    const handleBeforeUnload = async () => {
      if (user && hasUnsavedSessions()) {
        // Auto-save without showing popup
        console.log('🔄 Auto-saving sessions before page unload...');
        try {
          await saveAllUnsavedSessions();
          console.log('✅ Sessions auto-saved successfully');
        } catch (error) {
          console.error('Error auto-saving sessions:', error);
        }
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      // Detect Ctrl+R, F5, or Ctrl+Shift+R (refresh shortcuts)
      if ((event.ctrlKey && event.key === 'r') || 
          event.key === 'F5' || 
          (event.ctrlKey && event.shiftKey && event.key === 'R')) {
        if (user && hasUnsavedSessions()) {
          // Auto-save and refresh only chat components
          event.preventDefault();
          console.log('🔄 Refresh detected - auto-saving and refreshing chat components...');
          saveAllUnsavedSessions().then(() => {
            // Trigger a custom refresh event for chat components
            window.dispatchEvent(new CustomEvent('refreshChatComponents'));
          });
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [user, hasUnsavedSessions, saveAllUnsavedSessions]);

  // Refresh chat components function (blink effect removed to prevent blinking on page refresh)
  const refreshChatComponents = useCallback(async () => {
    console.log('🔄 Refreshing chat components...');
    
    try {
      // Auto-save any unsaved sessions first (non-blocking)
      if (user && hasUnsavedSessions()) {
        saveAllUnsavedSessions().catch(error => {
          console.error('Error auto-saving sessions:', error);
        });
      }
      
      // Reload sessions from the database/localStorage immediately
      await loadFromLocalStorage();
      
      console.log('✅ Chat components refreshed successfully');
    } catch (error) {
      console.error('Error refreshing chat components:', error);
    }
  }, [user, hasUnsavedSessions, saveAllUnsavedSessions, loadFromLocalStorage]);

  // Don't create sessions automatically - only when user explicitly clicks "New Chat"
  // This prevents unwanted session creation on page refresh

  // Calculate active session message count to detect session updates
  const activeSession = sessionsRef.current.find(s => s.id === activeSessionIdRef.current);
  const activeSessionMessageCount = activeSession?.messages.length || 0;

  const value: ChatHistoryContextType = {
    sessions,
    activeSessionId,
    isLoading: isLoading,
    isGuestMode,
    activeSessionMessageCount, // Track message count to detect session updates
    createNewSession,
    switchToSession,
    deleteSession,
    deleteAllSessions,
    updateSessionTitle,
    addMessage,
    getActiveSession,
    clearActiveSession,
    clearGuestHistory,
    saveSessionToSupabase: saveSessionToSupabaseById,
    hasUnsavedSessions,
    saveAllUnsavedSessions,
    refreshChatComponents
  };

  return (
    <ChatHistoryContext.Provider value={value}>
      {children}
    </ChatHistoryContext.Provider>
  );
};