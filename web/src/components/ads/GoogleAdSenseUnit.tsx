"use client";

import React, { useEffect, useRef, useState } from "react";

declare global {
  interface Window {
    adsbygoogle?: any[];
  }
}

interface GoogleAdSenseUnitProps {
  client?: string;
  slot?: string;
  format?: string;
  responsive?: boolean;
  style?: React.CSSProperties;
  className?: string;
}

export const GoogleAdSenseUnit: React.FC<GoogleAdSenseUnitProps> = ({
  client,
  slot,
  format = "auto",
  responsive = true,
  style = {},
  className = "",
}) => {
  const adClient = client || process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID || "ca-pub-9888591397038663";
  const adSlot = slot || process.env.NEXT_PUBLIC_ADSENSE_SLOT_ID || "";
  const adRef = useRef<HTMLModElement | null>(null);
  const [adLoaded, setAdLoaded] = useState(false);
  const [isTestMode, setIsTestMode] = useState(false);

  // An <ins> slot may only be pushed once; pushing again (e.g. on re-render or before the
  // AdSense script loads) throws "already have ads" and violates AdSense refresh policy.
  const pushedRef = useRef(false);

  useEffect(() => {
    const host = window.location.hostname;
    const isLocal = host === "localhost" || host === "127.0.0.1" || host.endsWith(".local");
    setIsTestMode(isLocal);
    const el = adRef.current;
    if (pushedRef.current || !el) return;
    // Set test mode on the element before the first push (state would apply too late)
    if (isLocal) el.setAttribute("data-ad-test", "on");

    // AdSense throws "No slot size for availableWidth=0" if pushed while the slot is
    // hidden (e.g. side rails below their breakpoint), so wait until it has a width.
    const push = () => {
      if (pushedRef.current || el.offsetWidth === 0) return false;
      pushedRef.current = true;
      try {
        (window.adsbygoogle = window.adsbygoogle || []).push({});
        setAdLoaded(true);
      } catch (e) {
        console.warn("[Google AdSense] Ad request push warning:", e);
      }
      return true;
    };
    if (push() || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      if (push()) ro.disconnect();
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div style={{ position: "relative", width: "100%", overflow: "hidden", ...style }} className={className}>
      <ins
        ref={adRef}
        className="adsbygoogle"
        style={{
          display: "block",
          minHeight: "120px",
          width: "100%",
          textAlign: "center",
        }}
        data-ad-client={adClient}
        {...(adSlot ? { "data-ad-slot": adSlot } : {})}
        data-ad-format={format}
        data-full-width-responsive={responsive ? "true" : "false"}
        data-ad-test={isTestMode ? "on" : undefined}
      />
      {isTestMode && !adLoaded && (
        <div
          style={{
            fontSize: "0.68rem",
            color: "var(--text-subtle)",
            textAlign: "center",
            marginTop: 4,
          }}
        >
          Google AdSense Active · Test Mode enabled for localhost
        </div>
      )}
    </div>
  );
};
