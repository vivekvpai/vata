import React from 'react';
import Navigation from './Navigation';
import { motion, AnimatePresence } from 'framer-motion';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', width: '100vw', background: 'var(--bg-black)' }}>
      <Navigation />
      <main 
        style={{
          marginLeft: 'calc(var(--sidebar-width) + 32px)',
          padding: '40px',
          width: 'calc(100% - (var(--sidebar-width) + 32px))',
          height: '100vh',
          overflowY: 'auto'
        }}
      >
        <AnimatePresence mode="wait">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
};

export default Layout;
