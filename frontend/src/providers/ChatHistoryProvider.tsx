"use client";
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useAuth } from './AuthProvider';
import { useSupabase } from './SupabaseProvider';

export interface ChatMessage {
  sender: 'user' | 'bot';
  text: string;
  type?: string;
  url?: string;
  videos?: any[];
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
      }
    } catch (error) {
      console.error('Error saving session to Supabase:', error);
    }
  }, [supabase, user]);

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

          setActiveSessionId(activeSessionId);
          console.log('Final active session:', activeSessionId);
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

              setActiveSessionId(activeSessionId);
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

            setActiveSessionId(activeSessionId);
            console.log('Fallback to localStorage sessions:', migratedSessions.length);
          } catch (error) {
            console.error('Error loading chat history from localStorage:', error);
          }
        }
      }
      setIsLoading(false);
    } else {
      console.log('No user, setting loading to false');
      setIsLoading(false);
    }
  }, [user, loadSessionsFromSupabase, migrateSessionId]);

  // Create new session
  const createNewSession = useCallback(async () => {
    if (!user) return;

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

    // Mark all other sessions as inactive and save new session
    const updatedSessions = sessions.map(session => ({ ...session, isActive: false }));
    const newSessions = [newSession, ...updatedSessions];
    
    setSessions(newSessions);
    setActiveSessionId(newSession.id);

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

    console.log('Created new session:', newSession.id);
  }, [user, sessions, saveSessionToSupabase]);

  // Switch to session
  const switchToSession = useCallback(async (sessionId: string) => {
    if (!user) return;

    // Update URL with session ID
    const url = new URL(window.location.href);
    url.searchParams.set('session', sessionId);
    window.history.pushState({}, '', url.toString());

    // Mark selected session as active and others as inactive
    const updatedSessions = sessions.map(session => ({
      ...session,
      isActive: session.id === sessionId
    }));
    
    setSessions(updatedSessions);
    setActiveSessionId(sessionId);

    // Save to Supabase
    await Promise.all(updatedSessions.map(session => saveSessionToSupabase(session)));

    // Save to localStorage as backup
    const userKey = `chat_history_${user.id}`;
    localStorage.setItem(userKey, JSON.stringify({
      sessions: updatedSessions,
      activeSessionId: sessionId
    }));

    console.log('Switched to session:', sessionId);
  }, [user, sessions, saveSessionToSupabase]);

  // Delete session
  const deleteSession = useCallback(async (sessionId: string) => {
    if (!user) return;

    const updatedSessions = sessions.filter(session => session.id !== sessionId);
    setSessions(updatedSessions);

    // If deleted session was active, switch to most recent or remove URL param
    if (activeSessionId === sessionId) {
      if (updatedSessions.length > 0) {
        const url = new URL(window.location.href);
        url.searchParams.set('session', updatedSessions[0].id);
        window.history.pushState({}, '', url.toString());
        setActiveSessionId(updatedSessions[0].id);
      } else {
        const url = new URL(window.location.href);
        url.searchParams.delete('session');
        window.history.pushState({}, '', url.toString());
        setActiveSessionId(null);
      }
    }

    // Delete from Supabase
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

    console.log('Deleted session:', sessionId);
  }, [user, sessions, activeSessionId, supabase]);

  // Delete all sessions
  const deleteAllSessions = useCallback(async () => {
    if (!user) return;

      setSessions([]);
      setActiveSessionId(null);

    // Remove session from URL
    const url = new URL(window.location.href);
    url.searchParams.delete('session');
    window.history.pushState({}, '', url.toString());

    // Delete from Supabase
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

    console.log('Deleted all sessions');
  }, [user, supabase]);

  // Update session title
  const updateSessionTitle = useCallback(async (sessionId: string, newTitle: string) => {
    if (!user) return;

    const updatedSessions = sessions.map(session => 
      session.id === sessionId 
        ? { ...session, title: newTitle, updated_at: new Date().toISOString() }
        : session
    );
    
    setSessions(updatedSessions);

    // Save to Supabase
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

    console.log('Updated session title:', sessionId, newTitle);
  }, [user, sessions, activeSessionId, saveSessionToSupabase]);

  // Add message to active session
  const addMessage = useCallback(async (message: ChatMessage) => {
    if (!user || !activeSessionId) {
      // Create new session if none exists
      await createNewSession();
      return;
    }

    const updatedSessions = sessions.map(session => {
      if (session.id === activeSessionId) {
        return {
          ...session,
          messages: [...session.messages, message],
          updated_at: new Date().toISOString()
        };
      }
      return session;
    });

    setSessions(updatedSessions);

    // Save to Supabase
    const activeSession = updatedSessions.find(s => s.id === activeSessionId);
    if (activeSession) {
      await saveSessionToSupabase(activeSession);
    }

    // Save to localStorage as backup
    const userKey = `chat_history_${user.id}`;
    localStorage.setItem(userKey, JSON.stringify({
      sessions: updatedSessions,
      activeSessionId
    }));

    console.log('Added message to session:', activeSessionId);
  }, [user, activeSessionId, sessions, createNewSession, saveSessionToSupabase]);

  // Get active session
  const getActiveSession = useCallback((): ChatSession | null => {
    return sessions.find(session => session.id === activeSessionId) || null;
  }, [sessions, activeSessionId]);

  // Clear active session
  const clearActiveSession = useCallback(() => {
    if (!user || !activeSessionId) return;

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

    // Save to Supabase
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

    console.log('Cleared active session:', activeSessionId);
  }, [user, activeSessionId, sessions, saveSessionToSupabase]);

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
  useEffect(() => {
    if (!user && activeSessionId) {
      const url = new URL(window.location.href);
      url.searchParams.delete('session');
      window.history.pushState({}, '', url.toString());
      setActiveSessionId(null);
      setSessions([]);
    }
  }, [user, activeSessionId]);

  // Create initial session if none exists
  useEffect(() => {
    if (user && !isLoading && sessions.length === 0 && !activeSessionId) {
      createNewSession();
    }
  }, [user, isLoading, sessions.length, activeSessionId, createNewSession]);

  const value: ChatHistoryContextType = {
    sessions,
    activeSessionId,
    isLoading,
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