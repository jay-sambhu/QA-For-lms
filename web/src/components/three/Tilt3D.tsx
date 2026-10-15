"use client";

import React, { useCallback, useEffect, useRef, useState } from 'react';
import styles from './three.module.css';
import { canAnimate3D } from './motion';

type Tilt3DProps = Omit<React.HTMLAttributes<HTMLDivElement>, 'onPointerEnter' | 'onPointerMove' | 'onPointerLeave'> & {
  children: React.ReactNode;
  /** Maximum rotation in degrees */
  max?: number;
  glare?: boolean;
};

/**
 * Card that tilts toward the pointer in 3D, lifts off the page and
 * catches a soft glare. Children marked data-depth="1|2" float above it.
 */
export const Tilt3D: React.FC<Tilt3DProps> = ({ children, className, max = 8, glare = true, ...rest }) => {
  const ref = useRef<HTMLDivElement>(null);
  const frame = useRef<number | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [active, setActive] = useState(false);

  useEffect(() => {
    setEnabled(canAnimate3D());
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current);
    };
  }, []);

  const onMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const el = ref.current;
      if (!enabled || !el) return;
      const { clientX, clientY } = e;
      if (frame.current) cancelAnimationFrame(frame.current);
      frame.current = requestAnimationFrame(() => {
        const r = el.getBoundingClientRect();
        const px = (clientX - r.left) / r.width;
        const py = (clientY - r.top) / r.height;
        el.style.setProperty('--ry', `${((px - 0.5) * 2 * max).toFixed(2)}deg`);
        el.style.setProperty('--rx', `${((0.5 - py) * 2 * max).toFixed(2)}deg`);
        el.style.setProperty('--gx', `${(px * 100).toFixed(1)}%`);
        el.style.setProperty('--gy', `${(py * 100).toFixed(1)}%`);
      });
    },
    [enabled, max],
  );

  const onLeave = useCallback(() => {
    const el = ref.current;
    if (frame.current) cancelAnimationFrame(frame.current);
    setActive(false);
    if (!el) return;
    el.style.setProperty('--rx', '0deg');
    el.style.setProperty('--ry', '0deg');
  }, []);

  return (
    <div
      {...rest}
      ref={ref}
      className={`${styles.tilt} ${active ? styles.tiltActive : ''} ${className ?? ''}`}
      onPointerEnter={() => enabled && setActive(true)}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
    >
      {children}
      {glare && enabled && <span className={styles.glare} aria-hidden="true" />}
    </div>
  );
};
