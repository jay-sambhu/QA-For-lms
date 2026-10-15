"use client";

import React, { useLayoutEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';

/**
 * Replays a short 3D rise-in whenever the route changes (not on first load).
 * Starts before paint so the new page never flashes, pivots around the part of
 * the page in view, and leaves no transform behind once finished.
 */
export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const ref = useRef<HTMLDivElement>(null);
  const lastPath = useRef(pathname);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || lastPath.current === pathname) return;
    lastPath.current = pathname;
    const top = el.getBoundingClientRect().top;
    el.style.transformOrigin = `50% ${Math.round(window.innerHeight * 0.4 - top)}px`;
    el.dataset.enter = el.dataset.enter === 'a' ? 'b' : 'a';
  }, [pathname]);

  const onAnimationEnd = (e: React.AnimationEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget) return;
    delete e.currentTarget.dataset.enter;
  };

  return (
    <div ref={ref} className="page-transition" onAnimationEnd={onAnimationEnd}>
      {children}
    </div>
  );
}
