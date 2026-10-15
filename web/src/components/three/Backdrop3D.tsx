import styles from './three.module.css';

/** Fixed perspective grid floor and soft light orbs behind every page. */
export function Backdrop3D() {
  return (
    <div className={styles.backdrop} aria-hidden="true">
      <div className={`${styles.orb} ${styles.orbA}`} />
      <div className={`${styles.orb} ${styles.orbB}`} />
      <div className={`${styles.orb} ${styles.orbC}`} />
      <div className={styles.floor} />
    </div>
  );
}
