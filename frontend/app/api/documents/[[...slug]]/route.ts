import { NextRequest, NextResponse } from 'next/server';

function getBackendUrl(reqUrl: string): string {
  let base = process.env.BACKEND_URL || 'http://localhost:8000';
  if (base.startsWith('/')) {
    const { origin } = new URL(reqUrl);
    base = `${origin}${base}`;
  }
  return base.replace(/\/+$/, '');
}

export async function GET(req: NextRequest, { params }: { params: Promise<{ slug?: string[] }> }) {
  try {
    const backendBase = getBackendUrl(req.url);
    const resolvedParams = await params;
    const slugPath = resolvedParams.slug ? resolvedParams.slug.join('/') : '';
    const searchParams = req.nextUrl.search;
    const url = `${backendBase}/api/documents${slugPath ? `/${slugPath}` : ''}${searchParams}`;

    const backendRes = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!backendRes.ok) {
      const err = await backendRes.json().catch(() => ({}));
      return NextResponse.json(
        { error: 'Backend error', details: err.detail || `Status: ${backendRes.status}` },
        { status: backendRes.status }
      );
    }

    const data = await backendRes.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('[Proxy GET /documents Error]', error);
    return NextResponse.json(
      { error: 'Backend connection error', details: error.message },
      { status: 500 }
    );
  }
}

export async function POST(req: NextRequest, { params }: { params: Promise<{ slug?: string[] }> }) {
  try {
    const backendBase = getBackendUrl(req.url);
    const resolvedParams = await params;
    const slugPath = resolvedParams.slug ? resolvedParams.slug.join('/') : '';
    const searchParams = req.nextUrl.search;
    const url = `${backendBase}/api/documents${slugPath ? `/${slugPath}` : ''}${searchParams}`;

    const formData = await req.formData();

    const backendRes = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!backendRes.ok) {
      const err = await backendRes.json().catch(() => ({}));
      return NextResponse.json(
        { error: 'Backend error', details: err.detail || `Status: ${backendRes.status}` },
        { status: backendRes.status }
      );
    }

    const data = await backendRes.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('[Proxy POST /documents Error]', error);
    return NextResponse.json(
      { error: 'Backend connection error', details: error.message },
      { status: 500 }
    );
  }
}
