import type { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { email } = req.body;

    if (!email || typeof email !== 'string') {
      return res.status(400).json({ error: 'Student email is required' });
    }

    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      supabaseServiceKey
    );

    // Find student profile by email
    const { data: profile, error: profileError } = await supabase
      .from('user_profiles')
      .select('user_id')
      .eq('email', email)
      .eq('role', 'student')
      .single();

    if (profileError || !profile) {
      return res.status(404).json({ error: 'Student profile not found' });
    }

    // Deactivate connection
    const { error } = await supabase
      .from('google_oauth_connections')
      .update({ is_active: false })
      .eq('user_id', profile.user_id)
      .eq('service', 'classroom');

    if (error) {
      console.error('Error disconnecting:', error);
      return res.status(500).json({ error: 'Failed to disconnect' });
    }

    return res.status(200).json({ success: true, message: 'Disconnected successfully' });
  } catch (error) {
    console.error('Error in disconnect:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}

