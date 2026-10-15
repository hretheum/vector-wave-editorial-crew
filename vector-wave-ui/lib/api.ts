export async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export type TopicSuggestion = {
  topic_id?: string;
  title: string;
  description?: string;
  score?: number;
  platform_fit?: string[];
};

export async function fetchTopicSuggestions(limit = 12): Promise<TopicSuggestion[]> {
  // Always use UI proxy to work both in docker and local npm dev
  const q = encodeURIComponent("AI");
  const url = `/api/topics/suggestions?q=${q}&limit=${limit}`;
  try {
    const res = await fetch(url, { cache: 'no-store' } as any);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const items = (data.items || []) as any[];
    return items.map((it) => {
      const meta = (it.metadata || {}) as any;
      const title = meta.title || it.title || it.document || "Suggested Topic";
      const description = meta.summary || meta.description || "";
      return {
        topic_id: it.topic_id || it.id,
        title,
        description,
        score: typeof it.score === "number" ? it.score : undefined,
        platform_fit: ["linkedin", "twitter", "ghost"],
      };
    });
  } catch {
    // Fallback mock
    return Array.from({ length: limit }).map((_, i) => ({
      topic_id: `mock_${i}`,
      title: `AI Suggestion #${i + 1}`,
      description: "Placeholder suggestion",
      score: Math.round(70 + Math.random() * 30),
      platform_fit: ["linkedin", "twitter"],
    }));
  }
}
