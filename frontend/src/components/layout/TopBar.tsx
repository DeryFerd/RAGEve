"use client";

import styles from "./TopBar.module.css";

export function TopBar() {
  return (
    <header className={styles.topbar}>
      {/* Left side intentionally empty for future use */}
      <div className={styles.left} />

      {/* Right side intentionally empty for future use */}
      <div className={styles.right} />
    </header>
  );
}
