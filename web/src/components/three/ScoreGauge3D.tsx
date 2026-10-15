import React from 'react';
import { cx, scoreTone } from './accent';
import s from './primitives.module.css';

export type ScoreGauge3DProps = {
  /** Quality score, 0-100 */
  score: number;
  /** Letter grade shown under the number, e.g. "A+" */
  grade?: string;
  /** Diameter in px (default 168, minimum 96) */
  size?: number;
  /** Caption under the dial, e.g. "Quality score" */
  label?: string;
  className?: string;
  style?: React.CSSProperties;
};

/**
 * Tilted 3D ring gauge for a 0-100 score. Red below 60, amber below 80, green from 80.
 * Rises into place once on mount; static afterwards.
 */
export function ScoreGauge3D({ score, grade, size = 168, label, className, style }: ScoreGauge3DProps) {
  const value = Number.isFinite(score) ? Math.round(Math.min(100, Math.max(0, score))) : 0;
  const tone = scoreTone(value);
  const diameter = Math.max(96, size);
  const vars = {
    ['--size' as string]: `${diameter}px`,
    ['--deg' as string]: `${value * 3.6}deg`,
  } as React.CSSProperties;

  return (
    <div
      className={cx(s.gauge, `tone-${tone}`, value === 0 && s.gaugeEmpty, className)}
      style={{ ...vars, ...style }}
      role="img"
      aria-label={`${label ?? 'Score'} ${value} out of 100${grade ? `, grade ${grade}` : ''}`}
    >
      <div className={s.gaugeStage}>
        <div className={s.gaugeDish}>
          <span className={s.gaugeShadow} />
          <span className={s.gaugeEdge} style={{ ['--z' as string]: '-8px' } as React.CSSProperties} />
          <span className={s.gaugeEdge} style={{ ['--z' as string]: '-4px' } as React.CSSProperties} />
          <span className={s.gaugeRing} />
          <span className={s.gaugeCap} />
          <span className={s.gaugeKnob} />
          <span className={s.gaugeFace} />
        </div>
        <div className={s.gaugeReadout}>
          <span className={s.gaugeValue}>{value}</span>
          {grade && <span className={`chip chip--solid chip--${tone}`}>{grade}</span>}
        </div>
      </div>
      {label && <span className={s.gaugeLabel}>{label}</span>}
    </div>
  );
}
