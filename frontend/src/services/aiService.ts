export interface SuggestionRequest {
  main_content: string;
  summary?: string;
  tags?: string[];
}

export const AIService = {
  async getSuggestions(data: SuggestionRequest) {
    const res = await fetch('/api/suggestions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch suggestions.');
    }
    return res.json();
  }
};
