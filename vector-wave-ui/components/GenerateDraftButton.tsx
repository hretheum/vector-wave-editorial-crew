 'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

type Props = { title: string; description?: string };

export default function GenerateDraftButton({ title, description }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ content: string; generator?: string | null; warnings?: any[] } | null>(null);
  const router = useRouter();

  const handleClick = async () => {
    try {
      setError(null);
      setLoading(true);
      setPreview(null);
      const r = await fetch('/api/generate-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic_title: title, topic_description: description || '' }),
      });
      const j = await r.json();
      if (!r.ok || !j?.success) {
        setError('Draft generation failed');
        return;
      }
      const content = j.draft?.content || '';
      const generator = j.draft?.generator || null;
      const warnings = j.draft?.warnings || [];
      const assets = j.draft?.assets || {};
      setPreview({ content, generator, warnings });

      // Persist and navigate to editor
      const key = `draft-${Date.now()}`;
      const payload = {
        content,
        generator,
        warnings,
        assets,
        topicTitle: title,
        platform: 'linkedin'
      };
      try { localStorage.setItem(key, JSON.stringify(payload)); } catch {}
      router.push(`/editor?k=${encodeURIComponent(key)}`);
    } catch (e: any) {
      setError(e?.message || 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        className="px-3 py-1 border rounded text-sm hover:bg-gray-50 disabled:opacity-50"
      >
        {loading ? 'Generuję…' : 'Wygeneruj draft (AIWF)'}
      </button>
      {error && <div className="text-sm text-red-600">{error}</div>}
      {preview && (
        <div className="border rounded p-3 bg-gray-50 text-sm">
          <div className="text-gray-700 whitespace-pre-wrap">
            {preview.content || ''}
          </div>
          <div className="text-xs text-gray-500 mt-2">
            {preview.generator ? `generator: ${preview.generator}` : ''}
            {preview.warnings && preview.warnings.length > 0 ? ` • warnings: ${preview.warnings.map((w: any) => w?.code || 'warn').join(', ')}` : ''}
          </div>
        </div>
      )}
    </div>
  );
}


