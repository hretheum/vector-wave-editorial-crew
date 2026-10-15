import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 15; // seconds (Vercel/serverless friendly)

type SummarizeReq = {
  title?: string;
  description?: string;
  document?: string;
};

export async function POST(req: NextRequest) {
  try {
    const apiKey = process.env.OPENAI_API_KEY || process.env.OPENAI_API_KEY_UI || process.env.OPENAI_API_KEY_DEV;
    const body = (await req.json().catch(() => ({}))) as SummarizeReq;
    const inputTitle = (body.title || "").toString();
    const inputDesc = (body.description || "").toString();
    const inputDoc = (body.document || "").toString();

    // Fallback if AI disabled
    if (!apiKey) {
      const shortTitle = clamp(inputTitle || firstLine(inputDoc) || "Suggested Topic", 80);
      const teaser = clamp(firstParagraph(inputDesc || inputDoc || ""), 180);
      return NextResponse.json({ shortTitle, teaser, source: "fallback" }, { status: 200 });
    }

    // Lazy import to avoid bundling when not needed
    const { default: OpenAI } = await import("openai");
    const client = new OpenAI({ apiKey });

    const content = [inputTitle, inputDesc, inputDoc].filter(Boolean).join("\n\n").slice(0, 4000);
    const sys = "You are a concise editor. Produce a shortTitle (<=80 chars, informative) and a teaser (<=180 chars, one sentence, no markdown). Return strict JSON with keys shortTitle, teaser.";
    const user = `Content to summarize:\n${content}`;

    const resp = await client.chat.completions.create({
      model: process.env.OPENAI_SUMMARY_MODEL || "gpt-4o-mini",
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: sys },
        { role: "user", content: user },
      ],
      temperature: 0.3,
      max_tokens: 200,
    });

    const txt = resp.choices?.[0]?.message?.content || "{}";
    let parsed: any = {};
    try { parsed = JSON.parse(txt); } catch {}
    const shortTitle = clamp(parsed.shortTitle || inputTitle || firstLine(inputDoc) || "Suggested Topic", 80);
    const teaser = clamp(parsed.teaser || firstParagraph(inputDesc || inputDoc || ""), 180);
    return NextResponse.json({ shortTitle, teaser, source: "ai" }, { status: 200 });
  } catch (e) {
    // Soft fallback
    try {
      const body = (await req.json().catch(() => ({}))) as SummarizeReq;
      const shortTitle = clamp((body.title || "Suggested Topic").toString(), 80);
      const teaser = clamp(firstParagraph((body.description || body.document || "").toString()), 180);
      return NextResponse.json({ shortTitle, teaser, source: "error_fallback" }, { status: 200 });
    } catch {}
    return NextResponse.json({ error: "summarize_failed" }, { status: 502 });
  }
}

function clamp(text: string, n: number): string {
  if (!text) return "";
  const t = text.trim();
  if (t.length <= n) return t;
  const slice = t.slice(0, n);
  const lastSpace = slice.lastIndexOf(" ");
  return (lastSpace > 40 ? slice.slice(0, lastSpace) : slice).trim() + "…";
}

function firstLine(text: string): string {
  if (!text) return "";
  const i = text.indexOf("\n");
  return i >= 0 ? text.slice(0, i) : text;
}

function firstParagraph(text: string): string {
  if (!text) return "";
  const m = text.split(/\n\n|\r\n\r\n/);
  return (m[0] || text).trim();
}


