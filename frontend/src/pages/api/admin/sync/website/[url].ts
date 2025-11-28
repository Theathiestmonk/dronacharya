import { NextApiRequest, NextApiResponse } from 'next';

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { url } = req.query;
  const { adminEmail } = req.body;

  if (!url || typeof url !== 'string') {
    return res.status(400).json({ error: 'URL is required' });
  }

  if (!adminEmail) {
    return res.status(400).json({ 
      error: 'User email is required. Please ensure you are logged in.' 
    });
  }

  try {
    // URL encode the URL parameter
    const encodedUrl = encodeURIComponent(url);
    const response = await fetch(`${backendUrl}/api/admin/sync/website/${encodedUrl}?email=${encodeURIComponent(adminEmail)}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return res.status(response.status).json({ 
        error: data.detail || data.message || 'Failed to sync website page' 
      });
    }

    return res.status(200).json(data);
  } catch (error) {
    console.error('Error syncing individual website page:', error);
    return res.status(500).json({ 
      error: 'Internal server error while syncing website page' 
    });
  }
}



