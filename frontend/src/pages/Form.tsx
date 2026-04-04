import React, { useState, useEffect } from 'react';
import { Plus, X, FileText, Layout, Hash, Send, Sparkles, Loader2, Bookmark, PlusCircle, RefreshCw, AlertCircle, Pencil, Trash2, Check, ArrowRight, ThumbsUp, ThumbsDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useToast } from '../contexts/ToastContext';
import ConfirmModal from '../components/ConfirmModal';


const Form = () => {
  const [categories, setCategories] = useState<string[]>([]);
  const [isCategoryLoading, setIsCategoryLoading] = useState(false);
  const [newCategory, setNewCategory] = useState('');
  const [isAddingCategory, setIsAddingCategory] = useState(false);
  const [editingCategory, setEditingCategory] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  
  const [formData, setFormData] = useState({
    main_content: '',
    summary: '',
    category: '',
  });
  const [tags, setTags] = useState<string[]>([]);
  const [currentTag, setCurrentTag] = useState('');
  const [submittedJson, setSubmittedJson] = useState<string | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);
  
  // Suggestion State
  const [suggestions, setSuggestions] = useState<{
    summary: string | null;
    tags: string[] | null;
    category: string | null;
  }>({
    summary: null,
    tags: null,
    category: null
  });
  
  const [history, setHistory] = useState<string[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<string | null>(null);

  // Deletion State
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [categoryToDelete, setCategoryToDelete] = useState<string | null>(null);

  const { showToast } = useToast();

  const fetchCategories = async () => {
    setIsCategoryLoading(true);
    try {
      const response = await fetch('/api/categories');
      if (response.ok) {
        const data = await response.json();
        // Backend returns dict { category_name: [files] }
        setCategories(Object.keys(data));
      } else {
        showToast('error', 'Fetch Failed', 'Could not load categories from server.');
      }
    } catch (error) {
      showToast('error', 'Fetch Error', 'Network error while fetching categories.');
    } finally {
      setIsCategoryLoading(false);
    }
  };

  const fetchHistory = async (category: string) => {
    try {
      const response = await fetch(`/api/categories/${category}`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data.files || []);
      }
    } catch (error) {
      console.error("Failed to fetch history:", error);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, [showToast]);

  useEffect(() => {
    if (formData.category) {
      fetchHistory(formData.category);
    } else {
      setHistory([]);
    }
  }, [formData.category]);

  const loadAsset = async (filename: string) => {
    try {
      const response = await fetch(`/api/categories/${formData.category}`);
      if (response.ok) {
        const data = await response.json();
        // Since get_category returns the latest content, we might need a more specific getter
        // But for now, let's assume get_category content is what we want if it's the latest
        // Or fetch specific file content if we had an endpoint for that.
        // Actually, main.py get_category returns the *resolved* (latest) file.
        // Let's assume we load the version context.
        const content = data.content;
        if (content && content.data) {
          setFormData({
            main_content: content.data.main_content || '',
            summary: content.data.summary || '',
            category: content.category || formData.category,
          });
          setTags(content.data.tags || []);
          setSelectedAsset(filename);
          showToast('info', 'Asset Loaded', `Loaded version: ${filename.split('_')[1].split('.')[0]}`);
        }
      }
    } catch (error) {
      showToast('error', 'Load Failed', 'Could not fetch asset content.');
    }
  };

  const deleteAsset = async (filename: string) => {
    if (!window.confirm(`Are you sure you want to delete this specific version?`)) return;
    
    setIsCategoryLoading(true);
    try {
      const response = await fetch(`/api/categories/${formData.category}/files/${filename}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        showToast('alert', 'Version Deleted', 'Specific asset version has been removed.');
        fetchHistory(formData.category);
        if (selectedAsset === filename) {
          setSelectedAsset(null);
        }
      } else {
        showToast('error', 'Deletion Failed', 'Server rejected asset deletion.');
      }
    } catch (error) {
      showToast('error', 'Network Error', 'Could not delete asset.');
    } finally {
      setIsCategoryLoading(false);
    }
  };

  const addTag = () => {
    if (currentTag.trim() && tags.length < 10 && !tags.includes(currentTag.trim())) {
      setTags([...tags, currentTag.trim()]);
      setCurrentTag('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  const handleCreateCategory = async () => {
    if (newCategory.trim() && !categories.includes(newCategory.trim())) {
      setIsCategoryLoading(true);
      try {
        const response = await fetch('/api/categories', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category: newCategory.trim() })
        });
        
        if (response.ok) {
          setCategories([...categories, newCategory.trim()]);
          setFormData(prev => ({ ...prev, category: newCategory.trim() }));
          setNewCategory('');
          setIsAddingCategory(false);
          showToast('success', 'Category Created', `"${newCategory.trim()}" has been added.`);
        } else {
          showToast('error', 'Creation Failed', 'Server rejected category creation.');
        }
      } catch (error) {
        showToast('error', 'Network Error', 'Could not connect to the server.');
      } finally {
        setIsCategoryLoading(false);
      }
    }
  };

  const handleEditCategory = async (oldName: string) => {
    if (editValue.trim() && (editValue.trim() === oldName || !categories.includes(editValue.trim()))) {
      if (editValue.trim() === oldName) {
        setEditingCategory(null);
        return;
      }

      setIsCategoryLoading(true);
      try {
        const response = await fetch(`/api/categories/${oldName}/rename`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ new_name: editValue.trim() })
        });

        if (response.ok) {
          setCategories(categories.map(c => c === oldName ? editValue.trim() : c));
          if (formData.category === oldName) {
            setFormData(prev => ({ ...prev, category: editValue.trim() }));
          }
          setEditingCategory(null);
          setEditValue('');
          showToast('success', 'Category Updated', `Renamed "${oldName}" to "${editValue.trim()}".`);
        } else {
          const err = await response.json();
          showToast('error', 'Update Failed', err.detail || 'Could not rename category.');
        }
      } catch (error) {
        showToast('error', 'Network Error', 'Could not connect to the server.');
      } finally {
        setIsCategoryLoading(false);
      }
    }
  };

  const handleDeleteCategory = (name: string) => {
    setCategoryToDelete(name);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (categoryToDelete) {
      setIsCategoryLoading(true);
      try {
        const response = await fetch(`/api/categories/${categoryToDelete}`, {
          method: 'DELETE'
        });

        if (response.ok) {
          setCategories(categories.filter(c => c !== categoryToDelete));
          if (formData.category === categoryToDelete) {
            setFormData(prev => ({ ...prev, category: '' }));
          }
          showToast('alert', 'Category Deleted', `"${categoryToDelete}" has been removed.`);
          setCategoryToDelete(null);
          setIsDeleteModalOpen(false);
        } else {
          showToast('error', 'Deletion Failed', 'Server rejected category deletion.');
        }
      } catch (error) {
        showToast('error', 'Network Error', 'Could not connect to the server.');
      } finally {
        setIsCategoryLoading(false);
      }
    }
  };

  const clearForm = () => {
    setFormData({ main_content: '', summary: '', category: '' });
    setTags([]);
    setSuggestions({ summary: null, tags: null, category: null });
    setSubmittedJson(null);
    showToast('info', 'Form Cleared', 'All fields have been reset.');
  };

  const handleSuggestAi = async () => {
    if (formData.main_content.length < 10) {
      showToast('alert', 'Incomplete Content', 'Provide more main content for AI to analyze.');
      return;
    }

    setIsAiLoading(true);
    // Simulate AI Processing
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    setSuggestions({
      summary: "This implementation leverages GPU-accelerated rendering via Graphistry for real-time visualization of multi-million node datasets, optimizing network analysis performance and interactive exploration.",
      category: "Analytics",
      tags: ["Graphistry", "GPU", "Performance", "Big Data", "Visual intelligence"]
    });
    
    setIsAiLoading(false);
    showToast('info', 'AI Suggestions Ready', 'Review the suggested improvements below each field.');
  };

  const isFormValid = formData.main_content.length >= 10 && formData.category !== '' && tags.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid) return;

    setIsCategoryLoading(true);
    try {
      // If selectedAsset is already set, we might want to update (PUT)
      // but for simplicity, let's always create a new version (POST)
      // as it's more "Vata" like (versioned)
      const response = await fetch('/api/categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: formData.category,
          data: {
            main_content: formData.main_content,
            summary: formData.summary,
            tags: tags
          }
        })
      });

      if (response.ok) {
        const finalData = { ...formData, tags };
        setSubmittedJson(JSON.stringify(finalData, null, 2));
        showToast('success', 'Asset Saved', 'Your digital asset has been successfully recorded.');
        fetchHistory(formData.category);
      } else {
        showToast('error', 'Save Failed', 'Server rejected asset submission.');
      }
    } catch (error) {
      showToast('error', 'Network Error', 'Could not save asset to server.');
    } finally {
      setIsCategoryLoading(false);
    }
  };

  const acceptSuggestion = (type: 'summary' | 'tags' | 'category') => {
    if (type === 'summary' && suggestions.summary) {
      setFormData(prev => ({ ...prev, summary: suggestions.summary! }));
      setSuggestions(prev => ({ ...prev, summary: null }));
    } else if (type === 'tags' && suggestions.tags) {
      setTags(suggestions.tags);
      setSuggestions(prev => ({ ...prev, tags: null }));
    } else if (type === 'category' && suggestions.category) {
      setFormData(prev => ({ ...prev, category: suggestions.category! }));
      setSuggestions(prev => ({ ...prev, category: null }));
    }
    showToast('success', 'Suggestion Accepted', `Applied improvement to ${type}.`);
  };

  const rejectSuggestion = (type: 'summary' | 'tags' | 'category') => {
    setSuggestions(prev => ({ ...prev, [type]: null }));
    showToast('info', 'Suggestion Rejected', `Removed improvement for ${type}.`);
  };

  return (
    <div style={{ display: 'flex', gap: '30px', height: 'calc(100vh - 100px)', maxWidth: '1200px', margin: '0 auto', overflow: 'hidden' }}>
      
      {/* Left Section: Categories */}
      <div style={{ width: '260px', display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ fontSize: '0.8rem', fontWeight: 800, color: '#9ca3af', letterSpacing: '1.2px' }}>CATEGORIES</h2>
          <button 
            type="button"
            onClick={() => setIsAddingCategory(true)}
            aria-label="Add new category"
            style={{ background: 'transparent', border: 'none', color: 'var(--accent)', cursor: 'pointer', display: 'flex', transition: 'transform 0.2s ease' }}
          >
            <PlusCircle size={18} />
          </button>
        </div>

        <div 
          className="scrollbar-hide"
          style={{ 
            flex: 1, 
            overflowY: 'auto', 
            padding: '12px',
            background: 'rgba(255, 122, 26, 0.03)',
            borderRadius: '16px',
            border: '1px solid rgba(255, 122, 26, 0.1)',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            position: 'relative'
          }}
        >
          {isCategoryLoading && (
            <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.2)', backdropFilter: 'blur(1px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10, borderRadius: '16px' }}>
              <Loader2 className="animate-spin text-accent" size={24} />
            </div>
          )}
          {isAddingCategory && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: '4px' }}>
              <input 
                autoFocus
                placeholder="Name…"
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreateCategory()}
                style={{ 
                  width: '100%', padding: '10px', background: 'rgba(255,255,255,0.05)', 
                  border: '1px solid var(--accent)', borderRadius: '8px', 
                  color: 'white', fontSize: '0.85rem', outline: 'none' 
                }}
              />
              <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                <button onClick={handleCreateCategory} style={{ flex: 1, padding: '6px', background: 'var(--accent)', border: 'none', borderRadius: '4px', color: 'white', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer' }}>ADD</button>
                <button onClick={() => setIsAddingCategory(false)} style={{ flex: 1, padding: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--glass-border)', borderRadius: '4px', color: 'white', fontSize: '0.75rem', cursor: 'pointer' }}>CANCEL</button>
              </div>
            </motion.div>
          )}

          {suggestions.category && (
             <motion.div 
               initial={{ opacity: 0, scale: 0.95 }} 
               animate={{ opacity: 1, scale: 1 }}
               style={{ 
                 background: 'rgba(74, 222, 128, 0.05)', 
                 border: '1px dashed #4ade80', 
                 borderRadius: '12px', 
                 padding: '10px', 
                 marginBottom: '10px',
                 fontSize: '0.75rem'
               }}
             >
               <div style={{ color: '#4ade80', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                 <Sparkles size={12} /> SUGGESTED CATEGORY
               </div>
               <div style={{ color: 'white', marginBottom: '8px', fontWeight: 600 }}>{suggestions.category}</div>
               <div style={{ display: 'flex', gap: '4px' }}>
                 <button onClick={() => acceptSuggestion('category')} style={{ flex: 1, padding: '4px', background: '#4ade80', border: 'none', borderRadius: '4px', color: '#050505', fontWeight: 700, cursor: 'pointer', fontSize: '0.65rem' }}>ACCEPT</button>
                 <button onClick={() => rejectSuggestion('category')} style={{ flex: 0.5, padding: '4px', background: 'rgba(255,255,255,0.05)', border: 'none', borderRadius: '4px', color: 'white', cursor: 'pointer', fontSize: '0.65rem' }}>X</button>
               </div>
             </motion.div>
          )}

          {categories.map((cat) => (
            <motion.div
              key={cat}
              style={{ position: 'relative', display: 'flex', alignItems: 'center' }}
            >
              {editingCategory === cat ? (
                <div style={{ display: 'flex', gap: '6px', width: '100%' }}>
                  <input 
                    autoFocus
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleEditCategory(cat)}
                    style={{ 
                      flex: 1, padding: '10px', background: 'rgba(255,255,255,0.05)', 
                      border: '1px solid var(--accent)', borderRadius: '8px', 
                      color: 'white', fontSize: '0.85rem', outline: 'none' 
                    }}
                  />
                  <button onClick={() => handleEditCategory(cat)} style={{ padding: '8px', background: 'var(--accent)', border: 'none', borderRadius: '8px', color: 'white', cursor: 'pointer' }}><Check size={14} /></button>
                </div>
              ) : (
                <div style={{ position: 'relative', width: '100%', display: 'flex', alignItems: 'center' }} className="category-item-container">
                  <motion.button
                    whileHover={{ x: 3, background: 'rgba(255, 122, 26, 0.05)' }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setFormData(prev => ({ ...prev, category: cat }))}
                    style={{
                      textAlign: 'left',
                      width: '100%',
                      padding: '12px 14px',
                      borderRadius: '12px',
                      border: '1px solid',
                      borderColor: formData.category === cat ? 'var(--accent)' : 'rgba(255, 255, 255, 0.05)',
                      background: formData.category === cat ? 'rgba(255, 122, 26, 0.1)' : 'rgba(10, 10, 10, 0.4)',
                      color: formData.category === cat ? 'white' : '#9ca3af',
                      fontWeight: formData.category === cat ? 700 : 500,
                      fontSize: '0.8rem',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      paddingRight: '60px'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {formData.category === cat && (
                        <motion.div 
                          initial={{ scale: 0 }} 
                          animate={{ scale: 1 }} 
                          style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)', boxShadow: '0 0 10px var(--accent)' }} 
                        />
                      )}
                      <span>{cat}</span>
                    </div>
                  </motion.button>
                  
                  <div className="category-actions" style={{ position: 'absolute', right: '8px', display: 'flex', gap: '4px', opacity: 0.2, transition: 'opacity 0.2s ease' }}>
                    <button 
                      onClick={(e) => { e.stopPropagation(); setEditingCategory(cat); setEditValue(cat); }}
                      style={{ background: 'transparent', border: 'none', color: '#9ca3af', cursor: 'pointer', padding: '4px' }}
                    >
                      <Pencil size={14} />
                    </button>
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleDeleteCategory(cat); }}
                      style={{ background: 'transparent', border: 'none', color: '#ff4d4d', cursor: 'pointer', padding: '4px' }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </div>

      {/* Right Section: Form */}
      <div 
        className="scrollbar-hide"
        style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '32px', height: '100%', overflowY: 'auto', paddingRight: '4px' }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ 
            fontSize: '2rem', fontWeight: 800, background: 'linear-gradient(to bottom, #ffffff, #888888)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0
          }}>Add Asset</h1>
          
          <div style={{ display: 'flex', gap: '8px' }}>
            <button 
              type="button" 
              onClick={clearForm}
              aria-label="Clear form"
              style={{ padding: '8px 12px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--glass-border)', borderRadius: '8px', color: '#9ca3af', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.75rem' }}
            >
              <RefreshCw size={12} aria-hidden="true" /> CLEAR
            </button>
            <button 
              type="button"
              onClick={handleSuggestAi}
              disabled={isAiLoading}
              className="accent-glow"
              style={{
                padding: '8px 16px', background: 'rgba(255, 122, 26, 0.05)', border: '1px solid var(--accent)', borderRadius: '8px',
                color: 'var(--accent)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.8rem'
              }}
            >
              {isAiLoading ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} aria-hidden="true" />}
              {isAiLoading ? 'ANALYZING…' : 'SUGGEST AI'}
            </button>

            {/* Accept All Button */}
            {(suggestions.summary || suggestions.tags || suggestions.category) && (
              <motion.button 
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                onClick={() => {
                  if (suggestions.summary) acceptSuggestion('summary');
                  if (suggestions.tags) acceptSuggestion('tags');
                  if (suggestions.category) acceptSuggestion('category');
                  showToast('success', 'All Suggestions Applied', 'Successfully integrated all AI improvements.');
                }}
                className="accent-glow"
                style={{
                  padding: '8px 16px', background: '#22c55e', border: 'none', borderRadius: '8px',
                  color: '#050505', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.8rem',
                  boxShadow: '0 0 15px rgba(34, 197, 94, 0.3)'
                }}
              >
                <Check size={14} /> ACCEPT ALL
              </motion.button>
            )}
          </div>
        </div>

        {/* Category History - Mini Row */}
        <AnimatePresence>
          {formData.category && history.length > 0 && (
            <motion.div 
              initial={{ height: 0, opacity: 0 }} 
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              style={{ paddingBottom: '16px', overflow: 'hidden' }}
            >
              <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '8px' }} className="scrollbar-hide">
                {history.map((fname, idx) => (
                  <motion.div 
                    key={fname}
                    whileHover={{ scale: 1.05 }}
                    style={{ 
                      flexShrink: 0, padding: '8px 12px', background: 'rgba(255,255,255,0.03)', 
                      border: selectedAsset === fname ? '1px solid var(--accent)' : '1px solid var(--glass-border)',
                      borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
                      fontSize: '0.7rem', color: selectedAsset === fname ? 'white' : '#9ca3af'
                    }}
                    onClick={() => loadAsset(fname)}
                  >
                    <Bookmark size={12} /> Version v{history.length - idx}
                    <button 
                      onClick={(e) => { e.stopPropagation(); deleteAsset(fname); }}
                      style={{ background: 'transparent', border: 'none', color: '#ff4d4d', cursor: 'pointer', display: 'flex', marginLeft: '4px' }}
                    >
                      <X size={10} />
                    </button>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
          {/* Main Content */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="main_content" style={{ fontSize: '0.75rem', fontWeight: 700, color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <FileText size={14} aria-hidden="true" /> MAIN CONTENT
              </label>
              <span style={{ fontSize: '0.65rem', fontWeight: 600, color: '#4b5563' }}>
                <span style={{ 
                  color: formData.main_content.length === 0 ? '#ff4d4d' : formData.main_content.length === 500 ? '#ff7a1a' : '#4ade80',
                  transition: 'color 0.3s ease'
                }}>
                  {formData.main_content.length}
                </span> / 500
              </span>
            </div>
            <textarea 
              id="main_content"
              placeholder="Enter the primary asset text here…" 
              rows={2}
              maxLength={500}
              value={formData.main_content}
              onChange={(e) => setFormData({...formData, main_content: e.target.value})}
              style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.03)', border: formData.main_content.length > 0 && formData.main_content.length < 10 ? '1px solid var(--accent)' : '1px solid var(--glass-border)', borderRadius: '12px', color: 'white', fontSize: '0.95rem', outline: 'none', resize: 'none' }}
            />
            {formData.main_content.length > 0 && formData.main_content.length < 10 && (
              <span style={{ fontSize: '0.65rem', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <AlertCircle size={10} /> Minimum 10 characters required.
              </span>
            )}
          </div>

          {/* AI Summary */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="summary" style={{ fontSize: '0.75rem', fontWeight: 700, color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Layout size={14} aria-hidden="true" /> SUMMARY & CONTEXT
              </label>
              <span style={{ fontSize: '0.65rem', fontWeight: 600, color: '#4b5563' }}>
                <span style={{ 
                  color: formData.summary.length === 0 ? '#ff4d4d' : formData.summary.length === 600 ? '#ff7a1a' : '#4ade80',
                  transition: 'color 0.3s ease'
                }}>
                  {formData.summary.length}
                </span> / 600
              </span>
            </div>
            <textarea 
              id="summary"
              placeholder="Provide a summary context for the asset…" 
              rows={4}
              maxLength={600}
              value={formData.summary}
              onChange={(e) => setFormData({...formData, summary: e.target.value})}
              style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--glass-border)', borderRadius: '12px', color: 'white', fontSize: '0.95rem', outline: 'none', resize: 'none' }}
            />
            
            <AnimatePresence>
              {suggestions.summary && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }} 
                  animate={{ opacity: 1, y: 0 }} 
                  exit={{ opacity: 0, y: -10 }}
                  style={{ 
                    marginTop: '8px', padding: '14px', background: 'rgba(74, 222, 128, 0.05)', 
                    border: '1px dashed #4ade80', borderRadius: '12px' 
                  }}
                >
                  <div style={{ color: '#4ade80', fontSize: '0.75rem', fontWeight: 800, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Sparkles size={14} /> AI RECOMMENDED SUMMARY
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'white', lineHeight: 1.6, marginBottom: '12px' }}>{suggestions.summary}</p>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button type="button" onClick={() => acceptSuggestion('summary')} style={{ padding: '6px 16px', background: '#4ade80', border: 'none', borderRadius: '6px', color: '#050505', fontWeight: 700, fontSize: '0.75rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}><ThumbsUp size={12}/> Accept</button>
                    <button type="button" onClick={() => rejectSuggestion('summary')} style={{ padding: '6px 16px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', color: 'white', fontSize: '0.75rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}><ThumbsDown size={12}/> Reject</button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Tags */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="tagInput" style={{ fontSize: '0.75rem', fontWeight: 700, color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Hash size={14} aria-hidden="true" /> KEYWORDS
              </label>
              <span style={{ fontSize: '0.65rem', fontWeight: 600, color: '#4b5563' }}>
                <span style={{ 
                  color: tags.length === 0 ? '#ff4d4d' : tags.length === 10 ? '#ff7a1a' : '#4ade80',
                  transition: 'color 0.3s ease'
                }}>
                  {tags.length}
                </span> / 10 tags
              </span>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input 
                id="tagInput"
                type="text" 
                placeholder="Type and press Enter…" 
                maxLength={25}
                value={currentTag}
                onChange={(e) => setCurrentTag(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                style={{ flex: 1, padding: '12px 14px', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--glass-border)', borderRadius: '10px', color: 'white', fontSize: '0.95rem', outline: 'none' }}
              />
              <button 
                type="button"
                onClick={addTag}
                aria-label="Add tag"
                style={{ width: '42px', height: '42px', borderRadius: '10px', border: 'none', background: 'var(--accent)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
              >
                <Plus size={20} aria-hidden="true" />
              </button>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              <AnimatePresence>
                {tags.map((tag) => (
                  <motion.span key={tag} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.8 }} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 12px', background: 'rgba(255, 122, 26, 0.1)', border: '1px solid rgba(255, 122, 26, 0.3)', borderRadius: '100px', color: 'white', fontSize: '0.75rem' }}>
                    {tag}
                    <button type="button" onClick={() => removeTag(tag)} aria-label={`Remove tag ${tag}`} style={{ background: 'transparent', border: 'none', color: 'rgba(255,255,255,0.4)', cursor: 'pointer', display: 'flex', padding: 0 }}><X size={10} aria-hidden="true" /></button>
                  </motion.span>
                ))}
              </AnimatePresence>
            </div>

            <AnimatePresence>
              {suggestions.tags && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }} 
                  animate={{ opacity: 1, y: 0 }} 
                  exit={{ opacity: 0, y: -10 }}
                  style={{ 
                    marginTop: '8px', padding: '14px', background: 'rgba(74, 222, 128, 0.05)', 
                    border: '1px dashed #4ade80', borderRadius: '12px' 
                  }}
                >
                  <div style={{ color: '#4ade80', fontSize: '0.75rem', fontWeight: 800, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Sparkles size={14} /> AI RECOMMENDED KEYWORDS
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
                    {suggestions.tags.map(t => (
                      <span key={t} style={{ padding: '2px 8px', background: 'rgba(74, 222, 128, 0.1)', borderRadius: '4px', fontSize: '0.7rem', color: '#4ade80' }}>{t}</span>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button type="button" onClick={() => acceptSuggestion('tags')} style={{ padding: '6px 16px', background: '#4ade80', border: 'none', borderRadius: '6px', color: '#050505', fontWeight: 700, fontSize: '0.75rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}><ThumbsUp size={12}/> Accept All</button>
                    <button type="button" onClick={() => rejectSuggestion('tags')} style={{ padding: '6px 16px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', color: 'white', fontSize: '0.75rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}><ThumbsDown size={12}/> Reject</button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }}>
            <button 
              type="submit" 
              disabled={!isFormValid}
              className={isFormValid ? "accent-glow" : ""}
              style={{ 
                padding: '12px 32px', 
                background: isFormValid ? 'var(--accent)' : 'rgba(255, 255, 255, 0.05)', 
                border: 'none', 
                borderRadius: '12px', 
                color: isFormValid ? 'white' : '#4b5563', 
                fontSize: '0.9rem', 
                fontWeight: 800, 
                cursor: isFormValid ? 'pointer' : 'not-allowed',
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                gap: '8px', 
                boxShadow: isFormValid ? '0 6px 20px rgba(255, 122, 26, 0.2)' : 'none',
                transition: 'all 0.3s ease'
              }}
            >
              <Send size={16} aria-hidden="true" /> 
              {isFormValid ? 'SAVE ASSET' : 'INCOMPLETE FORM'}
            </button>
          </div>
        </form>

        <AnimatePresence>
          {submittedJson && (
            <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} style={{ marginTop: '20px', paddingBottom: '60px' }}>
              <h3 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#9ca3af', marginBottom: '14px' }}>STRUCTURED RECORD</h3>
              <pre style={{ padding: '28px', borderRadius: '20px', background: 'rgba(0,0,0,0.6)', border: '1px solid rgba(255, 122, 26, 0.15)', color: 'var(--accent)', fontSize: '0.9rem', lineHeight: 1.6, overflowX: 'auto', whiteSpace: 'pre-wrap' }}>
                {submittedJson}
              </pre>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <ConfirmModal 
        isOpen={isDeleteModalOpen}
        title="Delete Category?"
        message={`Are you sure you want to delete "${categoryToDelete}"? This action cannot be undone.`}
        confirmText="Delete"
        onConfirm={confirmDelete}
        onCancel={() => {
          setIsDeleteModalOpen(false);
          setCategoryToDelete(null);
        }}
      />
    </div>
  );
};

export default Form;

