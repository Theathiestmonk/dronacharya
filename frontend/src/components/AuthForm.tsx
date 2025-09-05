"use client";
import React, { useState } from 'react';
import { useSupabase } from '../providers/SupabaseProvider';

const AuthForm: React.FC = () => {
  const supabase = useSupabase();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignup, setIsSignup] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirmationSent, setConfirmationSent] = useState(false);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (!supabase) {
        setError('Authentication not available');
        return;
      }
      
      let result;
      if (isSignup) {
        result = await supabase.auth.signUp({ email, password });
        if (!result.error) {
          setConfirmationSent(true);
        }
      } else {
        result = await supabase.auth.signInWithPassword({ email, password });
      }
      if (result.error) setError(result.error.message);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    setError(null);
    setLoading(true);
    try {
      if (!supabase) {
        setError('Authentication not available');
        return;
      }
      
      const { error } = await supabase.auth.signInWithOAuth({ provider: 'google' });
      if (error) setError(error.message);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  if (confirmationSent) {
    return (
      <div className="w-full max-w-md mx-auto bg-white rounded-xl shadow-lg p-8 mt-12 border border-gray-200 text-center">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Check your email</h2>
        <p className="text-gray-800 mb-4">A confirmation link has been sent to <span className="font-semibold">{email}</span>.</p>
        <p className="text-gray-600">Please check your inbox and follow the instructions to activate your account.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md rounded-xl shadow-lg p-8 border border-gray-200" style={{ background: 'transparent' }}>
        <div className="flex justify-center mb-6">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/prakriti_logo.webp" alt="Prakriti Logo" style={{ maxWidth: '90px', height: 'auto' }} />
        </div>
        <h2 className="text-2xl font-bold mb-6 text-center text-gray-900">{isSignup ? 'Sign Up' : 'Login'}</h2>
        <form onSubmit={handleAuth} className="flex flex-col gap-4">
          <input
            type="email"
            className="border border-gray-400 rounded px-4 py-2 text-gray-900 bg-gray-50 focus:outline-none focus:ring"
            style={{ borderColor: 'var(--brand-primary)', boxShadow: '0 0 0 1px var(--brand-primary)' }}
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            className="border border-gray-400 rounded px-4 py-2 text-gray-900 bg-gray-50 focus:outline-none focus:ring"
            style={{ borderColor: 'var(--brand-primary)', boxShadow: '0 0 0 1px var(--brand-primary)' }}
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />
          {error && <div className="text-red-700 text-sm font-semibold bg-red-50 border border-red-200 rounded px-2 py-1">{error}</div>}
          <button
            type="submit"
            className="w-full text-white py-2 rounded transition font-semibold shadow mb-2"
            style={{ backgroundColor: 'var(--brand-primary)' }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary-800)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-primary)'}
            disabled={loading}
          >
            {isSignup ? 'Sign Up' : 'Login'}
          </button>
          <button
            onClick={handleGoogle}
            type="button"
            className="w-full text-white py-2 rounded transition font-semibold shadow"
            style={{ backgroundColor: 'var(--brand-secondary)' }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-secondary-800)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--brand-secondary)'}
            disabled={loading}
          >
            Continue with Google
          </button>
        </form>
        <div className="mt-4 text-center">
          <button
            className="hover:underline font-semibold"
            style={{ color: 'var(--brand-primary)' }}
            onClick={() => setIsSignup(!isSignup)}
          >
            {isSignup ? 'Already have an account? Login' : "Don't have an account? Sign Up"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuthForm; 