import { NextApiRequest, NextApiResponse } from 'next';

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { event_id } = req.query;
  const { adminEmail, calendarId } = req.body;

  if (!event_id || typeof event_id !== 'string') {
    return res.status(400).json({ error: 'Event ID is required' });
  }

  if (!calendarId) {
    return res.status(400).json({ error: 'Calendar ID is required' });
  }

  if (!adminEmail) {
    return res.status(400).json({ 
      error: 'User email is required. Please ensure you are logged in.' 
    });
  }

  try {
    const response = await fetch(`${backendUrl}/api/admin/sync/event/${encodeURIComponent(event_id)}?email=${encodeURIComponent(adminEmail)}&calendar_id=${encodeURIComponent(calendarId)}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return res.status(response.status).json({ 
        error: data.detail || data.message || 'Failed to sync event' 
      });
    }

    return res.status(200).json(data);
  } catch (error) {
    console.error('Error syncing individual event:', error);
    return res.status(500).json({ 
      error: 'Internal server error while syncing event' 
    });
  }
}

