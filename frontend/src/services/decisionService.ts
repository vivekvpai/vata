export interface DecisionResult {
  asset_id: string;
  category: string;
  category_id?: string;
  summary: string;
  tags: string[];
  match_reason: string;
  content_snippet: string;
}

export interface DecisionResponse {
  message: string;
  memory_file: string;
  count: number;
  data: DecisionResult[];
}

export const DecisionService = {
  async query(queryText: string): Promise<DecisionResponse> {
    const res = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: queryText })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Decision AI query failed.');
    }
    return res.json();
  }
};
