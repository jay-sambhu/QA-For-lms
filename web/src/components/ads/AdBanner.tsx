"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { ExternalLink, ChevronRight, Volume2, VolumeX } from "lucide-react";

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
    localStorage.setItem(key, String(parseInt(localStorage.getItem(key) || "0", 10) + 1));
    // TODO: POST /api/v1/ads/impression { ad_id: adId }
  }
}

function trackClick(adId: string) {
  if (typeof window !== "undefined") {
    const key = `ad_clicks_${adId}`;
    localStorage.setItem(key, String(parseInt(localStorage.getItem(key) || "0", 10) + 1));
    // TODO: POST /api/v1/ads/click { ad_id: adId }
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
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const currentAd = ADS[adIndex % ADS.length];
  const adNumber = (adIndex % ADS.length) + 1;
  const progress = ((AD_DURATION_SECONDS - timeLeft) / AD_DURATION_SECONDS) * 100;

  // Track impression on each new ad
  useEffect(() => {
    if (!isAuthenticated) return;
    trackImpression(currentAd.id);
  }, [adIndex, isAuthenticated, currentAd.id]);

  const advanceAd = useCallback(() => {
    setAdIndex((prev) => {
      const next = prev + 1;
      const nextCycle = Math.floor(next / ADS.length);
      if (nextCycle > cycleCount) {
        setCycleCount(nextCycle);
        onCycleComplete?.(nextCycle);
      }
      return next;
    });
    setTimeLeft(AD_DURATION_SECONDS);
  }, [cycleCount, onCycleComplete]);

  // 1-second countdown
  useEffect(() => {
    if (!isAuthenticated) return;
    timerRef.current = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) {
          advanceAd();
          return AD_DURATION_SECONDS;
        }
        return t - 1;
      });
    }, 1000);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [isAuthenticated, advanceAd]);

  if (!isAuthenticated) return null;

  return (
    <div style={S.wrapper}>
      {/* Header */}
      <div style={S.header}>
        <div style={S.adLabel}>
          <span style={S.adDot} />
          ADVERTISEMENT
        </div>
        <div style={S.headerRight}>
          <span style={{ ...S.sponsorBadge, background: currentAd.badgeColor, color: currentAd.accentColor }}>
            Sponsored · {currentAd.sponsor}
          </span>
          <span style={S.adCount}>{adNumber} / {ADS.length}</span>
        </div>
      </div>

      {/* Card */}
      <div style={S.card}>
        {/* Image */}
        <div style={S.imageWrapper}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={currentAd.imageSrc} alt={currentAd.headline} style={S.image} key={currentAd.id} />
          <div style={S.imageOverlay} />
          <button style={S.muteBtn} onClick={() => setIsMuted((m) => !m)} aria-label="Toggle mute" type="button">
            {isMuted ? <VolumeX size={13} /> : <Volume2 size={13} />}
          </button>
        </div>

        {/* Copy */}
        <div style={S.copy}>
          <p style={S.sponsorName}>{currentAd.sponsor}</p>
          <h3 style={S.headline}>{currentAd.headline}</h3>
          <p style={S.subline}>{currentAd.subline}</p>
          <a
            href={currentAd.ctaUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{ ...S.ctaBtn, background: currentAd.accentColor }}
            onClick={() => trackClick(currentAd.id)}
          >
            {currentAd.cta} <ExternalLink size={12} style={{ marginLeft: 5 }} />
          </a>
        </div>

        {/* Countdown */}
        <div style={S.countdownWrapper}>
          <CountdownRing timeLeft={timeLeft} total={AD_DURATION_SECONDS} accent={currentAd.accentColor} />
        </div>
      </div>

      {/* Progress + skip */}
      <div style={S.footer}>
        <div style={S.progressTrack}>
          <div style={{ ...S.progressFill, width: `${progress}%`, background: currentAd.accentColor }} />
        </div>
        <button type="button" style={S.skipBtn} onClick={advanceAd}>
          Next ad <ChevronRight size={12} />
        </button>
      </div>

      {/* Dots */}
      <div style={S.dots}>
        {ADS.map((ad, i) => (
          <div
            key={ad.id}
            style={{
              ...S.dot,
              background: i === adIndex % ADS.length ? currentAd.accentColor : "rgba(148,163,184,0.25)",
              transform: i === adIndex % ADS.length ? "scale(1.4)" : "scale(1)",
            }}
          />
        ))}
      </div>

      {/* Disclaimer */}
      <p style={S.disclaimer}>
        Your free scan is powered by sponsor ads.{" "}
        <a href="/pricing" style={{ color: "#818cf8", textDecoration: "none" }}>Upgrade to Pro</a>
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
    <div style={{ position: "relative", width: 60, height: 60, flexShrink: 0 }}>
      <svg width={60} height={60} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={30} cy={30} r={r} fill="none" stroke="rgba(148,163,184,0.12)" strokeWidth={4} />
        <circle
          cx={30} cy={30} r={r} fill="none" stroke={accent} strokeWidth={4}
          strokeDasharray={circ} strokeDashoffset={circ - offset} strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.9s linear" }}
        />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.82rem", fontWeight: 700, color: "#f1f5f9" }}>
        {timeLeft}s
      </div>
    </div>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────
const S: Record<string, React.CSSProperties> = {
  wrapper: { background: "rgba(15,23,42,0.88)", border: "1px solid rgba(99,102,241,0.18)", borderRadius: 16, padding: "16px 20px 14px", backdropFilter: "blur(14px)", marginTop: 18 },
  header: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 },
  adLabel: { display: "flex", alignItems: "center", gap: 6, fontSize: "0.63rem", fontWeight: 700, letterSpacing: "0.13em", color: "#64748b", textTransform: "uppercase" },
  adDot: { width: 7, height: 7, borderRadius: "50%", background: "#f59e0b", boxShadow: "0 0 6px #f59e0b" },
  headerRight: { display: "flex", alignItems: "center", gap: 10 },
  sponsorBadge: { fontSize: "0.71rem", fontWeight: 600, padding: "3px 10px", borderRadius: 20 },
  adCount: { fontSize: "0.71rem", color: "#475569" },
  card: { display: "flex", gap: 16, alignItems: "center" },
  imageWrapper: { position: "relative", flexShrink: 0, width: 280, height: 158, borderRadius: 10, overflow: "hidden", border: "1px solid rgba(255,255,255,0.07)" },
  image: { width: "100%", height: "100%", objectFit: "cover" },
  imageOverlay: { position: "absolute", inset: 0, background: "linear-gradient(90deg,rgba(0,0,0,0) 55%,rgba(0,0,0,0.4) 100%)", pointerEvents: "none" },
  muteBtn: { position: "absolute", bottom: 8, right: 8, background: "rgba(0,0,0,0.5)", border: "none", borderRadius: 6, padding: "4px 6px", cursor: "pointer", color: "#cbd5e1", display: "flex", alignItems: "center" },
  copy: { flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 6 },
  sponsorName: { fontSize: "0.7rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em", margin: 0 },
  headline: { fontSize: "1rem", fontWeight: 700, color: "#f1f5f9", margin: 0, lineHeight: 1.35 },
  subline: { fontSize: "0.81rem", color: "#94a3b8", margin: 0, lineHeight: 1.5 },
  ctaBtn: { display: "inline-flex", alignItems: "center", padding: "8px 16px", borderRadius: 8, color: "#fff", fontWeight: 600, fontSize: "0.81rem", textDecoration: "none", alignSelf: "flex-start", marginTop: 4 },
  countdownWrapper: { display: "flex", alignItems: "center", justifyContent: "center", padding: "0 4px" },
  footer: { display: "flex", alignItems: "center", gap: 12, marginTop: 14 },
  progressTrack: { flex: 1, height: 3, borderRadius: 4, background: "rgba(148,163,184,0.12)", overflow: "hidden" },
  progressFill: { height: "100%", borderRadius: 4, transition: "width 1s linear" },
  skipBtn: { flexShrink: 0, background: "transparent", border: "1px solid rgba(148,163,184,0.18)", borderRadius: 6, padding: "3px 10px", cursor: "pointer", color: "#64748b", fontSize: "0.74rem", display: "flex", alignItems: "center", gap: 2 },
  dots: { display: "flex", justifyContent: "center", gap: 6, marginTop: 10 },
  dot: { width: 7, height: 7, borderRadius: "50%", transition: "all 0.3s ease" },
  disclaimer: { textAlign: "center", fontSize: "0.68rem", color: "#475569", marginTop: 10, marginBottom: 0 },
};
