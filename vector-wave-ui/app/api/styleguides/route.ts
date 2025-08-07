import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  try {
    // Proxy request to backend
    const response = await fetch('http://localhost:8001/api/styleguides');
    
    if (!response.ok) {
      const error = await response.text();
      return NextResponse.json(
        { error: error || 'Failed to load styleguides' },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to connect to backend' },
      { status: 500 }
    );
  }
}