'use client';

import { useCallback } from 'react';
import ReactFlow, {
    Background,
    Controls,
    Node,
    Edge,
    useNodesState,
    useEdgesState,
    ConnectionMode,
} from 'reactflow';
import 'reactflow/dist/style.css';



import TechNode from './TechNode';
import { getLayoutedElements } from '@/lib/tracks-parser';

const nodeTypes = {
    techNode: TechNode,
};

const { nodes: initialNodes, edges: initialEdges } = getLayoutedElements();

export default function TechTreeMap() {
    const [nodes, , onNodesChange] = useNodesState(initialNodes);
    const [edges, , onEdgesChange] = useEdgesState(initialEdges);

    const onInit = useCallback((reactFlowInstance: any) => {
        reactFlowInstance.fitView();
    }, []);

    return (
        <div style={{ width: '100%', height: '100%', minHeight: '600px', background: 'transparent' }}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                connectionMode={ConnectionMode.Loose}
                onInit={onInit}
                fitView
                proOptions={{ hideAttribution: true }}
            >
                <Background gap={20} size={1} color="#333" />
                <Controls
                    style={{
                        background: 'rgba(255,255,255,0.05)',
                        border: 'none',
                        fill: 'white'
                    }}
                />
            </ReactFlow>
        </div>
    );
}
