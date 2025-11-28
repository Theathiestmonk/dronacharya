import { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { service } = req.query;

  if (!service || (service !== 'classroom' && service !== 'calendar' && service !== 'website')) {
    return res.status(400).json({ error: 'Invalid service type' });
  }

  try {
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      supabaseServiceKey!
    );

    const adminEmail = req.body?.adminEmail;
    console.log(`🔍 Syncing ${service} for ${adminEmail || 'NO EMAIL'}`);

    if (!adminEmail) {
      return res.status(400).json({ 
        error: 'User email is required. Please ensure you are logged in.' 
      });
    }

    // Get user profile
    const { data: userProfile } = await supabase
      .from('user_profiles')
      .select('*')
      .eq('email', adminEmail)
      .eq('is_active', true)
      .single();

    if (!userProfile || !userProfile.admin_privileges) {
      return res.status(403).json({ 
        error: 'Admin privileges required' 
      });
    }

    // Website sync - handled separately
    if (service === 'website') {
      console.log(`🔍 Starting website data sync (clearing cache and re-crawling)...`);
      
      try {
        // Call backend API to refresh web crawler cache
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const syncResponse = await fetch(`${backendUrl}/api/admin/sync/website`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            adminEmail: adminEmail
          }),
        });

        if (!syncResponse.ok) {
          const errorData = await syncResponse.text();
          return res.status(syncResponse.status).json({ 
            error: `Failed to sync website data: ${errorData}` 
          });
        }

        const syncData = await syncResponse.json();
        
        return res.status(200).json({
          success: true,
          message: syncData.message || 'Website data synced successfully',
          stats: syncData.stats || {},
          summary: syncData.summary || {}
        });
      } catch (error: unknown) {
        console.error('❌ Error in website sync:', error);
        const errorDetails = error instanceof Error ? (error as Error).message : String(error);
        return res.status(500).json({
          error: 'Failed to sync website data',
          details: errorDetails
        });
      }
    }

    // For classroom and calendar, use DWD to sync
    const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/admin/sync-dwd/${service}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_email: adminEmail })
      });

      const data = await response.json();

      if (!response.ok) {
        return res.status(response.status).json(data);
      }

      return res.status(200).json(data);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to sync data';
      console.error(`Error syncing ${service} with DWD:`, error);
      return res.status(500).json({ error: errorMessage });
    }
  } catch (error: unknown) {
    console.error(`❌ Error syncing ${service}:`, error);
    const errorMessage = error instanceof Error ? (error as Error).message : 'Unknown error';
    return res.status(500).json({ 
      error: 'Internal server error',
      details: errorMessage 
    });
  }
}
