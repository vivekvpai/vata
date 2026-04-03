import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, X } from 'lucide-react';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  onConfirm,
  onCancel,
}) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onCancel}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              width: '100vw',
              height: '100vh',
              background: 'rgba(0, 0, 0, 0.7)',
              backdropFilter: 'blur(8px)',
              zIndex: 10000,
            }}
          />

          {/* Modal Container */}
          <div
            style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 10001,
              width: '90%',
              maxWidth: '400px',
              pointerEvents: 'none',
            }}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              className="glass-premium"
              style={{
                padding: '32px',
                borderRadius: '24px',
                textAlign: 'center',
                boxShadow: '0 20px 80px rgba(0, 0, 0, 0.5)',
                pointerEvents: 'auto',
              }}
            >
              <div
                style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '50%',
                  background: 'rgba(239, 68, 68, 0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 24px',
                  color: '#ef4444',
                }}
              >
                <AlertTriangle size={32} />
              </div>

              <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#fff', marginBottom: '12px' }}>
                {title}
              </h2>
              
              <p style={{ fontSize: '1rem', color: '#9ca3af', lineHeight: 1.6, marginBottom: '32px' }}>
                {message}
              </p>

              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  onClick={onCancel}
                  style={{
                    flex: 1,
                    padding: '12px',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--glass-border)',
                    borderRadius: '12px',
                    color: '#fff',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                  onMouseOver={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)')}
                  onMouseOut={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)')}
                >
                  {cancelText}
                </button>
                <button
                  onClick={onConfirm}
                  style={{
                    flex: 1,
                    padding: '12px',
                    background: '#ef4444',
                    border: 'none',
                    borderRadius: '12px',
                    color: '#fff',
                    fontWeight: 700,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: '0 4px 20px rgba(239, 68, 68, 0.3)',
                  }}
                  onMouseOver={(e) => (e.currentTarget.style.background = '#dc2626')}
                  onMouseOut={(e) => (e.currentTarget.style.background = '#ef4444')}
                >
                  {confirmText}
                </button>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
};

export default ConfirmModal;
