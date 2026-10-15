"use client";

import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { createClient, type Session } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const supabase =
  supabaseUrl && supabaseAnonKey ? createClient(supabaseUrl, supabaseAnonKey) : null;

export interface UserProfile {
  id: string;
  email: string;
  role: string;
  is_admin: boolean;
  plan_tier: string;
  has_gemini_key: boolean;
  dashboard_url: string;
}

interface AuthContextType {
  session: Session | null;
  sessionLoaded: boolean;
  /** True once the backend profile (role, plan) has been fetched for the current session. */
  roleLoaded: boolean;
  userProfile: UserProfile | null;
  isAdmin: boolean;
  authModalOpen: boolean;
  authMode: 'signin' | 'signup';
  userPlan: string;
  userRole: string;
  profileModalOpen: boolean;
  openAuthModal: (mode?: 'signin' | 'signup') => void;
  closeAuthModal: () => void;
  openProfileModal: () => void;
  closeProfileModal: () => void;
  signOut: () => Promise<void>;
  refreshPlan: () => Promise<void>;
  fetchUserProfile: (token?: string) => Promise<UserProfile | null>;
}

const AuthContext = createContext<AuthContextType>({
  session: null,
  sessionLoaded: false,
  roleLoaded: false,
  userProfile: null,
  isAdmin: false,
  authModalOpen: false,
  authMode: 'signin',
  userPlan: 'free',
  userRole: 'user',
  profileModalOpen: false,
  openAuthModal: () => {},
  closeAuthModal: () => {},
  openProfileModal: () => {},
  closeProfileModal: () => {},
  signOut: async () => {},
  refreshPlan: async () => {},
  fetchUserProfile: async () => null,
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(null);
  const [sessionLoaded, setSessionLoaded] = useState(!supabase);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin');
  const [userPlan, setUserPlan] = useState<string>('free');
  const [userRole, setUserRole] = useState<string>('user');
  // Pages that gate on the role (admin console) must wait for this instead of
  // acting on the default 'user' role while /api/v1/auth/me is still in flight.
  const [roleLoaded, setRoleLoaded] = useState(false);

  const isAdmin = userRole === 'admin' || userProfile?.is_admin === true;

  // Always read the latest session inside async callbacks (avoids stale closures
  // from the mount-time effect and the onAuthStateChange subscription).
  // Updated wherever setSession is called.
  const sessionRef = useRef<Session | null>(null);

  const fetchUserProfile = useCallback(async (accessToken?: string): Promise<UserProfile | null> => {
    const token = accessToken || sessionRef.current?.access_token;
    if (!token) {
      setUserProfile(null);
      setUserRole('user');
      setUserPlan('free');
      setRoleLoaded(true);
      return null;
    }

    const startUserId = sessionRef.current?.user?.id;
    setRoleLoaded(false);
    try {
      const res = await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      // Ignore late responses if the user changed meanwhile (e.g. signed out / switched account)
      if (sessionRef.current?.user?.id !== startUserId) return null;
      if (res.ok) {
        const data: UserProfile = await res.json();
        setUserProfile(data);
        setUserRole(data.role || (data.is_admin ? 'admin' : 'user'));
        setUserPlan(data.plan_tier || 'free');
        setRoleLoaded(true);
        return data;
      }
    } catch (e) {
      console.warn('Backend user profile check failed, using fallback:', e);
    }

    // Safety fallback if backend is momentarily unreachable. Only trust app_metadata
    // (server-controlled); user_metadata is editable by the user. The backend still
    // enforces admin access on every /api/v1/admin/* call.
    const current = sessionRef.current;
    if (current?.user && current.user.id === startUserId) {
      const email = (current.user.email || '').toLowerCase();
      const appRole = current.user.app_metadata?.role;
      setUserRole(appRole === 'admin' || email === 'dellizulter@gmail.com' ? 'admin' : 'user');
    }
    setRoleLoaded(true);
    return null;
  }, []);

  const refreshPlan = useCallback(async () => {
    if (sessionRef.current?.access_token) {
      await fetchUserProfile(sessionRef.current.access_token);
    }
  }, [fetchUserProfile]);

  useEffect(() => {
    if (!supabase) {
      setSessionLoaded(true);
      return;
    }

    let lastProfileToken: string | null = null;
    const loadProfileFor = (next: Session) => {
      // getSession() and the INITIAL_SESSION event both deliver the same token; fetch once.
      if (lastProfileToken === next.access_token) return;
      lastProfileToken = next.access_token;
      void fetchUserProfile(next.access_token);
    };

    supabase.auth
      .getSession()
      .then(({ data, error }) => {
        if (!error && data.session) {
          sessionRef.current = data.session;
          setSession(data.session);
          loadProfileFor(data.session);
        }
      })
      .finally(() => {
        setSessionLoaded(true);
      });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, nextSession) => {
      sessionRef.current = nextSession;
      setSession(nextSession);
      if (nextSession) {
        // Token refreshes don't change the user's plan/role — skip the extra /auth/me round trip
        if (event !== 'TOKEN_REFRESHED') loadProfileFor(nextSession);
      } else {
        lastProfileToken = null;
        setUserProfile(null);
        setUserPlan('free');
        setUserRole('user');
      }
    });

    return () => subscription.unsubscribe();
  }, [fetchUserProfile]);

  const openAuthModal = (mode: 'signin' | 'signup' = 'signin') => {
    setAuthMode(mode);
    setAuthModalOpen(true);
  };

  const closeAuthModal = () => {
    setAuthModalOpen(false);
  };

  const openProfileModal = () => {
    setProfileModalOpen(true);
  };

  const closeProfileModal = () => {
    setProfileModalOpen(false);
  };

  const signOut = async () => {
    try {
      if (supabase) {
        await supabase.auth.signOut();
      }
    } catch (e) {
      console.error('Error during signOut:', e);
    }
    if (typeof window !== 'undefined') {
      localStorage.removeItem('jasuss_session');
    }
    sessionRef.current = null;
    setSession(null);
    setUserProfile(null);
    setUserPlan('free');
    setUserRole('user');
    setProfileModalOpen(false);
    setAuthModalOpen(false);
    if (typeof window !== 'undefined') {
      // Intentional full reload: guarantees every component's in-memory user data is dropped.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = '/';
    }
  };

  return (
    <AuthContext.Provider
      value={{
        session,
        sessionLoaded,
        roleLoaded,
        userProfile,
        isAdmin,
        authModalOpen,
        authMode,
        userPlan,
        userRole,
        profileModalOpen,
        openAuthModal,
        closeAuthModal,
        openProfileModal,
        closeProfileModal,
        signOut,
        refreshPlan,
        fetchUserProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
