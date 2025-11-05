import type { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { email } = req.query;

    if (!email || typeof email !== 'string') {
      return res.status(400).json({ error: 'Student email is required' });
    }

    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    // Find student profile by email
    const { data: profile, error: profileError } = await supabase
      .from('user_profiles')
      .select('user_id, role')
      .eq('email', email)
      .eq('role', 'student')
      .single();

    if (profileError || !profile) {
      return res.status(404).json({ error: 'Student profile not found' });
    }

    // Check for Google Classroom connection
    const { data: connection, error: connectionError } = await supabase
      .from('google_oauth_connections')
      .select('id, is_active, token_expires_at')
      .eq('user_id', profile.user_id)
      .eq('service', 'classroom')
      .eq('is_active', true)
      .single();

    if (connectionError || !connection) {
      return res.status(200).json({ connected: false });
    }

    // Check if token is expired
    const isExpired = connection.token_expires_at 
      ? new Date(connection.token_expires_at) < new Date() 
      : false;

    return res.status(200).json({ 
      connected: !isExpired,
      expiresAt: connection.token_expires_at 
    });
  } catch (error) {
    console.error('Error checking Google Classroom status:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}

