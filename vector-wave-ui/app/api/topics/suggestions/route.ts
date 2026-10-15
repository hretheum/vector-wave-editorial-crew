import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q") || "AI";
  const limit = searchParams.get("limit") || "12";
  const token = process.env.TOPIC_MANAGER_TOKEN;
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const params = `q=${encodeURIComponent(q)}&limit=${encodeURIComponent(limit)}`;
  const bases = [
    process.env.TOPIC_MANAGER_URL || "http://localhost:8041",
    "http://topic-manager:8041",
  ];
  for (const base of bases) {
    try {
      const url = `${base}/topics/search?${params}`;
      const r = await fetch(url, { cache: "no-store", headers });
      if (r.ok) {
        const data = await r.json().catch(() => ({}));
        return NextResponse.json(data, { status: r.status || 200 });
      }
    } catch {
      // try next base
    }
  }
  return NextResponse.json({ items: [], error: "proxy_failed" }, { status: 502 });
}


