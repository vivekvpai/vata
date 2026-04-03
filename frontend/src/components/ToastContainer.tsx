import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';
import { useToast, ToastType } from '../contexts/ToastContext';

const getIcon = (type: ToastType) => {
  switch (type) {
    case 'success': return <CheckCircle size={18} />;
    case 'warning': return <AlertTriangle size={18} />;
    case 'alert': return <AlertCircle size={18} />;
    default: return <Info size={18} />;
  }
};

const getColor = (type: ToastType) => {
  switch (type) {
    case 'success': return '#22c55e';
    case 'warning': return '#eab308';
    case 'alert': return '#ef4444';
    default: return 'var(--accent)';
  }
};

const ToastItem: React.FC<{ toast: any; onRemove: (id: string) => void }> = ({ toast, onRemove }) => {
  const color = getColor(toast.type);
  
  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 50, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 20, scale: 0.9, transition: { duration: 0.2 } }}
      className="glass-premium"
      style={{
        width: '320px',
        padding: '16px',
        borderRadius: '16px',
        display: 'flex',
        gap: '14px',
        position: 'relative',
        overflow: 'hidden',
        borderLeft: `4px solid ${color}`,
        marginBottom: '10px',
        pointerEvents: 'auto',
      }}
    >
      <div style={{ color, marginTop: '2px' }}>
        {getIcon(toast.type)}
      </div>
      
      <div style={{ flex: 1 }}>
        <h4 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 700, color: '#fff' }}>{toast.title}</h4>
        {toast.subtitle && (
          <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#9ca3af', lineHeight: 1.4 }}>
            {toast.subtitle}
          </p>
        )}
      </div>

      <button
        onClick={() => onRemove(toast.id)}
        style={{
          background: 'none',
          border: 'none',
          color: '#4b5563',
          cursor: 'pointer',
          padding: '4px',
          display: 'flex',
          alignItems: 'start',
          transition: 'color 0.2s ease',
        }}
        onMouseOver={(e) => (e.currentTarget.style.color = '#fff')}
        onMouseOut={(e) => (e.currentTarget.style.color = '#4b5563')}
      >
        <X size={14} />
      </button>

      {/* Timer Bar */}
      <motion.div
        initial={{ width: '100%' }}
        animate={{ width: '0%' }}
        transition={{ duration: (toast.duration || 3000) / 1000, ease: 'linear' }}
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          height: '2px',
          background: color,
          opacity: 0.3,
        }}
      />
    </motion.div>
  );
};

const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useToast();

  return (
    <div
      style={{
        position: 'fixed',
        top: '24px',
        right: '24px',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        pointerEvents: 'none',
      }}
    >
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
        ))}
      </AnimatePresence>
    </div>
  );
};

export default ToastContainer;
