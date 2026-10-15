import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const { title, summary } = await req.json();
    const payload = { summary: String(summary || title || "") };
    const harvesterBases = [process.env.HARVESTER_URL || "http://localhost:8043", "http://harvester:8043"];
    const tmBases = [process.env.TOPIC_MANAGER_URL || "http://localhost:8041", "http://topic-manager:8041"];
    // 1) Full triage
    let triage: any = { ok: false };
    for (const base of harvesterBases) {
      try {
        const r = await fetch(`${base}/triage/selective`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const j = await r.json().catch(() => ({}));
        triage = { ok: r.ok, status: r.status, ...j };
        if (r.ok) break;
      } catch {}
    }
    // 2) Reindex if promoted
    let reindex: any = null;
    if (String(triage?.decision || "").toUpperCase() === "PROMOTE") {
      for (const base of tmBases) {
        try {
          const r = await fetch(`${base}/topics/index/reindex`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ limit: 200, reset: false }) });
          const j = await r.json().catch(() => ({}));
          reindex = { ok: r.ok, status: r.status, ...j };
          break;
        } catch {}
      }
    }
    return NextResponse.json({ triage, reindex }, { status: 200 });
  } catch (e) {
    return NextResponse.json({ error: "analyze_full_failed" }, { status: 502 });
  }
}


