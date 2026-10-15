import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const folder = body?.folder || "";
    // Minimal preview: call harvester selective-preview on folder name as summary
    const r = await fetch("http://harvester:8043/triage/selective-preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ summary: folder }),
    });
    const data = await r.json().catch(() => ({}));
    // Shape a simple analysis result for dashboard rendering
    return NextResponse.json({
      folder,
      filesCount: 1,
      contentType: 'STANDALONE',
      contentOwnership: 'EXTERNAL',
      valueScore: Math.round((data.profile_fit_score || 0) * 10),
      recommendation: data.decision === 'PROMOTE' ? 'Publikuj – wysoki potencjał' : 'Wymaga dopracowania',
      topTopics: [
        { title: `${folder} (preview)`, platform: 'linkedin', viralScore: Math.round(((data.novelty_score || 0) * 10)) }
      ],
    }, { status: r.status || 200 });
  } catch (e) {
    return NextResponse.json({ error: 'analyze_failed' }, { status: 500 });
  }
}


