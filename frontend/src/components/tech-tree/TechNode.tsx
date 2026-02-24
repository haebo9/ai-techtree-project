import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Star, Lock } from 'lucide-react';
import { TechNodeData } from '@/types/techtree';
import styles from './TechNode.module.css';

const TechNode = ({ data, selected }: NodeProps<TechNodeData>) => {
    const isLocked = data.status === 'locked';

    return (
        <div
            className={`
        ${styles.nodeWrapper} 
        ${styles[data.status]} 
        ${selected ? styles.selected : ''}
      `}
        >
            <Handle
                type="target"
                position={Position.Top}
                className={styles.handle}
            />

            <div className={styles.header}>
                <span className={styles.title}>{data.label}</span>
                {isLocked ? (
                    <Lock size={14} style={{ color: 'hsl(var(--color-text-muted))' }} />
                ) : (
                    <div className={styles.stars}>
                        {/* Level 1 Star */}
                        <Star
                            size={12}
                            fill={data.stars >= 1 ? "currentColor" : "transparent"}
                            className={data.stars >= 1
                                ? (data.status === 'mastered' ? styles.starGold : styles.starActive)
                                : styles.starInactive}
                        />
                        {/* Level 2 Star */}
                        <Star
                            size={12}
                            fill={data.stars >= 2 ? "currentColor" : "transparent"}
                            className={data.stars >= 2
                                ? (data.status === 'mastered' ? styles.starGold : styles.starActive)
                                : styles.starInactive}
                        />
                        {/* Level 3 Star */}
                        <Star
                            size={12}
                            fill={data.stars >= 3 ? "currentColor" : "transparent"}
                            className={data.stars >= 3
                                ? styles.starGold  // 3rd star is always gold if achieved (implies mastery)
                                : styles.starInactive}
                        />
                    </div>
                )}
            </div>

            <p className={styles.description}>{data.description}</p>

            <Handle
                type="source"
                position={Position.Bottom}
                className={styles.handle}
            />
        </div >
    );
};

export default memo(TechNode);
