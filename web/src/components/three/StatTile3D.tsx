"use client";

import React from 'react';
import { Surface3D } from './Surface3D';
import { cx, type Accent } from './accent';
import s from './primitives.module.css';

export type StatTrend = {
  value: string;
  /** Good news (green) or bad news (red) */
  positive: boolean;
  /** Arrow direction; defaults to up when positive, down when not */
  direction?: 'up' | 'down';
  /** Muted text after the chip, e.g. "vs last week" */
  label?: string;
};

export type StatTile3DProps = {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  /** Tone keyword or hex for the icon well, glow and hover shadow; inherits the page tone when omitted */
  accent?: Accent;
  hint?: React.ReactNode;
  trend?: StatTrend;
  /** Makes the whole tile one button */
  onClick?: () => void;
  /** Accessible name when clickable; defaults to "label: value" */
  actionLabel?: string;
  /** Smaller value text, for words such as "Operational" */
  compact?: boolean;
  /** Paint the value in the accent gradient instead of ink */
  valueAccent?: boolean;
  /** Pointer tilt on desktop; on by default */
  tilt?: boolean;
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
};

function TrendArrow({ up }: { up: boolean }) {
  return (
    <svg width="9" height="9" viewBox="0 0 10 10" aria-hidden="true">
      <path d={up ? 'M5 1.5 9 7.5H1z' : 'M5 8.5 1 2.5h8z'} fill="currentColor" />
    </svg>
  );
}

/** Dashboard / admin metric tile: label, big number, floating icon, optional trend. */
export function StatTile3D({
  label,
  value,
  icon,
  accent,
  hint,
  trend,
  onClick,
  actionLabel,
  compact = false,
  valueAccent = false,
  tilt = true,
  className,
  style,
  children,
}: StatTile3DProps) {
  const up = trend ? (trend.direction ?? (trend.positive ? 'up' : 'down')) === 'up' : false;
  const name =
    actionLabel ?? (typeof value === 'string' || typeof value === 'number' ? `${label}: ${value}` : label);

  return (
    <Surface3D
      tilt={tilt}
      max={7}
      accent={accent ?? true}
      interactive={!!onClick}
      className={cx(s.statTile, compact && s.statCompact, onClick && s.statClickable, className)}
      style={style}
    >
      <span className={s.statLabel}>{label}</span>
      {icon && (
        <span className={cx('icon-well', s.statIcon)} data-depth="2" aria-hidden="true">
          {icon}
        </span>
      )}
      <span
        className={cx('stat-number', compact && 'stat-number--sm', valueAccent && 'stat-number--accent', s.statValue)}
        data-depth="1"
      >
        {value}
      </span>
      {(hint || trend) && (
        <span className={s.statMeta}>
          {trend && (
            <span className={cx('chip chip--sm', trend.positive ? 'chip--success' : 'chip--danger')}>
              <TrendArrow up={up} />
              {trend.value}
            </span>
          )}
          {trend?.label && <span>{trend.label}</span>}
          {hint && <span>{hint}</span>}
        </span>
      )}
      {children && <div className={s.statExtra}>{children}</div>}
      {onClick && <button type="button" className={s.statHit} onClick={onClick} aria-label={name} />}
    </Surface3D>
  );
}
