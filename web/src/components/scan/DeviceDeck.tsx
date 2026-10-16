"use client";

import React from 'react';
import { TbDeviceDesktop, TbDeviceMobile, TbDeviceTablet, TbActivity } from 'react-icons/tb';
import { cx } from '../three';
import s from './scan3d.module.css';

interface DeviceDeckProps {
  activeDeviceName: string;
  activeUrl?: string;
  defaultUrl?: string;
}

const DEVICES = [
  {
    id: 'desktop',
    name: 'Desktop Chrome',
    resolution: '1920 × 1080',
    icon: <TbDeviceDesktop size={16} />,
    deviceClass: 'deviceDesktop',
    frameClass: 'frameDesktop',
  },
  {
    id: 'ipad',
    name: 'iPad (gen 7)',
    resolution: '820 × 1180 (Tablet)',
    icon: <TbDeviceTablet size={16} />,
    deviceClass: 'deviceIpad',
    frameClass: 'frameIpad',
  },
  {
    id: 'iphone',
    name: 'iPhone 13',
    resolution: '390 × 844 (Touch)',
    icon: <TbDeviceMobile size={16} />,
    deviceClass: 'deviceIphone',
    frameClass: 'frameIphone',
  },
] as const;

export const DeviceDeck: React.FC<DeviceDeckProps> = ({ activeDeviceName, activeUrl, defaultUrl }) => {
  const active = activeDeviceName.toLowerCase();

  return (
    <div className={s.deck}>
      <div className={s.deckHead}>
        <span className="section-eyebrow">
          <TbActivity size={14} /> Live multi-device emulation
        </span>
        <span className="chip chip--sm chip--success chip--dot">3 isolated contexts active</span>
      </div>

      <div className={s.deckStage}>
        {DEVICES.map((dev) => {
          const isCrawlingThis = active.includes(dev.id) || active.includes(dev.name.toLowerCase());
          const screenText = isCrawlingThis
            ? activeUrl || defaultUrl || 'Navigating DOM...'
            : 'Waiting for viewport pass...';

          return (
            <div
              key={dev.id}
              className={cx(s.device, s[dev.deviceClass], isCrawlingThis && s.deviceActive)}
              role="group"
              aria-label={`${dev.name}: ${isCrawlingThis ? 'crawling now' : 'ready'}`}
            >
              <div className={cx(s.frame, s[dev.frameClass])}>
                <div className={s.screen}>
                  {dev.id === 'desktop' && (
                    <span className={s.screenChrome} aria-hidden="true">
                      <i />
                      <i />
                      <i />
                      <i />
                    </span>
                  )}
                  <span className={s.screenLines} aria-hidden="true">
                    <i />
                    <i />
                    <i />
                    <i />
                  </span>
                  <span className={cx(s.screenUrl, s.truncate)} title={screenText}>
                    {screenText}
                  </span>
                </div>
              </div>

              <div className={s.deviceMeta}>
                <span className={s.deviceName}>
                  {dev.icon}
                  {dev.name}
                </span>
                <span className={cx('chip chip--sm', isCrawlingThis ? 'chip--info chip--live' : 'chip--neutral')}>
                  {isCrawlingThis ? 'Crawling now' : 'Ready'}
                </span>
                <span className={s.deviceRes}>{dev.resolution}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
