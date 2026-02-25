export type SkillStatus = 'locked' | 'available' | 'in_progress' | 'completed' | 'mastered';

export interface TechNodeData {
    id: string;
    label: string;
    description: string;
    status: SkillStatus;
    stars: 0 | 1 | 2 | 3;
    icon?: string; // We can use lucide icon names or image URLs
    category: string;
}

// React Flow expectation for Custom Node Data
export type CustomNodeProps = {
    data: TechNodeData;
    selected: boolean;
};
