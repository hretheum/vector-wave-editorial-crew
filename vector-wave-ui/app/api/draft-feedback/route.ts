import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    
    // Forward request to backend
    const response = await fetch('http://localhost:8001/api/draft-feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      const error = await response.text();
      return new Response(error, { 
        status: response.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const data = await response.json();
    return Response.json(data);
    
  } catch (error) {
    console.error('Draft feedback proxy error:', error);
    return new Response(
      JSON.stringify({ 
        error: 'Failed to send feedback',
        detail: error instanceof Error ? error.message : 'Unknown error'
      }), 
      { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}