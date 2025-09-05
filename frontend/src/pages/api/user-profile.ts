import { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

const supabase = createClient(supabaseUrl, supabaseServiceKey);

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'GET') {
    try {
      const { user_id } = req.query;
      
      if (!user_id) {
        return res.status(400).json({ error: 'User ID is required' });
      }

      const { data, error } = await supabase
        .from('user_profiles')
        .select('*')
        .eq('user_id', user_id)
        .single();

      if (error) {
        if (error.code === 'PGRST116') {
          return res.status(404).json({ error: 'Profile not found' });
        }
        throw error;
      }

      return res.status(200).json(data);
    } catch (error: unknown) {
      console.error('Error fetching user profile:', error);
      return res.status(500).json({ error: 'Internal server error' });
    }
  }

  if (req.method === 'POST' || req.method === 'PUT') {
    try {
      const profileData = req.body;
      
      // Validate required fields
      const requiredFields = ['user_id', 'role', 'first_name', 'last_name', 'email'];
      for (const field of requiredFields) {
        if (!profileData[field]) {
          return res.status(400).json({ error: `${field} is required` });
        }
      }

      // Validate role
      const validRoles = ['student', 'teacher', 'parent'];
      if (!validRoles.includes(profileData.role)) {
        return res.status(400).json({ error: 'Invalid role' });
      }

      // Add timestamp
      profileData.updated_at = new Date().toISOString();
      if (req.method === 'POST') {
        profileData.created_at = new Date().toISOString();
      }

      const { data, error } = await supabase
        .from('user_profiles')
        .upsert(profileData, { 
          onConflict: 'user_id',
          ignoreDuplicates: false 
        })
        .select()
        .single();

      if (error) {
        console.error('Supabase error:', error);
        return res.status(400).json({ error: error.message });
      }

      return res.status(200).json(data);
    } catch (error: unknown) {
      console.error('Error saving user profile:', error);
      return res.status(500).json({ error: 'Internal server error' });
    }
  }

  if (req.method === 'DELETE') {
    try {
      const { user_id } = req.query;
      
      if (!user_id) {
        return res.status(400).json({ error: 'User ID is required' });
      }

      const { error } = await supabase
        .from('user_profiles')
        .delete()
        .eq('user_id', user_id);

      if (error) {
        throw error;
      }

      return res.status(200).json({ message: 'Profile deleted successfully' });
    } catch (error: unknown) {
      console.error('Error deleting user profile:', error);
      return res.status(500).json({ error: 'Internal server error' });
    }
  }

  return res.status(405).json({ error: 'Method not allowed' });
}
