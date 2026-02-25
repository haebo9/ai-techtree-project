import TechTreeMap from '@/components/tech-tree/TechTreeMap';
import { Sparkles } from 'lucide-react';
import Link from 'next/link';
import styles from './dashboard.module.css';

export default function DashboardPage() {
    return (
        <main className={styles.mainContainer}>
            {/* Top Navigation Bar */}
            <header className={styles.header}>
                <Link href="/" className={styles.logoArea}>
                    <Sparkles className={styles.iconSecondary} />
                    <span>AI TechTree</span>
                </Link>

                <div className={styles.userArea}>
                    <div className={styles.trackBadge}>
                        Backend Track
                    </div>
                    <div className={styles.avatar} />
                </div>
            </header>

            {/* Main Workspace */}
            <div className={styles.workspace}>
                <div className={styles.mapContainer}>
                    <TechTreeMap />
                </div>

                {/* Overlay Info */}
                <div className={`glass-panel ${styles.overlay}`}>
                    <h3 className={styles.overlayTitle}>My Progress</h3>
                    <div className={styles.overlayItem}>
                        <span className={`${styles.dot} ${styles.dotGold}`}></span>
                        1 Mastered
                    </div>
                    <div className={styles.overlayItem}>
                        <span className={`${styles.dot} ${styles.dotPrimary}`}></span>
                        2 In Progress
                    </div>
                </div>
            </div>
        </main>
    );
}
