import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  const body = await req.json();
  
  // Create streaming response from backend
  const response = await fetch('http://localhost:8001/api/run-pipeline-stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  
  if (!response.ok) {
    return new Response('Pipeline failed', { status: response.status });
  }
  
  // Return the streaming response
  return new Response(response.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}