"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import {
  Send, RefreshCw, User, Terminal,
  CheckCircle2, LayoutDashboard, BrainCircuit, Lightbulb
} from "lucide-react";

// 그래프 라이브러리 (SSR 제외)
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

export default function AgenticDashBoard() {
  // --- 상태 관리 ---
  const [userId] = useState("haebo9@guest.com");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<any[]>([]);

  // 데이터 조각 상태
  const [keywordSummary, setKeywordSummary] = useState<any>(null);
  const [currentQuiz, setCurrentQuiz] = useState<any>(null);
  const [pendingQuiz, setPendingQuiz] = useState<any>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  // 주관식 답변용 상태
  const [subjectiveAnswer, setSubjectiveAnswer] = useState("");

  // 그래프 데이터 (더미 데이터 - 나중에 API 연결)
  const [graphData] = useState({
    nodes: [{ id: "Python", val: 10 }, { id: "Next.js", val: 5 }],
    links: [{ source: "Python", target: "Next.js" }]
  });

  // --- 에이전트 통신 함수 --- // Backend와 통신하는 함수
  const askAgent = async (input: string, isAnswer: boolean = false) => {
    setLoading(true);
    if (isAnswer) setFeedback(null);
    else {
      setLogs([]);
      setCurrentQuiz(null);
      setPendingQuiz(null);
      setFeedback(null);
    }

    try {
      // 백엔드 API 엔드포인트에 데이터를 던지는 부분
      const response = await fetch("http://localhost:8000/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input, thread_id: "user_session_1" }), // TODO: 나중에 고유 id 로 변경
      });

      // 백엔드가 보낸 응답을 한 줄씩 실시간을 읽어오는 과정 (Streaming)
      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const lines = decoder.decode(value).split("\n\n");
        lines.forEach((line) => {
          if (line.startsWith("data: ")) {
            try {
              // 받아온 JSON 데이터를 분석해서 화면의 각 부분에 뿌려줍니다. (JSON Parsing)
              const data = JSON.parse(line.replace("data: ", ""));
              setLogs((prev) => [...prev, data]); // 실시간 로그 저장

              const nodeName = Object.keys(data)[0];
              const nodeData = data[nodeName];

              // 1. 키워드 요약
              if (data.search_keyword?.keyword_data && !isAnswer) {
                setKeywordSummary(data.search_keyword.keyword_data);
              }

              // 2. 피드백 추출 (채점 결과)
              if (nodeName.includes("score") || nodeName.includes("eval") || nodeName.includes("generate_quiz")) {
                const msg = nodeData.messages?.[0]?.content;
                if (msg && (msg.includes("정답") || msg.includes("해설") || msg.includes("결과") || msg.includes("피드백"))) {
                  setFeedback(msg);
                }
              }

              // 3. 퀴즈 데이터 (객관식/주관식 공용)
              if (data.generate_quiz?.current_question) {
                const nextQ = data.generate_quiz.current_question;
                setCurrentQuiz((prev: any) => {
                  if (!prev) return nextQ;
                  setPendingQuiz(nextQ);
                  return prev;
                });
              }
            } catch (err) { console.error(err); }
          }
        });
      }
    } finally {
      setLoading(false);
    }
  };

  // 다음 문제로 넘어가기
  const handleNext = () => {
    if (pendingQuiz) {
      setCurrentQuiz(pendingQuiz);
      setPendingQuiz(null);
      setFeedback(null);
      setSubjectiveAnswer("");
    }
  };

  return (
    <div className="flex h-screen bg-[#F8FAFC] text-slate-800 font-sans overflow-hidden">

      {/* [1] Sidebar (Settings) */}
      <aside className="w-72 bg-white border-r border-slate-200 p-6 flex flex-col shadow-sm z-10">
        <div className="mb-10">
          <div className="flex items-center gap-2 mb-1">
            <BrainCircuit className="text-blue-600 w-8 h-8" />
            <h1 className="text-2xl font-black tracking-tighter text-slate-900">TechTree</h1>
          </div>
          <p className="text-[11px] text-slate-400 font-medium uppercase tracking-widest ml-1">AI Agent Learning System</p>
        </div>

        <div className="space-y-6">
          <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-600">
              <User size={20} />
            </div>
            <div className="overflow-hidden">
              <p className="text-[10px] text-slate-400 font-bold uppercase">Authorized User</p>
              <p className="text-sm font-bold text-slate-700 truncate">{userId}</p>
            </div>
          </div>

          <div>
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
              <LayoutDashboard size={14} /> Dashboard Config
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-[11px] font-bold text-slate-500 mb-2 block">Similarity Threshold</label>
                <input type="range" className="w-full accent-blue-600" defaultValue={0.37} />
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* [2] Main Mission Area (Quiz & Agent Action) */}
      <main className="flex-1 flex flex-col p-6 gap-6 overflow-hidden">

        {/* 상단 퀴즈 위젯 (에이전트와 소통하는 핵심 카드) */}
        <section className="flex-1 bg-white rounded-[2rem] shadow-xl shadow-slate-200/50 border border-slate-100 flex flex-col overflow-hidden">
          <div className="px-8 py-5 border-b border-slate-50 flex justify-between items-center bg-slate-50/50">
            <h2 className="font-black text-slate-700 flex items-center gap-2 uppercase tracking-tighter">
              <CheckCircle2 className="text-blue-500" size={20} /> Developer Quiz
            </h2>
            {loading && <div className="flex gap-1 items-center text-[10px] font-bold text-blue-500 animate-pulse">
              <RefreshCw size={12} className="animate-spin" /> AGENT THINKING...
            </div>}
          </div>

          <div className="flex-1 p-8 overflow-y-auto custom-scrollbar">
            {!currentQuiz && !loading ? (
              <div className="h-full flex flex-col items-center justify-center text-center space-y-4">
                <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center text-slate-300">
                  <BrainCircuit size={40} />
                </div>
                <p className="text-slate-400 font-medium">아직 시작된 면접이 없습니다.<br />하단에 기술 키워드를 입력해 에이전트를 깨우세요.</p>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
                {/* 질문 영역 */}
                <div className="bg-slate-900 rounded-[2rem] p-8 text-white shadow-2xl shadow-blue-900/20 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                    <BrainCircuit size={100} />
                  </div>
                  <p className="text-blue-400 text-[10px] font-black uppercase tracking-[0.3em] mb-4">Current Question</p>
                  <h3 className="text-2xl font-bold leading-snug">{currentQuiz?.question_text}</h3>
                </div>

                {/* 피드백 vs 입력/버튼 영역 */}
                {feedback ? (
                  <div className="animate-in zoom-in duration-500 space-y-6">
                    <div className="p-8 bg-blue-50 rounded-[2rem] border-2 border-blue-100">
                      <h4 className="font-black text-blue-900 mb-3 flex items-center gap-2">
                        <Lightbulb className="text-blue-600" /> AGENT FEEDBACK
                      </h4>
                      <p className="text-blue-800 whitespace-pre-wrap leading-relaxed font-medium">{feedback}</p>
                    </div>
                    <button onClick={handleNext} className="w-full py-5 bg-slate-900 text-white rounded-2xl font-black text-lg hover:scale-[1.02] transition-all shadow-xl shadow-slate-200">
                      NEXT STEP ➔
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* [핵심 분기] options 여부에 따라 객관식/주관식 전환 */}
                    {currentQuiz?.options && currentQuiz.options.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {currentQuiz.options.map((opt: string, i: number) => (
                          <button
                            key={i}
                            onClick={() => askAgent(opt, true)}
                            className="text-left p-6 border-2 border-slate-100 rounded-2xl hover:border-blue-500 hover:bg-blue-50 hover:shadow-lg transition-all group flex items-center bg-white"
                          >
                            <span className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center text-sm font-black mr-4 group-hover:bg-blue-600 group-hover:text-white transition-colors">{i + 1}</span>
                            <span className="font-bold text-slate-600">{opt}</span>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <textarea
                          className="w-full p-6 bg-slate-50 border-2 border-slate-100 rounded-[2rem] focus:border-blue-500 outline-none min-h-[150px] font-medium text-slate-700 transition-all shadow-inner"
                          placeholder="여기에 답변을 상세히 작성해주세요. 에이전트가 당신의 논리를 분석합니다."
                          value={subjectiveAnswer}
                          onChange={(e) => setSubjectiveAnswer(e.target.value)}
                        />
                        <button
                          onClick={() => askAgent(subjectiveAnswer, true)}
                          className="w-full py-5 bg-blue-600 text-white rounded-2xl font-black text-lg hover:bg-blue-700 transition-all shadow-lg shadow-blue-100"
                        >
                          SUBMIT ANSWER
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 하단 통합 입력창 (면접 시작용) */}
          <div className="p-6 bg-slate-50/50 border-t border-slate-100">
            <div className="max-w-3xl mx-auto flex gap-3 relative">
              <input
                className="flex-1 p-4 pl-6 bg-white border border-slate-200 rounded-2xl shadow-sm focus:ring-2 focus:ring-blue-500 outline-none font-medium pr-14"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && askAgent(message)}
                placeholder="배우고 싶은 기술 키워드를 입력하세요... (예: Python, Next.js)"
              />
              <button onClick={() => askAgent(message)} className="absolute right-2 top-2 bg-slate-900 text-white p-2 rounded-xl hover:bg-black transition-colors">
                <Send size={20} />
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* [3] Right Sidebar (Graph & Agent Console) */}
      <aside className="w-[28rem] flex flex-col p-6 gap-6 bg-white border-l border-slate-200">

        {/* 상단: Keyword Map */}
        <div className="flex-1 bg-slate-50 rounded-[2rem] border border-slate-100 overflow-hidden relative shadow-inner">
          <div className="absolute top-4 left-6 z-10">
            <h2 className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
              < BrainCircuit size={14} /> Knowledge Map
            </h2>
          </div>
          <ForceGraph2D
            graphData={graphData}
            width={400}
            height={400}
            nodeLabel="id"
            nodeColor={() => "#2563EB"}
            linkColor={() => "#CBD5E1"}
          />
        </div>

        {/* 하단: Agent Console (에이전트의 사고 과정 부활) */}
        <div className="h-72 bg-slate-900 rounded-[2rem] flex flex-col overflow-hidden shadow-2xl">
          <div className="px-5 py-3 bg-slate-800 flex justify-between items-center">
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
              <Terminal size={12} className="text-green-500" /> Agent Console
            </h3>
            <div className="flex gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-red-500"></div>
              <div className="w-1.5 h-1.5 rounded-full bg-yellow-500"></div>
              <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div>
            </div>
          </div>
          <div className="flex-1 p-5 overflow-y-auto font-mono text-[10px] space-y-3 custom-scrollbar">
            {logs.length === 0 && <p className="text-slate-600 italic leading-relaxed">준비 중... 유저의 입력을 기다리고 있습니다.</p>}
            {logs.map((log, idx) => (
              <div key={idx} className="border-l border-slate-700 pl-3">
                <span className="text-blue-500 font-bold uppercase">[{Object.keys(log)[0]}]</span>
                <pre className="text-slate-400 whitespace-pre-wrap mt-1 leading-normal">
                  {JSON.stringify(Object.values(log)[0], null, 1)}
                </pre>
              </div>
            ))}
          </div>
        </div>
      </aside>

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #E2E8F0; border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #CBD5E1; }
      `}</style>
    </div>
  );
}