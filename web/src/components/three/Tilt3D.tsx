"use client";

import React, { useRef } from 'react';
import { useTilt3D } from './useTilt3D';

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
  const tilt = useTilt3D(ref, { max });

  return (
    <div
      {...rest}
      ref={ref}
      className={`${tilt.className} ${className ?? ''}`}
      {...tilt.handlers}
    >
      {children}
      {glare && tilt.enabled && <span className={tilt.glareClassName} aria-hidden="true" />}
    </div>
  );
};
