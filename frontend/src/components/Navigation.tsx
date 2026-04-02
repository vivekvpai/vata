import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, History, FilePlus, LogOut } from 'lucide-react';
import { motion } from 'framer-motion';

const Navigation = () => {
  const navItems = [
    { title: 'Home', path: '/', icon: Home },
    { title: 'History', path: '/history', icon: History },
    { title: 'Form', path: '/form', icon: FilePlus },
  ];

  return (
    <nav 
      style={{
        width: 'var(--sidebar-width)',
        height: 'calc(100vh - 32px)',
        margin: '16px',
        position: 'fixed',
        left: 0,
        top: 0,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '24px 16px',
        zIndex: 50
      }}
      className="glass-premium"
    >
      <div>
        <div style={{ padding: '0 8px 32px 8px' }}>
          <h1 style={{ 
            fontSize: '1.5rem', 
            fontWeight: 700, 
            background: 'linear-gradient(to right, var(--accent), #ffa64d)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: '1px',
            textAlign: 'center'
          }}>V</h1>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              title={item.title}
              aria-label={item.title}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '12px',
                borderRadius: '12px',
                textDecoration: 'none',
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                background: isActive ? 'var(--glass-bg)' : 'transparent',
                border: isActive ? '1px solid var(--glass-border)' : '1px solid transparent',
                transition: 'background 0.2s ease, color 0.2s ease, border 0.2s ease',
              })}
            >
              <item.icon size={24} strokeWidth={2} aria-hidden="true" />
            </NavLink>
          ))}
        </div>
      </div>

      <div style={{ padding: '0 8px', display: 'flex', justifyContent: 'center' }}>
        <button 
          title="Settings"
          aria-label="Settings"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '12px',
            width: '100%',
            background: 'transparent',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'not-allowed',
            transition: 'color 0.2s ease',
          }}
        >
          <LogOut size={24} aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
};

export default Navigation;
