import Link from "next/link";
import { headers } from 'next/headers'
import GenerateDraftButton from '@/components/GenerateDraftButton'

export const dynamic = 'force-dynamic'

async function fetchJSON(url: string, init?: RequestInit) {
  const r = await fetch(url, init as any);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export default async function TopicDetails({ params, searchParams }: { params: Promise<{ id: string }>, searchParams?: Promise<Record<string, string>> }) {
  const { id: rawId } = await params;
  const id = decodeURIComponent(rawId);
  const hdrs = await headers();
  const host = hdrs.get('host') || 'localhost:3000'
  const proto = hdrs.get('x-forwarded-proto') || 'http'
  const base = `${proto}://${host}`
  // Prefer direct topic-manager on server via bases
  const bases = [process.env.TOPIC_MANAGER_URL || 'http://localhost:8041', 'http://topic-manager:8041']
  let topic: any = null
  for (const b of bases) {
    const t = await fetchJSON(`${b}/topics/${encodeURIComponent(id)}`).catch(() => null)
    if (t) { topic = t; break }
  }
  // Fallback: if id was a suggestion without stored topic, try by title passed in query
  const sp = searchParams ? await searchParams : undefined
  if (!topic && sp?.t) {
    const q = encodeURIComponent((sp as any).t)
    for (const b of bases) {
      const s = await fetchJSON(`${b}/topics/search?q=${q}&limit=1`).catch(() => null)
      const cand = s?.items?.[0]
      if (cand?.metadata?.title || cand?.document) {
        topic = {
          topic_id: cand.topic_id || cand.id,
          title: cand.metadata?.title || cand.title || cand.document,
          description: cand.metadata?.summary || cand.metadata?.description || cand.document || '',
          content_type: cand.metadata?.content_type || 'POST'
        }
        break
      }
    }
    // As a last-resort fallback (e.g., offline tests), synthesize a minimal topic from query param
    if (!topic) {
      topic = {
        topic_id: id,
        title: (sp as any).t,
        description: '',
        content_type: 'POST'
      }
    }
  }
  let nearest: any[] = [];
  if (topic?.title) {
    const q = encodeURIComponent(topic.title.slice(0, 60));
    let search: any = { items: [] }
    for (const b of bases) {
      const s = await fetchJSON(`${b}/topics/search?q=${q}&limit=5`).catch(() => null)
      if (s) { search = s; break }
    }
    nearest = search.items || [];
  }
  return (
    <main className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold">Szczegóły tematu</h1>
        <div className="flex items-center gap-3">
          <Link href="/" className="text-sm text-blue-600">← Dashboard</Link>
          <Link href="/topics" className="text-sm text-blue-600">Lista tematów</Link>
          <Link href="/publishing" className="text-sm text-blue-600">Publikacje</Link>
        </div>
      </div>
      {!topic ? (
        <div className="text-red-600">Not found</div>
      ) : (
        <div className="space-y-3">
          <div className="text-lg font-medium">{topic.title}</div>
          <div className="text-gray-600">{topic.description}</div>
          <div className="text-sm text-gray-500">content_type: {topic.content_type}</div>
          <div className="pt-4">
            <div className="font-semibold mb-2">Nearest</div>
            <ul className="list-disc pl-6">
              {nearest.map((n: any) => (
                <li key={n.topic_id} className="text-sm">
                  <Link href={`/topics/${encodeURIComponent(n.topic_id)}`} className="text-blue-600">
                    {n.metadata?.title || n.title || n.document}
                  </Link>
                  {typeof n.score === 'number' && <span className="text-gray-400"> (score: {n.score.toFixed(3)})</span>}
                </li>
              ))}
            </ul>
          </div>
          <div className="flex gap-2 pt-4">
            <form action="/api/publishing/publish" method="post">
              <input type="hidden" name="topic_title" value={topic.title} />
              <input type="hidden" name="platform" value="linkedin" />
              <button className="px-3 py-1 border rounded">Wygeneruj draft</button>
            </form>
            <Link href="/publishing" className="px-3 py-1 border rounded">Przejdź do publikacji</Link>
            <form action="/api/topics/analyze-full" method="post">
              <input type="hidden" name="title" value={topic.title} />
              <input type="hidden" name="summary" value={topic.description} />
              <button className="px-3 py-1 border rounded">Analizuj (full)</button>
            </form>
            <GenerateDraftButton title={topic.title} description={topic.description} />
          </div>
        </div>
      )}
    </main>
  );
}


