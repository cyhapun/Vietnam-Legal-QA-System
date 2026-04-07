import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    // Lấy Base URL từ Env, mặc định là localhost nếu không có
    const BACKEND_BASE_URL = process.env.BACKEND_URL || 'http://localhost:8000';

    // Gọi đến endpoint cụ thể
    // Kết quả sẽ là "/_/backend/chat" trên Vercel hoặc "http://localhost:8000/chat" ở local
    const response = await fetch(`${BACKEND_BASE_URL}/chat`, { 
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({})); 
      throw new Error(errorData.detail || `Backend error: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error: any) {
    console.error('Frontend API Proxy Error:', error);
    
    return NextResponse.json({ 
      error: 'Lỗi kết nối Backend',
      details: error.message 
    }, { status: 500 });
  }
}