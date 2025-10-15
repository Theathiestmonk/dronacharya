// Debug script to test password reset
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('❌ Missing Supabase environment variables');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseAnonKey);

async function testPasswordReset() {
  console.log('🧪 Testing password reset...');
  
  try {
    const { data, error } = await supabase.auth.resetPasswordForEmail('dhruvil2001@gmail.com', {
      redirectTo: 'http://localhost:3000/reset-password',
    });
    
    if (error) {
      console.error('❌ Error:', error);
    } else {
      console.log('✅ Success:', data);
    }
  } catch (err) {
    console.error('❌ Exception:', err);
  }
}

testPasswordReset();
