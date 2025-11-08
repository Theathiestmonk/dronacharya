import type { NextApiRequest, NextApiResponse } from 'next';

const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const GOOGLE_CLASSROOM_SCOPES = [
  'https://www.googleapis.com/auth/classroom.courses.readonly',
  'https://www.googleapis.com/auth/classroom.rosters.readonly',
  'https://www.googleapis.com/auth/classroom.coursework.me.readonly',
  'https://www.googleapis.com/auth/classroom.student-submissions.me.readonly',
];

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  if (!GOOGLE_CLIENT_ID) {
    return res.status(500).json({ error: 'Google Client ID not configured' });
  }

  // Use student-specific callback URL
  const redirectUri = process.env.GOOGLE_STUDENT_REDIRECT_URI || 
    `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/student/google-classroom/callback`;
  
  const scopeString = GOOGLE_CLASSROOM_SCOPES.join(' ');
  
  const authUrl = (
    `https://accounts.google.com/o/oauth2/v2/auth?` +
    `client_id=${GOOGLE_CLIENT_ID}&` +
    `redirect_uri=${encodeURIComponent(redirectUri)}&` +
    `response_type=code&` +
    `scope=${encodeURIComponent(scopeString)}&` +
    `access_type=offline&` +
    `prompt=consent&` +
    `state=student_classroom`
  );

  return res.status(200).json({ auth_url: authUrl });
}










