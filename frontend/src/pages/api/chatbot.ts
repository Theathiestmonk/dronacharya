import type { NextApiRequest, NextApiResponse } from 'next';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  try {
    // Try primary connection method first
    let backendRes;
    try {
      backendRes = await fetch(`${BACKEND_URL}/chatbot/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body),
      });
    } catch (fetchError) {
      // Fallback to alternative connection method
      backendRes = await fetch(`http://127.0.0.1:8000/chatbot/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body),
      });
    }
    
    const data = await backendRes.json();
    res.status(backendRes.status).json(data);
  } catch (error) {
    console.error('Chatbot API error:', error);
    res.status(500).json({ 
      error: 'Failed to connect to backend.',
      details: error instanceof Error ? error.message : String(error)
    });
  }
} 