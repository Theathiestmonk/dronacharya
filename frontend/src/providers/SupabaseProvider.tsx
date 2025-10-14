"use client";
import { createContext, useContext, useMemo } from 'react';
import { createClient, SupabaseClient } from '@supabase/supabase-js';

const SupabaseContext = createContext<SupabaseClient | null>(null);

export const SupabaseProvider = ({ children }: { children: React.ReactNode }) => {
  const supabase = useMemo(() => {
    // Get environment variables
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    
    console.log('Supabase URL:', supabaseUrl ? 'Set' : 'Not set');
    console.log('Supabase Anon Key:', supabaseAnonKey ? 'Set' : 'Not set');
    
    if (supabaseUrl) {
      console.log('Supabase URL value:', supabaseUrl);
    }
    if (supabaseAnonKey) {
      console.log('Supabase Anon Key length:', supabaseAnonKey.length);
      console.log('Supabase Anon Key starts with:', supabaseAnonKey.substring(0, 10) + '...');
    }
    
    if (!supabaseUrl || !supabaseAnonKey) {
      console.warn('Supabase environment variables not set. Auth features will be disabled.');
      return null;
    }
    
    try {
      const client = createClient(supabaseUrl, supabaseAnonKey, {
        auth: {
          autoRefreshToken: true,
          persistSession: true,
          detectSessionInUrl: true
        }
      });
      console.log('Supabase client created successfully');
      return client;
    } catch (error) {
      console.error('Error creating Supabase client:', error);
      return null;
    }
  }, []);
  
  return (
    <SupabaseContext.Provider value={supabase}>{children}</SupabaseContext.Provider>
  );
};

export const useSupabase = () => {
  const ctx = useContext(SupabaseContext);
  if (ctx === undefined) throw new Error('useSupabase must be used within SupabaseProvider');
  return ctx;
}; 