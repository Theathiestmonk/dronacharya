import { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      supabaseServiceKey!
    );

    // Get CURRENT USER email from query params - REQUIRED, NO FALLBACK
    // Admin is a feature, not a separate user - each user has their own integrations
    const adminEmail = req.query.email as string;
    
    if (!adminEmail) {
      console.log(`🔍 ❌ No email provided - each user must query their own integrations`);
      return res.status(400).json({
        error: 'User email is required. Please ensure you are logged in.',
        classroom_enabled: false,
        calendar_enabled: false,
        integrations: []
      });
    }
    
    console.log(`🔍 Fetching integrations for CURRENT USER: ${adminEmail}...`);
    
    // Get CURRENT USER's profile - NO FALLBACK to first admin
    const { data: userProfile } = await supabase
      .from('user_profiles')
      .select('*')
      .eq('email', adminEmail)
      .eq('is_active', true)
      .single();
    
    if (!userProfile) {
      console.log(`🔍 ❌ User profile not found for: ${adminEmail}`);
      return res.status(404).json({
        error: `User profile not found for ${adminEmail}. Please ensure you have completed account registration.`,
        classroom_enabled: false,
        calendar_enabled: false,
        integrations: []
      });
    }

    // Verify user has admin privileges
    if (!userProfile.admin_privileges) {
      console.log(`🔍 ❌ User ${adminEmail} does not have admin privileges`);
      return res.status(403).json({
        error: `User ${adminEmail} does not have admin privileges. Please contact an administrator to grant admin access.`,
        classroom_enabled: false,
        calendar_enabled: false,
        integrations: []
      });
    }

    const adminProfile = userProfile;
    console.log(`🔍 ✅ Using current user's profile: ${adminProfile.email} (ID: ${adminProfile.id})`);
    
    // Check integrations ONLY for the CURRENT logged-in user
    // Admin is a feature, not a separate user - each user has their own integrations
    console.log(`🔍 Checking integrations for CURRENT USER (${adminProfile.email})...`);
    const { data: integrations, error: intError } = await supabase
      .from('google_integrations')
      .select('*')
      .eq('admin_id', adminProfile.id)
      .eq('is_active', true);
    
    console.log(`🔍 Current user integrations found: ${integrations?.length || 0}`);
    
    if (integrations && integrations.length > 0) {
      console.log(`🔍 ✅ Using current user's own integrations (${adminProfile.email})`);
    } else {
      console.log(`🔍 ❌ No integrations found for current user (${adminProfile.email})`);
      console.log(`🔍 Looking for existing integrations with different admin_id to identify owner...`);
      
      // Debug: Check if there are any integrations at all, and who owns them
      const { data: allIntegrations } = await supabase
        .from('google_integrations')
        .select('admin_id, service_type, is_active')
        .eq('is_active', true)
        .limit(10);
      
      if (allIntegrations && allIntegrations.length > 0) {
        const uniqueAdminIds = [...new Set(allIntegrations.map(i => i.admin_id))];
        console.log(`🔍 Found ${allIntegrations.length} active integrations owned by ${uniqueAdminIds.length} different user(s)`);
        
        for (const adminId of uniqueAdminIds) {
          const { data: ownerProfile } = await supabase
            .from('user_profiles')
            .select('email, id')
            .eq('id', adminId)
            .single();
          
          if (ownerProfile) {
            console.log(`🔍 📧 Integrations exist under: ${ownerProfile.email} (ID: ${adminId})`);
          } else {
            console.log(`🔍 📧 Integrations exist under unknown user (ID: ${adminId})`);
          }
        }
      }
      
      console.log(`🔍 💡 Solution: Reconnect Google Services as ${adminProfile.email} to create integrations under your account`);
      // NO FALLBACK - each user must connect their own Google account
    }

    if (intError) {
      console.error('🔍 Error fetching integrations:', intError);
      return res.status(500).json({ error: 'Failed to fetch integrations' });
    }

    console.log(`🔍 Found ${integrations?.length || 0} active integrations:`, integrations);

    // Check which services are enabled based on active integrations
    const classroomEnabled = integrations?.some(i => i.service_type === 'classroom') || false;
    const calendarEnabled = integrations?.some(i => i.service_type === 'calendar') || false;

    console.log(`🔍 Classroom enabled: ${classroomEnabled}, Calendar enabled: ${calendarEnabled}`);

    // Set cache-control headers to prevent caching
    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');

    return res.status(200).json({
      classroom_enabled: classroomEnabled,
      calendar_enabled: calendarEnabled,
      integrations: integrations || []
    });
  } catch (error) {
    console.error('Error fetching integrations:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}







