"use client";

import React from 'react';
import { TbDeviceDesktop, TbDeviceMobile, TbDeviceTablet, TbActivity } from 'react-icons/tb';
import { CrossDeviceMetrics } from '../../../types/qa';
import { EmptyState3D, StatTile3D, Surface3D } from '../../three';

interface DevicesTabProps {
  crossDeviceMetrics?: CrossDeviceMetrics;
}

const enterDelay = (step: number) => ({ ['--enter-delay' as string]: `${step * 60}ms` }) as React.CSSProperties;

export const DevicesTab: React.FC<DevicesTabProps> = ({ crossDeviceMetrics }) => {
  if (!crossDeviceMetrics) {
    return (
      <Surface3D>
        <EmptyState3D
          icon={<TbDeviceDesktop size={16} />}
          title="No responsive telemetry"
          description="No responsive viewport telemetry was recorded for this scan."
        />
      </Surface3D>
    );
  }

  const breakdown = crossDeviceMetrics.device_breakdown || {
    desktop: 0,
    iphone: 0,
    ipad: 0,
  };
  const totalResponsive = crossDeviceMetrics.responsive_findings ?? 0;

  return (
    <div className="bento" style={{ ['--grid-gap' as string]: '16px' } as React.CSSProperties}>
      <div className="span-3 enter-3d" style={enterDelay(0)}>
        <StatTile3D
          label="Desktop (1920x1080)"
          value={breakdown.desktop}
          accent="primary"
          icon={<TbDeviceDesktop size={20} />}
          hint="Responsive Findings"
        />
      </div>
      <div className="span-3 enter-3d" style={enterDelay(1)}>
        <StatTile3D
          label="iPhone 13 (390x844)"
          value={breakdown.iphone}
          accent="info"
          icon={<TbDeviceMobile size={20} />}
          hint="Touch & Viewport Findings"
        />
      </div>
      <div className="span-3 enter-3d" style={enterDelay(2)}>
        <StatTile3D
          label="iPad (820x1180)"
          value={breakdown.ipad}
          accent="success"
          icon={<TbDeviceTablet size={20} />}
          hint="Tablet Layout Findings"
        />
      </div>
      <div className="span-3 enter-3d" style={enterDelay(3)}>
        <StatTile3D
          label="Total Responsive Issues"
          value={totalResponsive}
          accent={totalResponsive > 0 ? 'warning' : 'success'}
          icon={<TbActivity size={20} />}
          hint="Across all emulated viewports"
        />
      </div>
    </div>
  );
};
