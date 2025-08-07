import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { message, context } = await request.json();
    
    // Forward to new AI Assistant backend API with timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
    
    const response = await fetch('http://localhost:8003/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message,
        context: context || {}
      }),
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);

    if (!response.ok) {
      console.error('Backend response not ok:', response.status, response.statusText);
      const errorText = await response.text();
      console.error('Error details:', errorText);
      
      // Fallback to simple responses if backend is down
      return NextResponse.json({
        response: `Przepraszam, ale mój backend jest obecnie niedostępny (${response.status}). Mogę jednak pomóc Ci z podstawowymi pytaniami o Vector Wave. O co chciałbyś zapytać?`
      });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Chat API error:', error);
    console.error('Error details:', error instanceof Error ? error.message : 'Unknown error');
    
    // Check if it's a timeout error
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json({
        response: "Analiza zajmuje trochę więcej czasu. Proszę spróbuj ponownie lub zadaj prostsze pytanie.",
        error: "timeout"
      });
    }
    
    // Return a natural fallback response
    return NextResponse.json({
      response: `Ups, coś poszło nie tak z połączeniem: ${error instanceof Error ? error.message : 'Unknown error'}. Ale słucham - o czym chcesz pogadać?`,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}