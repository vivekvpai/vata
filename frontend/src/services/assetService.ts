export interface AssetData {
  main_content: string;
  summary?: string;
  tags?: string[];
}

export const AssetService = {
  async createAsset(categoryId: string, data: AssetData) {
    const res = await fetch(`/api/categories/${categoryId}/assets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Server rejected asset submission.');
    return res.json();
  },

  async updateAsset(categoryId: string, assetId: string, data: AssetData) {
    const res = await fetch(`/api/categories/${categoryId}/assets/${assetId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Server rejected the granular update.');
    return res.json();
  },

  async deleteAsset(categoryId: string, assetId: string) {
    const res = await fetch(`/api/categories/${categoryId}/assets/${assetId}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error('Failed to remove asset.');
    return res.json();
  }
};
