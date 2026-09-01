"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  ShieldCheck,
  LayoutDashboard,
  CreditCard,
  Settings,
  LogOut,
  Sparkles,
  Home,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import styles from '../../app/page.module.css';

export const NavBar: React.FC = () => {
  const pathname = usePathname();
  const { session, userPlan, openAuthModal, signOut } = useAuth();

  const isHome = pathname === '/';
  const isDashboard = pathname.startsWith('/dashboard');
  const isPricing = pathname === '/pricing';
  const isAdmin = pathname === '/admin';

  return (
    <header className={styles.header}>
      <Link href="/" className={styles.logo}>
        <div className={styles.logoIconWrapper}>
          <ShieldCheck size={22} color="#ffffff" />
        </div>
        <div>
          <span>JASUSS</span>
          <span className={styles.logoSub}>Powered by Nexus</span>
        </div>
      </Link>

      <div className={styles.headerRight}>
        <Link
          href="/"
          className={`${styles.navLink} ${isHome ? styles.navLinkActive : ''}`}
        >
          <Home size={15} />
          <span>Home</span>
        </Link>

        <Link
          href="/dashboard"
          className={`${styles.navLink} ${isDashboard ? styles.navLinkActive : ''}`}
        >
          <LayoutDashboard size={15} />
          <span>Dashboard</span>
        </Link>

        <Link
          href="/pricing"
          className={`${styles.navLink} ${isPricing ? styles.navLinkActive : ''}`}
        >
          <CreditCard size={15} />
          <span>Pricing</span>
        </Link>

        <Link
          href="/admin"
          className={`${styles.navLink} ${isAdmin ? styles.navLinkActive : ''}`}
        >
          <Settings size={15} />
          <span>Admin</span>
        </Link>

        <div className={styles.engineStatusPill}>
          <div className={styles.engineStatusDot} />
          <span>Engine Online</span>
        </div>

        {session ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className={styles.userBadge}>
              <div className={styles.userAvatar}>
                {session.user?.email ? session.user.email[0].toUpperCase() : 'U'}
              </div>
              <span>{session.user?.email || 'User'}</span>
              <span
                className={`${styles.tierPill} ${
                  userPlan === 'pro'
                    ? styles.tierPro
                    : userPlan === 'enterprise'
                    ? styles.tierEnterprise
                    : styles.tierFree
                }`}
                style={{ marginLeft: '4px' }}
              >
                {userPlan.toUpperCase()}
              </span>
            </div>
            <button onClick={signOut} className={styles.signOutBtn} title="Sign Out">
              <LogOut size={16} />
              <span>Exit</span>
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => openAuthModal('signin')}
              className={styles.headerSignInBtn}
            >
              Sign In
            </button>
            <button
              onClick={() => openAuthModal('signup')}
              className={styles.headerGetStartedBtn}
            >
              <Sparkles size={15} />
              <span>Get Started</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
