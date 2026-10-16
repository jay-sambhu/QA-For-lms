"use client";

import React from 'react';
import { FaArrowTrendUp, FaUsers } from 'react-icons/fa6';
import { TbActivityHeartbeat, TbServer2 } from 'react-icons/tb';
import { StatTile3D } from '../three';

interface AdminMetricsProps {
  metrics: any;
  usersCount: number;
  scansCount: number;
}

const enterDelay = (step: number) =>
  ({ ['--enter-delay' as string]: `${step * 60}ms` }) as React.CSSProperties;

export const AdminMetrics: React.FC<AdminMetricsProps> = ({
  metrics,
  usersCount,
  scansCount,
}) => {
  const mrr = metrics?.financial_metrics?.mrr_usd ?? 0;
  const paidSubs = metrics?.financial_metrics?.total_paid_subscriptions ?? 0;
  const totalUsers = metrics?.platform_overview?.total_users ?? usersCount;
  const totalScans = metrics?.platform_overview?.total_scans ?? scansCount;
  const successRate = metrics?.platform_overview?.scan_success_rate ?? 100;
  const runningScans = metrics?.platform_overview?.active_running_scans;
  const failedScans = metrics?.platform_overview?.failed_scans;

  return (
    <div className="bento" style={{ ['--grid-gap' as string]: '16px' } as React.CSSProperties}>
      <div className="span-3 enter-3d" style={enterDelay(1)}>
        <StatTile3D
          label="Monthly Recurring Revenue"
          value={`$${mrr}`}
          accent="success"
          icon={<FaArrowTrendUp size={20} />}
          hint={`${paidSubs} active paid subscriptions`}
        />
      </div>

      <div className="span-3 enter-3d" style={enterDelay(2)}>
        <StatTile3D
          label="Registered Tenants"
          value={totalUsers}
          icon={<FaUsers size={20} />}
          hint="Multi-tenant workspace accounts"
        />
      </div>

      <div className="span-3 enter-3d" style={enterDelay(3)}>
        <StatTile3D
          label="Total Scans Executed"
          value={totalScans}
          accent="info"
          icon={<TbActivityHeartbeat size={20} />}
          trend={{ value: `${successRate}%`, positive: successRate >= 80, label: 'success rate' }}
          hint={
            typeof runningScans === 'number' && typeof failedScans === 'number'
              ? `${runningScans} running · ${failedScans} failed`
              : undefined
          }
        />
      </div>

      <div className="span-3 enter-3d" style={enterDelay(4)}>
        <StatTile3D
          label="Cluster Worker Pool"
          value="Operational"
          compact
          valueAccent
          accent="success"
          icon={<TbServer2 size={20} />}
          hint="Redis Queue · Playwright Workers"
        />
      </div>
    </div>
  );
};
