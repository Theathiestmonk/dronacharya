import { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

const supabase = createClient(supabaseUrl, supabaseServiceKey);

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method === 'GET') {
    try {
      const { user_id } = req.query;
      
      console.log('GET /api/user-profile - user_id:', user_id);
      
      if (!user_id) {
        console.log('No user_id provided');
        return res.status(400).json({ error: 'User ID is required' });
      }

      console.log('Querying Supabase for user profile...');
      const { data, error } = await supabase
        .from('user_profiles')
        .select('*')
        .eq('user_id', user_id)
        .single();

      if (error) {
        console.log('Supabase error:', error);
        if (error.code === 'PGRST116') {
          console.log('Profile not found for user_id:', user_id);
          return res.status(404).json({ error: 'Profile not found' });
        }
        throw error;
      }

      console.log('Profile found:', data ? 'Yes' : 'No');
      return res.status(200).json(data);
    } catch (error: unknown) {
      console.error('Error fetching user profile:', error);
      return res.status(500).json({ error: 'Internal server error' });
    }
  }

  if (req.method === 'POST' || req.method === 'PUT') {
    try {
      const profileData = req.body;
      
      console.log('POST/PUT /api/user-profile - profileData:', profileData);
      
      // Convert comma-separated strings to arrays for text[] fields
      const arrayFields = ['subjects', 'interests', 'subjects_taught', 'specializations'];
      arrayFields.forEach(field => {
        if (profileData[field] && typeof profileData[field] === 'string') {
          // Convert comma-separated string to array
          profileData[field] = profileData[field]
            .split(',')
            .map(item => item.trim())
            .filter(item => item.length > 0);
          console.log(`Converted ${field} to array:`, profileData[field]);
        } else if (profileData[field] === '') {
          // Convert empty string to null for array fields
          profileData[field] = null;
        }
      });

      // Validate and truncate VARCHAR(20) fields
      const varchar20Fields = ['role', 'phone', 'emergency_contact_phone', 'preferred_contact_method', 'postal_code'];
      varchar20Fields.forEach(field => {
        if (profileData[field] && typeof profileData[field] === 'string' && profileData[field].length > 20) {
          console.warn(`Field ${field} exceeds 20 characters, truncating:`, profileData[field]);
          profileData[field] = profileData[field].substring(0, 20);
        }
      });

      // Handle learning_style field specifically (VARCHAR(50))
      if (profileData.learning_style && typeof profileData.learning_style === 'string' && profileData.learning_style.length > 50) {
        console.warn('learning_style exceeds 50 characters, truncating:', profileData.learning_style);
        profileData.learning_style = profileData.learning_style.substring(0, 50);
      }

      // Handle gender field specifically (VARCHAR(20))
      if (profileData.gender && typeof profileData.gender === 'string' && profileData.gender.length > 20) {
        console.warn('gender exceeds 20 characters, truncating:', profileData.gender);
        profileData.gender = profileData.gender.substring(0, 20);
      }

      // Handle empty string values for optional fields only
      const optionalFields = ['phone', 'preferred_contact_method', 'postal_code', 'learning_style'];
      optionalFields.forEach(field => {
        if (profileData[field] === '' || profileData[field] === 'Select Learning Style') {
          profileData[field] = null;
        }
      });
      
      // Keep emergency_contact_phone as string if provided, don't convert to null
      if (profileData.emergency_contact_phone === '') {
        profileData.emergency_contact_phone = null;
      }
      
      // Validate required fields
      const requiredFields = ['user_id', 'role', 'first_name', 'last_name', 'email'];
      for (const field of requiredFields) {
        if (!profileData[field]) {
          console.log(`Missing required field: ${field}`);
          return res.status(400).json({ error: `${field} is required` });
        }
      }

      // Validate role
      const validRoles = ['student', 'teacher', 'parent', 'admin'];
      if (!validRoles.includes(profileData.role)) {
        return res.status(400).json({ error: 'Invalid role' });
      }

      // Add timestamp
      profileData.updated_at = new Date().toISOString();
      if (req.method === 'POST') {
        profileData.created_at = new Date().toISOString();
      }

      console.log('Final profile data before Supabase upsert:', JSON.stringify(profileData, null, 2));

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
        
        // Convert technical database errors to user-friendly messages
        let userFriendlyError = error.message;
        
        if (error.message.includes('value too long for type character varying')) {
          const match = error.message.match(/column "(.*?)"/);
          const columnName = match ? match[1] : 'one of the fields';
          
          if (error.message.includes('(20)')) {
            userFriendlyError = `The value for "${columnName}" is too long. Please keep it under 20 characters.`;
          } else if (error.message.includes('(50)')) {
            userFriendlyError = `The value for "${columnName}" is too long. Please keep it under 50 characters.`;
          } else if (error.message.includes('(100)')) {
            userFriendlyError = `The value for "${columnName}" is too long. Please keep it under 100 characters.`;
          } else if (error.message.includes('(10)')) {
            userFriendlyError = `The value for "${columnName}" is too long. Please keep it under 10 characters.`;
          } else {
            userFriendlyError = `The value for "${columnName}" is too long. Please shorten it and try again.`;
          }
        } else if (error.message.includes('violates check constraint')) {
          userFriendlyError = 'Please select a valid role (Student, Teacher, or Parent).';
        } else if (error.message.includes('duplicate key value')) {
          userFriendlyError = 'A profile with this email already exists.';
        } else if (error.message.includes('not-null constraint')) {
          userFriendlyError = 'Please fill in all required fields marked with *.';
        }
        
        return res.status(400).json({ error: userFriendlyError });
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
