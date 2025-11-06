import { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // CRITICAL: Log immediately to confirm this route is being hit
  console.log(`🔍 [CALLBACK API] ===== CALLBACK API CALLED =====`);
  console.log(`🔍 [CALLBACK API] Timestamp: ${new Date().toISOString()}`);
  console.log(`🔍 [CALLBACK API] Method: ${req.method}`);
  console.log(`🔍 [CALLBACK API] URL: ${req.url}`);
  console.log(`🔍 [CALLBACK API] Headers:`, Object.keys(req.headers));
  console.log(`🔍 [CALLBACK API] Body:`, JSON.stringify(req.body, null, 2));
  console.log(`🔍 [CALLBACK API] Query:`, JSON.stringify(req.query, null, 2));
  
  if (req.method !== 'POST') {
    console.error(`🔍 [CALLBACK API] ❌ Wrong method: ${req.method}, expected POST`);
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { code, state, adminEmail } = req.body;
  console.log(`🔍 [CALLBACK API] Extracted - code: ${code ? 'EXISTS' : 'MISSING'}, state: ${state}, adminEmail: ${adminEmail || 'NOT PROVIDED'}`);

  // Ensure redirect_uri matches between auth URL generation and token exchange
  const googleRedirectUri = process.env.GOOGLE_REDIRECT_URI || 'http://localhost:3000/admin/callback';
  console.log(`🔍 [CALLBACK API] Using redirect_uri: ${googleRedirectUri}`);
  
  // Validate redirect_uri format
  if (!googleRedirectUri.includes('localhost:3000/admin/callback') && !googleRedirectUri.includes('/admin/callback')) {
    console.error(`🔍 [CALLBACK API] ⚠️ WARNING: redirect_uri may be incorrect: ${googleRedirectUri}`);
    console.error(`🔍 [CALLBACK API] Expected: http://localhost:3000/admin/callback`);
  }

  if (!code || !state) {
    return res.status(400).json({ error: 'Missing code or state parameter' });
  }

  try {
    // CRITICAL: Check environment variables before proceeding
    const googleClientId = process.env.GOOGLE_CLIENT_ID;
    const googleClientSecret = process.env.GOOGLE_CLIENT_SECRET;
    // Use the redirect_uri validated above
    // googleRedirectUri is already defined above
    
    console.log(`🔍 [CALLBACK API] Environment check:`);
    console.log(`🔍 [CALLBACK API] GOOGLE_CLIENT_ID: ${googleClientId ? 'EXISTS' : 'MISSING'}`);
    console.log(`🔍 [CALLBACK API] GOOGLE_CLIENT_SECRET: ${googleClientSecret ? 'EXISTS' : 'MISSING'}`);
    console.log(`🔍 [CALLBACK API] GOOGLE_REDIRECT_URI: ${googleRedirectUri}`);
    
    if (!googleClientId || !googleClientSecret) {
      console.error(`🔍 [CALLBACK API] ❌ Missing Google OAuth credentials!`);
      return res.status(500).json({ 
        error: 'Google OAuth credentials not configured. Please check environment variables.',
        missing: {
          client_id: !googleClientId,
          client_secret: !googleClientSecret
        }
      });
    }
    
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      supabaseServiceKey!
    );

    // Exchange code for tokens
    console.log(`🔍 [CALLBACK API] Exchanging OAuth code for tokens...`);
    console.log(`🔍 [CALLBACK API] Request details:`, {
      client_id: googleClientId ? `${googleClientId.substring(0, 20)}...` : 'MISSING',
      client_secret: googleClientSecret ? 'EXISTS' : 'MISSING',
      code: code ? `${code.substring(0, 20)}...` : 'MISSING',
      redirect_uri: googleRedirectUri,
      grant_type: 'authorization_code'
    });
    
    const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: googleClientId,
        client_secret: googleClientSecret,
        code,
        grant_type: 'authorization_code',
        redirect_uri: googleRedirectUri
      })
    });

    if (!tokenResponse.ok) {
      const errorText = await tokenResponse.text();
      console.error(`🔍 [CALLBACK API] ❌ Token exchange failed!`);
      console.error(`🔍 [CALLBACK API] Status: ${tokenResponse.status} ${tokenResponse.statusText}`);
      console.error(`🔍 [CALLBACK API] Error response:`, errorText);
      
      let errorData;
      try {
        errorData = JSON.parse(errorText);
      } catch {
        errorData = { error: errorText };
      }
      
      const errorMessage = errorData.error_description || errorData.error || 'Bad Request';
      console.error(`🔍 [CALLBACK API] Parsed error:`, errorMessage);
      console.error(`🔍 [CALLBACK API] Full error object:`, JSON.stringify(errorData, null, 2));
      
      return res.status(400).json({ 
        error: `Token exchange failed: ${errorMessage}`,
        details: errorData,
        hint: errorData.error === 'invalid_grant' ? 'The authorization code may have been used already or has expired. Try connecting again.' : ''
      });
    }

    const tokens = await tokenResponse.json();
    console.log('🔍 Tokens received:', { 
      has_access_token: !!tokens.access_token, 
      has_refresh_token: !!tokens.refresh_token 
    });

    // Get current logged-in user's profile - Admin is a feature, not a separate user
    console.log(`🔍 [CALLBACK] Looking for current user's profile...`);
    console.log(`🔍 [CALLBACK] Received adminEmail from request: ${adminEmail || 'NOT PROVIDED'}`);
    
    if (!adminEmail) {
      return res.status(400).json({ 
        error: 'User email is required. Please ensure you are logged in.' 
      });
    }
    
    // REQUIRED: Find the CURRENT USER's profile by email - NO FALLBACK logic
    // Admin is just a feature flag (admin_privileges=true), not a separate user
    console.log(`🔍 [CALLBACK] ===== USER LOOKUP - START =====`);
    console.log(`🔍 [CALLBACK] Looking for user profile with email: "${adminEmail}"`);
    console.log(`🔍 [CALLBACK] Email provided (exact): "${adminEmail}"`);
    
    // DEBUG: Show ALL admin users to see what exists
    const { data: allAdmins } = await supabase
      .from('user_profiles')
      .select('id, email, admin_privileges')
      .eq('admin_privileges', true)
      .eq('is_active', true);
    
    console.log(`🔍 [CALLBACK] DEBUG: All admin users in database:`, allAdmins?.map(a => ({ id: a.id, email: a.email })));
    console.log(`🔍 [CALLBACK] DEBUG: Checking if "${adminEmail}" exists in admin list...`);
    
    const requestedAdminExists = allAdmins?.some(a => a.email?.toLowerCase() === adminEmail.toLowerCase());
    console.log(`🔍 [CALLBACK] DEBUG: Requested email "${adminEmail}" exists in admin list: ${requestedAdminExists}`);
    
    // Query for exact email match (Supabase queries are case-sensitive, so try exact match first)
    let { data: userProfile } = await supabase
      .from('user_profiles')
      .select('*')
      .eq('email', adminEmail)
      .eq('is_active', true)
      .maybeSingle();
    
    console.log(`🔍 [CALLBACK] Exact email query result:`, userProfile ? { id: userProfile.id, email: userProfile.email } : 'NOT FOUND');
    
    // If not found, try case-insensitive match
    if (!userProfile) {
      console.log(`🔍 [CALLBACK] Exact email match failed, trying case-insensitive match...`);
      const { data: allProfiles } = await supabase
        .from('user_profiles')
        .select('*')
        .eq('is_active', true);
      
      const matchedProfile = allProfiles?.find(p => 
        p.email?.toLowerCase() === adminEmail.toLowerCase()
      );
      
      if (matchedProfile) {
        console.log(`🔍 [CALLBACK] Case-insensitive match found:`, { id: matchedProfile.id, email: matchedProfile.email });
        userProfile = matchedProfile;
      } else {
        console.log(`🔍 [CALLBACK] Case-insensitive match also failed`);
      }
    }
    
    if (!userProfile) {
      console.log(`🔍 [CALLBACK] ❌ User profile not found for: ${adminEmail}`);
      
      return res.status(404).json({ 
        error: `User profile not found for ${adminEmail}. Please ensure you have completed account registration.` 
      });
    }
    
    // CRITICAL VALIDATION: Ensure the found user's email EXACTLY matches what was sent
    if (userProfile.email?.toLowerCase() !== adminEmail.toLowerCase()) {
      console.error(`🔍 [CALLBACK] ❌ EMAIL MISMATCH DETECTED!`);
      console.error(`🔍 [CALLBACK] Requested email: "${adminEmail}"`);
      console.error(`🔍 [CALLBACK] Found user email: "${userProfile.email}"`);
      return res.status(400).json({ 
        error: `Email mismatch: Found user "${userProfile.email}" but requested "${adminEmail}". This should not happen.` 
      });
    }
    
    // CRITICAL SAFEGUARD: Reject if somehow the wrong user ID is found
    const WRONG_ADMIN_ID = 'cf04751c-f680-4995-8fb7-48a488100169'; // services@atsnai.com ID
    if (userProfile.id === WRONG_ADMIN_ID && adminEmail.toLowerCase() !== 'services@atsnai.com') {
      console.error(`🔍 [CALLBACK] ❌ CRITICAL ERROR: Wrong admin ID detected!`);
      console.error(`🔍 [CALLBACK] Found ID: ${userProfile.id} (services@atsnai.com)`);
      console.error(`🔍 [CALLBACK] But requested email: ${adminEmail}`);
      return res.status(400).json({ 
        error: `System error: Wrong user profile selected. Please try again or contact support.` 
      });
    }
    
    console.log(`🔍 [CALLBACK] ✅ Found user profile:`, { 
      id: userProfile.id, 
      email: userProfile.email, 
      admin_privileges: userProfile.admin_privileges 
    });
    console.log(`🔍 [CALLBACK] ✅ Email match confirmed: "${userProfile.email}" === "${adminEmail}"`);
    console.log(`🔍 [CALLBACK] ✅ User ID confirmed: ${userProfile.id} (NOT the services@atsnai.com ID)`);
    
    // Verify user has admin privileges
    if (!userProfile.admin_privileges) {
      console.log(`🔍 [CALLBACK] ❌ User ${adminEmail} does not have admin privileges`);
      return res.status(403).json({ 
        error: `User ${adminEmail} does not have admin privileges. Please contact an administrator to grant admin access.` 
      });
    }
    
    // Use the CURRENT USER's profile ID - STRICTLY enforce this, no fallback
    const userId = userProfile.id; // This MUST be the current user's ID, not a separate admin ID
    console.log(`🔍 [CALLBACK] ✅ Using CURRENT USER's profile ID: ${userId}`);
    console.log(`🔍 [CALLBACK] ✅ User email confirmed: ${userProfile.email}`);
    console.log(`🔍 [CALLBACK] ✅ This is the EXACT user ID that will be stored in google_integrations table`);
    console.log(`🔍 [CALLBACK] ⚠️  CRITICAL: Do NOT use any other ID or fallback to first admin!`);
    console.log(`🔍 [CALLBACK] ⚠️  CRITICAL: Will insert with admin_id = ${userId} for email ${userProfile.email}`);

    // Deactivate any existing integrations for this user before creating new ones
    console.log(`🔍 [CALLBACK] Deactivating any existing integrations for ${userProfile.email}...`);
    await supabase
      .from('google_integrations')
      .update({ is_active: false })
      .eq('admin_id', userId)
      .eq('is_active', true);
    
    // Store integration tokens - using current user's ID (admin is a feature, not a separate user)
    const expiresAt = new Date(Date.now() + (tokens.expires_in || 3600) * 1000);
    
    // FINAL VERIFICATION: Ensure userId is correct before inserting
    console.log(`🔍 [CALLBACK] ===== FINAL VERIFICATION BEFORE INSERT =====`);
    console.log(`🔍 [CALLBACK] User ID to store: ${userId}`);
    console.log(`🔍 [CALLBACK] User email: ${userProfile.email}`);
    console.log(`🔍 [CALLBACK] Requested email: ${adminEmail}`);
    console.log(`🔍 [CALLBACK] User IDs match: ${userProfile.id === userId}`);
    
    if (userProfile.id !== userId) {
      console.error(`🔍 [CALLBACK] ❌ CRITICAL ERROR: userId mismatch!`);
      return res.status(500).json({ error: 'Internal error: User ID mismatch detected' });
    }
    
    console.log(`🔍 [CALLBACK] Storing NEW integration for service(s): ${state}`);
    console.log(`🔍 [CALLBACK] Admin is a feature - storing under current user's ID`);
    
    if (state === 'both') {
      // Create integrations for both services
      console.log(`🔍 [CALLBACK] ===== INSERTING INTEGRATIONS =====`);
      console.log(`🔍 [CALLBACK] admin_id to INSERT: ${userId}`);
      console.log(`🔍 [CALLBACK] Expected user ID: ${userProfile.id}`);
      console.log(`🔍 [CALLBACK] User email: ${userProfile.email}`);
      console.log(`🔍 [CALLBACK] VERIFICATION: userId === userProfile.id? ${userId === userProfile.id}`);
      
      if (userId !== userProfile.id) {
        console.error(`🔍 [CALLBACK] ❌ FATAL: userId does not match userProfile.id!`);
        return res.status(500).json({ error: 'Critical error: User ID mismatch' });
      }
      
      // Only reject if using services@atsnai.com ID BUT the email doesn't match
      // If the email IS services@atsnai.com, then allow the ID
      const SERVICES_ID = 'cf04751c-f680-4995-8fb7-48a488100169';
      if (userId === SERVICES_ID && adminEmail.toLowerCase() !== 'services@atsnai.com') {
        console.error(`🔍 [CALLBACK] ❌ FATAL: Attempting to use services@atsnai.com ID for wrong email!`);
        console.error(`🔍 [CALLBACK] User ID: ${userId}, Email: ${adminEmail}`);
        console.error(`🔍 [CALLBACK] This should NEVER happen! Rejecting...`);
        return res.status(500).json({ error: 'Critical error: Wrong admin ID detected' });
      }
      
      // If email matches services@atsnai.com, allow it
      if (userId === SERVICES_ID && adminEmail.toLowerCase() === 'services@atsnai.com') {
        console.log(`🔍 [CALLBACK] ✅ Allowing services@atsnai.com ID for services@atsnai.com user`);
      }
      
      console.log(`🔍 [CALLBACK] Inserting classroom integration with admin_id: ${userId}`);
      const { data: classroomInsertData, error: classroomError } = await supabase
        .from('google_integrations')
        .insert({
          admin_id: userId,  // Current user's ID, not a separate admin
          service_type: 'classroom',
          access_token: tokens.access_token,
          refresh_token: tokens.refresh_token,
          token_expires_at: expiresAt.toISOString(),
          scope: tokens.scope || '',
          is_active: true
        })
        .select('id, admin_id, service_type');
      
      console.log(`🔍 [CALLBACK] Classroom insert result:`, { data: classroomInsertData, error: classroomError });
      if (classroomInsertData && classroomInsertData.length > 0) {
        const insertedId = classroomInsertData[0].admin_id;
        console.log(`🔍 [CALLBACK] ⚠️  CRITICAL CHECK: Insert returned admin_id: ${insertedId}, Expected: ${userId}`);
        if (insertedId !== userId) {
          console.error(`🔍 [CALLBACK] ❌ FATAL: Insert returned wrong admin_id!`);
          return res.status(500).json({ error: `Database returned wrong admin_id. Expected ${userId}, got ${insertedId}` });
        }
      }

      console.log(`🔍 [CALLBACK] Inserting calendar integration with admin_id: ${userId}`);
      console.log(`🔍 [CALLBACK] VERIFICATION before calendar insert: userId = ${userId}`);
      const { data: calendarInsertData, error: calendarError } = await supabase
        .from('google_integrations')
        .insert({
          admin_id: userId,  // Current user's ID, not a separate admin
          service_type: 'calendar',
          access_token: tokens.access_token,
          refresh_token: tokens.refresh_token,
          token_expires_at: expiresAt.toISOString(),
          scope: tokens.scope || '',
          is_active: true
        })
        .select('id, admin_id, service_type');
      
      console.log(`🔍 [CALLBACK] Calendar insert result:`, { data: calendarInsertData, error: calendarError });
      if (calendarInsertData && calendarInsertData.length > 0) {
        const insertedId = calendarInsertData[0].admin_id;
        console.log(`🔍 [CALLBACK] ⚠️  CRITICAL CHECK: Insert returned admin_id: ${insertedId}, Expected: ${userId}`);
        if (insertedId !== userId) {
          console.error(`🔍 [CALLBACK] ❌ FATAL: Insert returned wrong admin_id!`);
          return res.status(500).json({ error: `Database returned wrong admin_id. Expected ${userId}, got ${insertedId}` });
        }
      }

      if (classroomError || calendarError) {
        console.error('🔍 [CALLBACK] Failed to insert integrations:', classroomError || calendarError);
        return res.status(500).json({ error: 'Failed to store integrations' });
      }
      
      // Verify the integration was stored with the correct user ID
      console.log(`🔍 [CALLBACK] ===== POST-INSERT VERIFICATION =====`);
      console.log(`🔍 [CALLBACK] Checking what was actually stored in database...`);
      
      const { data: verifyIntegrations, error: verifyError } = await supabase
        .from('google_integrations')
        .select('id, admin_id, service_type, created_at')
        .eq('admin_id', userId)
        .eq('is_active', true)
        .order('created_at', { ascending: false })
        .limit(10);
      
      if (verifyError) {
        console.error(`🔍 [CALLBACK] ❌ Verification query error:`, verifyError);
      }
      
      console.log(`🔍 [CALLBACK] Expected admin_id: ${userId}`);
      console.log(`🔍 [CALLBACK] Expected email: ${userProfile.email}`);
      console.log(`🔍 [CALLBACK] Actually stored integrations:`, verifyIntegrations);
      
      if (verifyIntegrations && verifyIntegrations.length > 0) {
        const allHaveCorrectId = verifyIntegrations.every(i => i.admin_id === userId);
        if (!allHaveCorrectId) {
          console.error(`🔍 [CALLBACK] ❌ CRITICAL: Some integrations have wrong admin_id!`);
          console.error(`🔍 [CALLBACK] Expected: ${userId}, Found:`, verifyIntegrations.map(i => i.admin_id));
          return res.status(500).json({ 
            error: `Integration stored with wrong admin_id. Please check database.`,
            debug: { expected: userId, found: verifyIntegrations }
          });
        }
        console.log(`🔍 [CALLBACK] ✅ All integrations verified with correct admin_id: ${userId}`);
      } else {
        console.error(`🔍 [CALLBACK] ❌ CRITICAL: No integrations found after insert!`);
        return res.status(500).json({ error: 'Integration insert may have failed - no records found' });
      }
      
      console.log(`🔍 [CALLBACK] ✅ Successfully stored integrations for ${userProfile.email} (User ID: ${userId})`);
    } else {
      console.log(`🔍 [CALLBACK] ===== INSERTING SINGLE INTEGRATION =====`);
      console.log(`🔍 [CALLBACK] admin_id to INSERT: ${userId}`);
      console.log(`🔍 [CALLBACK] VERIFICATION: userId === userProfile.id? ${userId === userProfile.id}`);
      
      // Only reject if using services@atsnai.com ID BUT the email doesn't match
      // If the email IS services@atsnai.com, then allow the ID
      const SERVICES_ID = 'cf04751c-f680-4995-8fb7-48a488100169';
      if (userId === SERVICES_ID && adminEmail.toLowerCase() !== 'services@atsnai.com') {
        console.error(`🔍 [CALLBACK] ❌ FATAL: Attempting to use services@atsnai.com ID for wrong email!`);
        console.error(`🔍 [CALLBACK] User ID: ${userId}, Email: ${adminEmail}`);
        return res.status(500).json({ error: 'Critical error: Wrong admin ID detected' });
      }
      
      // If email matches services@atsnai.com, allow it
      if (userId === SERVICES_ID && adminEmail.toLowerCase() === 'services@atsnai.com') {
        console.log(`🔍 [CALLBACK] ✅ Allowing services@atsnai.com ID for services@atsnai.com user`);
      }
      
      console.log(`🔍 [CALLBACK] Inserting ${state} integration with admin_id: ${userId}`);
      const { data: integrationInsertData, error: integrationError } = await supabase
        .from('google_integrations')
        .insert({
          admin_id: userId,  // Current user's ID, not a separate admin
          service_type: state,
          access_token: tokens.access_token,
          refresh_token: tokens.refresh_token,
          token_expires_at: expiresAt.toISOString(),
          scope: tokens.scope || '',
          is_active: true
        })
        .select('id, admin_id, service_type');
      
      console.log(`🔍 [CALLBACK] ${state} insert result:`, { data: integrationInsertData, error: integrationError });
      if (integrationInsertData && integrationInsertData.length > 0) {
        const insertedId = integrationInsertData[0].admin_id;
        console.log(`🔍 [CALLBACK] ⚠️  CRITICAL CHECK: Insert returned admin_id: ${insertedId}, Expected: ${userId}`);
        if (insertedId !== userId) {
          console.error(`🔍 [CALLBACK] ❌ FATAL: Insert returned wrong admin_id!`);
          return res.status(500).json({ error: `Database returned wrong admin_id. Expected ${userId}, got ${insertedId}` });
        }
      }

      if (integrationError) {
        console.error('🔍 [CALLBACK] Failed to insert integration:', integrationError);
        return res.status(500).json({ error: 'Failed to store integration' });
      }
      
      // Verify the integration was stored with the correct user ID
      console.log(`🔍 [CALLBACK] ===== POST-INSERT VERIFICATION =====`);
      console.log(`🔍 [CALLBACK] Checking what was actually stored in database...`);
      
      const { data: verifyIntegration, error: verifyError } = await supabase
        .from('google_integrations')
        .select('id, admin_id, service_type, created_at')
        .eq('admin_id', userId)
        .eq('service_type', state)
        .eq('is_active', true)
        .order('created_at', { ascending: false })
        .limit(1)
        .single();
      
      if (verifyError) {
        console.error(`🔍 [CALLBACK] ❌ Verification query error:`, verifyError);
      }
      
      console.log(`🔍 [CALLBACK] Expected admin_id: ${userId}`);
      console.log(`🔍 [CALLBACK] Expected email: ${userProfile.email}`);
      console.log(`🔍 [CALLBACK] Actually stored integration:`, verifyIntegration);
      
      if (verifyIntegration) {
        if (verifyIntegration.admin_id !== userId) {
          console.error(`🔍 [CALLBACK] ❌ CRITICAL: Integration has wrong admin_id!`);
          console.error(`🔍 [CALLBACK] Expected: ${userId}, Found: ${verifyIntegration.admin_id}`);
          return res.status(500).json({ 
            error: `Integration stored with wrong admin_id. Please check database.`,
            debug: { expected: userId, found: verifyIntegration.admin_id }
          });
        }
        console.log(`🔍 [CALLBACK] ✅ Integration verified with correct admin_id: ${userId}`);
      } else {
        console.error(`🔍 [CALLBACK] ❌ CRITICAL: Integration not found after insert!`);
        return res.status(500).json({ error: 'Integration insert may have failed - no record found' });
      }
      
      console.log(`🔍 [CALLBACK] ✅ Successfully stored ${state} integration for ${userProfile.email} (User ID: ${userId})`);
    }

    return res.status(200).json({ 
      success: true, 
      message: `Integration completed successfully for ${userProfile.email}` 
    });
  } catch (error: unknown) {
    console.error('🔍 Error in callback:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}




















