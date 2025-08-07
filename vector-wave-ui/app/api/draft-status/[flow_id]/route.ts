import { NextRequest } from "next/server";

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ flow_id: string }> }
) {
  const params = await context.params;
  try {
    const { flow_id } = params;
    
    // Forward request to backend
    const response = await fetch(`http://localhost:8001/api/draft-status/${flow_id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
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
    console.error('Draft status proxy error:', error);
    return new Response(
      JSON.stringify({ 
        error: 'Failed to get draft status',
        detail: error instanceof Error ? error.message : 'Unknown error'
      }), 
      { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}