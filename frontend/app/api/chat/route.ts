import { NextRequest, NextResponse } from 'next/server';

function getBackendUrl(reqUrl: string): string {
  let base = process.env.BACKEND_URL || 'http://localhost:8000';
  if (base.startsWith('/')) {
    const { origin } = new URL(reqUrl);
    base = `${origin}${base}`;
  }
  return base.replace(/\/+$/, '');
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const backendBase = getBackendUrl(req.url);
    const streamUrl = `${backendBase}/chat/stream`;
    console.log(`[Proxy Stream] -> ${streamUrl}`);

    const backendRes = await fetch(streamUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!backendRes.ok) {
      const err = await backendRes.json().catch(() => ({}));
      return NextResponse.json(
        { error: 'Backend loi', details: err.detail || `Status: ${backendRes.status}` },
        { status: backendRes.status }
      );
    }

    return new NextResponse(backendRes.body, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
      },
    });

  } catch (error: any) {
    console.error('[Proxy Stream Error]', error);
    return NextResponse.json(
      { error: 'Loi ket noi Backend', details: error.message },
      { status: 500 }
    );
  }
}
