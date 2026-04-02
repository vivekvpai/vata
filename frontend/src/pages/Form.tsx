import React, { useState } from 'react';
import { Plus, X, FileText, Layout, Hash, Send, Sparkles, Loader2, Bookmark, PlusCircle, RefreshCw, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const INITIAL_CATEGORIES = [
  "Architecture", "Frontend", "Backend", "UI/UX", "Database", 
  "Security", "Mobile", "AI/ML", "DevOps", "Testing", 
  "Analytics", "Project Mgmt", "Strategy", "Other"
];

const Form = () => {
  const [categories, setCategories] = useState(INITIAL_CATEGORIES);
  const [newCategory, setNewCategory] = useState('');
  const [isAddingCategory, setIsAddingCategory] = useState(false);
  
  const [formData, setFormData] = useState({
    user_note: '',
    ai_summary: '',
    primary_category: '',
  });
  const [tags, setTags] = useState<string[]>([]);
  const [currentTag, setCurrentTag] = useState('');
  const [submittedJson, setSubmittedJson] = useState<string | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);

  const addTag = () => {
    if (currentTag.trim() && tags.length < 10 && !tags.includes(currentTag.trim())) {
      setTags([...tags, currentTag.trim()]);
      setCurrentTag('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  const handleCreateCategory = () => {
    if (newCategory.trim() && !categories.includes(newCategory.trim())) {
      setCategories([...categories, newCategory.trim()]);
      setFormData(prev => ({ ...prev, primary_category: newCategory.trim() }));
      setNewCategory('');
      setIsAddingCategory(false);
    }
  };

  const clearForm = () => {
    setFormData({ user_note: '', ai_summary: '', primary_category: '' });
    setTags([]);
    setSubmittedJson(null);
  };

  const handleAiAutoFill = async () => {
    setIsAiLoading(true);
    await new Promise(resolve => setTimeout(resolve, 1200));
    setFormData({
      user_note: "Integrate PyGraphistry for large-scale social network analysis.",
      ai_summary: "Graphistry is a cloud-native GPU platform for visual graph intelligence. By offloading rendering to the GPU, it enables interactively exploring millions of nodes and edges. This leaf explores the Python API (PyGraphistry) for uploading data frames and performing server-side analytics.",
      primary_category: "Analytics"
    });
    setTags(["Graphistry", "GPU Rendering", "Social Network", "Graph Intelligence", "Big Data"]);
    setIsAiLoading(false);
  };

  const isFormValid = formData.user_note.length >= 10 && formData.primary_category !== '' && tags.length > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid) return;
    const finalData = { ...formData, tags };
    setSubmittedJson(JSON.stringify(finalData, null, 2));
    console.log('Submitted Data:', finalData);
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
            gap: '10px'
          }}
        >
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

          {categories.map((cat) => (
            <motion.button
              key={cat}
              whileHover={{ x: 3, background: 'rgba(255, 122, 26, 0.05)' }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setFormData(prev => ({ ...prev, primary_category: cat }))}
              style={{
                textAlign: 'left',
                padding: '12px 14px',
                borderRadius: '12px',
                border: '1px solid',
                borderColor: formData.primary_category === cat ? 'var(--accent)' : 'rgba(255, 255, 255, 0.05)',
                background: formData.primary_category === cat ? 'rgba(255, 122, 26, 0.1)' : 'rgba(10, 10, 10, 0.4)',
                color: formData.primary_category === cat ? 'white' : '#9ca3af',
                fontWeight: formData.primary_category === cat ? 700 : 500,
                fontSize: '0.8rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                {cat}
                {formData.primary_category === cat && <Bookmark size={12} fill="var(--accent)" stroke="var(--accent)" aria-hidden="true" />}
              </div>
            </motion.button>
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
              onClick={handleAiAutoFill}
              disabled={isAiLoading}
              className="accent-glow"
              style={{
                padding: '8px 16px', background: 'rgba(255, 122, 26, 0.05)', border: '1px solid var(--accent)', borderRadius: '8px',
                color: 'var(--accent)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.8rem'
              }}
            >
              {isAiLoading ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} aria-hidden="true" />}
              {isAiLoading ? 'GENERATING…' : 'AI AUTO-FILL'}
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
          {/* User Note */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="user_note" style={{ fontSize: '0.75rem', fontWeight: 700, color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <FileText size={14} aria-hidden="true" /> ASSET DESCRIPTION
              </label>
              <span style={{ fontSize: '0.65rem', fontWeight: 600, color: '#4b5563' }}>
                <span style={{ 
                  color: formData.user_note.length === 0 ? '#ff4d4d' : formData.user_note.length === 500 ? '#ff7a1a' : '#4ade80',
                  transition: 'color 0.3s ease'
                }}>
                  {formData.user_note.length}
                </span> / 500
              </span>
            </div>
            <textarea 
              id="user_note"
              placeholder="Core asset content (min 10 characters)…" 
              rows={2}
              maxLength={500}
              value={formData.user_note}
              onChange={(e) => setFormData({...formData, user_note: e.target.value})}
              style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.03)', border: formData.user_note.length > 0 && formData.user_note.length < 10 ? '1px solid var(--accent)' : '1px solid var(--glass-border)', borderRadius: '12px', color: 'white', fontSize: '0.95rem', outline: 'none', resize: 'none' }}
            />
            {formData.user_note.length > 0 && formData.user_note.length < 10 && (
              <span style={{ fontSize: '0.65rem', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <AlertCircle size={10} /> Minimum 10 characters required.
              </span>
            )}
          </div>

          {/* AI Summary */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="ai_summary" style={{ fontSize: '0.75rem', fontWeight: 700, color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Layout size={14} aria-hidden="true" /> AI SUMMARY & CONTEXT
              </label>
              <span style={{ fontSize: '0.65rem', fontWeight: 600, color: '#4b5563' }}>
                <span style={{ 
                  color: formData.ai_summary.length === 0 ? '#ff4d4d' : formData.ai_summary.length === 600 ? '#ff7a1a' : '#4ade80',
                  transition: 'color 0.3s ease'
                }}>
                  {formData.ai_summary.length}
                </span> / 600
              </span>
            </div>
            <textarea 
              id="ai_summary"
              placeholder="Full summary details…" 
              rows={4}
              maxLength={600}
              value={formData.ai_summary}
              onChange={(e) => setFormData({...formData, ai_summary: e.target.value})}
              style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--glass-border)', borderRadius: '12px', color: 'white', fontSize: '0.95rem', outline: 'none', resize: 'none' }}
            />
          </div>

          {/* Tags */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="tagInput" style={{ fontSize: '0.75rem', fontWeight: 700, color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Hash size={14} aria-hidden="true" /> TAGS
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
                placeholder="Press Enter to add tag…" 
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
    </div>
  );
};

export default Form;
