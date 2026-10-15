import { fetchJSON } from '@/lib/api'

async function fetchPublications() {
  const data = await fetchJSON<any>('/api/publishing/publications', { cache: 'no-store' as any })
  return data.publications || []
}

export default async function RecentPublicationsPage() {
  const pubs = await fetchPublications()
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold mb-4">🗂️ Recent Publications</h1>
      <div className="space-y-3">
        {pubs.map((p: any) => (
          <div key={p.publication_id} className="border rounded p-3">
            <div className="text-sm text-gray-600">{p.created_at}</div>
            <div className="font-medium">{p.topic?.title || p.publication_id}</div>
            <div className="text-xs text-gray-500">Status: {p.status}</div>
          </div>
        ))}
        {pubs.length === 0 && <div className="text-sm text-gray-600">No publications yet.</div>}
      </div>
    </main>
  )
}
