"use client";

import React, { useEffect, useRef, useState } from 'react';
import styles from './three.module.css';

type RevealProps = {
  children: React.ReactNode;
  as?: 'div' | 'section';
  className?: string;
  style?: React.CSSProperties;
  /** Stagger delay in ms */
  delay?: number;
};

/** Rises into place with a 3D tilt the first time it scrolls into view. */
export const Reveal: React.FC<RevealProps> = ({ children, as = 'div', className, style, delay = 0 }) => {
  const ref = useRef<HTMLElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === 'undefined') {
      setShown(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setShown(true);
          io.disconnect();
        }
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.08 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const Tag = as;
  return (
    <Tag
      ref={ref as React.Ref<HTMLDivElement>}
      className={`${styles.reveal} ${shown ? styles.revealed : ''} ${className ?? ''}`}
      style={{ ...style, ['--reveal-delay' as string]: `${delay}ms` }}
    >
      {children}
    </Tag>
  );
};
