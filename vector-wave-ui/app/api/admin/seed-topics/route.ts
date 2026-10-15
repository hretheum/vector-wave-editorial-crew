import { NextRequest, NextResponse } from "next/server";

export async function POST(_req: NextRequest) {
  const harvesterBases = [
    process.env.HARVESTER_URL || "http://localhost:8043",
    "http://harvester:8043",
  ];
  const tmBases = [
    process.env.TOPIC_MANAGER_URL || "http://localhost:8041",
    "http://topic-manager:8041",
  ];
  const details: any = { harvest: { ok: false }, reindex: { ok: false } };
  // Step 1: harvest (best-effort)
  for (const base of harvesterBases) {
    try {
      const r = await fetch(`${base}/harvest/trigger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 50 }),
      });
      const j = await r.json().catch(() => ({}));
      details.harvest = { ok: r.ok, status: r.status, fetched: j.fetched ?? null, saved: j.saved ?? null, url: base };
      if (r.ok) break;
    } catch (e) {
      details.harvest = { ok: false, error: String(e) };
    }
  }
  // Optional: run one full cycle (fetch→triage→promote) if available
  for (const base of harvesterBases) {
    try {
      const r = await fetch(`${base}/harvest/full-cycle`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ limit: 50 }) })
      if (r.ok) {
        const j = await r.json().catch(() => ({}))
        details.full_cycle = { ok: true, promoted: j.promoted ?? null }
        break
      }
    } catch {}
  }
  // Step 2: reindex (best-effort)
  for (const base of tmBases) {
    try {
      const r = await fetch(`${base}/topics/index/reindex`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 200, reset: false }),
      });
      const j = await r.json().catch(() => ({}));
      details.reindex = { ok: r.ok, status: r.status, indexed: j.indexed ?? null, url: base };
      if (r.ok) break;
    } catch (e) {
      details.reindex = { ok: false, error: String(e) };
    }
  }
  // Consider success if harvest OR reindex succeeded
  const ok = Boolean(details.harvest.ok || details.reindex.ok);
  return NextResponse.json({ ok, ...details }, { status: 200 });
}


