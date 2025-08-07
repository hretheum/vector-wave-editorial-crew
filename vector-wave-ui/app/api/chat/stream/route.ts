import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { message, context } = await request.json();
    
    // Forward to streaming backend API
    const response = await fetch('http://localhost:8003/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message,
        context: context || {}
      })
    });

    if (!response.ok) {
      console.error('Backend streaming response not ok:', response.status, response.statusText);
      
      // Return error as SSE event
      const encoder = new TextEncoder();
      const stream = new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({
            type: 'error',
            message: `Backend error: ${response.status} ${response.statusText}`
          })}\n\n`));
          controller.close();
        }
      });
      
      return new Response(stream, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    }

    // Forward the streaming response
    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no', // Disable nginx buffering
      },
    });
  } catch (error) {
    console.error('Chat streaming API error:', error);
    
    // Return error as SSE event
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({
          type: 'error',
          message: error instanceof Error ? error.message : 'Unknown error'
        })}\n\n`));
        controller.close();
      }
    });
    
    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  }
}