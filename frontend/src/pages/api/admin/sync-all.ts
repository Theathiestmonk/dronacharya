import { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'POST') {
    // Start bulk sync
    try {
      const supabase = createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        supabaseServiceKey!
      );

      const adminEmail = req.body?.adminEmail;
      if (!adminEmail) {
        return res.status(400).json({ error: 'Admin email required' });
      }

      // Verify admin
      const { data: userProfile } = await supabase
        .from('user_profiles')
        .select('*')
        .eq('email', adminEmail)
        .eq('is_active', true)
        .single();

      if (!userProfile || !userProfile.admin_privileges) {
        return res.status(403).json({ error: 'Admin privileges required' });
      }

      // Call backend endpoint
      const response = await fetch(`${BACKEND_URL}/api/admin/sync-all?email=${encodeURIComponent(adminEmail)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      const data = await response.json();
      
      if (!response.ok) {
        return res.status(response.status).json(data);
      }

      return res.status(200).json(data);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return res.status(500).json({ error: errorMessage });
    }
  } else if (req.method === 'GET') {
    // Get sync status
    try {
      const response = await fetch(`${BACKEND_URL}/api/admin/sync-all/status`);
      const data = await response.json();
      return res.status(200).json(data);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return res.status(500).json({ error: errorMessage });
    }
  } else {
    return res.status(405).json({ error: 'Method not allowed' });
  }
}


