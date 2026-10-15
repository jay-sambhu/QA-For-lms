"use client";

import React, { useCallback } from 'react';
import { accentProps, cx, type Accent } from './accent';
import s from './primitives.module.css';

export type SegmentedTab<T extends string = string> = {
  id: T;
  label: React.ReactNode;
  icon?: React.ReactNode;
  /** Count or short text shown in a small pill (0 is shown) */
  badge?: React.ReactNode;
};

export type SegmentedTabs3DProps<T extends string = string> = {
  tabs: SegmentedTab<T>[];
  active: T;
  onChange: (id: T) => void;
  /** Accessible name of the tab list */
  ariaLabel?: string;
  /** md for page sections (default), sm for inline filters */
  size?: 'sm' | 'md';
  /** Stretch tabs to fill the row */
  fullWidth?: boolean;
  /** Tone for the selected tab; inherits the page tone when omitted */
  accent?: Accent;
  /** When set, tabs get id `${idPrefix}-tab-${id}` and aria-controls `${idPrefix}-panel-${id}` */
  idPrefix?: string;
  className?: string;
};

/** Tab switcher whose selected tab rises out of the groove as a raised 3D pill. */
export function SegmentedTabs3D<T extends string>({
  tabs,
  active,
  onChange,
  ariaLabel,
  size = 'md',
  fullWidth = false,
  accent,
  idPrefix,
  className,
}: SegmentedTabs3DProps<T>) {
  const a = accentProps(accent);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLButtonElement>) => {
      const index = tabs.findIndex((t) => t.id === active);
      let next = -1;
      if (e.key === 'ArrowRight') next = (index + 1) % tabs.length;
      else if (e.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
      else if (e.key === 'Home') next = 0;
      else if (e.key === 'End') next = tabs.length - 1;
      if (next < 0 || !tabs[next]) return;
      e.preventDefault();
      onChange(tabs[next].id);
      const list = e.currentTarget.parentElement;
      const target = list?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next];
      target?.focus();
    },
    [tabs, active, onChange],
  );

  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cx(s.seg, size === 'sm' && s.segSm, fullWidth && s.segFull, a.className, className)}
      style={a.style}
    >
      {tabs.map((tab) => {
        const selected = tab.id === active;
        const hasBadge = tab.badge !== undefined && tab.badge !== null && tab.badge !== false && tab.badge !== '';
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={idPrefix ? `${idPrefix}-tab-${tab.id}` : undefined}
            aria-controls={idPrefix ? `${idPrefix}-panel-${tab.id}` : undefined}
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            className={s.segTab}
            onClick={() => onChange(tab.id)}
            onKeyDown={onKeyDown}
          >
            {tab.icon}
            <span>{tab.label}</span>
            {hasBadge && <span className={s.segBadge}>{tab.badge}</span>}
          </button>
        );
      })}
    </div>
  );
}
