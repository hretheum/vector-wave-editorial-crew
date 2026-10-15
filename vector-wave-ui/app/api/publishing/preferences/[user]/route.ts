import { NextRequest, NextResponse } from "next/server";

export async function PUT(_req: NextRequest, { params }: { params: { user: string } }) {
  try {
    const body = await _req.json();
    const r = await fetch(`http://publishing-orchestrator:8080/preferences/${encodeURIComponent(params.user)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await r.json().catch(() => ({}));
    return NextResponse.json(data, { status: r.status || 200 });
  } catch (e) {
    return NextResponse.json({ error: "proxy_failed" }, { status: 502 });
  }
}

export async function GET(_req: NextRequest, { params }: { params: { user: string } }) {
  try {
    const r = await fetch(`http://publishing-orchestrator:8080/preferences/${encodeURIComponent(params.user)}`);
    const data = await r.json().catch(() => ({}));
    return NextResponse.json(data, { status: r.status || 200 });
  } catch (e) {
    return NextResponse.json({ error: "proxy_failed" }, { status: 502 });
  }
}


