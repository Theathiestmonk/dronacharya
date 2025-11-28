import { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'POST') {
    try {
      const supabase = createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        supabaseServiceKey!
      );

      const { adminEmail, user_email, service } = req.body;

      // Validate required fields
      if (!adminEmail) {
        return res.status(400).json({ error: 'Admin email required' });
      }

      if (!user_email) {
        return res.status(400).json({ error: 'User email (user_email) is required' });
      }

      if (!service || !['classroom', 'calendar'].includes(service)) {
        return res.status(400).json({ error: 'Service must be "classroom" or "calendar"' });
      }

      // Verify admin privileges
      const { data: userProfile } = await supabase
        .from('user_profiles')
        .select('*')
        .eq('email', adminEmail)
        .eq('is_active', true)
        .single();

      if (!userProfile || !userProfile.admin_privileges) {
        return res.status(403).json({ error: 'Admin privileges required' });
      }

      // Call backend DWD sync endpoint
      const response = await fetch(`${BACKEND_URL}/api/admin/sync-dwd/${service}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_email })
      });

      const data = await response.json();
      
      if (!response.ok) {
        return res.status(response.status).json(data);
      }

      return res.status(200).json(data);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Internal server error';
      console.error('DWD sync error:', error);
      return res.status(500).json({ error: errorMessage });
    }
  } else {
    return res.status(405).json({ error: 'Method not allowed' });
  }
}

