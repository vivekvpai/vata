import React from 'react';

const History = () => {
  const tableEntries = Array.from({ length: 6 }, (_, i) => ({
    id: i + 1,
    title: `Entry ${i + 1}`,
    date: '2026-04-01',
    status: i % 2 === 0 ? 'Success' : 'Pending',
    value: `$${(Math.random() * 1000).toFixed(2)}`,
  }));

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ 
        fontSize: '3.5rem', 
        fontWeight: 800, 
        marginBottom: '2rem',
        background: 'linear-gradient(to bottom, #ffffff, #888888)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
      }}>History</h1>
      
      <div className="glass-premium" style={{ width: '100%', overflow: 'hidden', padding: '1rem' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--glass-border)', color: 'var(--text-secondary)' }}>
              <th style={{ textAlign: 'left', padding: '16px' }}>Item</th>
              <th style={{ textAlign: 'left', padding: '16px' }}>Date</th>
              <th style={{ textAlign: 'left', padding: '16px' }}>Status</th>
              <th style={{ textAlign: 'right', padding: '16px' }}>Value</th>
            </tr>
          </thead>
          <tbody>
            {tableEntries.map((entry) => (
              <tr key={entry.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <td style={{ padding: '16px', fontWeight: 500 }}>{entry.title}</td>
                <td style={{ padding: '16px', color: 'var(--text-secondary)' }}>{entry.date}</td>
                <td style={{ padding: '16px' }}>
                  <span style={{ 
                    padding: '4px 10px', 
                    borderRadius: '20px', 
                    fontSize: '0.75rem',
                    background: entry.status === 'Success' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(234, 179, 8, 0.1)',
                    color: entry.status === 'Success' ? '#22c55e' : '#eab308'
                  }}>
                    {entry.status}
                  </span>
                </td>
                <td style={{ padding: '16px', textAlign: 'right', fontWeight: 600 }}>{entry.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default History;
