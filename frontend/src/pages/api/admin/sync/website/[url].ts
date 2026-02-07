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
    const fetchUrl = `${backendUrl}/api/admin/sync/website/${encodedUrl}?email=${encodeURIComponent(adminEmail)}`;
    
    console.log(`[Sync Website] Fetching from backend: ${fetchUrl}`);
    
    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minutes timeout
    
    const response = await fetch(fetchUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ 
        detail: `Backend returned status ${response.status}` 
      }));
      console.error(`[Sync Website] Backend error: ${response.status}`, errorData);
      return res.status(response.status).json({ 
        error: errorData.detail || errorData.message || `Failed to sync website page (Status: ${response.status})` 
      });
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error: unknown) {
    console.error('Error syncing individual website page:', error);
    
    // Provide more specific error messages
    const err = error as { code?: string; cause?: { code?: string }; name?: string; message?: string };
    
    if (err.code === 'ECONNREFUSED' || err.cause?.code === 'ECONNREFUSED') {
      return res.status(503).json({ 
        error: `Cannot connect to backend server at ${backendUrl}. Please ensure the backend server is running.` 
      });
    }
    
    if (err.name === 'AbortError' || err.name === 'TimeoutError') {
      return res.status(504).json({ 
        error: 'Request timed out. The website sync is taking too long. Please try again later.' 
      });
    }
    
    return res.status(500).json({ 
      error: err.message || 'Internal server error while syncing website page' 
    });
  }
}



















