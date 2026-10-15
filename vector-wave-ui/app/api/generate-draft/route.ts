import { NextRequest, NextResponse } from "next/server";

function normalizeDraft(pub: any) {
  try {
    const li = pub?.platform_content?.linkedin || {};
    const content = li.content || "";
    const generator = li.generator || null;
    const warnings = li.warnings || [];
    const assets = li.manual_upload || {};
    return { success: Boolean(content), draft: { content, generator, warnings, assets }, raw: pub };
  } catch {
    return { success: false, draft: null, raw: pub };
  }
}

// UI strict mode: no OpenAI rewrite fallback

export async function POST(req: NextRequest) {
  try {
    let title = "Untitled";
    let description = "";
    const ctype = req.headers.get('content-type') || '';
    if (ctype.includes('application/json')) {
      const body = await req.json();
      title = (body?.topic_title || body?.title || title).toString();
      description = (body?.editorial_recommendations || body?.topic_description || body?.description || description).toString();
    } else {
      const form = await req.formData();
      title = (form.get('topic_title') || form.get('title') || title).toString();
      description = (form.get('editorial_recommendations') || form.get('topic_description') || form.get('description') || description).toString();
    }
    const payload = {
      topic: { title, description, keywords: [], target_audience: "linkedin", content_type: "article" },
      // Switch back to prompt-mode (no direct_content hint) after AIWF v2 prompt fix
      platforms: { linkedin: { enabled: true, account_id: "dev" } },
      global_options: { force_presentation: false },
    };
    const bases = [process.env.ORCHESTRATOR_URL || "http://localhost:8085", "http://publishing-orchestrator:8080"];
    let pub: any = null; let status = 500;
    for (const base of bases) {
      try {
        const r = await fetch(`${base}/publish`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        status = r.status;
        const data = await r.json().catch(() => ({}));
        if (r.ok) { pub = data; break; }
        pub = data;
      } catch {}
    }
    const normalized = normalizeDraft(pub);
    const isFallback = !normalized.success || normalized?.draft?.generator === 'fallback' ||
      (Array.isArray(normalized?.draft?.warnings) && normalized.draft.warnings.some((w: any) => (w?.code || '').includes('aiwf_fallback')));
    if (isFallback) {
      return NextResponse.json({ success: false, error: 'aiwf_no_content', detail: 'AI Writing Flow did not return content', raw: pub }, { status: 502 });
    }
    return NextResponse.json(normalized, { status: status || 200 });
  } catch (e) {
    return NextResponse.json({ success: false, error: "draft_failed" }, { status: 500 });
  }
}

 