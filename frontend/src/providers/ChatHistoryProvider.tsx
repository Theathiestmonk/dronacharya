"use client";
import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { useAuth } from './AuthProvider';
import { useSupabase } from './SupabaseProvider';
import SaveChatDialog from '../components/SaveChatDialog';

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
  
  // Save dialog state
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  
  // Use ref to get current sessions state
  const sessionsRef = useRef<ChatSession[]>([]);
  const activeSessionIdRef = useRef<string | null>(null);
  
  // Helper function to update both state and ref
  const updateActiveSessionId = useCallback((sessionId: string | null) => {
    console.log('🔄 updateActiveSessionId called:', {
      newSessionId: sessionId,
      currentRefValue: activeSessionIdRef.current,
      currentStateValue: activeSessionId
    });
    setActiveSessionId(sessionId);
    activeSessionIdRef.current = sessionId;
    console.log('✅ updateActiveSessionId completed:', {
      refValue: activeSessionIdRef.current,
      stateValue: sessionId
    });
  }, [activeSessionId]); // Remove activeSessionId from dependencies to prevent loop
  
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

  // Save guest sessions to localStorage
  const saveGuestSessions = useCallback((sessions: ChatSession[], activeId: string | null) => {
    try {
      const guestKey = 'guest_chat_sessions';
      const data = {
        sessions,
        activeSessionId: activeId
      };
      localStorage.setItem(guestKey, JSON.stringify(data));
      console.log('💾 Saved guest sessions to localStorage:', {
        key: guestKey,
        sessionsCount: sessions.length,
        activeSessionId: activeId,
        sessionIds: sessions.map(s => s.id)
      });
    } catch (error) {
      console.error('Error saving guest sessions:', error);
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
        setSessions(guestSessions);
        
        // If URL has session ID, use it if it exists in sessions, otherwise create it
        let activeSessionId = data.activeSessionId || null;
        if (urlSessionId) {
          const urlSession = guestSessions.find((s: ChatSession) => s.id === urlSessionId);
          if (urlSession) {
            activeSessionId = urlSessionId;
            console.log('Using existing session from URL:', urlSessionId);
          } else {
            // Create a new session with the URL session ID
            console.log('Creating new session with URL session ID:', urlSessionId);
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
            setSessions(updatedSessions);
            activeSessionId = urlSessionId;
            
            // Save the new session to localStorage
            saveGuestSessions(updatedSessions, urlSessionId);
          }
        }
        
        updateActiveSessionId(activeSessionId);
        setIsGuestMode(true);
        console.log('Loaded guest sessions:', guestSessions.length);
      } else {
        console.log('No guest sessions found');
        
        // If URL has session ID but no localStorage data, create session
        if (urlSessionId) {
          console.log('Creating new session with URL session ID (no localStorage):', urlSessionId);
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
          setSessions([newSession]);
          updateActiveSessionId(urlSessionId);
          
          // Save the new session to localStorage
          saveGuestSessions([newSession], urlSessionId);
        }
        
        setIsGuestMode(true);
      }
    } catch (error) {
      console.error('Error loading guest sessions:', error);
      setIsGuestMode(true);
    } finally {
      setIsLoading(false);
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
        
        if (localData) {
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
        }

        // Then sync with Supabase in background
        const supabaseSessions = await loadSessionsFromSupabase();
        console.log('Supabase sessions loaded:', supabaseSessions.length);
        setHasCheckedDatabase(true); // Mark that we've checked the database
        
        if (supabaseSessions.length > 0) {
          // Use Supabase data
          setSessions(supabaseSessions);

          // Priority order for active session:
          // 1. Session ID from URL (if it exists in loaded sessions)
          // 2. Session marked as active in database
          // 3. Most recently updated session
          let activeSessionId = null;

          if (urlSessionId) {
            const urlSession = supabaseSessions.find((s: ChatSession) => s.id === urlSessionId);
            if (urlSession) {
              activeSessionId = urlSessionId;
              console.log('Using session from URL:', urlSessionId);
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
            
            const activeSession = supabaseSessions.find((s: ChatSession) => s.isActive);
            if (activeSession) {
              activeSessionId = activeSession.id;
              console.log('Using session marked as active:', activeSessionId);
            }
          }

          if (!activeSessionId) {
            // CRITICAL: Don't override manually created sessions
            if (justCreatedManualSession || isCreatingSession) {
              console.log('🚫 Skipping Supabase session override - manual session creation in progress');
              return;
            }
            
            activeSessionId = supabaseSessions[0]?.id || null;
            console.log('Using most recent session:', activeSessionId);
          }

          updateActiveSessionId(activeSessionId);
          console.log('Final active session set to:', activeSessionId);
          console.log('Session details:', supabaseSessions.find(s => s.id === activeSessionId));
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
  }, [user, loadSessionsFromSupabase, migrateSessionId, loadGuestSessions, updateActiveSessionId]);

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
        
        // For authenticated users, save to Supabase if dirty
        if (user && currentSession.isDirty && !currentSession.isSavedToSupabase) {
          console.log('🔄 Auto-saving previous session to Supabase...');
          await saveSessionToSupabase(currentSession);
          
          // Mark as saved
          setSessions(prevSessions => 
            prevSessions.map(s => 
              s.id === activeSessionIdRef.current 
                ? { ...s, isSavedToSupabase: true, isDirty: false }
                : s
            )
          );
          console.log('✅ Previous session auto-saved to Supabase');
        }
        
        // For all users (authenticated and guest), ensure localStorage is up to date
        if (user) {
          const userKey = `chat_history_${user.id}`;
          localStorage.setItem(userKey, JSON.stringify({
            sessions: currentSessions,
            activeSessionId: activeSessionIdRef.current
          }));
          console.log('💾 Updated localStorage for authenticated user');
        } else {
          // Guest user - ensure localStorage is up to date
          saveGuestSessions(currentSessions, activeSessionIdRef.current);
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
      
      setSessions(newSessions);
      updateActiveSessionId(newSession.id);
      
      // Immediately update the refs to prevent auto-creation conflicts
      sessionsRef.current = newSessions;
      activeSessionIdRef.current = newSession.id;

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
      
      setSessions(newSessions);
      updateActiveSessionId(newSession.id);
      setIsGuestMode(true);
      
      // Immediately update the refs to prevent auto-creation conflicts
      sessionsRef.current = newSessions;
      activeSessionIdRef.current = newSession.id;

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
    console.log('Current activeSessionId:', activeSessionId);
    console.log('Current sessions count:', sessions.length);
    
    // HOT RELOAD FIX: Always reload from localStorage first to survive hot reloads
    let latestSessions = sessionsRef.current;
    let currentActiveSessionId = activeSessionIdRef.current;
    
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
    
    // If no active session, don't create one automatically - user must click "New Chat"
    if (!currentActiveSessionId) {
      console.log('No active session - message will be discarded. User must click "New Chat" first.');
      return;
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
        const updatedSession = {
          ...session,
          messages: [...session.messages, message],
          updated_at: new Date().toISOString()
        };
        
        console.log('Updated session:', {
          id: updatedSession.id,
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
      // Guest user - save to localStorage only
      saveGuestSessions(updatedSessionsWithDirtyFlag, currentActiveSessionId || null);
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
  }, [sessions, activeSessionId]);

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

  // Load sessions when user changes
  useEffect(() => {
    setHasCheckedDatabase(false); // Reset database check flag when user changes
    setIsCreatingSession(false); // Reset session creation flag when user changes
    setLastCreateSessionTime(0); // Reset debounce timer when user changes
    setJustCreatedManualSession(false); // Reset manual session flag when user changes
    loadFromLocalStorage();
  }, [loadFromLocalStorage]);

  // Clear guest history when user logs in
  useEffect(() => {
    if (user && isGuestMode) {
      console.log('🔄 User logged in - clearing guest history');
      clearGuestHistory();
    }
  }, [user, isGuestMode, clearGuestHistory]);

  // Clear session from URL when user logs out
  // Clear session when user logs out (but not for guest users)
  useEffect(() => {
    // Only clear session if user was previously logged in and now logged out
    // Don't clear for guest users who were never logged in
    if (!user && activeSessionId && !isGuestMode) {
      console.log('🔄 User logged out - clearing session');
      const url = new URL(window.location.href);
      url.searchParams.delete('session');
      window.history.pushState({}, '', url.toString());
      updateActiveSessionId(null);
      setSessions([]);
      setIsGuestMode(false);
    }
  }, [user, activeSessionId, isGuestMode, updateActiveSessionId]);

  // Page refresh detection with custom save dialog
  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (user && hasUnsavedSessions() && !showSaveDialog) {
        // Show our custom dialog and prevent browser dialog
        setShowSaveDialog(true);
        event.preventDefault();
        event.returnValue = '';
        return '';
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      // Detect Ctrl+R, F5, or Ctrl+Shift+R (refresh shortcuts)
      if ((event.ctrlKey && event.key === 'r') || 
          event.key === 'F5' || 
          (event.ctrlKey && event.shiftKey && event.key === 'R')) {
        if (user && hasUnsavedSessions() && !showSaveDialog) {
          event.preventDefault();
          setShowSaveDialog(true);
        }
      }
    };

    const handlePageShow = (event: PageTransitionEvent) => {
      if (event.persisted && user && hasUnsavedSessions()) {
        // Page was restored from cache and has unsaved sessions
        console.log('🔄 Page restored from cache with unsaved sessions');
        setShowSaveDialog(true);
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('pageshow', handlePageShow);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('pageshow', handlePageShow);
    };
  }, [user, hasUnsavedSessions, showSaveDialog]);

  // Handle save dialog actions
  const handleSaveSessions = useCallback(async () => {
    setIsSaving(true);
    try {
      await saveAllUnsavedSessions();
      setShowSaveDialog(false);
      console.log('✅ All sessions saved successfully');
      // Reload the page after saving
      window.location.reload();
    } catch (error) {
      console.error('Error saving sessions:', error);
    } finally {
      setIsSaving(false);
    }
  }, [saveAllUnsavedSessions]);

  const handleDiscardSessions = useCallback(() => {
    setShowSaveDialog(false);
    console.log('🗑️ User chose to discard unsaved sessions');
    // Clear the unsaved sessions from localStorage
    if (user) {
      const userKey = `chat_history_${user.id}`;
      const savedData = localStorage.getItem(userKey);
      if (savedData) {
        const parsedData = JSON.parse(savedData);
        // Mark all sessions as saved to prevent the dialog from showing again
        const updatedSessions = parsedData.sessions.map((session: ChatSession) => ({
          ...session,
          isDirty: false,
          isSavedToSupabase: true
        }));
        localStorage.setItem(userKey, JSON.stringify({
          ...parsedData,
          sessions: updatedSessions
        }));
      }
    }
    // Reload the page without saving
    window.location.reload();
  }, [user]);

  const handleCloseDialog = useCallback(() => {
    setShowSaveDialog(false);
    console.log('❌ User cancelled save dialog');
  }, []);

  // Don't create sessions automatically - only when user explicitly clicks "New Chat"
  // This prevents unwanted session creation on page refresh

  const value: ChatHistoryContextType = {
    sessions,
    activeSessionId,
    isLoading,
    isGuestMode,
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
    saveAllUnsavedSessions
  };

  return (
    <ChatHistoryContext.Provider value={value}>
      {children}
      <SaveChatDialog
        isOpen={showSaveDialog}
        onClose={handleCloseDialog}
        onSave={handleSaveSessions}
        onDiscard={handleDiscardSessions}
        isLoading={isSaving}
        unsavedCount={sessions.filter(s => s.isDirty && !s.isSavedToSupabase).length}
      />
    </ChatHistoryContext.Provider>
  );
};