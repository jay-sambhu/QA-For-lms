"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  TbSparkles,
  TbExternalLink,
  TbShieldCheck,
  TbBolt,
  TbServer2,
  TbX,
  TbDeviceDesktop,
} from "react-icons/tb";
import { useAuth } from "../../context/AuthContext";
import { GoogleAdSenseUnit } from "./GoogleAdSenseUnit";

interface SideAdRailsProps {
  children: React.ReactNode;
}

export const SideAdRails: React.FC<SideAdRailsProps> = ({ children }) => {
  const { userPlan } = useAuth();
  const [leftDismissed, setLeftDismissed] = useState(false);
  const [rightDismissed, setRightDismissed] = useState(false);

  // Paid users (Pro / Enterprise) enjoy a 100% ad-free experience
  const isPaidUser = userPlan === "pro" || userPlan === "enterprise";
  if (isPaidUser) {
    return <>{children}</>;
  }

  return (
    <div className="sideAdRailsContainer">
      {/* Left Sidebar Rail */}
      {!leftDismissed && (
        <aside className="sideAdRail sideAdRailLeft" aria-label="Sponsored QA Tools">
          <div className="sideAdRailHeader">
            <span className="sideAdBadge">
              <TbShieldCheck size={13} color="#818cf8" />
              <span>SPONSORED QA</span>
            </span>
            <button
              type="button"
              onClick={() => setLeftDismissed(true)}
              className="sideAdCloseBtn"
              title="Hide sponsored rail for this session"
            >
              <TbX size={13} />
            </button>
          </div>

          {/* Useful Tool 1 */}
          <a
            href="https://playwright.dev"
            target="_blank"
            rel="noopener noreferrer"
            className="sideAdCard"
          >
            <div className="sideAdCardTop">
              <span className="sideAdIconBox" style={{ background: "rgba(16, 185, 129, 0.15)", color: "#10b981" }}>
                <TbDeviceDesktop size={15} />
              </span>
              <span className="sideAdCategory">TEST AUTOMATION</span>
            </div>
            <h4 className="sideAdCardTitle">Playwright Cloud</h4>
            <p className="sideAdCardDesc">
              Parallel multi-browser test execution with instant trace debugging and video replay.
            </p>
            <span className="sideAdAction">
              Explore Tool <TbExternalLink size={12} />
            </span>
          </a>

          {/* Useful Tool 2 */}
          <a
            href="https://www.postman.com"
            target="_blank"
            rel="noopener noreferrer"
            className="sideAdCard"
          >
            <div className="sideAdCardTop">
              <span className="sideAdIconBox" style={{ background: "rgba(249, 115, 22, 0.15)", color: "#f97316" }}>
                <TbBolt size={15} />
              </span>
              <span className="sideAdCategory">API TESTING</span>
            </div>
            <h4 className="sideAdCardTitle">Postman Sentinel</h4>
            <p className="sideAdCardDesc">
              Automated endpoint fuzzing, schema drift detection, and contract regression tests.
            </p>
            <span className="sideAdAction">
              Inspect APIs <TbExternalLink size={12} />
            </span>
          </a>

          {/* Google AdSense Dynamic Unit */}
          <div className="sideAdUnitBox">
            <span className="sideAdUnitLabel">ADVERTISEMENT</span>
            <GoogleAdSenseUnit
              style={{ minHeight: "140px" }}
              format="vertical"
              responsive={true}
            />
          </div>

          {/* Free Tier Callout */}
          <div className="sideAdFooter">
            <span style={{ fontSize: "0.72rem", color: "#64748b" }}>Free Tier Plan</span>
            <Link href="/pricing" className="sideAdUpgradeLink">
              Remove ads with Pro →
            </Link>
          </div>
        </aside>
      )}

      {/* Main Content Area */}
      <div className="sideAdMainContent">
        {children}
      </div>

      {/* Right Sidebar Rail */}
      {!rightDismissed && (
        <aside className="sideAdRail sideAdRailRight" aria-label="Developer Ecosystem">
          <div className="sideAdRailHeader">
            <span className="sideAdBadge">
              <TbSparkles size={13} color="#38bdf8" />
              <span>DEV ECOSYSTEM</span>
            </span>
            <button
              type="button"
              onClick={() => setRightDismissed(true)}
              className="sideAdCloseBtn"
              title="Hide sponsored rail for this session"
            >
              <TbX size={13} />
            </button>
          </div>

          {/* Useful Tool 3 */}
          <a
            href="https://sentry.io"
            target="_blank"
            rel="noopener noreferrer"
            className="sideAdCard"
          >
            <div className="sideAdCardTop">
              <span className="sideAdIconBox" style={{ background: "rgba(168, 85, 247, 0.15)", color: "#a855f7" }}>
                <TbServer2 size={15} />
              </span>
              <span className="sideAdCategory">OBSERVABILITY</span>
            </div>
            <h4 className="sideAdCardTitle">Sentry Crash Logs</h4>
            <p className="sideAdCardDesc">
              Real-time stack trace monitoring, frontend telemetry, and user session crash diagnostics.
            </p>
            <span className="sideAdAction">
              View Telemetry <TbExternalLink size={12} />
            </span>
          </a>

          {/* Useful Tool 4 */}
          <a
            href="https://k6.io"
            target="_blank"
            rel="noopener noreferrer"
            className="sideAdCard"
          >
            <div className="sideAdCardTop">
              <span className="sideAdIconBox" style={{ background: "rgba(56, 189, 248, 0.15)", color: "#38bdf8" }}>
                <TbBolt size={15} />
              </span>
              <span className="sideAdCategory">PERFORMANCE</span>
            </div>
            <h4 className="sideAdCardTitle">k6 Stress Engine</h4>
            <p className="sideAdCardDesc">
              Developer-centric load and stress testing for up to 100k simulated concurrent virtual users.
            </p>
            <span className="sideAdAction">
              Benchmark App <TbExternalLink size={12} />
            </span>
          </a>

          {/* Google AdSense Dynamic Unit */}
          <div className="sideAdUnitBox">
            <span className="sideAdUnitLabel">ADVERTISEMENT</span>
            <GoogleAdSenseUnit
              style={{ minHeight: "140px" }}
              format="vertical"
              responsive={true}
            />
          </div>

          {/* Free Tier Callout */}
          <div className="sideAdFooter">
            <span style={{ fontSize: "0.72rem", color: "#64748b" }}>JASUSS Cloud</span>
            <Link href="/blog" className="sideAdUpgradeLink">
              Read QA Articles →
            </Link>
          </div>
        </aside>
      )}
    </div>
  );
};
