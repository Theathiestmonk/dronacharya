import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { service } = req.query;

  if (!service || typeof service !== 'string') {
    return res.status(400).json({ error: 'Service parameter is required' });
  }

  if (service !== 'classroom' && service !== 'calendar' && service !== 'both') {
    return res.status(400).json({ error: "Service must be 'classroom', 'calendar', or 'both'" });
  }

  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const url = `${backendUrl}/api/admin/auth-url?service=${encodeURIComponent(service)}`;
    
    console.log(`🔍 [AUTH-URL API] Proxying to backend: ${url}`);
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`🔍 [AUTH-URL API] Backend error: ${response.status} - ${errorText}`);
      return res.status(response.status).json({ error: errorText || 'Failed to generate auth URL' });
    }

    const data = await response.json();
    console.log(`🔍 [AUTH-URL API] Successfully received auth URL from backend`);
    
    return res.status(200).json(data);
  } catch (error) {
    console.error(`🔍 [AUTH-URL API] Error proxying to backend:`, error);
    return res.status(500).json({ 
      error: 'Failed to generate auth URL',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}

