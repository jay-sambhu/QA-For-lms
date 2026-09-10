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
  RiGoogleFill,
  RiGithubFill,
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

  const handleGoogleSignIn = async () => {
    if (!supabase) {
      setError('Authentication service is not configured.');
      return;
    }
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    if (!clientId) {
      setError('Google Client ID is not configured. Set NEXT_PUBLIC_GOOGLE_CLIENT_ID in your .env.local file.');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      // Use Google Identity Services (GIS) popup flow
      const google = (window as unknown as Record<string, unknown>).google as {
        accounts: {
          oauth2: {
            initCodeClient: (config: {
              client_id: string;
              scope: string;
              ux_mode: string;
              callback: (response: { code?: string; error?: string }) => void;
            }) => { requestCode: () => void };
          };
          id: {
            initialize: (config: {
              client_id: string;
              callback: (response: { credential?: string; error?: string }) => void;
            }) => void;
            prompt: (notification?: (n: { isNotDisplayed: () => boolean; isSkippedMoment: () => boolean }) => void) => void;
          };
        };
      };

      if (!google?.accounts?.id) {
        setError('Google Sign-In SDK not loaded. Please refresh the page and try again.');
        setLoading(false);
        return;
      }

      // Use One Tap / popup to get an ID token, then pass it to Supabase
      google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response: { credential?: string; error?: string }) => {
          if (response.error || !response.credential) {
            setError('Google sign-in was cancelled or failed.');
            setLoading(false);
            return;
          }

          try {
            const { error: supabaseError } = await supabase!.auth.signInWithIdToken({
              provider: 'google',
              token: response.credential,
            });

            if (supabaseError) {
              setError(`Google authentication failed: ${supabaseError.message}`);
            } else {
              closeAuthModal();
              setEmail('');
              setPassword('');
            }
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Google sign-in failed.');
          } finally {
            setLoading(false);
          }
        },
      });

      google.accounts.id.prompt((notification) => {
        // If One Tap is not displayed (e.g. user dismissed it before), fall back to a popup
        if (notification?.isNotDisplayed() || notification?.isSkippedMoment()) {
          // Fall back to the OAuth2 code flow via popup
          const codeClient = google.accounts.oauth2.initCodeClient({
            client_id: clientId,
            scope: 'email profile openid',
            ux_mode: 'popup',
            callback: async (codeResponse: { code?: string; error?: string }) => {
              if (codeResponse.error || !codeResponse.code) {
                setError('Google sign-in was cancelled.');
                setLoading(false);
                return;
              }
              // For the code flow, we need to exchange the code server-side.
              // Instead, let's use the redirect-based signInWithOAuth as ultimate fallback.
              const { error: oauthError } = await supabase!.auth.signInWithOAuth({
                provider: 'google',
                options: {
                  redirectTo: typeof window !== 'undefined' ? `${window.location.origin}/auth/callback` : undefined,
                },
              });
              if (oauthError) {
                setError('Google login redirect failed. Please ensure Google is configured in your Supabase dashboard as a fallback.');
              }
              setLoading(false);
            },
          });
          codeClient.requestCode();
        }
      });
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
      if (data.user && Array.isArray(data.user.identities) && data.user.identities.length === 0) {
        setError('An account with this email already exists. Please sign in instead.');
        return;
      }
      if (data.session) {
        closeAuthModal();
        setEmail('');
        setPassword('');
        setConfirmPassword('');
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

            {/* Social OAuth Sign In Options (Google & GitHub) */}
            <div className={styles.socialAuthContainer}>
              <button
                type="button"
                onClick={handleGoogleSignIn}
                disabled={loading}
                className={`${styles.socialAuthBtn} ${styles.socialAuthBtnGoogle}`}
              >
                <RiGoogleFill size={18} color="#ea4335" />
                <span>Google</span>
              </button>

              <button
                type="button"
                onClick={handleGitHubSignIn}
                disabled={loading}
                className={`${styles.socialAuthBtn} ${styles.socialAuthBtnGithub}`}
              >
                <RiGithubFill size={18} color="#ffffff" />
                <span>GitHub</span>
              </button>
            </div>

            <div className={styles.socialAuthDivider}>
              <span>or continue with email</span>
            </div>

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
