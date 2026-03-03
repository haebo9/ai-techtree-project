"use client";

import { useState } from "react";

export default function InterviewPage() {
  const [message, setMessage] = useState(""); // 입력 필드
  const [loading, setLoading] = useState(false); // 로딩 상태

  // 데이터 상태 관리
  const [logs, setLogs] = useState<any[]>([]); // 우측 로그창
  const [keywordSummary, setKeywordSummary] = useState<any>(null); // 좌측 기술 요약
  const [currentQuiz, setCurrentQuiz] = useState<any>(null); // 현재 진행 중인 문제
  const [pendingQuiz, setPendingQuiz] = useState<any>(null); // 미리 도착한 다음 문제
  const [feedback, setFeedback] = useState<string | null>(null); // 채점 결과 및 해설

  /**
   * 에이전트와 통신하는 핵심 함수
   * @param input 전송할 메시지
   * @param isAnswer 답변 제출 여부 (true면 피드백 로직 작동)
   */
  const askAgent = async (input: string, isAnswer: boolean = false) => {
    setLoading(true);
    if (isAnswer) {
      setFeedback(null); // 새로운 답변 제출 시 이전 피드백 가림
    } else {
      // 새로운 면접 시작 시 전체 초기화
      setKeywordSummary(null);
      setCurrentQuiz(null);
      setPendingQuiz(null);
      setFeedback(null);
      setLogs([]);
    }

    try {
      const response = await fetch("http://localhost:8000/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          // 답변일 경우 에이전트가 채점 모드로 작동하도록 문구 보정
          message: isAnswer ? `사용자 선택 답변: ${input}` : input,
          thread_id: "user_session_1"
        }),
      });

      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n\n");

        lines.forEach((line) => {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.replace("data: ", ""));
              setLogs((prev) => [...prev, data]);

              const nodeName = Object.keys(data)[0];
              const nodeData = data[nodeName];

              // 1. 기술 요약 정보 (최초 검색 시에만 업데이트)
              if (data.search_keyword?.keyword_data && !isAnswer) {
                setKeywordSummary(data.search_keyword.keyword_data);
              }

              // 2. 피드백 정보 (scoring, evaluator 또는 generate_quiz 내의 메시지)
              if (nodeName.includes("score") || nodeName.includes("eval") || nodeName.includes("generate_quiz")) {
                const content = nodeData.messages?.[0]?.content;
                // 내용에 채점 관련 키워드가 포함되어 있다면 피드백 상태에 저장
                if (content && (content.includes("정답") || content.includes("해설") || content.includes("오답"))) {
                  setFeedback(content);
                }
              }

              // 3. 퀴즈 정보
              if (data.generate_quiz?.current_question) {
                const nextQ = data.generate_quiz.current_question;
                setCurrentQuiz((prev: any) => {
                  if (!prev) return nextQ; // 퀴즈가 없었으면 바로 표시
                  setPendingQuiz(nextQ); // 이미 있으면 대기소로
                  return prev;
                });
              }
            } catch (err) {
              console.error("Parsing error:", err);
            }
          }
        });
      }
    } catch (err) {
      console.error("Fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  // ✅ [수정됨] 누락되었던 답변 제출 함수 추가
  const handleAnswerSubmit = (option: string) => {
    if (loading) return;
    askAgent(option, true); // true를 넘겨서 답변임을 알림
  };

  // '다음 문제' 버튼 클릭 시 대기 중인 퀴즈를 화면으로 올림
  const handleNext = () => {
    if (pendingQuiz) {
      setCurrentQuiz(pendingQuiz);
      setPendingQuiz(null);
      setFeedback(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 lg:p-10 font-sans text-gray-900">
      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* [좌측] 입력 및 키워드 요약 */}
        <section className="lg:col-span-4 space-y-6">
          <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100">
            <h3 className="text-sm font-bold text-gray-400 mb-4 uppercase tracking-widest">Interview Setting</h3>
            <div className="flex gap-2">
              <input
                className="flex-1 p-4 bg-gray-50 rounded-2xl outline-none focus:ring-2 focus:ring-blue-400 transition-all"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="어떤 기술을 면접보실까요?"
              />
              <button
                onClick={() => askAgent(message)}
                disabled={loading}
                className="bg-blue-600 text-white px-6 rounded-2xl font-bold hover:bg-blue-700 disabled:bg-gray-200 transition-all"
              >
                시작
              </button>
            </div>
          </div>

          <div className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100 min-h-[200px]">
            <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">📚 기술 요약</h3>
            {keywordSummary ? (
              <div className="animate-in fade-in slide-in-from-left-2 duration-500">
                <div className="inline-block bg-blue-50 text-blue-600 px-3 py-1 rounded-lg text-xs font-bold mb-3 uppercase">
                  {keywordSummary.keyword_key}
                </div>
                <p className="text-gray-600 text-sm leading-relaxed">{keywordSummary.summary}</p>
              </div>
            ) : (
              <p className="text-gray-300 italic text-sm text-center py-10">키워드를 입력하면 요약이 나타납니다.</p>
            )}
          </div>
        </section>

        {/* [중앙] 메인 면접 구역 */}
        <section className="lg:col-span-5 bg-white p-10 rounded-[2.5rem] shadow-xl shadow-blue-900/5 border border-white min-h-[600px] flex flex-col">
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-2xl font-black text-gray-800 tracking-tight">🎯 Interview Question</h2>
            {loading && <div className="w-5 h-5 border-3 border-blue-600 border-t-transparent rounded-full animate-spin"></div>}
          </div>

          {currentQuiz ? (
            <div className="flex-1 flex flex-col">
              {/* 질문 텍스트 카드 */}
              <div className="p-8 bg-gradient-to-br from-blue-600 to-blue-700 rounded-[2rem] text-white shadow-lg mb-8 shadow-blue-200">
                <p className="text-xl font-bold leading-snug">{currentQuiz.question_text}</p>
              </div>

              {/* 채점 결과 피드백 모드 */}
              {feedback ? (
                <div className="space-y-6 animate-in zoom-in duration-300">
                  <div className="p-6 bg-green-50 border-2 border-green-100 rounded-[1.5rem]">
                    <h4 className="font-bold text-green-800 mb-2 flex items-center gap-2">✅ 에이전트의 피드백</h4>
                    <p className="text-sm text-green-700 whitespace-pre-wrap leading-relaxed">{feedback}</p>
                  </div>
                  <button
                    onClick={handleNext}
                    className="w-full py-5 bg-gray-900 text-white rounded-2xl font-black text-lg hover:bg-black transition-all shadow-xl"
                  >
                    다음 문제 풀기 ➔
                  </button>
                </div>
              ) : (
                /* 답변 선택지 (피드백이 없을 때만 노출) */
                <div className="grid gap-4">
                  {currentQuiz.options?.map((option: string, i: number) => (
                    <button
                      key={i}
                      disabled={loading}
                      onClick={() => handleAnswerSubmit(option)}
                      className="text-left p-5 border-2 border-gray-100 rounded-2xl hover:border-blue-400 hover:bg-blue-50 transition-all group flex items-center"
                    >
                      <span className="w-10 h-10 bg-gray-100 rounded-xl flex items-center justify-center text-lg font-black mr-4 group-hover:bg-blue-200 transition-colors">
                        {i + 1}
                      </span>
                      <span className="font-bold text-gray-700">{option}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-gray-300 py-20">
              <span className="text-6xl mb-4">💬</span>
              <p className="font-medium text-center leading-relaxed">준비되셨나요?<br />왼쪽에서 키워드를 입력해 면접을 시작하세요.</p>
            </div>
          )}
        </section>

        {/* [우측] 에이전트 로그 콘솔 */}
        <section className="lg:col-span-3 bg-[#0d1117] rounded-[2rem] shadow-2xl flex flex-col max-h-[700px] overflow-hidden">
          <div className="bg-[#161b22] px-6 py-4 flex justify-between items-center border-b border-gray-800">
            <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Agent Logic</span>
            <div className="flex gap-1">
              <div className="w-2 h-2 rounded-full bg-red-500"></div>
              <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
              <div className="w-2 h-2 rounded-full bg-green-500"></div>
            </div>
          </div>
          <div className="p-6 overflow-y-auto flex-1 font-mono text-[10px] space-y-4">
            {logs.map((log, idx) => (
              <div key={idx} className="border-l-2 border-blue-900/50 pl-3">
                <span className="text-blue-500 font-bold mb-1 block uppercase">[{Object.keys(log)[0]}]</span>
                <pre className="text-gray-400 whitespace-pre-wrap leading-relaxed">
                  {JSON.stringify(Object.values(log)[0], null, 1)}
                </pre>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}