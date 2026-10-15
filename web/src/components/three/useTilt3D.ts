"use client";

import type React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import styles from './three.module.css';
import { useCanAnimate3D } from './motion';

type TiltOptions = {
  /** Maximum rotation in degrees */
  max?: number;
  /** Turn the tilt off without unmounting */
  enabled?: boolean;
};

/**
 * Pointer-driven 3D tilt for any element. Writes CSS variables inside
 * requestAnimationFrame, so moving the pointer never re-renders React.
 * Inactive on touch screens and when the user prefers reduced motion.
 */
export function useTilt3D<T extends HTMLElement>(
  ref: React.RefObject<T | null>,
  { max = 8, enabled = true }: TiltOptions = {},
) {
  const frame = useRef<number | null>(null);
  const canAnimate = useCanAnimate3D();
  const on = enabled && canAnimate;
  const [hovering, setHovering] = useState(false);

  const cancelFrame = useCallback(() => {
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    frame.current = null;
  }, []);

  useEffect(() => cancelFrame, [cancelFrame]);

  const onPointerLeave = useCallback(() => {
    cancelFrame();
    setHovering(false);
    const el = ref.current;
    if (!el) return;
    el.style.setProperty('--rx', '0deg');
    el.style.setProperty('--ry', '0deg');
  }, [ref, cancelFrame]);

  useEffect(() => {
    if (!on) onPointerLeave();
  }, [on, onPointerLeave]);

  const onPointerEnter = useCallback(
    (e: React.PointerEvent<T>) => {
      if (on && e.pointerType !== 'touch') setHovering(true);
    },
    [on],
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent<T>) => {
      const el = ref.current;
      if (!on || !el || e.pointerType === 'touch') return;
      const { clientX, clientY } = e;
      cancelFrame();
      frame.current = requestAnimationFrame(() => {
        frame.current = null;
        const r = el.getBoundingClientRect();
        const px = (clientX - r.left) / r.width;
        const py = (clientY - r.top) / r.height;
        el.style.setProperty('--ry', `${((px - 0.5) * 2 * max).toFixed(2)}deg`);
        el.style.setProperty('--rx', `${((0.5 - py) * 2 * max).toFixed(2)}deg`);
        el.style.setProperty('--gx', `${(px * 100).toFixed(1)}%`);
        el.style.setProperty('--gy', `${(py * 100).toFixed(1)}%`);
      });
    },
    [ref, on, max, cancelFrame],
  );

  const active = on && hovering;

  return {
    /** Tilt can run on this device */
    enabled: on,
    /** Pointer is over the element and it is tilting */
    active,
    className: active ? `${styles.tilt} ${styles.tiltActive}` : styles.tilt,
    glareClassName: styles.glare,
    handlers: { onPointerEnter, onPointerMove, onPointerLeave },
  };
}
