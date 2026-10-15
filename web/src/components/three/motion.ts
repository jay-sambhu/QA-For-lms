import { useSyncExternalStore } from 'react';

const FINE_POINTER = '(hover: hover) and (pointer: fine)';
const REDUCED_MOTION = '(prefers-reduced-motion: reduce)';

let queries: [MediaQueryList, MediaQueryList] | null = null;

function mediaQueries(): [MediaQueryList, MediaQueryList] | null {
  if (typeof window === 'undefined' || !window.matchMedia) return null;
  if (!queries) queries = [window.matchMedia(FINE_POINTER), window.matchMedia(REDUCED_MOTION)];
  return queries;
}

/** True when the device has a precise pointer and the user allows motion. */
export function canAnimate3D(): boolean {
  const mq = mediaQueries();
  return !!mq && mq[0].matches && !mq[1].matches;
}

function prefersReducedMotion(): boolean {
  const mq = mediaQueries();
  return !!mq && mq[1].matches;
}

function subscribe(onChange: () => void) {
  const mq = mediaQueries();
  if (!mq) return () => {};
  mq.forEach((q) => q.addEventListener('change', onChange));
  return () => mq.forEach((q) => q.removeEventListener('change', onChange));
}

const onServer = () => false;

/** Reactive canAnimate3D(): false on the server and during hydration, then follows the device. */
export function useCanAnimate3D(): boolean {
  return useSyncExternalStore(subscribe, canAnimate3D, onServer);
}

/** Reactive prefers-reduced-motion. */
export function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(subscribe, prefersReducedMotion, onServer);
}
