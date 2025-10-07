import type { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

// Only create Supabase client if both URL and key are available
const supabase = supabaseUrl && supabaseServiceKey 
  ? createClient(supabaseUrl, supabaseServiceKey)
  : null;

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  try {
    // Get user profile - prioritize user_profile from request body, fallback to database fetch
    let userProfile = null;
    
    // First, check if user_profile is provided in the request body
    if (req.body.user_profile && req.body.user_profile !== null) {
      userProfile = req.body.user_profile;
      console.log('✅ User profile from request body:', JSON.stringify(userProfile, null, 2));
      console.log('✅ Gender field in profile:', userProfile.gender);
    } else if (req.body.user_id && req.body.user_id !== null && supabase) {
      console.log('❌ No user_profile in request body, attempting to fetch from database...');
      console.log('Request body keys:', Object.keys(req.body));
      try {
        const { data, error } = await supabase
          .from('user_profiles')
          .select('*')
          .eq('user_id', req.body.user_id)
          .single();
        
        if (!error && data) {
          userProfile = data;
          console.log('User profile fetched from database:', JSON.stringify(userProfile, null, 2));
        }
      } catch (error) {
        console.error('Error fetching user profile:', error);
        // Continue without profile data
      }
    } else {
      console.log('❌ No user_profile or user_id provided in request body. Cannot fetch profile.');
      console.log('Request body keys:', Object.keys(req.body));
    }

    // Prepare request body with user profile
    const requestBody = {
      ...req.body,
      user_profile: userProfile
    };
    
    console.log('Request body being sent to backend:', JSON.stringify(requestBody, null, 2));
    
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