import React, { useState, useEffect } from 'react';
import { RiKey2Line, RiAddLine, RiDeleteBinLine, RiRefreshLine } from 'react-icons/ri';
import styles from '../../app/page.module.css';

interface ApiKey {
  id: string;
  key_value: string;
  status: string;
  service: string;
  rate_limit_reset_at: string | null;
  created_at: string | null;
}

export const ApiKeyManager: React.FC = () => {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [newKey, setNewKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchKeys = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/admin/api-keys');
      if (res.ok) {
        const data = await res.json();
        setKeys(data.api_keys || []);
      }
    } catch (err) {
      console.error('Failed to fetch API keys', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleAddKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey.trim()) return;
    setError(null);
    setLoading(true);
    
    try {
      const res = await fetch('/api/v1/admin/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key_value: newKey.trim(), service: 'gemini' }),
      });
      if (res.ok) {
        setNewKey('');
        fetchKeys();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to add API key');
      }
    } catch (_err) {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteKey = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this API Key?")) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/admin/api-keys/${id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchKeys();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ background: 'rgba(30, 41, 59, 0.4)', borderRadius: '16px', padding: '24px', border: '1px solid rgba(148, 163, 184, 0.1)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h3 style={{ fontSize: '1.2rem', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <RiKey2Line color="#10b981" /> Gemini API Key Rotation Manager
        </h3>
        <button onClick={fetchKeys} className={styles.exportBtn} disabled={loading} style={{ padding: '6px 12px', fontSize: '0.85rem' }}>
          <RiRefreshLine /> Refresh
        </button>
      </div>

      <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '20px' }}>
        Add multiple Gemini API keys to automatically rotate them if one hits a `429 Too Many Requests` limit.
      </p>

      {error && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', padding: '12px', borderRadius: '8px', marginBottom: '16px', fontSize: '0.9rem' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleAddKey} style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
        <input 
          type="password"
          value={newKey}
          onChange={(e) => setNewKey(e.target.value)}
          placeholder="Paste new Gemini API Key here (AIzaSy...)"
          style={{ flex: 1, padding: '10px 16px', borderRadius: '8px', background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(148, 163, 184, 0.2)', color: '#f8fafc' }}
        />
        <button type="submit" disabled={loading || !newKey.trim()} className="btn btn-primary" style={{ padding: '0 20px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <RiAddLine /> Add Key
        </button>
      </form>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(148, 163, 184, 0.1)', color: '#94a3b8', textAlign: 'left' }}>
              <th style={{ padding: '12px' }}>Key (Masked)</th>
              <th style={{ padding: '12px' }}>Status</th>
              <th style={{ padding: '12px' }}>Added At</th>
              <th style={{ padding: '12px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {keys.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>No API keys configured. Using fallback from .env</td>
              </tr>
            ) : (
              keys.map(key => (
                <tr key={key.id} style={{ borderBottom: '1px solid rgba(148, 163, 184, 0.05)' }}>
                  <td style={{ padding: '12px', color: '#f8fafc', fontFamily: 'monospace' }}>{key.key_value}</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ 
                      padding: '4px 8px', 
                      borderRadius: '4px', 
                      fontSize: '0.8rem', 
                      background: key.status === 'active' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                      color: key.status === 'active' ? '#10b981' : '#ef4444' 
                    }}>
                      {key.status.toUpperCase()}
                      {key.rate_limit_reset_at && ` (Resets: ${new Date(key.rate_limit_reset_at).toLocaleTimeString()})`}
                    </span>
                  </td>
                  <td style={{ padding: '12px', color: '#94a3b8' }}>{new Date(key.created_at!).toLocaleString()}</td>
                  <td style={{ padding: '12px' }}>
                    <button onClick={() => handleDeleteKey(key.id)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                      <RiDeleteBinLine size={18} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
