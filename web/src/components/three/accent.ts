import type React from 'react';

/** Semantic colors: primary indigo, success emerald, warning amber, danger rose, info sky. */
export type Tone = 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'violet' | 'neutral';

/** A tone keyword (preferred) or a hex color such as '#0891b2'. */
export type Accent = Tone | `#${string}`;

const TONES: readonly string[] = ['primary', 'success', 'warning', 'danger', 'info', 'violet', 'neutral'];

export function isTone(value: string): value is Tone {
  return TONES.includes(value);
}

function hexToRgb(hex: string): [number, number, number] | null {
  let h = hex.replace('#', '');
  if (h.length === 3 || h.length === 4) h = h.slice(0, 3).split('').map((c) => c + c).join('');
  if (h.length !== 6 && h.length !== 8) return null;
  const rgb = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  return rgb.some(Number.isNaN) ? null : [rgb[0], rgb[1], rgb[2]];
}

/**
 * Class name and/or inline CSS variables that set --accent-rgb and --accent-ink
 * for an element and its subtree.
 */
export function accentProps(accent?: Accent): { className?: string; style?: React.CSSProperties } {
  if (!accent) return {};
  if (isTone(accent)) return { className: `tone-${accent}` };
  const rgb = hexToRgb(accent);
  if (!rgb) return {};
  const ink = rgb.map((c) => Math.round(c * 0.72));
  return {
    style: {
      ['--accent-rgb' as string]: rgb.join(', '),
      ['--accent-ink' as string]: `rgb(${ink.join(', ')})`,
    } as React.CSSProperties,
  };
}

/** Tone for a 0-100 quality score: green from 80, amber from 60, red below. */
export function scoreTone(score: number): Tone {
  if (score >= 80) return 'success';
  if (score >= 60) return 'warning';
  return 'danger';
}

export function cx(...parts: Array<string | false | null | undefined | 0>): string {
  return parts.filter(Boolean).join(' ');
}
