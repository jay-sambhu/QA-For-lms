"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  LuShieldAlert as ShieldAlert,
  LuRefreshCw as RefreshCw,
  LuExternalLink as ExternalLink,
  LuX as X,
  LuCircleCheck as CheckCircle2,
} from "react-icons/lu";
import Link from "next/link";
import { useAuth } from "../../context/AuthContext";
import c from "../../app/content3d.module.css";

const DISMISS_KEY = "adblock_dismissed";

export const AdBlockerDetector: React.FC = () => {
  const [isBlocked, setIsBlocked] = useState<boolean>(false);
  const [isDismissed, setIsDismissed] = useState<boolean>(false);
  const [isChecking, setIsChecking] = useState<boolean>(false);
  const { userPlan } = useAuth();
  // Paid plans are ad-free, so never nag them about ad blockers
  const isPaid = userPlan === "pro" || userPlan === "enterprise";

  const dismiss = useCallback(() => {
    setIsDismissed(true);
    try {
      sessionStorage.setItem(DISMISS_KEY, "1");
    } catch {
      // storage unavailable (private mode) — dismiss for this page view only
    }
  }, []);

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
    if (isPaid) return;
    try {
      if (sessionStorage.getItem(DISMISS_KEY) === "1") return;
    } catch {
      // ignore
    }
    // Initial check after component mounts
    const timer = setTimeout(() => {
      checkAdBlocker();
    }, 1200);

    return () => clearTimeout(timer);
  }, [checkAdBlocker, isPaid]);

  if (isPaid || !isBlocked || isDismissed) {
    return null;
  }

  return (
    <div className={c.overlay}>
      <div className={`glass-3d tone-danger ${c.modal}`} role="dialog" aria-modal="true" aria-labelledby="adblock-title">
        {/* Close / Dismiss icon */}
        <button
          type="button"
          onClick={dismiss}
          className={c.modalClose}
          aria-label="Dismiss ad blocker warning"
        >
          <X size={18} />
        </button>

        {/* Warning Icon Badge */}
        <span className={`icon-well icon-well--lg ${c.modalIcon}`} aria-hidden="true">
          <ShieldAlert size={28} />
        </span>

        {/* Header Text */}
        <h2 id="adblock-title" className={c.modalTitle}>
          Ad Blocker Detected
        </h2>
        <p className={c.modalSubtitle}>
          Please disable your ad blocker to support free QA scans
        </p>

        {/* Explanation Card */}
        <div className={`surface-inset ${c.modalInfo}`}>
          <p>
            <strong>JASUSS.TECH</strong> provides autonomous multi-viewport web QA crawling, regression testing, and executive reporting completely free.
          </p>
          <p>
            Our infrastructure and AI analysis are sponsored by display advertisements. To keep this platform free and accessible to all developers, please whitelist our domain or disable your ad blocker.
          </p>
        </div>

        {/* Whitelisting Tips */}
        <div className={`surface-inset ${c.modalSteps}`}>
          <div className={c.modalStep}>
            <CheckCircle2 size={15} />
            <span>Click your ad blocker extension icon (uBlock, AdBlock, Brave Shields, etc.)</span>
          </div>
          <div className={c.modalStep}>
            <CheckCircle2 size={15} />
            <span>Toggle the power switch or select <strong>&quot;Pause on this site&quot;</strong></span>
          </div>
          <div className={c.modalStep}>
            <CheckCircle2 size={15} />
            <span>Click <strong>&quot;Recheck &amp; Reload&quot;</strong> below</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className={c.modalActions}>
          <button
            type="button"
            onClick={() => {
              checkAdBlocker();
              if (typeof window !== "undefined") {
                window.location.reload();
              }
            }}
            disabled={isChecking}
            className="btn btn-primary"
          >
            <RefreshCw size={15} className={isChecking ? "pulse" : ""} />
            {isChecking ? "Checking..." : "Recheck & Reload Page"}
          </button>

          <Link href="/pricing" onClick={dismiss} className="btn btn-secondary">
            Ad-free Pro (coming soon) <ExternalLink size={14} />
          </Link>
        </div>

        {/* Temporary Dismiss Footer */}
        <button
          type="button"
          onClick={dismiss}
          className={c.modalDismiss}
        >
          Dismiss for this session
        </button>
      </div>
    </div>
  );
};
