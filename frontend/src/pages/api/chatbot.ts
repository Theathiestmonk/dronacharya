import type { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

const supabase = createClient(supabaseUrl, supabaseServiceKey);

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  try {
    // Get user profile if user_id is provided
    let userProfile = null;
    if (req.body.user_id && req.body.user_id !== null) {
      try {
        const { data, error } = await supabase
          .from('user_profiles')
          .select('*')
          .eq('user_id', req.body.user_id)
          .single();
        
        if (!error && data) {
          userProfile = data;
        }
      } catch (error) {
        console.error('Error fetching user profile:', error);
        // Continue without profile data
      }
    }

    // Prepare request body with user profile
    const requestBody = {
      ...req.body,
      user_profile: userProfile
    };
    
    // Try primary connection method first
    let backendRes;
    try {
      backendRes = await fetch(`${BACKEND_URL}/chatbot/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });
    } catch {
      // Fallback to alternative connection method
      backendRes = await fetch(`http://127.0.0.1:8000/chatbot/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });
    }
    
    const data = await backendRes.json();
    console.log('API route received response length:', data?.response?.length);
    console.log('API route received response:', data?.response);
    res.status(backendRes.status).json(data);
  } catch (error) {
    console.error('Chatbot API error:', error);
    res.status(500).json({ 
      error: 'Failed to connect to backend.',
      details: error instanceof Error ? error.message : String(error)
    });
  }
} 