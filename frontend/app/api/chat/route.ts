import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    // In a real deployment, this URL would be your FastAPI server address
    // For local development, it's usually http://localhost:8000
    console.log(process.env.BACKEND_URL)
    const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

    const response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Backend error');
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error: any) {
    console.error('Frontend API Proxy Error:', error);
    
    // Fallback or error message
    return NextResponse.json({ 
      error: 'Không thể kết nối với Backend Python. Hãy đảm bảo đã khởi chạy FastAPI server.',
      details: error.message 
    }, { status: 500 });
  }
}
