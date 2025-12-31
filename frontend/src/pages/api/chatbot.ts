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
    // Backend will fetch user profile embedding based on user_id
    const requestBody = req.body;

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