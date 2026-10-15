"use client";

import React, { useImperativeHandle, useRef } from 'react';
import { useTilt3D } from './useTilt3D';
import { accentProps, cx, type Accent } from './accent';

type SurfaceTag = 'div' | 'section' | 'article' | 'aside' | 'header' | 'footer' | 'li';

export type Surface3DProps = React.HTMLAttributes<HTMLElement> & {
  /** Element to render; defaults to div */
  as?: SurfaceTag;
  /** Tilt toward the pointer (desktop only). Use for small self-contained cards. */
  tilt?: boolean;
  /** Maximum tilt in degrees */
  max?: number;
  /** Soft light sweep while tilting */
  glare?: boolean;
  /** Corner glow, lit top edge and tinted hover shadow: a tone keyword, a hex color, or true for the inherited page tone */
  accent?: Accent | boolean;
  /** Hover lift + pointer cursor, for cards that are clickable */
  interactive?: boolean;
  /** Animated multicolor border, for the one primary panel on a page */
  ring?: boolean;
  /** Inner padding: none 0, sm 16px, md 24px (default), lg 32px */
  pad?: 'none' | 'sm' | 'md' | 'lg';
  ref?: React.Ref<HTMLElement>;
};

const PAD_CLASS = {
  none: 'surface-3d--pad-0',
  sm: 'surface-3d--pad-sm',
  md: '',
  lg: 'surface-3d--pad-lg',
} as const;

/** White card with layered depth; the building block for every panel. */
export function Surface3D({
  as: Tag = 'div',
  tilt = false,
  max = 6,
  glare = true,
  accent,
  interactive = false,
  ring = false,
  pad = 'md',
  className,
  style,
  children,
  ref,
  onPointerEnter,
  onPointerMove,
  onPointerLeave,
  ...rest
}: Surface3DProps) {
  const innerRef = useRef<HTMLElement>(null);
  const t = useTilt3D(innerRef, { max, enabled: tilt });
  const a = typeof accent === 'string' ? accentProps(accent) : {};

  useImperativeHandle(ref, () => innerRef.current as HTMLElement);

  const Element = Tag as React.ElementType;

  return (
    <Element
      {...rest}
      ref={innerRef}
      className={cx(
        'surface-3d',
        accent && 'surface-3d--accent',
        interactive && 'surface-3d--interactive',
        ring && 'gradient-ring',
        PAD_CLASS[pad],
        a.className,
        tilt && t.className,
        className,
      )}
      style={a.style ? { ...a.style, ...style } : style}
      onPointerEnter={(e: React.PointerEvent<HTMLElement>) => {
        onPointerEnter?.(e);
        if (tilt) t.handlers.onPointerEnter(e);
      }}
      onPointerMove={(e: React.PointerEvent<HTMLElement>) => {
        onPointerMove?.(e);
        if (tilt) t.handlers.onPointerMove(e);
      }}
      onPointerLeave={(e: React.PointerEvent<HTMLElement>) => {
        onPointerLeave?.(e);
        if (tilt) t.handlers.onPointerLeave();
      }}
    >
      {children}
      {tilt && glare && t.enabled && <span className={t.glareClassName} aria-hidden="true" />}
    </Element>
  );
}
