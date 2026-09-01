import React from 'react';
import styles from '../../app/page.module.css';

export const Footer: React.FC = () => {
  return (
    <footer style={{ marginTop: '80px', padding: '32px 0 24px', borderTop: '1px solid rgba(255,255,255,0.06)', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
      <p>© {new Date().getFullYear()} JASUSS QA Suite. Powered by Nexus Engine. Engineered for enterprise quality assurance.</p>
    </footer>
  );
};
