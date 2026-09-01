"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  RiShieldFlashFill,
  RiHome5Line,
  RiShieldUserLine,
  RiLoginCircleLine,
  RiUser3Line,
} from 'react-icons/ri';
import { TbDashboard, TbCreditCard } from 'react-icons/tb';
import { HiSparkles } from 'react-icons/hi2';
import { useAuth } from '../../context/AuthContext';
import styles from '../../app/page.module.css';

export const NavBar: React.FC = () => {
  const pathname = usePathname();
  const { session, userPlan, userRole, openAuthModal, openProfileModal } = useAuth();

  const isHome = pathname === '/';
  const isDashboard = pathname.startsWith('/dashboard');
  const isPricing = pathname === '/pricing';
  const isAdmin = pathname === '/admin';

  return (
    <header className={styles.header}>
      <Link href="/" className={styles.logo}>
        <div className={styles.logoIconWrapper}>
          <RiShieldFlashFill size={24} color="#ffffff" />
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
          <RiHome5Line size={17} />
          <span>Home</span>
        </Link>

        <Link
          href="/dashboard"
          className={`${styles.navLink} ${isDashboard ? styles.navLinkActive : ''}`}
        >
          <TbDashboard size={17} />
          <span>Dashboard</span>
        </Link>

        <Link
          href="/pricing"
          className={`${styles.navLink} ${isPricing ? styles.navLinkActive : ''}`}
        >
          <TbCreditCard size={17} />
          <span>Pricing</span>
        </Link>

        {/* Admin Link ONLY visible if user has admin role */}
        {userRole === 'admin' && (
          <Link
            href="/admin"
            className={`${styles.navLink} ${isAdmin ? styles.navLinkActive : ''}`}
          >
            <RiShieldUserLine size={17} />
            <span>Admin</span>
          </Link>
        )}

        <div className={styles.engineStatusPill}>
          <div className={styles.engineStatusDot} />
          <span>Engine Online</span>
        </div>

        {session ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {/* Clickable User Avatar Button - opens profile & settings */}
            <button
              onClick={openProfileModal}
              className={styles.userBadge}
              style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
              title="Click to view Profile & Settings"
            >
              <div className={styles.userAvatar}>
                {session.user?.email ? session.user.email[0].toUpperCase() : <RiUser3Line size={14} />}
              </div>
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
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={() => openAuthModal('signin')}
              className={styles.headerSignInBtn}
            >
              <RiLoginCircleLine size={16} />
              <span>Sign In</span>
            </button>
            <button
              onClick={() => openAuthModal('signup')}
              className={styles.headerGetStartedBtn}
            >
              <HiSparkles size={16} />
              <span>Get Started</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
