"use client";
import { createContext, useContext, useMemo } from 'react';
import { createClient, SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

const SupabaseContext = createContext<SupabaseClient | null>(null);

export const SupabaseProvider = ({ children }: { children: React.ReactNode }) => {
  const supabase = useMemo(() => {
    const options = {
      auth: {
        redirectTo: typeof window !== 'undefined' 
          ? `${window.location.origin}/auth/callback`
          : 'http://localhost:3000/auth/callback'
      }
    };
    return createClient(supabaseUrl, supabaseAnonKey, options);
  }, []);
  return (
    <SupabaseContext.Provider value={supabase}>{children}</SupabaseContext.Provider>
  );
};

export const useSupabase = () => {
  const ctx = useContext(SupabaseContext);
  if (!ctx) throw new Error('useSupabase must be used within SupabaseProvider');
  return ctx;
}; 