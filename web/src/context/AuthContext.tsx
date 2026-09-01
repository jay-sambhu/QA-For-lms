"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';
import { createClient, type Session } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const supabase =
  supabaseUrl && supabaseAnonKey ? createClient(supabaseUrl, supabaseAnonKey) : null;

interface AuthContextType {
  session: Session | null;
  sessionLoaded: boolean;
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
}

const AuthContext = createContext<AuthContextType>({
  session: null,
  sessionLoaded: false,
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
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(null);
  const [sessionLoaded, setSessionLoaded] = useState(!supabase);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin');
  const [userPlan, setUserPlan] = useState<string>('free');
  const [userRole, setUserRole] = useState<string>('user');

  const checkUserRoleAndPlan = (s: Session | null) => {
    if (!s || !s.user) {
      setUserPlan('free');
      setUserRole('user');
      return;
    }
    const email = (s.user.email || '').toLowerCase();
    const appRole = s.user.app_metadata?.role || s.user.user_metadata?.role;
    
    // Check if admin role
    if (appRole === 'admin' || email.startsWith('admin@') || email.includes('admin') || email.endsWith('@admin.jasuss.io')) {
      setUserRole('admin');
    } else {
      setUserRole('user');
    }
  };

  const fetchUserSubscription = async (accessToken?: string, currentSession?: Session | null) => {
    checkUserRoleAndPlan(currentSession || session);
    if (!accessToken) return;
    try {
      const res = await fetch('/api/v1/billing/subscription', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUserPlan(data?.plan?.id || 'free');
      }
    } catch {
      // fallback default
    }
  };

  useEffect(() => {
    if (!supabase) {
      setSessionLoaded(true);
      return;
    }

    supabase.auth
      .getSession()
      .then(({ data, error }) => {
        if (!error && data.session) {
          setSession(data.session);
          fetchUserSubscription(data.session.access_token, data.session);
        }
      })
      .finally(() => {
        setSessionLoaded(true);
      });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      if (nextSession) {
        fetchUserSubscription(nextSession.access_token, nextSession);
      } else {
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
    if (supabase) {
      await supabase.auth.signOut();
    }
    setSession(null);
    setUserPlan('free');
    setUserRole('user');
    setProfileModalOpen(false);
  };

  const refreshPlan = async () => {
    if (session?.access_token) {
      await fetchUserSubscription(session.access_token, session);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        session,
        sessionLoaded,
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
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
