"use client";

import React from 'react';
import { LazyMotion } from 'framer-motion';

const loadFeatures = () => import('../lib/motionFeatures').then((mod) => mod.default);

export const MotionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <LazyMotion features={loadFeatures}>{children}</LazyMotion>
);
