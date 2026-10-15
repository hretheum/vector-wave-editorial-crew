"use client"

import { useEffect, useState } from 'react'

type Service = {
  name: string
  url: string
}

const SERVICES: Service[] = [
  { name: 'Editorial', url: 'http://localhost:8040/health' },
  { name: 'TopicMgr', url: 'http://localhost:8041/health' },
  { name: 'Publisher', url: 'http://localhost:8085/health' },
]

function dotClass(ok: boolean | null) {
  if (ok === null) return 'bg-gray-300'
  return ok ? 'bg-green-500' : 'bg-red-500'
}

export default function ServiceStatus() {
  const [statuses, setStatuses] = useState<Record<string, boolean | null>>({})

  useEffect(() => {
    let timer: any
    const fetchStatuses = async () => {
      const entries = await Promise.all(
        SERVICES.map(async (s) => {
          try {
            const res = await fetch(s.url, { cache: 'no-store' })
            return [s.name, res.ok] as const
          } catch {
            return [s.name, false] as const
          }
        })
      )
      const obj: Record<string, boolean> = {}
      for (const [name, ok] of entries) obj[name] = ok
      setStatuses(obj)
    }
    fetchStatuses()
    timer = setInterval(fetchStatuses, 10000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="flex items-center gap-3 text-xs text-gray-600">
      {SERVICES.map((s) => (
        <div key={s.name} className="flex items-center gap-1">
          <span className={`inline-block w-2 h-2 rounded-full ${dotClass(statuses[s.name] ?? null)}`}></span>
          <span>{s.name}</span>
        </div>
      ))}
    </div>
  )
}
