"use client";

import React, { useCallback, useEffect, useRef } from 'react';
import { accentProps, cx, isTone, type Accent } from './accent';
import { useCanAnimate3D } from './motion';
import s from './primitives.module.css';

export type PageHeader3DProps = {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  /** Buttons / links shown under the subtitle */
  actions?: React.ReactNode;
  /** Text renders as a solid chip in the accent tone; a node renders as-is */
  badge?: React.ReactNode;
  /** Icon shown in a solid accent tile before the title */
  icon?: React.ReactNode;
  /** Accent tone; inherits the page tone when omitted (admin pages pass "violet" or sit inside .tone-violet) */
  accent?: Accent;
  /** Heading level of the title (default h1) */
  as?: 'h1' | 'h2';
  className?: string;
  style?: React.CSSProperties;
  /** Extra content under the actions */
  children?: React.ReactNode;
};

/** Page title block with a light 3D scene of floating shapes that drift with the pointer. */
export function PageHeader3D({
  eyebrow,
  title,
  subtitle,
  actions,
  badge,
  icon,
  accent,
  as: Heading = 'h1',
  className,
  style,
  children,
}: PageHeader3DProps) {
  const sceneRef = useRef<HTMLDivElement>(null);
  const frame = useRef<number | null>(null);
  const motionOK = useCanAnimate3D();
  const a = accentProps(accent);

  useEffect(
    () => () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current);
    },
    [],
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if (!motionOK || e.pointerType === 'touch') return;
      const target = e.currentTarget;
      const { clientX, clientY } = e;
      if (frame.current !== null) cancelAnimationFrame(frame.current);
      frame.current = requestAnimationFrame(() => {
        frame.current = null;
        const scene = sceneRef.current;
        if (!scene) return;
        const r = target.getBoundingClientRect();
        scene.style.setProperty('--mx', (((clientX - r.left) / r.width) * 2 - 1).toFixed(3));
        scene.style.setProperty('--my', (((clientY - r.top) / r.height) * 2 - 1).toFixed(3));
      });
    },
    [motionOK],
  );

  const onPointerLeave = useCallback(() => {
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    frame.current = null;
    const scene = sceneRef.current;
    if (!scene) return;
    scene.style.setProperty('--mx', '0');
    scene.style.setProperty('--my', '0');
  }, []);

  const hasBadge = badge !== undefined && badge !== null && badge !== false && badge !== '';
  const badgeTone = accent && isTone(accent) ? `chip--${accent}` : 'chip--accent';

  return (
    <header
      className={cx('surface-3d surface-3d--accent', s.ph, a.className, className)}
      style={a.style ? { ...a.style, ...style } : style}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
    >
      <div ref={sceneRef} className={s.phScene} aria-hidden="true">
        <span className={s.phGlow} />
        <span className={s.phGrid} />
        <span className={cx(s.phItem, s.phCardPos)}>
          <span className={s.phCard}>
            <i />
            <i />
            <i />
          </span>
        </span>
        <span className={cx(s.phItem, s.phCubePos)}>
          <span className={s.phCube}>
            <i />
            <i />
            <i />
          </span>
        </span>
        <span className={cx(s.phItem, s.phRingPos)}>
          <span className={s.phRing} />
        </span>
        <span className={cx(s.phItem, s.phOrbPos)}>
          <span className={s.phOrb} />
        </span>
      </div>

      <div className={s.phCopy}>
        {eyebrow && <span className="section-eyebrow">{eyebrow}</span>}
        <div className={s.phTitleRow}>
          {icon && (
            <span className="icon-well icon-well--solid icon-well--lg" aria-hidden="true">
              {icon}
            </span>
          )}
          <Heading className={s.phTitle}>{title}</Heading>
          {hasBadge &&
            (typeof badge === 'string' || typeof badge === 'number' ? (
              <span className={cx('chip chip--solid', badgeTone)}>{badge}</span>
            ) : (
              badge
            ))}
        </div>
        {subtitle && <p className={s.phSubtitle}>{subtitle}</p>}
        {actions && <div className={s.phActions}>{actions}</div>}
        {children}
      </div>
    </header>
  );
}
