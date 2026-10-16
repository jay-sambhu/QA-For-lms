"use client";

import React from 'react';
import { LuSparkles as Sparkles } from 'react-icons/lu';
import { PricingCards } from '../components/pricing/PricingCards';
import { PageHeader3D } from '../components/three';

export const PricingPage: React.FC = () => {
  return (
    <div className="page-shell">
      <PageHeader3D
        eyebrow="Pricing"
        icon={<Sparkles size={24} />}
        title={
          <>
            Scale your QA with <span className="text-gradient">JASUSS Enterprise</span>
          </>
        }
        badge="FREE DURING BETA"
        subtitle="Start free today, no credit card required. Paid plans for growing teams are coming soon."
      />

      <div className="enter-3d" style={{ ['--enter-delay' as string]: '120ms' } as React.CSSProperties}>
        <PricingCards />
      </div>
    </div>
  );
};
