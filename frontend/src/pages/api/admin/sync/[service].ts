import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { service } = req.query;

  if (!service || (service !== 'classroom' && service !== 'calendar')) {
    return res.status(400).json({ error: 'Invalid service type' });
  }

  try {
    const response = await fetch(`${process.env.BACKEND_URL}/api/admin/sync/${service}`, {
      method: 'POST',
      headers: {
        'Authorization': req.headers.authorization || '',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      return res.status(response.status).json(errorData);
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error) {
    console.error(`Error syncing ${service}:`, error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}



