"use client";

import React, { useEffect, useRef } from 'react';
import styles from './three.module.css';
import { canAnimate3D } from './motion';

// Page blocks on the map, in % of the plane, with extrusion height in px
const NODES = [
  { x: 18, y: 22, h: 30, d: '0s' },
  { x: 50, y: 18, h: 44, d: '-1.2s' },
  { x: 82, y: 26, h: 26, d: '-2.1s' },
  { x: 30, y: 56, h: 22, d: '-0.6s' },
  { x: 64, y: 54, h: 36, d: '-3s' },
  { x: 20, y: 84, h: 18, d: '-1.8s' },
  { x: 52, y: 86, h: 28, d: '-2.6s' },
  { x: 84, y: 78, h: 20, d: '-0.9s' },
];

// Crawl paths between pages (indexes into NODES)
const LINKS: [number, number][] = [
  [1, 0], [1, 2], [1, 4], [0, 3], [3, 5], [4, 6], [4, 7], [3, 6],
];

const PINS = [
  { x: 64, y: 54, ok: false, d: '0s' },
  { x: 20, y: 84, ok: false, d: '-1.1s' },
  { x: 82, y: 26, ok: true, d: '-0.5s' },
  { x: 50, y: 18, ok: true, d: '-1.6s' },
];

/** Isometric "site being mapped" scene for the landing hero. */
export const Hero3DMap: React.FC = () => {
  const sceneRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const scene = sceneRef.current;
    const stage = stageRef.current;
    if (!scene || !stage || !canAnimate3D()) return;
    let frame = 0;
    const onMove = (e: PointerEvent) => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const r = scene.getBoundingClientRect();
        const px = (e.clientX - (r.left + r.width / 2)) / window.innerWidth;
        const py = (e.clientY - (r.top + r.height / 2)) / window.innerHeight;
        stage.style.setProperty('--sx', `${(-py * 10).toFixed(2)}deg`);
        stage.style.setProperty('--sy', `${(px * 14).toFixed(2)}deg`);
      });
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('pointermove', onMove);
    };
  }, []);

  return (
    <div ref={sceneRef} className={styles.scene} aria-hidden="true">
      <div ref={stageRef} className={styles.stage}>
        <div className={styles.plane}>
          <div className={styles.beamClip}>
            <div className={styles.beam} />
          </div>
          <svg className={styles.links} viewBox="0 0 100 100" preserveAspectRatio="none">
            {LINKS.map(([a, b]) => (
              <path
                key={`${a}-${b}`}
                className={styles.link}
                d={`M${NODES[a].x} ${NODES[a].y} Q ${(NODES[a].x + NODES[b].x) / 2} ${Math.min(NODES[a].y, NODES[b].y) - 6} ${NODES[b].x} ${NODES[b].y}`}
              />
            ))}
          </svg>
          {NODES.map((n, i) => (
            <div
              key={i}
              className={styles.node}
              style={{ left: `${n.x}%`, top: `${n.y}%`, ['--h' as string]: `${n.h}px`, ['--d' as string]: n.d }}
            >
              <div className={styles.nodeShadow} />
              <div className={styles.nodeBody}>
                <div className={styles.nodeWall} />
                <div className={styles.nodeWallSide} />
                <div className={styles.nodeTop} />
              </div>
            </div>
          ))}
          {PINS.map((p, i) => (
            <div
              key={i}
              className={`${styles.pin} ${p.ok ? styles.pinOk : ''}`}
              style={{ left: `${p.x}%`, top: `${p.y}%`, ['--d' as string]: p.d }}
            >
              <div className={styles.pinStem} />
              <div className={styles.pinHead} />
            </div>
          ))}
        </div>
      </div>

      <div className={styles.devices}>
        <div className={`${styles.device} ${styles.deviceDesktop}`}>
          <span className={styles.deviceLabel}>Desktop 1920</span>
          <i /><i /><i />
        </div>
        <div className={`${styles.device} ${styles.deviceTablet}`}>
          <span className={styles.deviceLabel}>iPad</span>
          <i /><i /><i />
        </div>
        <div className={`${styles.device} ${styles.devicePhone}`}>
          <span className={styles.deviceLabel}>iPhone</span>
          <i /><i />
        </div>
        <div className={styles.scoreChip}>
          <span className={styles.scoreValue}>A+</span>
          <span className={styles.scoreText}>Quality score<br />8 pages mapped</span>
        </div>
      </div>
    </div>
  );
};
