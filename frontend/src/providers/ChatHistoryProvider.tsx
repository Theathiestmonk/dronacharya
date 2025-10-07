"use client";
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthProvider';
import { useSupabase } from './SupabaseProvider';

export interface ChatMessage {
  sender: 'user' | 'bot';
  text: string;
  timestamp: number;
  type?: 'calendar' | 'map' | 'videos';
  url?: string;
  videos?: Array<{video_id: string; title: string; description: string; category: string; duration: string; thumbnail_url: string}>;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
  isActive: boolean;
}

interface ChatHistoryContextType {
  sessions: ChatSession[];
  activeSessionId: string | null;
  isLoading: boolean;
  retentionPolicy: SessionRetentionOption;
  supabaseAvailable: boolean;
  createNewSession: () => string;
  switchToSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
  deleteAllSessions: () => void;
  updateSessionTitle: (sessionId: string, title: string) => void;
  addMessage: (message: ChatMessage) => void;
  clearActiveSession: () => void;
  getActiveSession: () => ChatSession | null;
  saveToLocalStorage: () => void;
  loadFromLocalStorage: () => void;
  cleanupOldSessions: () => void;
  setRetentionPolicy: (policy: SessionRetentionOption) => void;
}

const ChatHistoryContext = createContext<ChatHistoryContextType | undefined>(undefined);

export const useChatHistory = () => {
  const context = useContext(ChatHistoryContext);
  if (!context) {
    throw new Error('useChatHistory must be used within a ChatHistoryProvider');
  }
  return context;
};

// Session retention options
export const SESSION_RETENTION_OPTIONS = {
  NEVER: 'never',           // Keep forever
  ONE_DAY: '1_day',         // 1 day
  THREE_DAYS: '3_days',     // 3 days
  ONE_WEEK: '1_week',       // 1 week
  TWO_WEEKS: '2_weeks',     // 2 weeks
  ONE_MONTH: '1_month',     // 1 month
  THREE_MONTHS: '3_months', // 3 months
} as const;

export type SessionRetentionOption = typeof SESSION_RETENTION_OPTIONS[keyof typeof SESSION_RETENTION_OPTIONS];

export const ChatHistoryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const supabase = useSupabase();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  // Default retention policy - can be configured
  const [retentionPolicy, setRetentionPolicy] = useState<SessionRetentionOption>(SESSION_RETENTION_OPTIONS.ONE_WEEK);
  
  // Track if Supabase is available and working
  const [supabaseAvailable, setSupabaseAvailable] = useState(true);

  // Get retention period in milliseconds
  const getRetentionPeriodMs = (policy: SessionRetentionOption): number => {
    switch (policy) {
      case SESSION_RETENTION_OPTIONS.NEVER:
        return Infinity;
      case SESSION_RETENTION_OPTIONS.ONE_DAY:
        return 24 * 60 * 60 * 1000; // 1 day
      case SESSION_RETENTION_OPTIONS.THREE_DAYS:
        return 3 * 24 * 60 * 60 * 1000; // 3 days
      case SESSION_RETENTION_OPTIONS.ONE_WEEK:
        return 7 * 24 * 60 * 60 * 1000; // 1 week
      case SESSION_RETENTION_OPTIONS.TWO_WEEKS:
        return 14 * 24 * 60 * 60 * 1000; // 2 weeks
      case SESSION_RETENTION_OPTIONS.ONE_MONTH:
        return 30 * 24 * 60 * 60 * 1000; // 1 month
      case SESSION_RETENTION_OPTIONS.THREE_MONTHS:
        return 90 * 24 * 60 * 60 * 1000; // 3 months
      default:
        return 7 * 24 * 60 * 60 * 1000; // Default to 1 week
    }
  };

  // Clean up old sessions based on retention policy
  const cleanupOldSessions = useCallback(() => {
    if (retentionPolicy === SESSION_RETENTION_OPTIONS.NEVER) {
      return; // Don't clean up if retention is set to never
    }

    const retentionPeriodMs = getRetentionPeriodMs(retentionPolicy);
    const cutoffTime = Date.now() - retentionPeriodMs;

    setSessions(prevSessions => {
      const filteredSessions = prevSessions.filter(session => session.updatedAt >= cutoffTime);
      
      // If we filtered out the active session, switch to the most recent remaining session
      if (filteredSessions.length > 0 && activeSessionId) {
        const activeSessionExists = filteredSessions.some(session => session.id === activeSessionId);
        if (!activeSessionExists) {
          const mostRecent = filteredSessions.sort((a, b) => b.updatedAt - a.updatedAt)[0];
          setActiveSessionId(mostRecent.id);
        }
      } else if (filteredSessions.length === 0) {
        setActiveSessionId(null);
      }
      
      return filteredSessions;
    });
  }, [retentionPolicy, activeSessionId]);

  // Generate unique session ID using proper UUID format
  const generateSessionId = () => {
    // Generate a proper UUID v4
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  };

  // Check if a string is a valid UUID
  const isValidUUID = (str: string) => {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(str);
  };

  // Migrate old session IDs to UUID format
  const migrateSessionId = useCallback((oldId: string) => {
    if (isValidUUID(oldId)) {
      return oldId; // Already a valid UUID
    }
    // Convert old format to UUID
    return generateSessionId();
  }, []);

  // Save session to Supabase
  const saveSessionToSupabase = useCallback(async (session: ChatSession) => {
    if (!supabase || !user || !supabaseAvailable) {
      console.log('Supabase not available, skipping save');
      return;
    }

    try {
      console.log('Attempting to save session to Supabase:', {
        id: session.id,
        title: session.title,
        messageCount: session.messages.length,
        userId: user.id
      });

      const { error } = await supabase
        .from('chat_sessions')
        .upsert({
          id: session.id,
          user_id: user.id,
          title: session.title,
          messages: session.messages,
          is_active: session.isActive,
          updated_at: new Date(session.updatedAt).toISOString(),
        });

      if (error) {
        console.error('Error saving session to Supabase:', {
          error: error,
          message: error.message,
          details: error.details,
          hint: error.hint,
          code: error.code
        });
        
        // If it's a table doesn't exist error, disable Supabase
        if (error.code === '42P01' || error.message.includes('relation "chat_sessions" does not exist')) {
          console.warn('❌ chat_sessions table does not exist! Please run the SQL schema in your Supabase dashboard.');
          console.warn('📋 Go to Supabase Dashboard → SQL Editor → Run the chat_sessions_schema.sql file');
          setSupabaseAvailable(false);
        } else if (error.code === '42501') {
          console.warn('❌ Permission denied! Please check your Supabase RLS policies.');
          setSupabaseAvailable(false);
        } else {
          console.warn('❌ Supabase error:', error.message);
          setSupabaseAvailable(false);
        }
      } else {
        console.log('✅ Session saved to Supabase successfully:', session.id);
      }
    } catch (error) {
      console.error('Exception saving session to Supabase:', {
        error: error,
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined
      });
      
      // Disable Supabase on any exception
      setSupabaseAvailable(false);
    }
  }, [supabase, user, supabaseAvailable]);

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

      return data.map(session => ({
        id: session.id,
        title: session.title,
        messages: session.messages || [],
        createdAt: new Date(session.created_at).getTime(),
        updatedAt: new Date(session.updated_at).getTime(),
        isActive: session.is_active || false,
      }));
    } catch (error) {
      console.error('Error loading sessions from Supabase:', error);
      return [];
    }
  }, [supabase, user]);

  // Delete session from Supabase
  const deleteSessionFromSupabase = useCallback(async (sessionId: string) => {
    if (!supabase || !user || !supabaseAvailable) {
      console.log('Supabase not available, skipping delete for session:', sessionId);
      return;
    }

    try {
      console.log('🗑️ Deleting session from Supabase:', sessionId);
      
      const { error } = await supabase
        .from('chat_sessions')
        .delete()
        .eq('id', sessionId)
        .eq('user_id', user.id);

      if (error) {
        console.error('❌ Error deleting session from Supabase:', {
          sessionId,
          error: error.message,
          details: error.details,
          hint: error.hint
        });
      } else {
        console.log('✅ Session deleted from Supabase successfully:', sessionId);
      }
    } catch (error) {
      console.error('❌ Exception deleting session from Supabase:', {
        sessionId,
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }, [supabase, user, supabaseAvailable]);

  // Generate intelligent session title from first user message
  const generateSessionTitle = (firstMessage: string) => {
    const text = firstMessage.toLowerCase();
    
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
    const words = firstMessage.trim().split(' ').slice(0, 4);
    return words.join(' ') + (firstMessage.split(' ').length > 4 ? '...' : '');
  };

  // Create new chat session
  const createNewSession = useCallback((): string => {
    console.log('🆕 Creating new session...');
    const newSession: ChatSession = {
      id: generateSessionId(), // This now generates proper UUIDs
      title: 'New Chat',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
      isActive: true,
    };

    console.log('New session created with ID:', newSession.id);

    setSessions(prevSessions => {
      console.log('Previous sessions count:', prevSessions.length);
      // Deactivate all other sessions
      const updatedSessions = prevSessions.map(session => ({
        ...session,
        isActive: false,
      }));

      const newSessions = [...updatedSessions, newSession];
      console.log('Total sessions after adding new one:', newSessions.length);
      
      // Save to Supabase
      saveSessionToSupabase(newSession);
      
      return newSessions;
    });

    setActiveSessionId(newSession.id);
    console.log('Active session set to:', newSession.id);
    return newSession.id;
  }, [saveSessionToSupabase]);

  // Switch to existing session
  const switchToSession = useCallback((sessionId: string) => {
    setSessions(prevSessions => 
      prevSessions.map(session => ({
        ...session,
        isActive: session.id === sessionId,
      }))
    );
    setActiveSessionId(sessionId);
  }, []);

  // Delete session
  const deleteSession = useCallback(async (sessionId: string) => {
    console.log('🗑️ Deleting session:', sessionId);
    
    // First, delete from Supabase
    await deleteSessionFromSupabase(sessionId);
    
    // Then update local state
    setSessions(prevSessions => {
      const filteredSessions = prevSessions.filter(session => session.id !== sessionId);
      
      // If we deleted the active session, switch to the most recent one
      if (sessionId === activeSessionId) {
        if (filteredSessions.length > 0) {
          const mostRecent = filteredSessions.sort((a, b) => b.updatedAt - a.updatedAt)[0];
          setActiveSessionId(mostRecent.id);
          mostRecent.isActive = true;
        } else {
          setActiveSessionId(null);
        }
      }
      
      console.log('✅ Session deleted locally. Remaining sessions:', filteredSessions.length);
      return filteredSessions;
    });
  }, [activeSessionId, deleteSessionFromSupabase]);

  // Delete all sessions (useful for clearing all history)
  const deleteAllSessions = useCallback(async () => {
    if (!supabase || !user || !supabaseAvailable) {
      console.log('Supabase not available, only clearing local sessions');
      setSessions([]);
      setActiveSessionId(null);
      return;
    }

    try {
      console.log('🗑️ Deleting all sessions from Supabase');
      
      const { error } = await supabase
        .from('chat_sessions')
        .delete()
        .eq('user_id', user.id);

      if (error) {
        console.error('❌ Error deleting all sessions from Supabase:', error);
      } else {
        console.log('✅ All sessions deleted from Supabase successfully');
      }
    } catch (error) {
      console.error('❌ Exception deleting all sessions from Supabase:', error);
    }

    // Clear local state regardless of Supabase result
    setSessions([]);
    setActiveSessionId(null);
    console.log('✅ All sessions cleared locally');
  }, [supabase, user, supabaseAvailable]);

  // Update session title
  const updateSessionTitle = useCallback((sessionId: string, title: string) => {
    setSessions(prevSessions =>
      prevSessions.map(session =>
        session.id === sessionId
          ? { ...session, title, updatedAt: Date.now() }
          : session
      )
    );
  }, []);

  // Add message to active session
  const addMessage = useCallback((message: ChatMessage) => {
    if (!activeSessionId) {
      // Create new session if none exists
      const newSessionId = createNewSession();
      setActiveSessionId(newSessionId);
    }

    setSessions(prevSessions =>
      prevSessions.map(session => {
        if (session.id === activeSessionId) {
          const updatedMessages = [...session.messages, message];
          
          // Update title if this is the first user message
          let updatedTitle = session.title;
          if (message.sender === 'user' && session.messages.length === 0) {
            updatedTitle = generateSessionTitle(message.text);
          }

          const updatedSession = {
            ...session,
            messages: updatedMessages,
            title: updatedTitle,
            updatedAt: Date.now(),
          };

          // Save to Supabase
          saveSessionToSupabase(updatedSession);

          return updatedSession;
        }
        return session;
      })
    );
  }, [activeSessionId, createNewSession, saveSessionToSupabase]);

  // Clear active session
  const clearActiveSession = useCallback(() => {
    if (activeSessionId) {
      setSessions(prevSessions =>
        prevSessions.map(session =>
          session.id === activeSessionId
            ? { ...session, messages: [], updatedAt: Date.now() }
            : session
        )
      );
    }
  }, [activeSessionId]);

  // Get active session
  const getActiveSession = useCallback((): ChatSession | null => {
    return sessions.find(session => session.id === activeSessionId) || null;
  }, [sessions, activeSessionId]);

  // Save to localStorage
  const saveToLocalStorage = useCallback(() => {
    if (user) {
      const userKey = `chat_history_${user.id}`;
      
      if (sessions.length === 0) {
        // Clear localStorage when no sessions remain
        localStorage.removeItem(userKey);
        console.log('🗑️ Cleared localStorage - no sessions remaining');
      } else {
        // Save current sessions to localStorage
        localStorage.setItem(userKey, JSON.stringify({
          sessions,
          activeSessionId,
        }));
        console.log('💾 Saved to localStorage:', sessions.length, 'sessions');
      }
    }
  }, [sessions, activeSessionId, user]);

  // Load from localStorage and Supabase
  const loadFromLocalStorage = useCallback(async () => {
    if (user) {
      try {
        console.log('Loading chat history for user:', user.id);
        // First try to load from Supabase
        const supabaseSessions = await loadSessionsFromSupabase();
        console.log('Supabase sessions loaded:', supabaseSessions.length);
        
        if (supabaseSessions.length > 0) {
          // Use Supabase data
          setSessions(supabaseSessions);
          const activeSession = supabaseSessions.find(s => s.isActive);
          setActiveSessionId(activeSession?.id || supabaseSessions[0]?.id || null);
          console.log('Using Supabase sessions, active session:', activeSession?.id || supabaseSessions[0]?.id);
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
              setActiveSessionId(data.activeSessionId ? migrateSessionId(data.activeSessionId) : null);
              console.log('Using localStorage sessions:', migratedSessions.length, 'Active:', data.activeSessionId);
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
            setActiveSessionId(data.activeSessionId ? migrateSessionId(data.activeSessionId) : null);
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

  // Auto-save to localStorage when sessions change
  useEffect(() => {
    if (user) {
      saveToLocalStorage();
    }
  }, [sessions, user, saveToLocalStorage]);

  // Load from localStorage and Supabase when user changes
  useEffect(() => {
    if (user) {
      setHasAttemptedLoad(false); // Reset flag for new user
      loadFromLocalStorage();
    } else {
      // Clear sessions when user logs out
      setSessions([]);
      setActiveSessionId(null);
      setIsLoading(false); // Important: set loading to false when no user
      setHasAttemptedLoad(false); // Reset flag when no user
    }
  }, [user, loadFromLocalStorage]);

  // Fallback timeout to prevent infinite loading
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (isLoading) {
        console.log('ChatHistory loading timeout - forcing false');
        setIsLoading(false);
      }
    }, 2000); // 2 second timeout

    return () => clearTimeout(timeout);
  }, [isLoading]);

  // Track if we've already attempted to load sessions
  const [hasAttemptedLoad, setHasAttemptedLoad] = useState(false);
  
  // Create initial session only if no sessions exist after loading from localStorage
  // Only create a new session if we've finished loading and truly have no sessions
  useEffect(() => {
    console.log('Checking if should create new session:', { 
      user: !!user, 
      isLoading, 
      sessionsLength: sessions.length, 
      activeSessionId,
      hasAttemptedLoad
    });
    
    // Only check once after loading is complete
    if (user && !isLoading && !hasAttemptedLoad) {
      setHasAttemptedLoad(true);
      
      if (sessions.length === 0 && activeSessionId === null) {
        console.log('Creating new session - no existing sessions found');
        // Add a small delay to ensure localStorage has been checked
        const timer = setTimeout(() => {
          createNewSession();
        }, 100);
        return () => clearTimeout(timer);
      } else {
        console.log('Existing sessions found, not creating new session');
      }
    }
  }, [user, isLoading, sessions.length, activeSessionId, createNewSession, hasAttemptedLoad]);

  // Clean up old sessions when retention policy changes
  useEffect(() => {
    if (user && !isLoading) {
      cleanupOldSessions();
    }
  }, [retentionPolicy, user, isLoading, cleanupOldSessions]);

  // Clean up old sessions periodically (every hour)
  useEffect(() => {
    if (user && retentionPolicy !== SESSION_RETENTION_OPTIONS.NEVER) {
      const interval = setInterval(() => {
        cleanupOldSessions();
      }, 60 * 60 * 1000); // Run every hour

      return () => clearInterval(interval);
    }
  }, [user, retentionPolicy, cleanupOldSessions]);

  const value: ChatHistoryContextType = {
    sessions,
    activeSessionId,
    isLoading,
    retentionPolicy,
    supabaseAvailable,
    createNewSession,
    switchToSession,
    deleteSession,
    deleteAllSessions,
    updateSessionTitle,
    addMessage,
    clearActiveSession,
    getActiveSession,
    saveToLocalStorage,
    loadFromLocalStorage,
    cleanupOldSessions,
    setRetentionPolicy,
  };

  return (
    <ChatHistoryContext.Provider value={value}>
      {children}
    </ChatHistoryContext.Provider>
  );
};
