import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
import styles from "./page.module.css";

export default function Home() {
  return (
    <main className={styles.main}>
      <div className={`${styles.glow} ${styles.glowPrimary}`} />
      <div className={`${styles.glow} ${styles.glowSecondary}`} />

      <div className={`glass-panel ${styles.heroContent}`}>
        <div className={styles.badge}>
          <Sparkles size={16} />
          <span>AI-Powered Career Growth</span>
        </div>

        <h1 className={styles.title}>
          Master Your <br />
          <span className="text-gradient">Tech Stack</span>
        </h1>

        <p className={styles.description}>
          Prove your skills with AI interviewers, unlock new levels,
          and build a visual roadmap of your expertise.
        </p>

        <div className={styles.actions}>
          <Link href="/dashboard" className="button-primary">
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              Start Your Journey
              <ArrowRight size={18} />
            </span>
          </Link>
          <Link href="/about" className={styles.secondaryButton}>
            Learn More
          </Link>
        </div>
      </div>
    </main>
  );
}
