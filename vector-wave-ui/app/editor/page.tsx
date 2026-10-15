'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { DraftEditor } from '@/components/DraftEditor'

type StoredDraft = {
  content: string
  generator?: string | null
  warnings?: any[]
  assets?: any
  topicTitle: string
  platform: string
}

export default function EditorPage() {
  const router = useRouter()
  const params = useSearchParams()
  const key = params.get('k') || ''
  const [draft, setDraft] = useState<StoredDraft | null>(null)

  useEffect(() => {
    if (!key) return
    try {
      const raw = localStorage.getItem(key)
      if (raw) {
        const parsed = JSON.parse(raw)
        setDraft(parsed)
      }
    } catch {}
  }, [key])

  

  const warningsList = useMemo(() => (Array.isArray(draft?.warnings) ? draft?.warnings : []), [draft])
  const assets = draft?.assets || {}

  if (!key) {
    return (
      <div className="p-6">
        <p className="text-sm text-gray-600">Brak klucza draftu. Wróć do dashboardu i wygeneruj draft.</p>
      </div>
    )
  }

  if (!draft) {
    return (
      <div className="p-6">
        <p className="text-sm text-gray-600">Ładowanie edytora…</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="w-full px-4">
        
      {/* Diagnostics: warnings and assets */}
      <div className="w-full pt-4">
        {(warningsList && warningsList.length > 0) && (
          <div className="mb-4 p-3 border border-yellow-300 bg-yellow-50 rounded">
            <div className="text-sm font-medium text-yellow-900">Ostrzeżenia</div>
            <ul className="list-disc list-inside text-sm text-yellow-900 mt-1">
              {warningsList.map((w: any, idx: number) => (
                <li key={`warn-${idx}`}>{w?.code || 'warn'}{w?.message ? `: ${w.message}` : ''}</li>
              ))}
            </ul>
          </div>
        )}
        {assets && (assets.file_id || assets.upload_url) && (
          <div className="mb-4 p-3 border border-blue-200 bg-blue-50 rounded">
            <div className="text-sm font-medium text-blue-900">Załączniki</div>
            <div className="text-sm text-blue-900 mt-1 space-y-1">
              {assets.file_id && <div>file_id: <code>{assets.file_id}</code></div>}
              {assets.upload_url && (
                <div>
                  upload_url: <a href={assets.upload_url} target="_blank" rel="noreferrer" className="text-blue-700 underline">{assets.upload_url}</a>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <DraftEditor 
        initialDraft={draft.content}
        topicTitle={draft.topicTitle}
        platform={draft.platform}
        onBack={() => router.push('/')}
        onPublish={() => {}}
      />
      </div>
    </div>
  )
}

