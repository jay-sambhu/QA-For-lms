"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  RiHome5Line,
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
import s from './shell3d.module.css';

const tierChipClass = (isAdmin: boolean, plan: string) => {
  if (isAdmin) return 'chip--violet';
  if (plan === 'pro') return 'chip--primary';
  if (plan === 'enterprise') return 'chip--warning';
  return 'chip--neutral';
};

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

  const navItems = [
    { href: '/', label: 'Home', mobileLabel: 'Home', Icon: RiHome5Line, active: isHome, admin: false },
    { href: '/dashboard', label: 'Dashboard', mobileLabel: 'Dashboard', Icon: TbDashboard, active: isDashboard, admin: false },
    { href: '/pricing', label: 'Pricing', mobileLabel: 'Pricing & Plans', Icon: TbCreditCard, active: isPricing, admin: false },
    { href: '/blog', label: 'Blog', mobileLabel: 'Engineering Blog', Icon: RiArticleLine, active: isBlog, admin: false },
    ...(userIsAdmin
      ? [{ href: '/admin', label: 'Admin', mobileLabel: 'Admin Console', Icon: RiShieldUserFill, active: isAdmin, admin: true }]
      : []),
  ];

  const avatarChar = session?.user?.email ? session.user.email[0].toUpperCase() : null;
  const tierLabel = userIsAdmin ? 'ADMIN' : userPlan.toUpperCase();
  const tierChip = tierChipClass(userIsAdmin, userPlan);

  return (
    <header className={`${s.header} glass-3d`}>
      {/* Brand Logo */}
      <Link href="/" className={s.logo} onClick={() => setMobileMenuOpen(false)} aria-label="JASUSS.TECH home">
        <img src="/logo-icon.png" alt="" width={36} height={36} className={s.logoMark} />
        <span className={s.logoText}>
          <span>JASUSS</span>
          <span className={s.logoSub}>.TECH</span>
        </span>
      </Link>

      {/* Desktop Navigation Links */}
      <nav className={s.headerRight} aria-label="Main Navigation">
        {navItems.map(({ href, label, Icon, active, admin }) => (
          <Link
            key={href}
            href={href}
            className={`${s.navLink} ${active ? s.navLinkActive : ''} ${admin ? 'tone-violet' : ''}`}
            aria-current={active ? 'page' : undefined}
          >
            <Icon size={17} />
            <span>{label}</span>
          </Link>
        ))}

        <div className={s.headerActions}>
          <span className={`chip chip--success chip--live ${s.headerEngine}`}>Engine online</span>

          {session ? (
            <>
              {/* Quick direct dashboard navigation pill */}
              {userIsAdmin ? (
                <Link href="/admin" className={`btn btn-secondary btn-sm tone-violet ${s.navQuick}`}>
                  <RiShieldUserFill size={15} />
                  <span>Admin Console</span>
                </Link>
              ) : (
                <Link href="/dashboard" className={`btn btn-secondary btn-sm tone-primary ${s.navQuick}`}>
                  <TbDashboard size={15} />
                  <span>My Dashboard</span>
                </Link>
              )}

              <button
                type="button"
                onClick={openProfileModal}
                className={s.userBadge}
                title="Click to view Account & Settings"
                aria-label="Open account and settings"
              >
                <span className={`${s.userAvatar} ${userIsAdmin ? s.userAvatarAdmin : ''}`} aria-hidden="true">
                  {avatarChar ?? <RiUser3Line size={14} />}
                </span>
                <span className={`chip chip--sm ${tierChip}`}>{tierLabel}</span>
              </button>
            </>
          ) : (
            <>
              <button type="button" onClick={() => openAuthModal('signin')} className="btn btn-secondary btn-sm">
                <RiLoginCircleLine size={16} />
                <span>Sign In</span>
              </button>
              <button type="button" onClick={() => openAuthModal('signup')} className="btn btn-primary btn-sm">
                <HiSparkles size={16} />
                <span>Get Started</span>
              </button>
            </>
          )}
        </div>
      </nav>

      {/* Mobile & Tablet Controls (Right aligned on <= 900px) */}
      <div className={s.mobileHeaderControls}>
        {session ? (
          <button
            type="button"
            onClick={openProfileModal}
            className={s.userBadge}
            title="Profile"
            aria-label="Open account and settings"
          >
            <span className={`${s.userAvatar} ${s.userAvatarSm} ${userIsAdmin ? s.userAvatarAdmin : ''}`} aria-hidden="true">
              {avatarChar ?? <RiUser3Line size={13} />}
            </span>
            <span className={`chip chip--sm ${tierChip}`}>{tierLabel}</span>
          </button>
        ) : (
          <button type="button" onClick={() => openAuthModal('signin')} className="btn btn-secondary btn-sm">
            Sign In
          </button>
        )}

        {/* Hamburger Toggle Button */}
        <button
          type="button"
          onClick={() => setMobileMenuOpen((prev) => !prev)}
          className={s.mobileMenuToggle}
          aria-label={mobileMenuOpen ? 'Close Navigation Menu' : 'Open Navigation Menu'}
          aria-expanded={mobileMenuOpen}
          aria-controls="mobile-nav-drawer"
        >
          {mobileMenuOpen ? <RiCloseLine size={24} /> : <RiMenu3Line size={24} />}
        </button>
      </div>

      {/* Mobile & Tablet Dropdown Drawer */}
      {mobileMenuOpen && (
        <div id="mobile-nav-drawer" className={s.mobileNavDrawer}>
          <nav className={s.mobileNavList} aria-label="Mobile Navigation">
            {navItems.map(({ href, mobileLabel, Icon, active, admin }) => (
              <Link
                key={href}
                href={href}
                onClick={() => setMobileMenuOpen(false)}
                className={`${s.mobileNavLink} ${active ? s.mobileNavLinkActive : ''} ${admin ? 'tone-violet' : ''}`}
                aria-current={active ? 'page' : undefined}
              >
                <Icon size={18} />
                <span>{mobileLabel}</span>
              </Link>
            ))}
          </nav>

          <div className={s.mobileNavFooter}>
            <div className={s.mobileNavStatus}>
              <span className="chip chip--success chip--live">Nexus Engine Online · 99.9%</span>
            </div>

            {session ? (
              <>
                <button
                  type="button"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    openProfileModal();
                  }}
                  className="btn btn-secondary"
                  style={{ width: '100%' }}
                >
                  <RiUser3Line size={16} />
                  <span>Account &amp; API Key</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    signOut();
                  }}
                  className={`btn btn-secondary ${s.logoutBtn}`}
                >
                  <RiLogoutBoxRLine size={16} />
                  <span>Log Out</span>
                </button>
              </>
            ) : (
              <div className={s.mobileNavAuthGrid}>
                <button
                  type="button"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    openAuthModal('signin');
                  }}
                  className="btn btn-secondary"
                >
                  <RiLoginCircleLine size={16} />
                  <span>Sign In</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    openAuthModal('signup');
                  }}
                  className="btn btn-primary"
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
