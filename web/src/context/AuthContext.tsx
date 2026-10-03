"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';
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

  const isAdmin = userRole === 'admin' || userProfile?.is_admin === true;

  const fetchUserProfile = async (accessToken?: string): Promise<UserProfile | null> => {
    const token = accessToken || session?.access_token;
    if (!token) {
      setUserProfile(null);
      setUserRole('user');
      setUserPlan('free');
      return null;
    }

    try {
      const res = await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data: UserProfile = await res.json();
        setUserProfile(data);
        setUserRole(data.role || (data.is_admin ? 'admin' : 'user'));
        setUserPlan(data.plan_tier || 'free');
        return data;
      }
    } catch (e) {
      console.warn('Backend user profile check failed, using fallback:', e);
    }

    // Safety fallback if backend is momentarily unreachable
    if (session?.user) {
      const email = (session.user.email || '').toLowerCase();
      const appRole = session.user.app_metadata?.role || session.user.user_metadata?.role;
      const derivedRole =
        appRole === 'admin' ||
        email === 'dellizulter@gmail.com' ||
        email.startsWith('admin@') ||
        email.endsWith('@admin.jasuss.io')
          ? 'admin'
          : 'user';
      setUserRole(derivedRole);
    }
    return null;
  };

  const refreshPlan = async () => {
    if (session?.access_token) {
      await fetchUserProfile(session.access_token);
    }
  };

  useEffect(() => {
    if (!supabase) {
      setSessionLoaded(true);
      return;
    }

    supabase.auth
      .getSession()
      .then(async ({ data, error }) => {
        if (!error && data.session) {
          setSession(data.session);
          await fetchUserProfile(data.session.access_token);
        }
      })
      .finally(() => {
        setSessionLoaded(true);
      });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, nextSession) => {
      setSession(nextSession);
      if (nextSession) {
        await fetchUserProfile(nextSession.access_token);
      } else {
        setUserProfile(null);
        setUserPlan('free');
        setUserRole('user');
      }
    });

    return () => subscription.unsubscribe();
  }, []);

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
    setSession(null);
    setUserProfile(null);
    setUserPlan('free');
    setUserRole('user');
    setProfileModalOpen(false);
    setAuthModalOpen(false);
    if (typeof window !== 'undefined') {
      window.location.href = '/';
    }
  };

  return (
    <AuthContext.Provider
      value={{
        session,
        sessionLoaded,
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
