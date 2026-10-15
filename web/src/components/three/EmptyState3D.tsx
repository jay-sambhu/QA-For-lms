import React from 'react';
import { accentProps, cx, type Accent } from './accent';
import s from './primitives.module.css';

export type EmptyState3DProps = {
  title: React.ReactNode;
  description?: React.ReactNode;
  /** Button or link that resolves the empty state */
  action?: React.ReactNode;
  /** Small icon floating beside the stack */
  icon?: React.ReactNode;
  accent?: Accent;
  /** Tighter version for table bodies and small panels */
  compact?: boolean;
  className?: string;
  style?: React.CSSProperties;
};

/** Friendly empty state with a floating stack of 3D tiles drawn in CSS. */
export function EmptyState3D({ title, description, action, icon, accent, compact = false, className, style }: EmptyState3DProps) {
  const a = accentProps(accent);

  return (
    <div
      className={cx(s.empty, compact && s.emptyCompact, a.className, className)}
      style={a.style ? { ...a.style, ...style } : style}
    >
      <div className={s.emptyStage} aria-hidden="true">
        <div className={s.emptyStack}>
          <span className={cx(s.emptyLayer, s.emptyShadow)} />
          <span className={cx(s.emptyLayer, s.emptyLayer1)} />
          <span className={cx(s.emptyLayer, s.emptyLayer2)} />
          <span className={cx(s.emptyLayer, s.emptyLayer3)}>
            <i />
            <i />
            <i />
          </span>
        </div>
        {icon && <span className={cx('icon-well icon-well--sm icon-well--solid', s.emptyIcon)}>{icon}</span>}
      </div>
      <h3 className={s.emptyTitle}>{title}</h3>
      {description && <p className={s.emptyDesc}>{description}</p>}
      {action && <div className={s.emptyAction}>{action}</div>}
    </div>
  );
}
