"use client";
import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useSupabase } from './SupabaseProvider';
import { User } from '@supabase/supabase-js';

interface UserProfile {
  id: string;
  user_id: string;
  role: 'student' | 'teacher' | 'parent';
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
  date_of_birth?: string;
  grade?: string;
  student_id?: string;
  subjects?: string[];
  learning_goals?: string;
  interests?: string[];
  learning_style?: string;
  special_needs?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  employee_id?: string;
  department?: string;
  subjects_taught?: string[];
  years_of_experience?: number;
  qualifications?: string;
  specializations?: string[];
  office_location?: string;
  office_hours?: string;
  relationship_to_student?: string;
  occupation?: string;
  workplace?: string;
  preferred_contact_method?: string;
  communication_preferences?: string;
  address?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  preferred_language?: string;
  timezone?: string;
  onboarding_completed: boolean;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  profile: UserProfile | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>;
  signInWithGoogle: () => Promise<{ error: Error | null }>;
  signUp: (email: string, password: string, userData?: Record<string, unknown>) => Promise<{ error: Error | null }>;
  signOut: () => Promise<void>;
  updateProfile: (profileData: Partial<UserProfile>) => Promise<{ error: Error | null }>;
  completeOnboarding: () => void;
  needsOnboarding: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [isFirstLogin, setIsFirstLogin] = useState(false);
  const supabase = useSupabase();

  const fetchUserProfile = useCallback(async (userId: string) => {
    try {
      const response = await fetch(`/api/user-profile?user_id=${userId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setProfile(data);
        setIsFirstLogin(false);
      } else if (response.status === 404) {
        // Profile not found - this is a first-time user
        console.log('User profile not found - first time user');
        setProfile(null);
        setIsFirstLogin(true);
      } else {
        console.error('Error fetching user profile:', response.status, response.statusText);
        setProfile(null);
        setIsFirstLogin(true);
      }
    } catch (error) {
      console.error('Error fetching user profile:', error);
      setProfile(null);
      // If there's an error fetching profile, treat as first-time user
      setIsFirstLogin(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // If Supabase is not available, disable auth features
    if (!supabase) {
      console.log('Supabase not available - disabling auth features');
      setLoading(false);
      return;
    }

    // Add a timeout to prevent infinite loading
    const timeoutId = setTimeout(() => {
      console.log('Auth loading timeout - setting loading to false');
      setLoading(false);
    }, 5000); // 5 second timeout

    // Get initial session
    const getInitialSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        setUser(session?.user ?? null);
        
        if (session?.user) {
          await fetchUserProfile(session.user.id);
        } else {
          setLoading(false);
        }
      } catch (error) {
        console.error('Error getting initial session:', error);
        setLoading(false);
      }
    };

    getInitialSession();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      setUser(session?.user ?? null);
      
      if (session?.user) {
        await fetchUserProfile(session.user.id);
      } else {
        setProfile(null);
        setLoading(false);
      }
    });

    return () => {
      clearTimeout(timeoutId);
      subscription.unsubscribe();
    };
  }, [supabase, fetchUserProfile]);

  const signIn = async (email: string, password: string) => {
    if (!supabase) {
      return { error: new Error('Authentication not available') };
    }
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    return { error };
  };

  const signInWithGoogle = async () => {
    if (!supabase) {
      return { error: new Error('Authentication not available') };
    }

    try {
      console.log('Starting Google OAuth...');
      // Let Supabase handle the OAuth flow and redirect back to our app
      const redirectUrl = `http://localhost:3000`;
      console.log('Redirect URL:', redirectUrl);
      console.log('Current URL before OAuth:', window.location.href);
      console.log('Window origin:', window.location.origin);
      
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: redirectUrl,
        },
      });

      console.log('OAuth response:', { data, error });
      console.log('OAuth data URL:', data?.url);
      console.log('Expected Supabase OAuth URL should contain:', 'tvtfuexwurcdjevdnrqd.supabase.co');
      
      if (data?.url) {
        if (data.url.includes('supabase.co')) {
          console.log('✅ Correct: OAuth URL contains Supabase domain');
        } else if (data.url.includes('google.com')) {
          console.log('❌ Issue: OAuth URL goes directly to Google, not through Supabase');
          console.log('This means Google OAuth provider is not properly configured in Supabase');
        } else {
          console.log('⚠️ Unknown OAuth URL format:', data.url);
        }
      }

      if (error) {
        console.error('OAuth error:', error);
        return { error };
      }

      console.log('OAuth initiated successfully');
      console.log('About to redirect to:', data?.url);
      
      // If we have a URL, redirect immediately
      if (data?.url) {
        console.log('Redirecting to Google OAuth...');
        console.log('Full redirect URL:', data.url);
        
        // Force immediate redirect
        console.log('Attempting redirect to:', data.url);
        
        // Use the most reliable redirect method
        window.location.assign(data.url);
        
        // Don't return here - let the redirect happen
        return { error: null };
      } else {
        console.warn('No redirect URL received from OAuth');
        console.warn('This might mean Google OAuth is not properly configured in Supabase');
        return { error: new Error('Google OAuth not configured properly') };
      }
    } catch (error) {
      console.error('OAuth exception:', error);
      return { error: error instanceof Error ? error : new Error('Unknown error') };
    }
  };

  const signUp = async (email: string, password: string, userData?: Record<string, unknown>) => {
    if (!supabase) {
      return { error: new Error('Authentication not available') };
    }
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: userData
      }
    });
    return { error };
  };

  const signOut = async () => {
    if (!supabase) {
      console.error('Authentication not available');
      return;
    }
    const { error } = await supabase.auth.signOut();
    if (!error) {
      setUser(null);
      setProfile(null);
    } else {
      console.error('Error signing out:', error);
    }
  };

  const updateProfile = async (profileData: Partial<UserProfile>) => {
    if (!user) {
      return { error: new Error('No user logged in') };
    }

    try {
      const response = await fetch('/api/user-profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...profileData,
          user_id: user.id,
          updated_at: new Date().toISOString(),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        return { error: new Error(errorData.error || 'Failed to update profile') };
      }

      const data = await response.json();
      setProfile(data);
      // Mark onboarding as completed and reset first login flag
      setIsFirstLogin(false);
      return { error: null };
    } catch (error) {
      return { error: error instanceof Error ? error : new Error('Unknown error') };
    }
  };

  const completeOnboarding = async () => {
    setIsFirstLogin(false);
    // Fetch the updated profile from the server to ensure we have the latest data
    if (user) {
      await fetchUserProfile(user.id);
    }
  };

  const needsOnboarding = Boolean(user && (isFirstLogin || !profile || !profile.onboarding_completed));

  const value = {
    user,
    profile,
    loading,
    signIn,
    signInWithGoogle,
    signUp,
    signOut,
    updateProfile,
    completeOnboarding,
    needsOnboarding,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
