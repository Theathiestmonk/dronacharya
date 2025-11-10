import type { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET;

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { code, studentEmail } = req.body;

  if (!code) {
    return res.status(400).json({ error: 'Missing authorization code' });
  }

  if (!studentEmail) {
    return res.status(400).json({ error: 'Student email is required' });
  }

  if (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET) {
    return res.status(500).json({ error: 'Google OAuth credentials not configured' });
  }

  const redirectUri = process.env.GOOGLE_STUDENT_REDIRECT_URI || 
    `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/student/google-classroom/callback`;

  try {
    // Exchange code for tokens
    const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: GOOGLE_CLIENT_ID,
        client_secret: GOOGLE_CLIENT_SECRET,
        code,
        grant_type: 'authorization_code',
        redirect_uri: redirectUri
      })
    });

    if (!tokenResponse.ok) {
      const errorText = await tokenResponse.text();
      console.error('Token exchange failed:', errorText);
      return res.status(400).json({ error: 'Token exchange failed' });
    }

    const tokens = await tokenResponse.json();

    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      supabaseServiceKey
    );

    // Find student profile
    const { data: userProfile, error: profileError } = await supabase
      .from('user_profiles')
      .select('id, user_id, role')
      .eq('email', studentEmail)
      .eq('role', 'student')
      .single();

    if (profileError || !userProfile) {
      return res.status(404).json({ error: 'Student profile not found' });
    }

    // Calculate token expiration
    const expiresAt = tokens.expires_in
      ? new Date(Date.now() + tokens.expires_in * 1000).toISOString()
      : null;

    // Store or update connection in google_oauth_connections table
    const { error: upsertError } = await supabase
      .from('google_oauth_connections')
      .upsert({
        user_id: userProfile.user_id,
        service: 'classroom',
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
        token_expires_at: expiresAt,
        scope: tokens.scope?.split(' ') || [],
        is_active: true,
        updated_at: new Date().toISOString()
      }, {
        onConflict: 'user_id,service'
      });

    if (upsertError) {
      console.error('Error storing OAuth connection:', upsertError);
      return res.status(500).json({ error: 'Failed to store connection' });
    }

    return res.status(200).json({ 
      success: true,
      message: 'Google Classroom connected successfully' 
    });
  } catch (error) {
    console.error('Error in callback:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}











