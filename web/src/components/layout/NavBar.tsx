"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  RiHome5Line,
  RiShieldUserLine,
  RiShieldUserFill,
  RiLoginCircleLine,
  RiUser3Line,
  RiArticleLine,
  RiMenu3Line,
  RiCloseLine,
  RiLogoutBoxRLine,
} from 'react-icons/ri';
import { TbDashboard, TbCreditCard } from 'react-icons/tb';
import { HiSparkles } from 'react-icons/hi2';
import { useAuth } from '../../context/AuthContext';
import styles from '../../app/page.module.css';

export const NavBar: React.FC = () => {
  const pathname = usePathname();
  const { session, userPlan, userRole, isAdmin: authIsAdmin, openAuthModal, openProfileModal, signOut } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const userIsAdmin = authIsAdmin || userRole === 'admin';

  const isHome = pathname === '/';
  const isDashboard = pathname.startsWith('/dashboard');
  const isPricing = pathname === '/pricing';
  const isBlog = pathname.startsWith('/blog');
  const isAdmin = pathname === '/admin';

  // Automatically close mobile menu whenever route changes
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  return (
    <header className={styles.header} style={{ position: 'relative', zIndex: 100 }}>
      {/* Brand Logo */}
      <Link href="/" className={styles.logo} onClick={() => setMobileMenuOpen(false)}>
        <div className={styles.logoIconWrapper} style={{ overflow: 'hidden', padding: 0 }}>
          <img
            src="/logo.png"
            alt="JASUSS.TECH"
            width={38}
            height={38}
            style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '10px' }}
          />
        </div>
        <div>
          <span>JASUSS</span>
          <span className={styles.logoSub}>.TECH</span>
        </div>
      </Link>

      {/* Desktop Navigation Links */}
      <nav className={styles.headerRight} aria-label="Main Navigation">
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

        <Link
          href="/blog"
          className={`${styles.navLink} ${isBlog ? styles.navLinkActive : ''}`}
        >
          <RiArticleLine size={17} />
          <span>Blog</span>
        </Link>

        {/* Admin Link ONLY visible if user has admin role */}
        {userIsAdmin && (
          <Link
            href="/admin"
            className={`${styles.navLink} ${isAdmin ? styles.navLinkActive : ''}`}
            style={{ color: '#c084fc' }}
          >
            <RiShieldUserFill size={17} />
            <span>Admin</span>
          </Link>
        )}

        <div className={styles.engineStatusPill}>
          <div className={styles.engineStatusDot} />
          <span>Engine Online</span>
        </div>

        {session ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Quick direct dashboard navigation pill */}
            {userIsAdmin ? (
              <Link
                href="/admin"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 14px',
                  borderRadius: '10px',
                  background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.25), rgba(99, 102, 241, 0.25))',
                  border: '1px solid rgba(168, 85, 247, 0.45)',
                  color: '#e9d5ff',
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  boxShadow: '0 0 16px rgba(168, 85, 247, 0.25)',
                  transition: 'all 0.2s ease',
                  textDecoration: 'none',
                }}
              >
                <RiShieldUserFill size={15} color="#c084fc" />
                <span>Admin Console</span>
              </Link>
            ) : (
              <Link
                href="/dashboard"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 14px',
                  borderRadius: '10px',
                  background: 'rgba(99, 102, 241, 0.15)',
                  border: '1px solid rgba(99, 102, 241, 0.35)',
                  color: '#818cf8',
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  transition: 'all 0.2s ease',
                  textDecoration: 'none',
                }}
              >
                <TbDashboard size={15} color="#818cf8" />
                <span>My Dashboard</span>
              </Link>
            )}

            <button
              onClick={openProfileModal}
              className={styles.userBadge}
              style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
              title="Click to view Account & Settings"
            >
              <div className={styles.userAvatar}>
                {session.user?.email ? session.user.email[0].toUpperCase() : <RiUser3Line size={14} />}
              </div>
              <span
                className={`${styles.tierPill} ${
                  userIsAdmin
                    ? styles.tierEnterprise
                    : userPlan === 'pro'
                    ? styles.tierPro
                    : userPlan === 'enterprise'
                    ? styles.tierEnterprise
                    : styles.tierFree
                }`}
                style={
                  userIsAdmin
                    ? {
                        background: 'rgba(168, 85, 247, 0.2)',
                        color: '#c084fc',
                        border: '1px solid rgba(168, 85, 247, 0.4)',
                        fontWeight: 800,
                      }
                    : undefined
                }
              >
                {userIsAdmin ? 'ADMIN' : userPlan.toUpperCase()}
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
      </nav>

      {/* Mobile & Tablet Controls (Right aligned on <= 900px) */}
      <div className={styles.mobileHeaderControls}>
        {session ? (
          <button
            onClick={openProfileModal}
            className={styles.userBadge}
            style={{ cursor: 'pointer', padding: '4px 8px' }}
            title="Profile"
          >
            <div className={styles.userAvatar} style={{ width: 26, height: 26, fontSize: '0.75rem' }}>
              {session.user?.email ? session.user.email[0].toUpperCase() : <RiUser3Line size={13} />}
            </div>
            <span
              className={`${styles.tierPill} ${
                userIsAdmin
                  ? styles.tierEnterprise
                  : userPlan === 'pro'
                  ? styles.tierPro
                  : userPlan === 'enterprise'
                  ? styles.tierEnterprise
                  : styles.tierFree
              }`}
              style={{
                fontSize: '0.65rem',
                padding: '1px 6px',
                background: userIsAdmin ? 'rgba(168, 85, 247, 0.2)' : undefined,
                color: userIsAdmin ? '#c084fc' : undefined,
                border: userIsAdmin ? '1px solid rgba(168, 85, 247, 0.4)' : undefined,
                fontWeight: 800,
              }}
            >
              {userIsAdmin ? 'ADMIN' : userPlan.toUpperCase()}
            </span>
          </button>
        ) : (
          <button
            onClick={() => openAuthModal('signin')}
            className={styles.mobileSignInBtn}
          >
            Sign In
          </button>
        )}

        {/* Hamburger Toggle Button */}
        <button
          onClick={() => setMobileMenuOpen((prev) => !prev)}
          className={styles.mobileMenuToggle}
          aria-label={mobileMenuOpen ? 'Close Navigation Menu' : 'Open Navigation Menu'}
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? <RiCloseLine size={24} /> : <RiMenu3Line size={24} />}
        </button>
      </div>

      {/* Mobile & Tablet Dropdown Drawer */}
      {mobileMenuOpen && (
        <div className={styles.mobileNavDrawer}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <Link
              href="/"
              onClick={() => setMobileMenuOpen(false)}
              className={`${styles.mobileNavLink} ${isHome ? styles.mobileNavLinkActive : ''}`}
            >
              <RiHome5Line size={18} />
              <span>Home</span>
            </Link>

            <Link
              href="/dashboard"
              onClick={() => setMobileMenuOpen(false)}
              className={`${styles.mobileNavLink} ${isDashboard ? styles.mobileNavLinkActive : ''}`}
            >
              <TbDashboard size={18} />
              <span>Dashboard</span>
            </Link>

            <Link
              href="/pricing"
              onClick={() => setMobileMenuOpen(false)}
              className={`${styles.mobileNavLink} ${isPricing ? styles.mobileNavLinkActive : ''}`}
            >
              <TbCreditCard size={18} />
              <span>Pricing &amp; Plans</span>
            </Link>

            <Link
              href="/blog"
              onClick={() => setMobileMenuOpen(false)}
              className={`${styles.mobileNavLink} ${isBlog ? styles.mobileNavLinkActive : ''}`}
            >
              <RiArticleLine size={18} />
              <span>Engineering Blog</span>
            </Link>

            {userIsAdmin && (
              <Link
                href="/admin"
                onClick={() => setMobileMenuOpen(false)}
                className={`${styles.mobileNavLink} ${isAdmin ? styles.mobileNavLinkActive : ''}`}
                style={{ color: '#c084fc' }}
              >
                <RiShieldUserFill size={18} />
                <span>Admin Console</span>
              </Link>
            )}
          </div>

          <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
            <div className={styles.engineStatusPill} style={{ width: '100%', justifyContent: 'center', marginBottom: '12px' }}>
              <div className={styles.engineStatusDot} />
              <span>Nexus Engine Online · 99.9%</span>
            </div>

            {session ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    openProfileModal();
                  }}
                  className="btn btn-secondary"
                  style={{ width: '100%', justifyContent: 'center', fontSize: '0.85rem' }}
                >
                  <RiUser3Line size={16} />
                  <span>Account &amp; API Key</span>
                </button>
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    signOut();
                  }}
                  className="btn btn-secondary"
                  style={{
                    width: '100%',
                    justifyContent: 'center',
                    fontSize: '0.85rem',
                    color: '#f87171',
                    borderColor: 'rgba(239, 68, 68, 0.3)',
                    background: 'rgba(239, 68, 68, 0.06)',
                  }}
                >
                  <RiLogoutBoxRLine size={16} />
                  <span>Log Out</span>
                </button>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    openAuthModal('signin');
                  }}
                  className={styles.headerSignInBtn}
                  style={{ width: '100%', justifyContent: 'center' }}
                >
                  <RiLoginCircleLine size={16} />
                  <span>Sign In</span>
                </button>
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    openAuthModal('signup');
                  }}
                  className={styles.headerGetStartedBtn}
                  style={{ width: '100%', justifyContent: 'center' }}
                >
                  <HiSparkles size={16} />
                  <span>Get Started</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
