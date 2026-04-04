import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Calendar, Sparkles, User, ChevronRight } from 'lucide-react';
import HierarchicalTree, { TreeNode } from '../components/HierarchicalTree';

interface ChatSession {
  id: string;
  userName: string;
  userQuestion: string;
  date: string;
  summary: string;
  treeData: TreeNode;
}

const mockHistory: ChatSession[] = [
  {
    id: '1',
    userName: 'Shoaib',
    userQuestion: 'How should I structure my Q2 asset strategy for maximum growth?',
    date: '2026-04-01 14:30',
    summary: 'Analyzed the current asset distribution and suggested a balanced approach between high-growth links and stable text resources. The orchestration plan focuses on cross-pollinating insights from AI reports into the main knowledge base.',
    treeData: {
      name: "KNOWLEDGE BASE",
      children: [
        {
          name: "ASSETS",
          children: [{ name: "LINKS" }, { name: "TEXT" }],
        },
        {
          name: "SUMMARIES",
          children: [{ name: "AI INSIGHTS" }, { name: "REPORTS" }],
        },
      ],
    }
  },
  {
    id: '2',
    userName: 'Shoaib',
    userQuestion: 'Create a hierarchical map for Project Alpha research notes.',
    date: '2026-03-28 09:15',
    summary: 'Gathered initial data points for Project Alpha. Identified key dependencies between technical documentation and implementation nodes. Proposed a hierarchical structure for the new research repository.',
    treeData: {
      name: "PROJECT ALPHA",
      children: [
        {
          name: "CORE",
          children: [{ name: "DOCS" }, { name: "SOURCE" }],
        },
        {
          name: "RESEARCH",
          children: [{ name: "PAPERS" }, { name: "NOTES" }],
        },
      ],
    }
  }
];

const History = () => {
  const [selectedId, setSelectedId] = useState<string>(mockHistory[0].id);
  const selectedChat = mockHistory.find(chat => chat.id === selectedId) || mockHistory[0];

  return (
    <div style={{ 
      display: 'flex', 
      height: 'calc(100vh - 120px)', 
      gap: '24px',
      maxWidth: '1400px',
      margin: '0 auto',
      padding: '0 20px' 
    }}>
      {/* Left Side: 30% List */}
      <div style={{ 
        flex: '0 0 30%', 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '12px',
        overflowY: 'auto',
        paddingRight: '8px'
      }}>
        <div style={{ marginBottom: '16px' }}>
          <h1 style={{ 
            fontSize: '2rem', 
            fontWeight: 800, 
            background: 'linear-gradient(to bottom, #ffffff, #888888)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>History</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Recent Orchestrations</p>
        </div>

        {mockHistory.map((chat) => (
          <button
            key={chat.id}
            onClick={() => setSelectedId(chat.id)}
            style={{
              width: '100%',
              textAlign: 'left',
              padding: '16px',
              background: selectedId === chat.id ? 'rgba(255, 122, 26, 0.08)' : 'rgba(255, 255, 255, 0.02)',
              border: selectedId === chat.id ? '1px solid var(--accent)' : '1px solid var(--glass-border)',
              borderRadius: '16px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}
          >
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              background: selectedId === chat.id ? 'var(--accent)' : 'rgba(255, 255, 255, 0.05)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              color: selectedId === chat.id ? 'white' : 'var(--text-secondary)'
            }}>
              <User size={20} />
            </div>
            
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <span style={{ fontWeight: 700, color: 'white', fontSize: '0.95rem' }}>{chat.userName}</span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{chat.date.split(' ')[0]}</span>
              </div>
              <p style={{ 
                fontSize: '0.8rem', 
                color: 'var(--text-secondary)',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {chat.userQuestion}
              </p>
            </div>
            
            {selectedId === chat.id && (
              <ChevronRight size={16} color="var(--accent)" />
            )}
          </button>
        ))}
      </div>

      {/* Right Side: 70% Details */}
      <div className="glass-premium" style={{ 
        flex: '1', 
        borderRadius: '24px', 
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative'
      }}>
        <AnimatePresence mode="wait">
          <motion.div
            key={selectedChat.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
            style={{ 
              height: '100%', 
              display: 'flex', 
              flexDirection: 'column',
              padding: '32px',
              overflowY: 'auto'
            }}
          >
            <div style={{ marginBottom: '32px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                <div style={{ padding: '8px', background: 'rgba(255, 122, 26, 0.1)', borderRadius: '8px', color: 'var(--accent)' }}>
                  <MessageSquare size={20} />
                </div>
                <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'white' }}>{selectedChat.userQuestion}</h2>
              </div>
              
              <div style={{ display: 'flex', gap: '24px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Calendar size={14} /> {selectedChat.date}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <User size={14} /> {selectedChat.userName}
                </span>
              </div>
            </div>

            <div style={{ marginBottom: '40px' }}>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '8px', 
                color: 'var(--accent)',
                marginBottom: '16px',
                fontSize: '0.9rem',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '1px'
              }}>
                <Sparkles size={16} /> Knowledge Structure
              </div>
              <HierarchicalTree data={selectedChat.treeData} height={450} />
            </div>

            <div style={{ marginTop: 'auto' }}>
              <div style={{ 
                color: 'var(--text-secondary)',
                fontSize: '0.9rem',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '1px',
                marginBottom: '16px'
              }}>
                Summary Response
              </div>
              <div className="glass" style={{ 
                padding: '24px', 
                borderRadius: '20px',
                lineHeight: 1.8,
                color: 'rgba(255, 255, 255, 0.9)',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                fontSize: '1.05rem'
              }}>
                {selectedChat.summary}
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};

export default History;

