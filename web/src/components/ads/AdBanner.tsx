"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  LuExternalLink as ExternalLink,
  LuChevronRight as ChevronRight,
  LuVolume2 as Volume2,
  LuVolumeX as VolumeX,
  LuShieldCheck as ShieldCheck,
} from "react-icons/lu";
import { GoogleAdSenseUnit } from "./GoogleAdSenseUnit";
import { accentProps, cx } from "../three";
import c from "../../app/content3d.module.css";

// ─── Ad data ─────────────────────────────────────────────────────────────────
export interface AdCreative {
  id: string;
  sponsor: string;
  headline: string;
  subline: string;
  cta: string;
  ctaUrl: string;
  imageSrc: string;
  accentColor: string;
  badgeColor: string;
}

const AD_DURATION_SECONDS = 30;

const ADS: AdCreative[] = [
  {
    id: "analytics-pro",
    sponsor: "Analytics Pro",
    headline: "Boost Your Web Performance",
    subline: "Track, analyze & optimize with real-time insights trusted by 5,000+ enterprises.",
    cta: "Start Free Trial →",
    ctaUrl: "https://analyticspro.io",
    imageSrc: "/ads/ad_analytics_pro.jpg",
    accentColor: "#7c3aed",
    badgeColor: "rgba(124,58,237,0.15)",
  },
  {
    id: "cloudbase",
    sponsor: "CloudBase",
    headline: "Deploy Faster, Scale Smarter",
    subline: "99.99% uptime guaranteed. Global edge network with auto-scaling built in.",
    cta: "Get Started Now →",
    ctaUrl: "https://cloudbase.io",
    imageSrc: "/ads/ad_cloudbase.jpg",
    accentColor: "#06b6d4",
    badgeColor: "rgba(6,182,212,0.15)",
  },
  {
    id: "ciphershield",
    sponsor: "CipherShield",
    headline: "Catch Vulnerabilities Before They Catch You",
    subline: "AI-powered code analysis & real-time security scanning for modern dev teams.",
    cta: "Secure Your Code →",
    ctaUrl: "https://ciphershield.dev",
    imageSrc: "/ads/ad_ciphershield.jpg",
    accentColor: "#10b981",
    badgeColor: "rgba(16,185,129,0.15)",
  },
];

// ─── Impression / click tracking ─────────────────────────────────────────────
function trackImpression(adId: string) {
  if (typeof window !== "undefined") {
    const key = `ad_impressions_${adId}`;
    try {
      localStorage.setItem(key, String(parseInt(localStorage.getItem(key) || "0", 10) + 1));
    } catch {
      // storage unavailable (private mode / blocked) — tracking is best-effort
    }
  }
}

function trackClick(adId: string) {
  if (typeof window !== "undefined") {
    const key = `ad_clicks_${adId}`;
    try {
      localStorage.setItem(key, String(parseInt(localStorage.getItem(key) || "0", 10) + 1));
    } catch {
      // storage unavailable (private mode / blocked) — tracking is best-effort
    }
  }
}

// ─── Props ───────────────────────────────────────────────────────────────────
interface AdBannerProps {
  isAuthenticated: boolean;
  onCycleComplete?: (cycleIndex: number) => void;
}

// ─── Main component ───────────────────────────────────────────────────────────
export const AdBanner: React.FC<AdBannerProps> = ({ isAuthenticated, onCycleComplete }) => {
  const [adIndex, setAdIndex] = useState(0);
  const [timeLeft, setTimeLeft] = useState(AD_DURATION_SECONDS);
  const [cycleCount, setCycleCount] = useState(0);
  const [isMuted, setIsMuted] = useState(true);

  const adClient = process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID || "ca-pub-9888591397038663";
  const currentAd = ADS[adIndex % ADS.length];
  const adNumber = (adIndex % ADS.length) + 1;
  const progress = ((AD_DURATION_SECONDS - timeLeft) / AD_DURATION_SECONDS) * 100;

  // Track impression on each new ad
  useEffect(() => {
    if (!isAuthenticated) return;
    trackImpression(currentAd.id);
  }, [adIndex, isAuthenticated, currentAd.id]);

  // Safely notify parent when a full ad cycle completes, outside the render phase
  const onCycleCompleteRef = useRef(onCycleComplete);
  useEffect(() => {
    onCycleCompleteRef.current = onCycleComplete;
  }, [onCycleComplete]);

  useEffect(() => {
    const currentCycle = Math.floor(adIndex / ADS.length);
    if (currentCycle > cycleCount) {
      setCycleCount(currentCycle);
      onCycleCompleteRef.current?.(currentCycle);
    }
  }, [adIndex, cycleCount]);

  const advanceAd = useCallback(() => {
    setAdIndex((prev) => prev + 1);
    setTimeLeft(AD_DURATION_SECONDS);
  }, []);

  // 1-second countdown
  useEffect(() => {
    if (!isAuthenticated) return;
    const interval = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  // Auto-advance ad when timer reaches 0
  useEffect(() => {
    if (timeLeft === 0) {
      advanceAd();
    }
  }, [timeLeft, advanceAd]);

  if (!isAuthenticated) return null;

  const sponsorAccent = accentProps(currentAd.accentColor as `#${string}`);

  return (
    <div className={cx("surface-3d surface-3d--accent", c.ad)} aria-label="Advertisement">
      {/* Header */}
      <div className={c.adHeader}>
        <span className={c.adLabel}>Advertisement · Google AdSense</span>
        <div className={c.adHeaderRight}>
          <span className="chip chip--sm chip--info">
            <ShieldCheck size={12} />
            Verified Partner · AdSense
          </span>
          <span className={c.adCount}>{adNumber} / {ADS.length} (30s)</span>
        </div>
      </div>

      {/* Embedded Google AdSense Tag Container */}
      <div className={cx("surface-inset", c.adSlot)}>
        <GoogleAdSenseUnit
          client={adClient}
          style={{ minHeight: "60px" }}
        />
      </div>

      {/* Sponsor Creative Card */}
      <div className={cx(c.adCard, sponsorAccent.className)} style={sponsorAccent.style}>
        {/* Image */}
        <div className={c.adImage}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={currentAd.imageSrc} alt={currentAd.headline} key={currentAd.id} />
          <div className={c.adImageShade} />
          <button className={c.adMute} onClick={() => setIsMuted((m) => !m)} aria-label="Mute" aria-pressed={isMuted} type="button">
            {isMuted ? <VolumeX size={13} /> : <Volume2 size={13} />}
          </button>
        </div>

        {/* Copy */}
        <div className={c.adCopy}>
          <div className={c.adSponsorRow}>
            <p className={c.adSponsor}>{currentAd.sponsor}</p>
            <span className="chip chip--sm chip--accent">Featured</span>
          </div>
          <h3 className={c.adHeadline}>{currentAd.headline}</h3>
          <p className={c.adSubline}>{currentAd.subline}</p>
          <a
            href={currentAd.ctaUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={c.adCta}
            onClick={() => trackClick(currentAd.id)}
          >
            {currentAd.cta} <ExternalLink size={12} />
          </a>
        </div>

        {/* Countdown */}
        <CountdownRing timeLeft={timeLeft} total={AD_DURATION_SECONDS} accent="rgb(var(--accent-rgb))" />
      </div>

      {/* Progress + skip */}
      <div className={cx(c.adFooter, sponsorAccent.className)} style={sponsorAccent.style}>
        <div className={c.adProgress} role="progressbar" aria-label="Time until next ad" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)}>
          <div className={c.adProgressFill} style={{ ["--p" as string]: progress / 100 } as React.CSSProperties} />
        </div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={advanceAd}>
          Next ad <ChevronRight size={12} />
        </button>
      </div>

      {/* Dots */}
      <div className={cx(c.adDots, sponsorAccent.className)} style={sponsorAccent.style} aria-hidden="true">
        {ADS.map((ad, i) => (
          <span key={ad.id} className={cx(c.adDot, i === adIndex % ADS.length && c.adDotActive)} />
        ))}
      </div>

      {/* Disclaimer */}
      <p className={c.adNote}>
        Ads powered by Google AdSense & certified partners. Scan continues in the background.{" "}
        <a href="/pricing">Pro plans coming soon</a>
        {" "}for an ad-free experience.
      </p>
    </div>
  );
};

// ─── SVG ring countdown ───────────────────────────────────────────────────────
function CountdownRing({ timeLeft, total, accent }: { timeLeft: number; total: number; accent: string }) {
  const r = 22;
  const circ = 2 * Math.PI * r;
  const offset = circ * (timeLeft / total);
  return (
    <div className={c.adRing}>
      <svg width={60} height={60} aria-hidden="true">
        <circle cx={30} cy={30} r={r} fill="none" stroke="rgba(var(--ink-rgb), 0.1)" strokeWidth={4} />
        <circle
          cx={30} cy={30} r={r} fill="none" stroke={accent} strokeWidth={4}
          strokeDasharray={circ} strokeDashoffset={circ - offset} strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.9s linear" }}
        />
      </svg>
      <span className={c.adRingText}>{timeLeft}s</span>
    </div>
  );
}
