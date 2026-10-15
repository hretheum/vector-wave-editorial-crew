import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const r = await fetch("http://publishing-orchestrator:8080/publish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await r.json().catch(() => ({}));
    return NextResponse.json(data, { status: r.status || 200 });
  } catch (e) {
    return NextResponse.json({ error: "proxy_failed" }, { status: 502 });
  }
}


