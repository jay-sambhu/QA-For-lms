"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RiShieldFlashFill,
  RiCloseLine,
  RiLoginCircleLine,
  RiUserAddLine,
  RiMailLine,
  RiLockPasswordLine,
  RiCheckboxCircleFill,
  RiErrorWarningFill,
} from 'react-icons/ri';
import { TbLoader2 } from 'react-icons/tb';
import { useAuth, supabase } from '../../context/AuthContext';
import styles from '../../app/page.module.css';

export const AuthModal: React.FC = () => {
  const { authModalOpen, authMode, closeAuthModal, openAuthModal } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  if (!authModalOpen) return null;

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supabase) {
      setError('Authentication service is not configured.');
      return;
    }
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (signInError) throw signInError;
      closeAuthModal();
      setEmail('');
      setPassword('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supabase) {
      setError('Authentication service is not configured.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password,
      });
      if (signUpError) throw signUpError;
      if (data.session) {
        closeAuthModal();
        setEmail('');
        setPassword('');
        setConfirmPassword('');
      } else {
        setSuccess('Account created! Check your email to confirm and sign in.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        className={styles.modalOverlay}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={closeAuthModal}
      >
        <motion.div
          className={styles.modalCard}
          initial={{ scale: 0.95, y: 15, opacity: 0 }}
          animate={{ scale: 1, y: 0, opacity: 1 }}
          exit={{ scale: 0.95, y: 15, opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className={styles.modalHeader}>
            <div className={styles.modalLogo}>
              <RiShieldFlashFill size={22} color="#6366f1" />
              <span>JASUSS Workspace</span>
            </div>
            <button
              type="button"
              onClick={closeAuthModal}
              className={styles.modalCloseBtn}
              title="Close"
            >
              <RiCloseLine size={20} />
            </button>
          </div>

          <div className={styles.modalTabs}>
            <button
              type="button"
              onClick={() => {
                openAuthModal('signin');
                setError('');
                setSuccess('');
              }}
              className={`${styles.modalTab} ${authMode === 'signin' ? styles.modalTabActive : ''}`}
            >
              <RiLoginCircleLine size={16} style={{ display: 'inline', marginRight: '5px' }} />
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                openAuthModal('signup');
                setError('');
                setSuccess('');
              }}
              className={`${styles.modalTab} ${authMode === 'signup' ? styles.modalTabActive : ''}`}
            >
              <RiUserAddLine size={16} style={{ display: 'inline', marginRight: '5px' }} />
              Get Started
            </button>
          </div>

          <form
            onSubmit={authMode === 'signin' ? handleSignIn : handleSignUp}
            className={styles.modalBody}
          >
            {error && (
              <div className={`${styles.authBanner} ${styles.authBannerError}`}>
                <RiErrorWarningFill size={18} />
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div className={`${styles.authBanner} ${styles.authBannerSuccess}`}>
                <RiCheckboxCircleFill size={18} />
                <span>{success}</span>
              </div>
            )}

            <div className={styles.modalFormGroup}>
              <label className={styles.modalFormLabel}>
                <RiMailLine size={14} style={{ display: 'inline', marginRight: '4px' }} /> Email Address
              </label>
              <input
                type="email"
                required
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={styles.modalInput}
                autoComplete="email"
              />
            </div>

            <div className={styles.modalFormGroup}>
              <label className={styles.modalFormLabel}>
                <RiLockPasswordLine size={14} style={{ display: 'inline', marginRight: '4px' }} /> Password
              </label>
              <input
                type="password"
                required
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={styles.modalInput}
                autoComplete={authMode === 'signin' ? 'current-password' : 'new-password'}
              />
            </div>

            {authMode === 'signup' && (
              <div className={styles.modalFormGroup}>
                <label className={styles.modalFormLabel}>
                  <RiLockPasswordLine size={14} style={{ display: 'inline', marginRight: '4px' }} /> Confirm Password
                </label>
                <input
                  type="password"
                  required
                  placeholder="••••••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className={styles.modalInput}
                  autoComplete="new-password"
                />
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className={styles.modalSubmitBtn}
            >
              {loading ? (
                <>
                  <TbLoader2 size={18} className="pulse" />
                  <span>{authMode === 'signin' ? 'Signing In...' : 'Creating Account...'}</span>
                </>
              ) : (
                <>
                  {authMode === 'signin' ? <RiLoginCircleLine size={18} /> : <RiUserAddLine size={18} />}
                  <span>{authMode === 'signin' ? 'Sign In to Workspace' : 'Create JASUSS Account'}</span>
                </>
              )}
            </button>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};
