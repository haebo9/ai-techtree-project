"use client";

import { useState, useEffect, useRef } from "react";
import {
    Terminal,
    Activity,
    MessageSquare,
    Settings,
    Send,
    Trash2,
    Search,
    BrainCircuit,
    ChevronRight,
    CircleDot
} from "lucide-react";

export default function DebugPage() {
    const [input, setInput] = useState("");
    const [threadId, setThreadId] = useState("debug_session_001");
    const [loading, setLoading] = useState(false);
    const [messages, setMessages] = useState<{ role: 'user' | 'ai', content: string }[]>([]);

    // 모든 수신 데이터를 담는 로그 배열
    const [fullLogs, setFullLogs] = useState<any[]>([]);
    // 현재 추출된 핵심 상태 (State)
    const [currentState, setCurrentState] = useState<any>({
        node: "idle",
        quiz_in_progress: false,
        current_question: null,
        feedback: null
    });

    const scrollRef = useRef<HTMLDivElement>(null);
    const chatScrollRef = useRef<HTMLDivElement>(null);

    // 로그 자동 스크롤
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [fullLogs]);

    // 채팅 자동 스크롤
    useEffect(() => {
        if (chatScrollRef.current) {
            chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
        }
    }, [messages]);

    const clearLogs = () => {
        setFullLogs([]);
        setMessages([]);
        setCurrentState({
            node: "idle",
            quiz_in_progress: false,
            current_question: null,
            feedback: null
        });
    };

    const callAgent = async (message: string) => {
        if (!message.trim()) return;

        setLoading(true);
        // 사용자 메시지 추가
        const userMsg = { role: 'user' as const, content: message };
        setMessages(prev => [...prev, userMsg]);

        const currentInput = message;
        setInput("");

        try {
            const response = await fetch("http://localhost:8000/api/chat/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: currentInput, thread_id: threadId }),
            });

            if (!response.body) return;
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedBuffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                accumulatedBuffer += decoder.decode(value, { stream: true });
                const lines = accumulatedBuffer.split("\n\n");

                // 마지막 비완성 데이터는 버퍼에 유지
                accumulatedBuffer = lines.pop() || "";

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        try {
                            const jsonStr = line.replace("data: ", "").trim();
                            if (!jsonStr) continue;

                            const rawData = JSON.parse(jsonStr);
                            const nodeName = Object.keys(rawData)[0];
                            const nodeContent = rawData[nodeName];

                            if (!nodeName || !nodeContent) continue;

                            // 1. 원본 로그 추가 (Console용)
                            setFullLogs((prev) => [...prev, {
                                node: nodeName,
                                data: nodeContent,
                                time: new Date().toLocaleTimeString('ko-KR', { hour12: false })
                            }]);

                            // 2. AI 응답 메시지 추출 및 Chat UI 업데이트
                            if (nodeContent.messages && Array.isArray(nodeContent.messages)) {
                                const aiMsgs = nodeContent.messages.filter((m: any) =>
                                    m.type === 'ai' || m.role === 'assistant'
                                );

                                if (aiMsgs.length > 0) {
                                    const lastAiMsg = aiMsgs[aiMsgs.length - 1].content;

                                    if (lastAiMsg && typeof lastAiMsg === 'string' && lastAiMsg.trim() !== '') {
                                        setMessages(prev => {
                                            const lastMsgInState = prev[prev.length - 1];

                                            // 메시지 내용이 완전히 동일하면 무시
                                            if (lastMsgInState?.role === 'ai' && lastMsgInState.content === lastAiMsg) {
                                                return prev;
                                            }

                                            // 부분 문자열이 포함된 형태 (스트리밍 중복 현상) 방지
                                            if (lastMsgInState?.role === 'user' && lastAiMsg === currentInput) {
                                                return prev;
                                            }

                                            return [...prev, { role: 'ai', content: lastAiMsg }];
                                        });
                                    }
                                }
                            }

                            // 3. 핵심 상태 추출 (Extraction State용)
                            if (nodeName === "generate_quiz") {
                                setCurrentState((prev: any) => ({
                                    ...prev,
                                    node: nodeName,
                                    current_question: nodeContent.current_question,
                                    quiz_in_progress: nodeContent.quiz_in_progress
                                }));
                            } else if (nodeName.includes("score") || nodeName.includes("eval")) {
                                const feedback = nodeContent.messages?.[nodeContent.messages.length - 1]?.content || nodeContent.feedback;
                                if (feedback) {
                                    setCurrentState((prev: any) => ({
                                        ...prev,
                                        node: nodeName,
                                        feedback: feedback
                                    }));
                                }
                            } else {
                                setCurrentState((prev: any) => ({ ...prev, node: nodeName }));
                            }
                        } catch (e) {
                            console.error("JSON 파싱 에러:", e, "Line:", line);
                        }
                    }
                }
            }
        } catch (error) {
            console.error("통신 에러:", error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-screen bg-[#0f1115] text-slate-300 font-sans selection:bg-indigo-500/30">
            {/* Header */}
            <header className="h-16 flex items-center justify-between px-6 border-b border-white/5 bg-white/5 backdrop-blur-md sticky top-0 z-50">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-500/10 rounded-lg">
                        <BrainCircuit className="w-5 h-5 text-indigo-400" />
                    </div>
                    <div>
                        <h1 className="text-lg font-bold text-white tracking-tight">Agentic Interview Tester</h1>
                        <p className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold flex items-center gap-1">
                            <CircleDot className="w-2 h-2 text-emerald-500" /> System live
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-full border border-white/10 ring-1 ring-white/5 transition-all hover:ring-indigo-500/50">
                        <Settings className="w-3.5 h-3.5 text-slate-500" />
                        <span className="text-xs text-slate-400 font-medium whitespace-nowrap">Thread:</span>
                        <input
                            value={threadId}
                            onChange={(e) => setThreadId(e.target.value)}
                            className="bg-transparent border-none outline-none text-xs text-indigo-300 w-32 font-mono"
                        />
                    </div>
                    <button
                        onClick={clearLogs}
                        className="p-2 hover:bg-rose-500/10 hover:text-rose-400 rounded-lg transition-colors group"
                        title="Clear all logs"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            </header>

            <main className="flex-1 flex overflow-hidden p-4 gap-4">
                {/* Left Section: Interaction & State */}
                <section className="flex-[1.2] flex flex-col gap-4 min-w-0">
                    {/* Current State Card */}
                    <div className="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col gap-4 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-8 opacity-5 pointer-events-none group-hover:opacity-10 transition-opacity">
                            <Activity className="w-24 h-24" />
                        </div>

                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                                <Activity className="w-4 h-4 text-indigo-400" />
                                Extraction State
                            </h3>
                            <span className="text-[10px] px-2 py-0.5 bg-indigo-500/20 text-indigo-300 rounded-full font-mono border border-indigo-500/30">
                                {currentState.node}
                            </span>
                        </div>

                        <div className="bg-black/40 rounded-xl p-4 border border-white/5 font-mono text-xs overflow-auto max-h-[300px] scrollbar-hide">
                            <pre className="text-indigo-200/80">{JSON.stringify(currentState, null, 2)}</pre>
                        </div>

                        {/* Quiz Detail View */}
                        {currentState.current_question && (
                            <div className="mt-2 p-5 bg-gradient-to-br from-indigo-500/10 to-purple-500/10 rounded-xl border border-indigo-500/20 animate-in fade-in slide-in-from-bottom-2 duration-500">
                                <div className="flex items-center gap-2 mb-3">
                                    <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
                                    <span className="text-xs font-bold text-indigo-300 uppercase tracking-wider">Quiz Detected</span>
                                </div>
                                <p className="text-sm text-white font-medium mb-4 leading-relaxed">
                                    {currentState.current_question.question_text}
                                </p>
                                <div className="grid grid-cols-1 gap-2">
                                    {currentState.current_question.options?.map((opt: string, i: number) => (
                                        <button
                                            key={i}
                                            onClick={() => callAgent(opt)}
                                            className="flex items-center gap-3 w-full p-3 text-left text-xs bg-white/5 hover:bg-indigo-500/20 rounded-lg border border-white/5 transition-all group/opt"
                                        >
                                            <span className="w-6 h-6 flex items-center justify-center bg-white/10 rounded-md group-hover/opt:bg-indigo-500/40 text-[10px] font-bold transition-colors">
                                                {i + 1}
                                            </span>
                                            <span className="flex-1 truncate">{opt}</span>
                                            <ChevronRight className="w-3 h-3 opacity-0 group-hover/opt:opacity-100 transition-all -translate-x-2 group-hover/opt:translate-x-0" />
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Chat Input Section */}
                    <div className="flex-1 flex flex-col bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
                        <div className="p-4 border-b border-white/5 bg-white/2 flex items-center justify-between">
                            <span className="text-xs font-semibold text-slate-400 flex items-center gap-2">
                                <MessageSquare className="w-3.5 h-3.5" />
                                Interaction
                            </span>
                        </div>

                        <div ref={chatScrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-hide">
                            {messages.length === 0 && (
                                <div className="h-full flex flex-col items-center justify-center text-slate-600 opacity-50">
                                    <MessageSquare className="w-8 h-8 mb-2 stroke-1" />
                                    <p className="text-xs font-medium italic">Waiting for interaction...</p>
                                </div>
                            )}
                            {messages.map((msg, i) => (
                                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-[85%] p-3 rounded-2xl text-xs leading-relaxed ${msg.role === 'user'
                                        ? 'bg-indigo-600 text-white rounded-tr-none'
                                        : 'bg-white/10 text-slate-200 rounded-tl-none border border-white/5 shadow-xl'
                                        }`}>
                                        {msg.content}
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="p-4 bg-white/2 mt-auto">
                            <div className="relative group/input">
                                <input
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && !e.nativeEvent.isComposing) {
                                            e.preventDefault();
                                            if (!loading && input.trim()) {
                                                callAgent(input);
                                            }
                                        }
                                    }}
                                    placeholder="Type your message..."
                                    className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3.5 pr-14 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all placeholder:text-slate-600"
                                />
                                <button
                                    onClick={() => callAgent(input)}
                                    disabled={loading || !input.trim()}
                                    className="absolute right-2 top-2 p-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-400 disabled:opacity-30 disabled:hover:bg-indigo-500 transition-all active:scale-95 shadow-lg shadow-indigo-500/20"
                                >
                                    {loading ? (
                                        <Activity className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Send className="w-4 h-4" />
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Right Section: Stream Console */}
                <section className="flex-1 flex flex-col bg-black/50 border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
                    <div className="p-4 border-b border-white/10 bg-black/40 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div className="flex gap-1.5 mr-2">
                                <div className="w-2.5 h-2.5 rounded-full bg-rose-500/50 border border-rose-500/40" />
                                <div className="w-2.5 h-2.5 rounded-full bg-amber-500/50 border border-amber-500/40" />
                                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/50 border border-emerald-500/40" />
                            </div>
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-tighter flex items-center gap-2">
                                <Terminal className="w-3.5 h-3.5" />
                                Stream Console
                            </span>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 font-mono">
                                RAW_SOCKET
                            </div>
                        </div>
                    </div>

                    <div
                        ref={scrollRef}
                        className="flex-1 overflow-y-auto p-4 font-mono text-[11px] leading-relaxed scrollbar-thin scrollbar-thumb-white/10"
                    >
                        {fullLogs.length === 0 ? (
                            <div className="h-full flex flex-col items-center justify-center text-slate-700 animate-pulse">
                                <Search className="w-8 h-8 mb-2 stroke-1" />
                                <p>Listening for backend events...</p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {fullLogs.map((log, idx) => (
                                    <div key={idx} className="group/log border-l border-white/5 pl-4 ml-1 transition-all hover:border-indigo-500/50">
                                        <div className="flex items-center gap-3 mb-1.5 opacity-60 group-hover/log:opacity-100 transition-opacity">
                                            <span className="text-slate-500">[{log.time}]</span>
                                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${log.node === 'generate_quiz' ? 'bg-indigo-500/20 text-indigo-400' :
                                                log.node.includes('score') ? 'bg-amber-500/20 text-amber-400' :
                                                    'bg-slate-800 text-slate-400'
                                                }`}>
                                                NODE: {log.node}
                                            </span>
                                        </div>
                                        <div className="bg-white/2 p-3 rounded-lg border border-white/5 backdrop-blur-sm group-hover/log:bg-white/5 transition-colors">
                                            <pre className="whitespace-pre-wrap break-all text-slate-400 group-hover/log:text-slate-300">
                                                {JSON.stringify(log.data, null, 1)}
                                            </pre>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </section>
            </main>
        </div>
    );
}