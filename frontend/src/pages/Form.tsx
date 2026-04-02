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
    <div style={{ display: 'flex', gap: '40px', height: 'calc(100vh - 120px)', maxWidth: '1200px', margin: '0 auto' }}>
      
      {/* Left Section: Categories */}
      <div style={{ width: '280px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ fontSize: '0.85rem', fontWeight: 800, color: '#9ca3af', letterSpacing: '1.5px' }}>CATEGORIES</h2>
          <button 
            type="button"
            onClick={() => setIsAddingCategory(true)}
            aria-label="Add new category"
            style={{ background: 'transparent', border: 'none', color: 'var(--accent)', cursor: 'pointer', display: 'flex', transition: 'transform 0.2s ease' }}
          >
            <PlusCircle size={20} />
          </button>
        </div>

        <div 
          className="scrollbar-hide"
          style={{ 
            flex: 1, 
            overflowY: 'auto', 
            padding: '16px',
            background: 'rgba(255, 122, 26, 0.03)',
            borderRadius: '20px',
            border: '1px solid rgba(255, 122, 26, 0.1)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}
        >
          {isAddingCategory && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: '8px' }}>
              <input 
                autoFocus
                placeholder="Name…"
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreateCategory()}
                style={{ 
                  width: '100%', padding: '12px', background: 'rgba(255,255,255,0.05)', 
                  border: '1px solid var(--accent)', borderRadius: '10px', 
                  color: 'white', fontSize: '0.9rem', outline: 'none' 
                }}
              />
              <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                <button onClick={handleCreateCategory} style={{ flex: 1, padding: '8px', background: 'var(--accent)', border: 'none', borderRadius: '6px', color: 'white', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer' }}>ADD</button>
                <button onClick={() => setIsAddingCategory(false)} style={{ flex: 1, padding: '8px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--glass-border)', borderRadius: '6px', color: 'white', fontSize: '0.8rem', cursor: 'pointer' }}>CANCEL</button>
              </div>
            </motion.div>
          )}

          {categories.map((cat) => (
            <motion.button
              key={cat}
              whileHover={{ x: 4, background: 'rgba(255, 122, 26, 0.05)' }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setFormData(prev => ({ ...prev, primary_category: cat }))}
              style={{
                textAlign: 'left',
                padding: '14px 18px',
                borderRadius: '14px',
                border: '1px solid',
                borderColor: formData.primary_category === cat ? 'var(--accent)' : 'rgba(255, 255, 255, 0.05)',
                background: formData.primary_category === cat ? 'rgba(255, 122, 26, 0.1)' : 'rgba(10, 10, 10, 0.4)',
                color: formData.primary_category === cat ? 'white' : '#9ca3af',
                fontWeight: formData.primary_category === cat ? 700 : 500,
                fontSize: '0.85rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                {cat}
                {formData.primary_category === cat && <Bookmark size={14} fill="var(--accent)" stroke="var(--accent)" aria-hidden="true" />}
              </div>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Right Section: Form */}
      <div 
        className="scrollbar-hide"
        style={{ flex: 1, overflowY: 'auto', paddingRight: '10px', display: 'flex', flexDirection: 'column', gap: '32px' }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ 
            fontSize: '2.5rem', fontWeight: 800, background: 'linear-gradient(to bottom, #ffffff, #888888)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0
          }}>Add Leaf</h1>
          
          <div style={{ display: 'flex', gap: '12px' }}>
            <button 
              type="button" 
              onClick={clearForm}
              aria-label="Clear form"
              style={{ padding: '10px 16px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--glass-border)', borderRadius: '10px', color: '#9ca3af', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.8rem' }}
            >
              <RefreshCw size={14} aria-hidden="true" /> CLEAR ALL
            </button>
            <button 
              type="button"
              onClick={handleAiAutoFill}
              disabled={isAiLoading}
              className="accent-glow"
              style={{
                padding: '10px 20px', background: 'rgba(255, 122, 26, 0.05)', border: '1px solid var(--accent)', borderRadius: '10px',
                color: 'var(--accent)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.85rem'
              }}
            >
              {isAiLoading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} aria-hidden="true" />}
              {isAiLoading ? 'GENERATING…' : 'AI SUGGEST'}
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {/* User Note */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="user_note" style={{ fontSize: '0.8rem', fontWeight: 700, color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={16} aria-hidden="true" /> USER NOTE
              </label>
              <span style={{ fontSize: '0.7rem', fontWeight: 600, color: '#4b5563' }}>
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
              placeholder="Core leaf content (min 10 characters)…" 
              rows={3}
              maxLength={500}
              value={formData.user_note}
              onChange={(e) => setFormData({...formData, user_note: e.target.value})}
              style={{ padding: '16px', background: 'rgba(255, 255, 255, 0.03)', border: formData.user_note.length > 0 && formData.user_note.length < 10 ? '1px solid var(--accent)' : '1px solid var(--glass-border)', borderRadius: '16px', color: 'white', fontSize: '1rem', outline: 'none', resize: 'none' }}
            />
            {formData.user_note.length > 0 && formData.user_note.length < 10 && (
              <span style={{ fontSize: '0.7rem', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <AlertCircle size={10} /> Minimum 10 characters required.
              </span>
            )}
          </div>

          {/* AI Summary */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="ai_summary" style={{ fontSize: '0.8rem', fontWeight: 700, color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Layout size={16} aria-hidden="true" /> AI SUMMARY
              </label>
              <span style={{ fontSize: '0.7rem', fontWeight: 600, color: '#4b5563' }}>
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
              placeholder="System-generated context…" 
              rows={6}
              maxLength={600}
              value={formData.ai_summary}
              onChange={(e) => setFormData({...formData, ai_summary: e.target.value})}
              style={{ padding: '16px', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--glass-border)', borderRadius: '16px', color: 'white', fontSize: '1rem', outline: 'none', resize: 'vertical' }}
            />
          </div>

          {/* Tags */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="tagInput" style={{ fontSize: '0.8rem', fontWeight: 700, color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Hash size={16} aria-hidden="true" /> TAGS
              </label>
              <span style={{ fontSize: '0.7rem', fontWeight: 600, color: '#4b5563' }}>
                <span style={{ 
                  color: tags.length === 0 ? '#ff4d4d' : tags.length === 10 ? '#ff7a1a' : '#4ade80',
                  transition: 'color 0.3s ease'
                }}>
                  {tags.length}
                </span> / 10 tags
              </span>
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <input 
                id="tagInput"
                type="text" 
                placeholder="5 - 25 characters…" 
                maxLength={25}
                value={currentTag}
                onChange={(e) => setCurrentTag(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                style={{ flex: 1, padding: '14px 16px', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--glass-border)', borderRadius: '12px', color: 'white', fontSize: '1rem', outline: 'none' }}
              />
              <button 
                type="button"
                onClick={addTag}
                aria-label="Add tag"
                style={{ width: '48px', height: '48px', borderRadius: '12px', border: 'none', background: 'var(--accent)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
              >
                <Plus size={22} aria-hidden="true" />
              </button>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              <AnimatePresence>
                {tags.map((tag) => (
                  <motion.span key={tag} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.8 }} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 14px', background: 'rgba(255, 122, 26, 0.1)', border: '1px solid rgba(255, 122, 26, 0.3)', borderRadius: '100px', color: 'white', fontSize: '0.8rem' }}>
                    {tag}
                    <button type="button" onClick={() => removeTag(tag)} aria-label={`Remove tag ${tag}`} style={{ background: 'transparent', border: 'none', color: 'rgba(255,255,255,0.4)', cursor: 'pointer', display: 'flex', padding: 0 }}><X size={12} aria-hidden="true" /></button>
                  </motion.span>
                ))}
              </AnimatePresence>
            </div>
          </div>

          <button 
            type="submit" 
            disabled={!isFormValid}
            className={isFormValid ? "accent-glow" : ""}
            style={{ 
              padding: '20px', 
              background: isFormValid ? 'var(--accent)' : 'rgba(255, 255, 255, 0.05)', 
              border: 'none', 
              borderRadius: '18px', 
              color: isFormValid ? 'white' : '#4b5563', 
              fontSize: '1.1rem', 
              fontWeight: 800, 
              cursor: isFormValid ? 'pointer' : 'not-allowed',
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              gap: '12px', 
              boxShadow: isFormValid ? '0 8px 30px rgba(255, 122, 26, 0.3)' : 'none',
              transition: 'all 0.3s ease'
            }}
          >
            <Send size={18} aria-hidden="true" /> 
            {isFormValid ? 'DEPLOY LEAF' : 'INCOMPLETE FORM'}
          </button>
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
