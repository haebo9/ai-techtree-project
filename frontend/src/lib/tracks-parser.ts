import { Node, Edge } from 'reactflow';
import dagre from 'dagre';
import tracksData from '@/data/tracks.json';
import { TechNodeData, SkillStatus } from '@/types/techtree';

// Define types for the raw JSON structure
interface RawTrackData {
    description: string;
    steps: {
        [stepName: string]: {
            description: string;
            [optionName: string]: any; // Options are mixed with description, so using any for flexibility or stricter parsing if possible
        };
    };
}

interface RawTracks {
    [trackName: string]: RawTrackData;
}

const rawTracks = tracksData as RawTracks;

// Helper to determine node status (mock logic for now)
const getStatus = (trackIndex: number, stepIndex: number): SkillStatus => {
    if (trackIndex === 0) {
        if (stepIndex <= 1) return 'mastered';
        if (stepIndex === 2) return 'available';
    }
    return 'locked';
};

// Helper to determine category based on Track name
const getCategory = (trackName: string): string => {
    if (trackName.includes('Track 0')) return 'Common';
    if (trackName.includes('Track 1')) return 'Engineer';
    if (trackName.includes('Track 2')) return 'Modeler';
    if (trackName.includes('Track 3')) return 'LLM App';
    if (trackName.includes('Track 4')) return 'Data';
    if (trackName.includes('Track 5')) return 'MLOps';
    return 'Other';
};

export const getLayoutedElements = () => {
    const nodes: Node<TechNodeData>[] = [];
    const edges: Edge[] = [];
    const dagreGraph = new dagre.graphlib.Graph();

    dagreGraph.setGraph({ rankdir: 'TB', nodesep: 100, ranksep: 150 });
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    let globalNodeId = 0;
    const trackNodes: { [key: string]: string[] } = {}; // To store last nodes of previous step to connect to next step

    Object.keys(rawTracks).forEach((trackName, trackIndex) => {
        const track = rawTracks[trackName];
        let previousStepNodes: string[] = [];

        // Sort steps by name to ensure order (Step 1, Step 2...)
        const sortedSteps = Object.keys(track.steps).sort();

        sortedSteps.forEach((stepName, stepIndex) => {
            const step = track.steps[stepName];
            const currentStepNodes: string[] = [];

            // Iterate over Options (filtering out 'description')
            Object.keys(step).forEach((key) => {
                if (key === 'description') return;

                // key is Option Name (e.g., "Option 1: Python Fundamentals")
                const option = step[key];

                // Iterate over Subjects within Option (filtering out 'description')
                Object.keys(option).forEach((subjectKey) => {
                    if (subjectKey === 'description') return;

                    // subjectKey is the actual Topic (e.g., "Python Syntax & Types")
                    const subject = option[subjectKey];
                    const nodeId = `node-${globalNodeId++}`;
                    const category = getCategory(trackName);

                    // Basic Mock Status Logic
                    const status = getStatus(trackIndex, stepIndex);
                    const starCount = status === 'mastered' ? 3 : (status === 'available' ? 1 : 0);

                    const newNode: Node<TechNodeData> = {
                        id: nodeId,
                        type: 'techNode',
                        position: { x: 0, y: 0 }, // Position will be set by dagre
                        data: {
                            id: nodeId,
                            label: subjectKey,
                            description: subject.description || '',
                            status: status,
                            stars: starCount as 0 | 1 | 2 | 3,
                            category: category
                        }
                    };

                    nodes.push(newNode);
                    currentStepNodes.push(nodeId);
                    dagreGraph.setNode(nodeId, { width: 200, height: 100 }); // Estimate node size

                    // Internal Edges: Connect previous step nodes to ALL nodes in this step
                    // This creates a dense graph. For better visuals, maybe connect to the "Option" parent?
                    // For now, let's connect all previous step nodes to all current step nodes (Full Mesh between steps)
                    // Or better: Connect first node of previous to first of current? 
                    // Let's try fully connecting for "Dependency" visualization.

                    if (previousStepNodes.length > 0) {
                        previousStepNodes.forEach(prevId => {
                            const edgeId = `e-${prevId}-${nodeId}`;
                            edges.push({
                                id: edgeId,
                                source: prevId,
                                target: nodeId,
                                type: 'default',
                                style: { stroke: '#444', strokeWidth: 1 },
                                animated: status === 'available' || status === 'mastered'
                            });
                            dagreGraph.setEdge(prevId, nodeId);
                        });
                    } else if (trackIndex > 0 && stepIndex === 0) {
                        // Connect Track 0's last step to Track N's first step
                        // Finding Track 0's last nodes is tricky without state.
                        // Ideally we connect "The Origin" to specific starter nodes.
                        // Let's skip cross-track connections for this immediate auto-generation 
                        // and focus on intra-track visualization first.
                    }
                });
            });

            previousStepNodes = currentStepNodes;
        });
    });

    dagre.layout(dagreGraph);

    const layoutedNodes = nodes.map((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        return {
            ...node,
            position: {
                x: nodeWithPosition.x - 100, // Center offset
                y: nodeWithPosition.y - 50,
            },
        };
    });

    return { nodes: layoutedNodes, edges };
};
