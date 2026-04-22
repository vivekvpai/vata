export const CategoryService = {
  async getCategories() {
    const res = await fetch('/api/categories');
    if (!res.ok) throw new Error('Failed to load categories.');
    return res.json();
  },
  
  async getCategory(categoryId: string) {
    const res = await fetch(`/api/categories/${categoryId}`);
    if (!res.ok) throw new Error('Failed to load category assets.');
    return res.json();
  },

  async createCategory(category: string) {
    const res = await fetch('/api/categories', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category })
    });
    if (!res.ok) throw new Error('Server rejected category creation.');
    return res.json();
  },

  async updateCategoryName(oldName: string, newName: string) {
    const res = await fetch(`/api/categories/${oldName}/rename`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_name: newName })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Could not rename category.');
    }
    return res.json();
  },

  async deleteCategory(categoryId: string) {
    const res = await fetch(`/api/categories/${categoryId}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error('Server rejected category deletion.');
    return res.json();
  }
};
