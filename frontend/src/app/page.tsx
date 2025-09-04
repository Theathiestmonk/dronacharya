"use client";
import React, { useEffect, useState } from 'react';
import Chatbot from '../components/Chatbot';
import AuthForm from '../components/AuthForm';

import { useSupabase } from '../providers/SupabaseProvider';
import type { Session } from '@supabase/supabase-js';

const HomePage: React.FC = () => {
  const supabase = useSupabase();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [chatKey, setChatKey] = useState(0); // Key to force re-render of Chatbot
  
  useEffect(() => {
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setLoading(false);
    });
    
    // Get initial session
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });
    
    return () => {
      listener?.subscription.unsubscribe();
    };
  }, [supabase]);

  // Show loading state while checking authentication
  if (loading) {
    return (
      <div className="flex min-h-screen h-screen">
        <main className="flex-1 flex items-center justify-center h-screen">
          <div className="w-full max-w-2xl h-full flex flex-col justify-center">
            <div className="flex justify-center mb-6">
              <img src="/prakriti_logo.webp" alt="Prakriti Visual" style={{ maxWidth: '150px', height: 'auto' }} />
            </div>
            <div className="text-center">
              <span className="text-gray-600">Loading...</span>
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="flex flex-col min-h-screen items-center justify-center">
        <div className="w-full max-w-2xl flex-1 flex flex-col justify-end">
          <AuthForm />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen h-screen">
      <main className="flex-1 flex items-center justify-center h-screen">
        <div className="w-full max-w-2xl h-full flex flex-col justify-center">
          <Chatbot key={chatKey} />
        </div>
      </main>
    </div>
  );
};

export default HomePage;
