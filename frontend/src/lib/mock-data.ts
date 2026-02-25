import { Edge, Node } from 'reactflow';
import { TechNodeData } from '@/types/techtree';

// Based on backend/app/source/tracks.json
// Track 0: Python -> Track 1: AI Engineer path

export const initialNodes: Node<TechNodeData>[] = [
    // --- Step 1: Programming Basics ---
    {
        id: 'python-syntax',
        type: 'techNode',
        position: { x: 250, y: 0 },
        data: {
            id: 'python-syntax',
            label: 'Python Syntax & Types',
            description: '변수, 제어문, 함수 등 Python의 가장 기초적인 문법 요소들입니다.',
            status: 'mastered',
            stars: 3,
            category: 'Language'
        },
    },
    {
        id: 'data-structure',
        type: 'techNode',
        position: { x: 100, y: 150 },
        data: {
            id: 'data-structure',
            label: 'Data Structure Core',
            description: 'List, Dictionary 등 데이터 관리를 위한 핵심 자료구조입니다.',
            status: 'mastered',
            stars: 3,
            category: 'CS'
        },
    },
    {
        id: 'oop-functional',
        type: 'techNode',
        position: { x: 400, y: 150 },
        data: {
            id: 'oop-functional',
            label: 'OOP & Functional',
            description: '객체지향(Class)과 함수형 프로그래밍의 기초 개념입니다.',
            status: 'available', // User is currently here
            stars: 1, // Level 1 completed
            category: 'Paradigm'
        },
    },

    // --- Step 2: Infrastructure Fundamentals ---
    {
        id: 'linux-cli',
        type: 'techNode',
        position: { x: 100, y: 350 },
        data: {
            id: 'linux-cli',
            label: 'Linux CLI',
            description: '마우스 없이 컴퓨터를 제어하는 명령어 기초입니다.',
            status: 'locked',
            stars: 0,
            category: 'OS'
        },
    },
    {
        id: 'git-vc',
        type: 'techNode',
        position: { x: 400, y: 350 },
        data: {
            id: 'git-vc',
            label: 'Git Version Control',
            description: '소스코드의 역사를 기록하고 협업하기 위한 도구입니다.',
            status: 'locked',
            stars: 0,
            category: 'Tool'
        },
    },

    // --- Step 3: Math & Logic (Common for AI) ---
    {
        id: 'math-linear',
        type: 'techNode',
        position: { x: 700, y: 350 },
        data: {
            id: 'math-linear',
            label: 'Linear Algebra & Stats',
            description: '딥러닝의 재료가 되는 행렬 연산과 확률 통계입니다.',
            status: 'locked',
            stars: 0,
            category: 'Math'
        },
    },

    // --- Track 1: AI Engineer (Backend focused) ---
    {
        id: 'fastapi-essentials',
        type: 'techNode',
        position: { x: 100, y: 600 },
        data: {
            id: 'fastapi-essentials',
            label: 'FastAPI Essentials',
            description: 'Python 기반의 고성능 웹 프레임워크인 FastAPI의 핵심 기능을 익힙니다.',
            status: 'locked',
            stars: 0,
            category: 'Backend'
        },
    },
    {
        id: 'docker-basics',
        type: 'techNode',
        position: { x: 300, y: 600 },
        data: {
            id: 'docker-basics',
            label: 'Docker Basics',
            description: '어디서나 동일하게 실행되는 컨테이너 환경을 구축합니다.',
            status: 'locked',
            stars: 0,
            category: 'DevOps'
        },
    },

    // --- Track 2: AI Modeler (Math/Model focused) ---
    {
        id: 'dl-basics',
        type: 'techNode',
        position: { x: 600, y: 600 },
        data: {
            id: 'dl-basics',
            label: 'Deep Learning Basics',
            description: 'PyTorch를 사용하여 딥러닝 모델이 어떻게 학습되는지 이해합니다.',
            status: 'locked',
            stars: 0,
            category: 'AI'
        },
    },
    {
        id: 'vision-nlp',
        type: 'techNode',
        position: { x: 600, y: 750 },
        data: {
            id: 'vision-nlp',
            label: 'Vision & NLP',
            description: '이미지 처리(CNN)와 자연어 처리(Transformer)의 핵심을 배웁니다.',
            status: 'locked',
            stars: 0,
            category: 'AI'
        },
    },

    // --- Track 3: LLM App Engineer (Application focused) ---
    {
        id: 'prompt-engineering',
        type: 'techNode',
        position: { x: 900, y: 600 },
        data: {
            id: 'prompt-engineering',
            label: 'Prompt Engineering',
            description: 'LLM에게 원하는 답변을 얻어내기 위한 프롬프트 작성의 기초 기술입니다.',
            status: 'locked',
            stars: 0,
            category: 'LLM'
        },
    },
    {
        id: 'rag-basics',
        type: 'techNode',
        position: { x: 900, y: 750 },
        data: {
            id: 'rag-basics',
            label: 'RAG Fundamentals',
            description: '외부 지식을 검색하여 LLM의 답변 정확도를 높이는 기술입니다.',
            status: 'locked',
            stars: 0,
            category: 'LLM'
        },
    }
];

export const initialEdges: Edge[] = [
    // Python -> branches to Data Structure & OOP
    { id: 'e-py-ds', source: 'python-syntax', target: 'data-structure', animated: true },
    { id: 'e-py-oop', source: 'python-syntax', target: 'oop-functional', animated: true },

    // Foundation -> Infra (Logic: Need programming skills before system basics)
    { id: 'e-ds-linux', source: 'data-structure', target: 'linux-cli', style: { strokeOpacity: 0.2 } },
    { id: 'e-oop-git', source: 'oop-functional', target: 'git-vc', style: { strokeOpacity: 0.2 } },

    // Foundation -> Math (For AI Modeler path)
    { id: 'e-ds-math', source: 'data-structure', target: 'math-linear', style: { strokeOpacity: 0.2 } },

    // --- Branching to Tracks ---

    // Track 1 (Engineer): Infra -> Backend/Docker
    { id: 'e-linux-docker', source: 'linux-cli', target: 'docker-basics', style: { strokeOpacity: 0.2 } },
    { id: 'e-git-fastapi', source: 'git-vc', target: 'fastapi-essentials', style: { strokeOpacity: 0.2 } },

    // Track 2 (Modeler): Math -> Deep Learning
    { id: 'e-math-dl', source: 'math-linear', target: 'dl-basics', style: { strokeOpacity: 0.2 } },
    { id: 'e-dl-vision', source: 'dl-basics', target: 'vision-nlp', style: { strokeOpacity: 0.2 } },

    // Track 3 (LLM App): Python/API -> Prompting (Can start early)
    { id: 'e-oop-prompt', source: 'oop-functional', target: 'prompt-engineering', style: { strokeOpacity: 0.2 } },
    { id: 'e-prompt-rag', source: 'prompt-engineering', target: 'rag-basics', style: { strokeOpacity: 0.2 } },
];
