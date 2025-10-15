import { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

// Use service role if available, otherwise use anon key (less secure but works for development)
const supabase = createClient(
  supabaseUrl, 
  supabaseServiceKey || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { action, email, adminEmail } = req.body;

  if (!action) {
    return res.status(400).json({ error: 'Missing required fields' });
  }

  // Only require email for actions that need it
  if ((action === 'assign' || action === 'remove') && !email) {
    return res.status(400).json({ error: 'Email is required for this action' });
  }

  try {
    // Verify the requesting user has admin privileges
    if (adminEmail) {
      // First try to check admin_privileges column
      let adminProfile;
      try {
        const { data } = await supabase
          .from('user_profiles')
          .select('admin_privileges, role')
          .eq('email', adminEmail)
          .single();
        
        adminProfile = data;
      } catch (_error) { // eslint-disable-line @typescript-eslint/no-unused-vars
        // If admin_privileges column doesn't exist, fall back to role check
        const { data } = await supabase
          .from('user_profiles')
          .select('role')
          .eq('email', adminEmail)
          .eq('role', 'admin')
          .single();
        
        adminProfile = data;
      }

      if (!adminProfile || (!(adminProfile as { admin_privileges?: boolean }).admin_privileges && adminProfile.role !== 'admin')) {
        return res.status(403).json({ error: 'Admin privileges required' });
      }
    }

    let result;
    
    if (action === 'assign') {
      // Try to assign admin privileges first, fall back to role if column doesn't exist
      let data, error;
      try {
        const result = await supabase
          .from('user_profiles')
          .update({ 
            admin_privileges: true,
            updated_at: new Date().toISOString()
          })
          .eq('email', email)
          .select();
        
        data = result.data;
        error = result.error;
      } catch (_err) { // eslint-disable-line @typescript-eslint/no-unused-vars
        // Fall back to role-based system
        const result = await supabase
          .from('user_profiles')
          .update({ 
            role: 'admin',
            updated_at: new Date().toISOString()
          })
          .eq('email', email)
          .select();
        
        data = result.data;
        error = result.error;
      }

      if (error) {
        console.error('Error assigning admin privileges:', error);
        return res.status(500).json({ error: 'Failed to assign admin privileges. Make sure the user exists and has a profile.' });
      }

      if (!data || data.length === 0) {
        return res.status(404).json({ error: 'User not found. User must have a profile first.' });
      }

      result = { data: data };
    } else if (action === 'remove') {
      // Try to remove admin privileges first, fall back to role if column doesn't exist
      let data, error;
      try {
        const result = await supabase
          .from('user_profiles')
          .update({ admin_privileges: false })
          .eq('email', email)
          .eq('admin_privileges', true)
          .select();
        
        data = result.data;
        error = result.error;
      } catch (_err) { // eslint-disable-line @typescript-eslint/no-unused-vars
        // Fall back to role-based system
        const result = await supabase
          .from('user_profiles')
          .update({ role: 'student' })
          .eq('email', email)
          .eq('role', 'admin')
          .select();
        
        data = result.data;
        error = result.error;
      }

      if (error) {
        console.error('Error removing admin privileges:', error);
        return res.status(500).json({ error: 'Failed to remove admin privileges' });
      }

      result = { data: data };
    } else if (action === 'list') {
      // List all users with admin privileges
      console.log('Fetching admin users...');
      
      const { data, error } = await supabase
        .from('user_profiles')
        .select('user_id, email, first_name, last_name, role, admin_privileges, created_at')
        .eq('admin_privileges', true)
        .eq('is_active', true)
        .order('created_at', { ascending: false });

      console.log('Admin users query result:', { data, error });

      if (error) {
        console.error('Error listing admins:', error);
        return res.status(500).json({ error: `Failed to list admins: ${error.message}` });
      }

      result = { data: data || [] };
    } else if (action === 'list_all_users') {
      // List all users for admin management
      console.log('Fetching all users...');
      
      const { data, error } = await supabase
        .from('user_profiles')
        .select('user_id, email, first_name, last_name, role, admin_privileges, created_at')
        .eq('is_active', true)
        .order('created_at', { ascending: false });

      console.log('Users query result:', { data, error });

      if (error) {
        console.error('Error listing users:', error);
        return res.status(500).json({ error: `Failed to list users: ${error.message}` });
      }

      result = { data: data || [] };
    } else {
      return res.status(400).json({ error: 'Invalid action' });
    }

    return res.status(200).json({ 
      success: true, 
      data: result.data,
      message: action === 'assign' ? 'Admin privileges assigned successfully' :
               action === 'remove' ? 'Admin privileges removed successfully' :
               'Data retrieved successfully'
    });

  } catch (error) {
    console.error('Error in admin role management:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}
