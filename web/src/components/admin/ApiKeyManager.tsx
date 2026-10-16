import React, { useState, useEffect, useCallback } from 'react';
import { RiKey2Line, RiAddLine, RiDeleteBinLine, RiRefreshLine, RiErrorWarningFill } from 'react-icons/ri';
import { useAuth } from '../../context/AuthContext';
import { Surface3D, EmptyState3D } from '../three';
import a from './admin3d.module.css';

interface ApiKey {
  id: string;
  key_value: string;
  status: string;
  service: string;
  rate_limit_reset_at: string | null;
  created_at: string | null;
}

export const ApiKeyManager: React.FC = () => {
  const { session } = useAuth();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [newKey, setNewKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    if (!session?.access_token) return;
    setLoading(true);
    try {
      const headers: Record<string, string> = {};
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }
      const res = await fetch('/api/v1/admin/api-keys', { headers });
      if (res.ok) {
        const data = await res.json();
        setKeys(data.api_keys || []);
      }
    } catch (err) {
      console.error('Failed to fetch API keys', err);
    } finally {
      setLoading(false);
    }
  }, [session?.access_token]);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  const handleAddKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey.trim()) return;
    setError(null);
    setLoading(true);

    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }
      const res = await fetch('/api/v1/admin/api-keys', {
        method: 'POST',
        headers,
        body: JSON.stringify({ key_value: newKey.trim(), service: 'gemini' }),
      });
      if (res.ok) {
        setNewKey('');
        fetchKeys();
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || 'Failed to add API key');
      }
    } catch {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteKey = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this API Key?")) return;
    setLoading(true);
    try {
      const headers: Record<string, string> = {};
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }
      const res = await fetch(`/api/v1/admin/api-keys/${id}`, { method: 'DELETE', headers });
      if (res.ok) {
        fetchKeys();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const activeCount = keys.filter((k) => k.status === 'active').length;

  return (
    <Surface3D as="section" aria-labelledby="api-keys-title">
      <div className={a.panelHead}>
        <div className={a.panelTitleBlock}>
          <span className="icon-well tone-success" aria-hidden="true">
            <RiKey2Line size={20} />
          </span>
          <div>
            <span className="section-eyebrow">Key rotation</span>
            <div className={a.panelTitleRow}>
              <h2 id="api-keys-title" className={a.panelTitle}>Gemini API Key Rotation Manager</h2>
              <span className={`chip chip--sm ${activeCount > 0 ? 'chip--success chip--dot' : 'chip--neutral'}`}>
                {activeCount} active
              </span>
            </div>
            <p className={a.panelSub}>
              Add multiple Gemini API keys to automatically rotate them if one hits a 429 Too Many Requests limit.
            </p>
          </div>
        </div>
        <button type="button" onClick={fetchKeys} className="btn btn-secondary btn-sm" disabled={loading}>
          <RiRefreshLine size={14} className={loading ? 'pulse' : ''} /> Refresh
        </button>
      </div>

      <div className={a.panelBody}>
        {error && (
          <div className={`${a.notice} ${a.noticeDanger}`} role="alert">
            <RiErrorWarningFill size={18} />
            {error}
          </div>
        )}

        <form onSubmit={handleAddKey} className={`surface-inset ${a.inset}`}>
          <div className={a.fieldGroup}>
            <label htmlFor="admin-new-gemini-key" className={a.fieldLabel}>
              <RiAddLine size={14} /> Add a Gemini key to the pool
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
              <input
                id="admin-new-gemini-key"
                type="password"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                placeholder="Paste new Gemini API Key here (AIzaSy...)"
                autoComplete="off"
                className={`${a.field} ${a.mono}`}
                style={{ flex: '1 1 260px' }}
              />
              <button type="submit" disabled={loading || !newKey.trim()} className="btn btn-primary">
                <RiAddLine size={16} /> Add Key
              </button>
            </div>
          </div>
        </form>

        <div className="table-3d-wrap">
          <table className="table-3d">
            <thead>
              <tr>
                <th>Key (Masked)</th>
                <th>Status</th>
                <th>Added At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {keys.length === 0 ? (
                <tr>
                  <td colSpan={4}>
                    <EmptyState3D
                      compact
                      accent="success"
                      icon={<RiKey2Line size={16} />}
                      title="No API keys configured"
                      description="The engine is using the fallback key from .env until you add one here."
                    />
                  </td>
                </tr>
              ) : (
                keys.map(key => (
                  <tr key={key.id}>
                    <td className={`${a.mono} ${a.titleCell}`}>{key.key_value}</td>
                    <td>
                      <div className={a.rowActions}>
                        <span className={`chip chip--sm ${key.status === 'active' ? 'chip--success chip--dot' : 'chip--danger chip--dot'}`}>
                          {key.status.toUpperCase()}
                        </span>
                        {key.rate_limit_reset_at && (
                          <span className={a.metaCell}>
                            Resets {new Date(key.rate_limit_reset_at).toLocaleTimeString()}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className={a.metaCell}>{new Date(key.created_at!).toLocaleString()}</td>
                    <td>
                      <button type="button" onClick={() => handleDeleteKey(key.id)} className="btn btn-danger btn-sm">
                        <RiDeleteBinLine size={14} />
                        <span className="sr-only">Delete key</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Surface3D>
  );
};
