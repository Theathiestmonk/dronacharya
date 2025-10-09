"use client";
import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { useAuth } from './AuthProvider';
import { useSupabase } from './SupabaseProvider';

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
  }, [activeSessionId]);
  
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

  // Load guest sessions from localStorage
  const loadGuestSessions = useCallback(async () => {
    try {
      const guestKey = 'guest_chat_sessions';
      const saved = localStorage.getItem(guestKey);
      console.log('Loading guest sessions from localStorage');
      
      if (saved) {
        const data = JSON.parse(saved);
        const guestSessions = data.sessions || [];
        setSessions(guestSessions);
        updateActiveSessionId(data.activeSessionId || null);
        setIsGuestMode(true);
        console.log('Loaded guest sessions:', guestSessions.length);
      } else {
        console.log('No guest sessions found');
        setIsGuestMode(true);
      }
    } catch (error) {
      console.error('Error loading guest sessions:', error);
      setIsGuestMode(true);
    } finally {
      setIsLoading(false);
    }
  }, [updateActiveSessionId]);

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

  // Load from localStorage with priority order
  const loadFromLocalStorage = useCallback(async () => {
    if (user) {
      // Check for session ID in URL first
      const urlParams = new URLSearchParams(window.location.search);
      const urlSessionId = urlParams.get('session');
      console.log('URL session ID:', urlSessionId);

      try {
        console.log('Loading chat history for user:', user.id);

        // First try to load from Supabase
        const supabaseSessions = await loadSessionsFromSupabase();
        console.log('Supabase sessions loaded:', supabaseSessions.length);
        
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
            }
          }

          if (!activeSessionId) {
            const activeSession = supabaseSessions.find((s: ChatSession) => s.isActive);
            if (activeSession) {
              activeSessionId = activeSession.id;
              console.log('Using session marked as active:', activeSessionId);
            }
          }

          if (!activeSessionId) {
            activeSessionId = supabaseSessions[0]?.id || null;
            console.log('Using most recent session:', activeSessionId);
          }

          updateActiveSessionId(activeSessionId);
          console.log('Final active session set to:', activeSessionId);
          console.log('Session details:', supabaseSessions.find(s => s.id === activeSessionId));
        } else {
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

  // Create new session
  const createNewSession = useCallback(async () => {
    const newSession: ChatSession = {
      id: crypto.randomUUID(),
      title: 'New Chat',
      messages: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      isActive: true
    };

    // Update URL with new session ID
    const url = new URL(window.location.href);
    url.searchParams.set('session', newSession.id);
    window.history.pushState({}, '', url.toString());

    if (user) {
      // Authenticated user - save to Supabase and localStorage
    const updatedSessions = sessions.map(session => ({ ...session, isActive: false }));
    const newSessions = [newSession, ...updatedSessions];
    
    setSessions(newSessions);
      updateActiveSessionId(newSession.id);

    // Save to Supabase
    await Promise.all([
      ...updatedSessions.map(session => saveSessionToSupabase(session)),
      saveSessionToSupabase(newSession)
    ]);

    // Save to localStorage as backup
    const userKey = `chat_history_${user.id}`;
    localStorage.setItem(userKey, JSON.stringify({
      sessions: newSessions,
      activeSessionId: newSession.id
    }));
    } else {
      // Guest user - save to localStorage only
      const updatedSessions = sessions.map(session => ({ ...session, isActive: false }));
      const newSessions = [newSession, ...updatedSessions];
      
      setSessions(newSessions);
      updateActiveSessionId(newSession.id);
      setIsGuestMode(true);

      // Save guest sessions to localStorage
      saveGuestSessions(newSessions, newSession.id);
    }

    console.log('Created new session:', newSession.id);
  }, [user, sessions, saveSessionToSupabase, saveGuestSessions, updateActiveSessionId]);

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
    
    // If no active session, create one for guest users
    if (!currentActiveSessionId) {
      console.log('No active session - creating new session automatically for guest user');
      if (!user || isGuestMode) {
        // Create a new session for guest users
        const newSession: ChatSession = {
          id: crypto.randomUUID(),
          title: 'New Chat',
          messages: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          isActive: true
        };

        // Update URL with new session ID
        const url = new URL(window.location.href);
        url.searchParams.set('session', newSession.id);
        window.history.pushState({}, '', url.toString());

        if (user) {
          // Authenticated user - save to Supabase and localStorage
          const updatedSessions = sessions.map(session => ({ ...session, isActive: false }));
          const newSessions = [newSession, ...updatedSessions];
          
          setSessions(newSessions);
          updateActiveSessionId(newSession.id);

          // Save to Supabase
          await Promise.all([
            ...updatedSessions.map(session => saveSessionToSupabase(session)),
            saveSessionToSupabase(newSession)
          ]);

          // Save to localStorage as backup
          const userKey = `chat_history_${user.id}`;
          localStorage.setItem(userKey, JSON.stringify({
            sessions: newSessions,
            activeSessionId: newSession.id
          }));
        } else {
          // Guest user - save to localStorage only
          const updatedSessions = sessions.map(session => ({ ...session, isActive: false }));
          const newSessions = [newSession, ...updatedSessions];
          
          setSessions(newSessions);
          updateActiveSessionId(newSession.id);
          setIsGuestMode(true);

          // Save guest sessions to localStorage
          saveGuestSessions(newSessions, newSession.id);
        }

        console.log('Created new session automatically:', newSession.id);
        
        // Update the sessionsRef to reflect the new session immediately
        const updatedSessionsForRef = user ? 
          [...sessions.map(session => ({ ...session, isActive: false })), newSession] :
          [...sessions.map(session => ({ ...session, isActive: false })), newSession];
        sessionsRef.current = updatedSessionsForRef;
        // activeSessionIdRef is now updated by updateActiveSessionId
        
        // Use the new session ID immediately
        currentActiveSessionId = newSession.id;
        
        console.log('✅ Session created and refs updated immediately:', {
          sessionId: newSession.id,
          totalSessions: updatedSessionsForRef.length,
          activeSession: updatedSessionsForRef.find(s => s.isActive)?.id,
          activeSessionIdRef: activeSessionIdRef.current
        });
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

    setSessions(updatedSessions);

    if (user) {
      // Authenticated user - save to Supabase
      const activeSession = updatedSessions.find(s => s.id === currentActiveSessionId);
    if (activeSession) {
      console.log('Saving updated session to Supabase with', activeSession.messages.length, 'messages');
      await saveSessionToSupabase(activeSession);
    }

    // Save to localStorage as backup
    const userKey = `chat_history_${user.id}`;
    localStorage.setItem(userKey, JSON.stringify({
      sessions: updatedSessions,
        activeSessionId: currentActiveSessionId
    }));
    } else {
      // Guest user - save to localStorage only
      saveGuestSessions(updatedSessions, currentActiveSessionId || null);
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
  }, [user, activeSessionId, sessions, saveSessionToSupabase, saveGuestSessions, isGuestMode, updateActiveSessionId]);

  // Get active session
  const getActiveSession = useCallback((): ChatSession | null => {
    return sessions.find(session => session.id === activeSessionId) || null;
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

  // Load sessions when user changes
  useEffect(() => {
    loadFromLocalStorage();
  }, [loadFromLocalStorage]);

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
    clearActiveSession
  };

  return (
    <ChatHistoryContext.Provider value={value}>
      {children}
    </ChatHistoryContext.Provider>
  );
};