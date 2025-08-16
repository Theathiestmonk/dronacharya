import { NextApiRequest, NextApiResponse } from 'next';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { method, body, query } = req;
  
  try {
    let url = `${BACKEND_URL}/students`;
    
    // Handle different HTTP methods and routes
    if (method === 'GET' && query.studentId) {
      // Get specific student profile
      url = `${BACKEND_URL}/students/profile/${query.studentId}`;
    } else if (method === 'PUT' && query.studentId) {
      // Update student profile
      url = `${BACKEND_URL}/students/profile/${query.studentId}`;
    } else if (method === 'DELETE' && query.studentId) {
      // Delete student
      url = `${BACKEND_URL}/students/${query.studentId}`;
    }
    
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: method !== 'GET' ? JSON.stringify(body) : undefined,
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return res.status(response.status).json({
        error: errorData.detail || 'Backend request failed',
        status: response.status,
      });
    }
    
    const data = await response.json();
    return res.status(response.status).json(data);
    
  } catch (error) {
    console.error('Student API error:', error);
    return res.status(500).json({ 
      error: 'Internal server error',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}
