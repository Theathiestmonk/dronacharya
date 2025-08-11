"use client";
import React, { useEffect, useState } from 'react';
import Chatbot from '../components/Chatbot';
import AuthForm from '../components/AuthForm';
import { useSupabase } from '../providers/SupabaseProvider';
import LeftPanel from "./components/LeftPanel";

const HomePage: React.FC = () => {
  const supabase = useSupabase();
  const [session, setSession] = useState<any>(null);
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

  return (
    <div className="flex min-h-screen h-screen">
      <LeftPanel user={session.user} />
      <main className="flex-1 flex items-center justify-center h-screen">
        <div className="w-full max-w-2xl h-full flex flex-col justify-center">
          <Chatbot />
        </div>
      </main>
    </div>
  );
};

export default HomePage;
