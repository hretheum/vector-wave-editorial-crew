export const dynamic = 'force-dynamic'
import Link from 'next/link'
import { headers } from 'next/headers'
// Bypass lib to avoid any fallback and force fresh server fetch via UI proxy with absolute URL

export default async function TopicsPage() {
  const hdrs = headers()
  const host = hdrs.get('host') || 'localhost:3000'
  const proto = hdrs.get('x-forwarded-proto') || 'http'
  const base = `${proto}://${host}`
  const url = new URL('/api/topics/suggestions', base)
  url.searchParams.set('limit', '12')
  const r = await fetch(url.toString(), { cache: 'no-store' as any })
  const data = r.ok ? await r.json() : { items: [] }
  const clamp = (text: string, n: number) => {
    if (!text) return ''
    const t = text.trim()
    if (t.length <= n) return t
    // cut on word boundary
    const slice = t.slice(0, n)
    const lastSpace = slice.lastIndexOf(' ')
    return (lastSpace > 40 ? slice.slice(0, lastSpace) : slice).trim() + '…'
  }
  const firstParagraph = (text: string) => {
    if (!text) return ''
    const p = text.split(/\n\n|\r\n\r\n/)[0] || text
    return p
  }
  // Generate AI teasers in parallel (best-effort)
  const aiSummaries = await Promise.all(
    (data.items || []).map(async (it: any) => {
      const meta = (it.metadata || {}) as any
      const payload = {
        title: meta.title || it.title || it.document || '',
        description: meta.summary || meta.description || '',
        document: it.document || ''
      }
      try {
        const rr = await fetch(new URL('/api/ai/summarize-topic', base).toString(), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          cache: 'no-store' as any
        })
        if (!rr.ok) throw new Error('ai_failed')
        const jj = await rr.json()
        return { shortTitle: jj.shortTitle, teaser: jj.teaser }
      } catch {
        return { shortTitle: payload.title, teaser: firstParagraph(payload.description || payload.document) }
      }
    })
  )

  const suggestions = (data.items || []).map((it: any, idx: number) => {
    const meta = (it.metadata || {}) as any
    const ai = aiSummaries[idx] || { shortTitle: meta.title || it.title || it.document || 'Suggested Topic', teaser: meta.summary || meta.description || it.document || '' }
    const title = clamp(String(ai.shortTitle), 80)
    const description = clamp(String(ai.teaser), 180)
    return {
      topic_id: it.topic_id || it.id,
      title,
      description,
      platform_fit: ['linkedin', 'twitter', 'ghost'],
    }
  })
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold mb-4">🎯 AI-Suggested Topics</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {suggestions.map((s) => (
          <div key={s.topic_id} className="border rounded-lg p-4 shadow-sm">
            <div className="text-lg font-medium">{s.title}</div>
            <div className="text-sm text-gray-500 mt-1">{s.description}</div>
            <div className="text-xs text-gray-400 mt-2">Fit: {(s.platform_fit||[]).join(', ')}</div>
            <Link href={`/topics/${encodeURIComponent(s.topic_id||s.title)}?t=${encodeURIComponent(s.title)}`} className="text-blue-600 text-sm mt-3 inline-block">Details →</Link>
          </div>
        ))}
      </div>
    </main>
  )
}
