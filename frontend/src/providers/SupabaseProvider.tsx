"use client";
import { createContext, useContext, useMemo } from 'react';
import { createClient, SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

const SupabaseContext = createContext<SupabaseClient | null>(null);

export const SupabaseProvider = ({ children }: { children: React.ReactNode }) => {
  const supabase = useMemo(() => {
    if (!supabaseUrl || !supabaseAnonKey) {
      console.warn('Supabase environment variables not set. Auth features will be disabled.');
      return null;
    }
    return createClient(supabaseUrl, supabaseAnonKey);
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