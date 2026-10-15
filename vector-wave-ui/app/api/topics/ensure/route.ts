import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const title: string = body?.title || "Untitled";
    const summary: string = body?.summary || title;
    const idem = `ui_${Buffer.from(title).toString("base64").slice(0, 32)}`;
    const r = await fetch("http://topic-manager:8041/topics/suggestion", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": idem },
      body: JSON.stringify({ title, summary, keywords: ["ui"], content_type: "POST" }),
    });
    const data = await r.json().catch(() => ({}));
    return NextResponse.json(data, { status: r.status || 200 });
  } catch (e) {
    return NextResponse.json({ error: "ensure_failed" }, { status: 500 });
  }
}


