import React from 'react';
import Link from 'next/link';

export const Footer: React.FC = () => {
  return (
    <footer style={{ marginTop: '80px', padding: '40px 0 28px', borderTop: '1px solid rgba(255,255,255,0.06)', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '10px', textDecoration: 'none', color: '#fff', fontWeight: 700, fontSize: '1.15rem' }}>
          <img
            src="/logo.png"
            alt="JASUSS.TECH Logo"
            width={40}
            height={40}
            style={{ borderRadius: '10px', objectFit: 'cover', boxShadow: '0 0 16px rgba(56, 189, 248, 0.3)' }}
          />
          <span>JASUSS<span style={{ color: '#38bdf8' }}>.TECH</span></span>
        </Link>
        <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.88rem', maxWidth: '480px' }}>
          Next-Generation Autonomous Web Quality Assurance & Regression Suite
        </p>
      </div>
      <p style={{ margin: 0 }}>© {new Date().getFullYear()} JASUSS.TECH. Powered by Nexus Engine. Engineered for enterprise quality assurance.</p>
    </footer>
  );
};
