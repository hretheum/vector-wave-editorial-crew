import { NextRequest, NextResponse } from "next/server";

export async function GET(_req: NextRequest) {
  try {
    const r = await fetch("http://publishing-orchestrator:8080/publications", { cache: "no-store" });
    const data = await r.json().catch(() => ({}));
    return NextResponse.json(data, { status: r.status || 200 });
  } catch (e) {
    return NextResponse.json({ publications: [], error: "proxy_failed" }, { status: 502 });
  }
}


