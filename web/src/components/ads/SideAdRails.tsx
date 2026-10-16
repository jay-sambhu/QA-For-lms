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
import c from "../../app/content3d.module.css";

interface SideAdRailsProps {
  children: React.ReactNode;
}

export const SideAdRails: React.FC<SideAdRailsProps> = ({ children }) => {
  const { userPlan } = useAuth();
  const [leftDismissed, setLeftDismissed] = useState(false);
  const [rightDismissed, setRightDismissed] = useState(false);

  // Paid users (Pro / Enterprise) enjoy a 100% ad-free experience. Only the rails are
  // gated: keeping the wrapper stable avoids remounting the whole app when the plan loads.
  const isPaidUser = userPlan === "pro" || userPlan === "enterprise";

  return (
    <div className="sideAdRailsContainer">
      {/* Left Sidebar Rail */}
      {!isPaidUser && !leftDismissed && (
        <aside className={`sideAdRail sideAdRailLeft ${c.rail}`} aria-label="Sponsored QA Tools">
          <div className="sideAdRailHeader">
            <span className="sideAdBadge">
              <TbShieldCheck size={13} color="var(--tone-primary)" />
              <span>SPONSORED QA</span>
            </span>
            <button
              type="button"
              onClick={() => setLeftDismissed(true)}
              className="sideAdCloseBtn"
              title="Hide sponsored rail for this session"
              aria-label="Hide sponsored rail for this session"
            >
              <TbX size={13} />
            </button>
          </div>

          {/* Useful Tool 1 */}
          <a
            href="https://playwright.dev"
            target="_blank"
            rel="noopener noreferrer"
            className={`sideAdCard ${c.railCard} tone-success`}
          >
            <div className="sideAdCardTop">
              <span className={`icon-well icon-well--sm ${c.railIcon}`}>
                <TbDeviceDesktop size={15} />
              </span>
              <span className="sideAdCategory">TEST AUTOMATION</span>
            </div>
            <h4 className="sideAdCardTitle">Playwright Cloud</h4>
            <p className="sideAdCardDesc">
              Parallel multi-browser test execution with instant trace debugging and video replay.
            </p>
            <span className={`sideAdAction ${c.railAction}`}>
              Explore Tool <TbExternalLink size={12} />
            </span>
          </a>

          {/* Useful Tool 2 */}
          <a
            href="https://www.postman.com"
            target="_blank"
            rel="noopener noreferrer"
            className={`sideAdCard ${c.railCard} tone-warning`}
          >
            <div className="sideAdCardTop">
              <span className={`icon-well icon-well--sm ${c.railIcon}`}>
                <TbBolt size={15} />
              </span>
              <span className="sideAdCategory">API TESTING</span>
            </div>
            <h4 className="sideAdCardTitle">Postman Sentinel</h4>
            <p className="sideAdCardDesc">
              Automated endpoint fuzzing, schema drift detection, and contract regression tests.
            </p>
            <span className={`sideAdAction ${c.railAction}`}>
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
            <span className="chip chip--sm chip--neutral" style={{ alignSelf: "center" }}>Free Tier Plan</span>
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
      {!isPaidUser && !rightDismissed && (
        <aside className={`sideAdRail sideAdRailRight ${c.rail}`} aria-label="Developer Ecosystem">
          <div className="sideAdRailHeader">
            <span className="sideAdBadge">
              <TbSparkles size={13} color="var(--tone-info)" />
              <span>DEV ECOSYSTEM</span>
            </span>
            <button
              type="button"
              onClick={() => setRightDismissed(true)}
              className="sideAdCloseBtn"
              title="Hide sponsored rail for this session"
              aria-label="Hide sponsored rail for this session"
            >
              <TbX size={13} />
            </button>
          </div>

          {/* Useful Tool 3 */}
          <a
            href="https://sentry.io"
            target="_blank"
            rel="noopener noreferrer"
            className={`sideAdCard ${c.railCard} tone-violet`}
          >
            <div className="sideAdCardTop">
              <span className={`icon-well icon-well--sm ${c.railIcon}`}>
                <TbServer2 size={15} />
              </span>
              <span className="sideAdCategory">OBSERVABILITY</span>
            </div>
            <h4 className="sideAdCardTitle">Sentry Crash Logs</h4>
            <p className="sideAdCardDesc">
              Real-time stack trace monitoring, frontend telemetry, and user session crash diagnostics.
            </p>
            <span className={`sideAdAction ${c.railAction}`}>
              View Telemetry <TbExternalLink size={12} />
            </span>
          </a>

          {/* Useful Tool 4 */}
          <a
            href="https://k6.io"
            target="_blank"
            rel="noopener noreferrer"
            className={`sideAdCard ${c.railCard} tone-info`}
          >
            <div className="sideAdCardTop">
              <span className={`icon-well icon-well--sm ${c.railIcon}`}>
                <TbBolt size={15} />
              </span>
              <span className="sideAdCategory">PERFORMANCE</span>
            </div>
            <h4 className="sideAdCardTitle">k6 Stress Engine</h4>
            <p className="sideAdCardDesc">
              Developer-centric load and stress testing for up to 100k simulated concurrent virtual users.
            </p>
            <span className={`sideAdAction ${c.railAction}`}>
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
            <span className="chip chip--sm chip--neutral" style={{ alignSelf: "center" }}>JASUSS Cloud</span>
            <Link href="/blog" className="sideAdUpgradeLink">
              Read QA Articles →
            </Link>
          </div>
        </aside>
      )}
    </div>
  );
};
