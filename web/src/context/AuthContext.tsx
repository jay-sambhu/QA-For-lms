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
  openAuthModal: (mode?: 'signin' | 'signup') => void;
  closeAuthModal: () => void;
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
  openAuthModal: () => {},
  closeAuthModal: () => {},
  signOut: async () => {},
  refreshPlan: async () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(null);
  const [sessionLoaded, setSessionLoaded] = useState(!supabase);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin');
  const [userPlan, setUserPlan] = useState<string>('free');
  const [userRole, setUserRole] = useState<string>('user');

  const fetchUserSubscription = async (accessToken?: string) => {
    if (!accessToken) {
      setUserPlan('free');
      setUserRole('user');
      return;
    }
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
          fetchUserSubscription(data.session.access_token);
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
        fetchUserSubscription(nextSession.access_token);
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

  const signOut = async () => {
    if (supabase) {
      await supabase.auth.signOut();
    }
    setSession(null);
    setUserPlan('free');
    setUserRole('user');
  };

  const refreshPlan = async () => {
    if (session?.access_token) {
      await fetchUserSubscription(session.access_token);
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
        openAuthModal,
        closeAuthModal,
        signOut,
        refreshPlan,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
