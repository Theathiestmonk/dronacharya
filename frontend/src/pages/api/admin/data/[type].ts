import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { type } = req.query;

  if (!type || (type !== 'classroom' && type !== 'calendar')) {
    return res.status(400).json({ error: 'Invalid data type' });
  }

  try {
    const response = await fetch(`${process.env.BACKEND_URL}/api/admin/data/${type}`, {
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
    console.error(`Error fetching ${type} data:`, error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}



