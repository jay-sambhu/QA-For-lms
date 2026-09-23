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
  refreshKey?: string | number;
}

export const GoogleAdSenseUnit: React.FC<GoogleAdSenseUnitProps> = ({
  client,
  slot,
  format = "auto",
  responsive = true,
  style = {},
  className = "",
  refreshKey,
}) => {
  const adClient = client || process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID || "ca-pub-0000000000000000";
  const adSlot = slot || process.env.NEXT_PUBLIC_ADSENSE_SLOT_ID || "";
  const adRef = useRef<HTMLModElement | null>(null);
  const [adLoaded, setAdLoaded] = useState(false);
  const [isTestMode, setIsTestMode] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const isLocal =
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1" ||
        window.location.hostname.endsWith(".local");
      setIsTestMode(isLocal);

      try {
        // Push ad request to Google AdSense queue
        if (adRef.current && (!adRef.current.innerHTML || adRef.current.getAttribute("data-adsbygoogle-status") !== "done")) {
          (window.adsbygoogle = window.adsbygoogle || []).push({});
          setAdLoaded(true);
        }
      } catch (e) {
        console.warn("[Google AdSense] Ad request push warning:", e);
      }
    }
  }, [refreshKey, adClient, adSlot]);

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
            color: "#64748b",
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
