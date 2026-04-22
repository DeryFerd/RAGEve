"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAppStore } from "@/stores/useAppStore";
import styles from "./Sidebar.module.css";

const NAV_ITEMS = [
  {
    href: "/models",
    label: "Models",
    icon: (
      <img src="/ollama.png" alt="Models" className={styles.navIcon} />
    ),
  },
  {
    href: "/datasets",
    label: "Datasets",
    icon: (
      <img src="/datasets.png" alt="Datasets" className={styles.navIcon} />
    ),
  },
  {
    href: "/huggingface",
    label: "HuggingFace",
    icon: (
      <img src="/huggingface.png" alt="HuggingFace" className={styles.navIcon} />
    ),
  },
  {
    href: "/agents",
    label: "Agents",
    icon: (
      <img src="/agent.png" alt="Chat" className={styles.navIcon} />
    ),
  },
  {
    href: "/chat",
    label: "Chat",
    icon: (
      <img src="/chat.png" alt="Chat" className={styles.navIcon} />
    ),
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, setSidebarCollapsed } = useAppStore();

  return (
    <aside className={`${styles.sidebar} ${sidebarCollapsed ? styles.collapsed : ""}`}>
      <div className={styles.logo}>
        <img src="/logo.png" alt="RAGEve logo" className={styles.logoIcon} />
        <span className={styles.logoText}>RAGEve</span>
      </div>

      <nav className={styles.nav}>
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navItem} ${active ? styles.active : ""}`}
              title={item.label}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              <span className={styles.navLabel}>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <button
        className={styles.collapseBtn}
        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          style={{ transform: sidebarCollapsed ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}
        >
          <path d="M10 3L5 8l5 5" />
        </svg>
      </button>
    </aside>
  );
}
