"use client";

import React, { useState, useEffect, useCallback } from "react";
import { ShieldAlert, RefreshCw, ExternalLink, X, CheckCircle2 } from "lucide-react";
import Link from "next/link";

export const AdBlockerDetector: React.FC = () => {
  const [isBlocked, setIsBlocked] = useState<boolean>(false);
  const [isDismissed, setIsDismissed] = useState<boolean>(false);
  const [isChecking, setIsChecking] = useState<boolean>(false);

  const checkAdBlocker = useCallback(async () => {
    setIsChecking(true);
    let adBlockDetected = false;

    // 1. DOM Bait Test: Test if ad-related classes are hidden by browser extensions
    try {
      const bait = document.createElement("div");
      bait.className = "ad-banner adsbox ad-placement doubleclick pub_300x250 text-ad";
      bait.style.position = "absolute";
      bait.style.left = "-9999px";
      bait.style.top = "-9999px";
      bait.style.width = "1px";
      bait.style.height = "1px";
      bait.innerHTML = "&nbsp;";
      document.body.appendChild(bait);

      // Give browser extensions a frame to hide or remove the element
      await new Promise((resolve) => setTimeout(resolve, 100));

      const styles = window.getComputedStyle(bait);
      if (
        bait.offsetParent === null ||
        bait.offsetHeight === 0 ||
        bait.offsetLeft === 0 ||
        styles.display === "none" ||
        styles.visibility === "hidden"
      ) {
        adBlockDetected = true;
      }
      document.body.removeChild(bait);
    } catch {
      // DOM error
    }

    // 2. Network Probe Test: Test if requests to Google AdSense are intercepted/blocked
    if (!adBlockDetected) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2500);
        await fetch(
          "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js",
          {
            method: "HEAD",
            mode: "no-cors",
            cache: "no-store",
            signal: controller.signal,
          }
        );
        clearTimeout(timeoutId);
      } catch (err: unknown) {
        // If fetch failed due to ad blocker client filter (net::ERR_BLOCKED_BY_CLIENT)
        if (err instanceof Error && err.name !== "AbortError") {
          adBlockDetected = true;
        }
      }
    }

    setIsBlocked(adBlockDetected);
    setIsChecking(false);
  }, []);

  useEffect(() => {
    // Initial check after component mounts
    const timer = setTimeout(() => {
      checkAdBlocker();
    }, 1200);

    return () => clearTimeout(timer);
  }, [checkAdBlocker]);

  if (!isBlocked || isDismissed) {
    return null;
  }

  return (
    <div style={styles.overlay}>
      <div style={styles.modal} role="dialog" aria-modal="true" aria-labelledby="adblock-title">
        {/* Close / Dismiss icon */}
        <button
          onClick={() => setIsDismissed(true)}
          style={styles.closeBtn}
          aria-label="Dismiss ad blocker warning"
        >
          <X size={18} />
        </button>

        {/* Warning Icon Badge */}
        <div style={styles.iconWrapper}>
          <ShieldAlert size={36} color="#ef4444" />
        </div>

        {/* Header Text */}
        <h2 id="adblock-title" style={styles.title}>
          Ad Blocker Detected
        </h2>
        <p style={styles.subtitle}>
          Please disable your ad blocker to support free QA scans
        </p>

        {/* Explanation Card */}
        <div style={styles.infoBox}>
          <p style={styles.infoText}>
            <strong>JASUSS.TECH</strong> provides autonomous multi-viewport web QA crawling, regression testing, and executive reporting completely free.
          </p>
          <p style={{ ...styles.infoText, marginTop: 8, color: "#94a3b8" }}>
            Our infrastructure and AI analysis are sponsored by display advertisements. To keep this platform free and accessible to all developers, please whitelist our domain or disable your ad blocker.
          </p>
        </div>

        {/* Whitelisting Tips */}
        <div style={styles.stepsBox}>
          <div style={styles.stepItem}>
            <CheckCircle2 size={15} color="#10b981" style={{ flexShrink: 0, marginTop: 2 }} />
            <span>Click your ad blocker extension icon (uBlock, AdBlock, Brave Shields, etc.)</span>
          </div>
          <div style={styles.stepItem}>
            <CheckCircle2 size={15} color="#10b981" style={{ flexShrink: 0, marginTop: 2 }} />
            <span>Toggle the power switch or select <strong>&quot;Pause on this site&quot;</strong></span>
          </div>
          <div style={styles.stepItem}>
            <CheckCircle2 size={15} color="#10b981" style={{ flexShrink: 0, marginTop: 2 }} />
            <span>Click <strong>&quot;Recheck &amp; Reload&quot;</strong> below</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={styles.actions}>
          <button
            onClick={() => {
              checkAdBlocker();
              if (typeof window !== "undefined") {
                window.location.reload();
              }
            }}
            disabled={isChecking}
            style={styles.primaryBtn}
          >
            <RefreshCw size={15} className={isChecking ? "spin" : ""} style={{ marginRight: 8 }} />
            {isChecking ? "Checking..." : "Recheck & Reload Page"}
          </button>

          <Link href="/pricing" onClick={() => setIsDismissed(true)} style={styles.secondaryBtn}>
            Upgrade to Pro (Ad-free) <ExternalLink size={14} style={{ marginLeft: 6 }} />
          </Link>
        </div>

        {/* Temporary Dismiss Footer */}
        <div style={styles.dismissFooter}>
          <button
            onClick={() => setIsDismissed(true)}
            style={styles.textDismissBtn}
          >
            Dismiss for this session
          </button>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "fixed",
    inset: 0,
    backgroundColor: "rgba(10, 15, 29, 0.85)",
    backdropFilter: "blur(8px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 999999,
    padding: "20px",
    animation: "fadeIn 0.25s ease-out",
  },
  modal: {
    position: "relative",
    width: "100%",
    maxWidth: "520px",
    backgroundColor: "#0f172a",
    border: "1px solid rgba(239, 68, 68, 0.35)",
    boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.7), 0 0 35px rgba(239, 68, 68, 0.15)",
    borderRadius: "18px",
    padding: "32px 28px 24px",
    color: "#f8fafc",
    textAlign: "center",
  },
  closeBtn: {
    position: "absolute",
    top: "16px",
    right: "16px",
    background: "transparent",
    border: "none",
    color: "#94a3b8",
    cursor: "pointer",
    padding: "6px",
    borderRadius: "8px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  iconWrapper: {
    width: "68px",
    height: "68px",
    margin: "0 auto 16px",
    borderRadius: "50%",
    backgroundColor: "rgba(239, 68, 68, 0.12)",
    border: "1px solid rgba(239, 68, 68, 0.3)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  title: {
    fontSize: "1.45rem",
    fontWeight: 700,
    margin: "0 0 6px",
    color: "#ffffff",
    letterSpacing: "-0.01em",
  },
  subtitle: {
    fontSize: "0.92rem",
    color: "#f87171",
    fontWeight: 500,
    margin: "0 0 20px",
  },
  infoBox: {
    backgroundColor: "rgba(30, 41, 59, 0.7)",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    borderRadius: "12px",
    padding: "16px",
    textAlign: "left",
    marginBottom: "16px",
  },
  infoText: {
    fontSize: "0.84rem",
    lineHeight: 1.5,
    margin: 0,
    color: "#e2e8f0",
  },
  stepsBox: {
    backgroundColor: "rgba(15, 23, 42, 0.6)",
    border: "1px solid rgba(148, 163, 184, 0.1)",
    borderRadius: "10px",
    padding: "12px 14px",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    marginBottom: "24px",
    textAlign: "left",
  },
  stepItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: "10px",
    fontSize: "0.8rem",
    color: "#cbd5e1",
    lineHeight: 1.4,
  },
  actions: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  primaryBtn: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#ef4444",
    color: "#ffffff",
    border: "none",
    borderRadius: "10px",
    padding: "12px 20px",
    fontSize: "0.92rem",
    fontWeight: 600,
    cursor: "pointer",
    boxShadow: "0 4px 14px rgba(239, 68, 68, 0.35)",
    transition: "background-color 0.2s ease",
  },
  secondaryBtn: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(255, 255, 255, 0.06)",
    color: "#93c5fd",
    border: "1px solid rgba(147, 197, 253, 0.25)",
    borderRadius: "10px",
    padding: "11px 20px",
    fontSize: "0.88rem",
    fontWeight: 500,
    textDecoration: "none",
    transition: "background-color 0.2s ease",
  },
  dismissFooter: {
    marginTop: "14px",
  },
  textDismissBtn: {
    background: "transparent",
    border: "none",
    color: "#64748b",
    fontSize: "0.78rem",
    cursor: "pointer",
    textDecoration: "underline",
  },
};
