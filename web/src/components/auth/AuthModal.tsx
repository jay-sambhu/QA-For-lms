"use client";

import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { m as motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import {
  RiCloseLine,
  RiLoginCircleLine,
  RiUserAddLine,
  RiMailLine,
  RiLockPasswordLine,
  RiCheckboxCircleFill,
  RiErrorWarningFill,
  RiGoogleFill,
  RiGithubFill,
} from 'react-icons/ri';
import { TbLoader2 } from 'react-icons/tb';
import { useAuth, supabase } from '../../context/AuthContext';
import { SegmentedTabs3D } from '../three';
import s from './auth3d.module.css';

type AuthMode = 'signin' | 'signup';

export const AuthModal: React.FC = () => {
  const router = useRouter();
  const { authModalOpen, authMode, closeAuthModal, openAuthModal, fetchUserProfile } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const reduceMotion = useReducedMotion();

  const cardMotion = reduceMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 } }
    : {
        initial: { opacity: 0, y: 28, scale: 0.96, rotateX: 10 },
        animate: { opacity: 1, y: 0, scale: 1, rotateX: 0 },
        exit: { opacity: 0, y: 16, scale: 0.97, rotateX: 6 },
      };

  const switchMode = (mode: AuthMode) => {
    openAuthModal(mode);
    setError('');
    setSuccess('');
  };

  const handleGoogleSignIn = async () => {
    if (!supabase) {
      setError('Authentication service is not configured.');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const redirectOrigin = typeof window !== 'undefined' ? window.location.origin : '';
      const { error: oauthError } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${redirectOrigin}/auth/callback`,
        },
      });
      if (oauthError) {
        setError(oauthError.message || 'Google login failed. Please ensure Google provider is enabled in Supabase.');
        setLoading(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Google sign-in request failed.');
      setLoading(false);
    }
  };

  const handleGitHubSignIn = async () => {
    if (!supabase) {
      setError('Authentication service is not configured.');
      return;
    }
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const { error: oauthError } = await supabase.auth.signInWithOAuth({
        provider: 'github',
        options: {
          redirectTo: typeof window !== 'undefined' ? `${window.location.origin}/auth/callback` : undefined,
        },
      });

      if (oauthError) {
        setError('GitHub login is currently unavailable or unconfigured in Supabase console.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'GitHub login request failed.');
    } finally {
      setLoading(false);
    }
  };

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
      const { data: signInData, error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (signInError) throw signInError;
      closeAuthModal();
      setEmail('');
      setPassword('');

      let targetUrl = '/dashboard';
      if (signInData.session?.access_token) {
        const profile = await fetchUserProfile(signInData.session.access_token);
        if (profile?.is_admin || profile?.role === 'admin' || profile?.role === 'superuser') {
          targetUrl = '/admin';
        }
      }
      router.push(targetUrl);
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
      if (data.user && Array.isArray(data.user.identities) && data.user.identities.length === 0) {
        setError('An account with this email already exists. Please sign in instead.');
        return;
      }
      if (data.session) {
        closeAuthModal();
        setEmail('');
        setPassword('');
        setConfirmPassword('');
        const profile = await fetchUserProfile(data.session.access_token);
        router.push(profile?.is_admin || profile?.role === 'admin' ? '/admin' : '/dashboard');
      } else {
        setSuccess('Account created! Please check your email to confirm and sign in.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {authModalOpen && (
        <motion.div
          key="auth-modal-overlay"
          className={s.modalOverlay}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={closeAuthModal}
        >
          <motion.div
            className={`${s.modalCard} glass-3d`}
            role="dialog"
            aria-modal="true"
            aria-labelledby="auth-modal-title"
            style={{ transformPerspective: 1400, transformOrigin: '50% 0%' }}
            {...cardMotion}
            transition={{ duration: reduceMotion ? 0.15 : 0.45, ease: [0.16, 1, 0.3, 1] }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={s.modalHeader}>
              <div className={s.modalLogo} id="auth-modal-title">
                <img src="/logo-icon.png" alt="" width={28} height={28} className={s.modalLogoMark} />
                <span>JASUSS Workspace</span>
              </div>
              <button type="button" onClick={closeAuthModal} className={s.iconBtn} title="Close" aria-label="Close">
                <RiCloseLine size={20} />
              </button>
            </div>

            <div className={s.modalTabs}>
              <SegmentedTabs3D<AuthMode>
                fullWidth
                ariaLabel="Authentication mode"
                idPrefix="auth"
                tabs={[
                  { id: 'signin', label: 'Sign In', icon: <RiLoginCircleLine size={16} /> },
                  { id: 'signup', label: 'Get Started', icon: <RiUserAddLine size={16} /> },
                ]}
                active={authMode}
                onChange={switchMode}
              />
            </div>

            <form
              onSubmit={authMode === 'signin' ? handleSignIn : handleSignUp}
              className={s.modalBody}
              role="tabpanel"
              id={`auth-panel-${authMode}`}
              aria-labelledby={`auth-tab-${authMode}`}
            >
              {error && (
                <div className={`${s.notice} tone-danger`} role="alert">
                  <RiErrorWarningFill size={18} />
                  <span>{error}</span>
                </div>
              )}

              {success && (
                <div className={`${s.notice} tone-success`} role="status">
                  <RiCheckboxCircleFill size={18} />
                  <span>{success}</span>
                </div>
              )}

              {/* Social OAuth Sign In Options (Google & GitHub) */}
              <div className={s.socialGrid}>
                <button
                  type="button"
                  onClick={handleGoogleSignIn}
                  disabled={loading}
                  className={`btn btn-secondary ${s.socialGoogle}`}
                >
                  <RiGoogleFill size={18} color="#ea4335" />
                  <span>Google</span>
                </button>

                <button
                  type="button"
                  onClick={handleGitHubSignIn}
                  disabled={loading}
                  className={`btn btn-secondary ${s.socialGithub}`}
                >
                  <RiGithubFill size={18} />
                  <span>GitHub</span>
                </button>
              </div>

              <div className={s.socialDivider}>
                <span>or continue with email</span>
              </div>

              <div className={s.formGroup}>
                <label className={s.formLabel} htmlFor="auth-email">
                  <RiMailLine size={14} /> Email Address
                </label>
                <input
                  id="auth-email"
                  type="email"
                  required
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={s.field}
                  autoComplete="email"
                />
              </div>

              <div className={s.formGroup}>
                <label className={s.formLabel} htmlFor="auth-password">
                  <RiLockPasswordLine size={14} /> Password
                </label>
                <input
                  id="auth-password"
                  type="password"
                  required
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={s.field}
                  autoComplete={authMode === 'signin' ? 'current-password' : 'new-password'}
                />
              </div>

              {authMode === 'signup' && (
                <div className={s.formGroup}>
                  <label className={s.formLabel} htmlFor="auth-confirm-password">
                    <RiLockPasswordLine size={14} /> Confirm Password
                  </label>
                  <input
                    id="auth-confirm-password"
                    type="password"
                    required
                    placeholder="••••••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className={s.field}
                    autoComplete="new-password"
                  />
                </div>
              )}

              <button type="submit" disabled={loading} className={`btn btn-primary ${s.submitBtn}`}>
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
      )}
    </AnimatePresence>
  );
};
