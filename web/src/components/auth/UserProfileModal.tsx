"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RiUser3Fill,
  RiCloseLine,
  RiShieldUserLine,
  RiLogoutBoxRLine,
  RiMailLine,
  RiKey2Line,
  RiSettings4Line,
  RiCheckboxCircleFill,
  RiSparklingLine,
} from 'react-icons/ri';
import { TbCreditCard, TbDeviceDesktop, TbBell, TbCopy, TbCheck } from 'react-icons/tb';
import { useAuth } from '../../context/AuthContext';
import styles from '../../app/page.module.css';

export const UserProfileModal: React.FC = () => {
  const { session, userPlan, userRole, profileModalOpen, closeProfileModal, signOut } = useAuth();
  const [copiedId, setCopiedId] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [defaultViewport, setDefaultViewport] = useState('all');

  if (!profileModalOpen || !session) return null;

  const email = session.user?.email || 'User';
  const userId = session.user?.id || 'usr_anonymous';
  const avatarChar = email[0].toUpperCase();

  const handleCopyId = () => {
    navigator.clipboard.writeText(userId);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  return (
    <AnimatePresence>
      <motion.div
        className={styles.modalOverlay}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={closeProfileModal}
      >
        <motion.div
          className={styles.modalCard}
          style={{ maxWidth: '480px' }}
          initial={{ scale: 0.95, y: 15, opacity: 0 }}
          animate={{ scale: 1, y: 0, opacity: 1 }}
          exit={{ scale: 0.95, y: 15, opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className={styles.modalHeader}>
            <div className={styles.modalLogo}>
              <RiUser3Fill size={20} color="#6366f1" />
              <span>User Profile & Account</span>
            </div>
            <button
              type="button"
              onClick={closeProfileModal}
              className={styles.modalCloseBtn}
              title="Close"
            >
              <RiCloseLine size={20} />
            </button>
          </div>

          <div className={styles.modalBody} style={{ gap: '20px' }}>
            {/* User Identity Card */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '16px', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '14px' }}>
              <div style={{ width: '52px', height: '52px', borderRadius: '16px', background: 'linear-gradient(135deg, #6366f1, #a855f7)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.4rem', fontWeight: 800, color: '#fff', boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)' }}>
                {avatarChar}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc' }}>{email}</span>
                  <span
                    className={`${styles.tierPill} ${
                      userPlan === 'pro'
                        ? styles.tierPro
                        : userPlan === 'enterprise'
                        ? styles.tierEnterprise
                        : styles.tierFree
                    }`}
                  >
                    {userPlan.toUpperCase()}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: '#64748b' }}>
                  <span>ID: {userId.substring(0, 12)}...</span>
                  <button onClick={handleCopyId} style={{ color: copiedId ? '#10b981' : '#94a3b8', display: 'inline-flex', alignItems: 'center', gap: '3px' }} title="Copy User ID">
                    {copiedId ? <TbCheck size={12} /> : <TbCopy size={12} />}
                  </button>
                </div>
              </div>
            </div>

            {/* Subscription & Plan Status */}
            <div style={{ padding: '14px', background: 'rgba(99, 102, 241, 0.06)', border: '1px solid rgba(99, 102, 241, 0.2)', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#c7d2fe' }}>Current Subscription</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', textTransform: 'capitalize' }}>{userPlan} Tier</div>
              </div>
              <Link
                href="/pricing"
                onClick={closeProfileModal}
                className="btn btn-primary"
                style={{ padding: '7px 14px', fontSize: '0.82rem', borderRadius: '8px' }}
              >
                <TbCreditCard size={14} /> Upgrade Plan
              </Link>
            </div>

            {/* Account Settings */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748b' }}>
                Preferences
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <span style={{ fontSize: '0.88rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <TbBell size={16} color="#818cf8" /> Email Scan Reports
                </span>
                <input
                  type="checkbox"
                  checked={notificationsEnabled}
                  onChange={(e) => setNotificationsEnabled(e.target.checked)}
                  style={{ width: '16px', height: '16px', accentColor: '#6366f1' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <span style={{ fontSize: '0.88rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <TbDeviceDesktop size={16} color="#38bdf8" /> Default Testing Viewport
                </span>
                <select
                  value={defaultViewport}
                  onChange={(e) => setDefaultViewport(e.target.value)}
                  style={{ background: '#1e293b', color: '#f8fafc', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '6px', padding: '4px 8px', fontSize: '0.8rem' }}
                >
                  <option value="all">Desktop + Mobile + Tablet</option>
                  <option value="desktop">Desktop Only</option>
                  <option value="mobile">Mobile Only</option>
                </select>
              </div>
            </div>

            {/* Admin console link if admin role */}
            {userRole === 'admin' && (
              <Link
                href="/admin"
                onClick={closeProfileModal}
                style={{ padding: '10px 14px', background: 'rgba(168, 85, 247, 0.12)', border: '1px solid rgba(168, 85, 247, 0.3)', borderRadius: '10px', color: '#c084fc', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.88rem', fontWeight: 600 }}
              >
                <RiShieldUserLine size={16} /> Open Admin & Telemetry Console →
              </Link>
            )}

            {/* Log Out Button */}
            <button
              type="button"
              onClick={signOut}
              className="btn btn-secondary"
              style={{ padding: '10px 16px', color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.3)', background: 'rgba(239, 68, 68, 0.06)', width: '100%', marginTop: '4px' }}
            >
              <RiLogoutBoxRLine size={16} />
              <span>Log Out</span>
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};
