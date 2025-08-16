"use client";
import React, { useEffect, useState } from 'react';
import Chatbot from '../components/Chatbot';
import AuthForm from '../components/AuthForm';
import StudentAuth from '../components/StudentAuth';
import { useSupabase } from '../providers/SupabaseProvider';
import LeftPanel from "./components/LeftPanel";

const HomePage: React.FC = () => {
  const supabase = useSupabase();
  const [session, setSession] = useState<any>(null);
  const [studentSession, setStudentSession] = useState<any>(null);
  const [authMode, setAuthMode] = useState<'teacher' | 'student'>('teacher');
  const [chatKey, setChatKey] = useState(0); // Key to force re-render of Chatbot
  useEffect(() => {
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    return () => {
      listener?.subscription.unsubscribe();
    };
  }, [supabase]);

  if (!session) {
    return (
      <div className="flex flex-col min-h-screen items-center justify-center">
        <div className="w-full max-w-2xl flex-1 flex flex-col justify-end">
          <AuthForm />
        </div>
      </div>
    );
  }

  // Function to clear chat and start fresh
  const handleClearChat = () => {
    setChatKey(prev => prev + 1); // Force re-render of Chatbot
  };

  return (
    <div className="flex min-h-screen h-screen">
      <LeftPanel user={session.user} onLogoClick={handleClearChat} />
      <main className="flex-1 flex items-center justify-center h-screen">
        <div className="w-full max-w-2xl h-full flex flex-col justify-center">
          <Chatbot key={chatKey} />
        </div>
      </main>
    </div>
  );
};

export default HomePage;
