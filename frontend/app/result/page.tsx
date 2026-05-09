"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

interface QnAReview {
  question: string;
  answer: string;
  feedback: string;
}

interface JobRecommendation {
  company: string;
  title: string;
  url?: string;
}

interface EvaluationResult {
  session_id?: string;
  score: number;
  strengths: string[];
  weaknesses: string[];
  qa_review: QnAReview[];
  job_recommendations: JobRecommendation[];
}

export default function ResultPage() {
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [transcripts, setTranscripts] = useState<any[]>([]);
  const [duration, setDuration] = useState("");
  const [date, setDate] = useState("");
  const [email, setEmail] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [emailStatus, setEmailStatus] = useState<"idle" | "success" | "error">("idle");
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    const savedResult = localStorage.getItem("interviewResult");
    const savedTranscripts = localStorage.getItem("interviewTranscripts");
    const savedDuration = localStorage.getItem("interviewDuration");
    const savedDate = localStorage.getItem("interviewDate");

    if (savedResult) {
      try {
        setResult(JSON.parse(savedResult));
      } catch (e) {
        console.error("Failed to parse result", e);
        setLoadError(true);
      }
    } else {
      const timer = setTimeout(() => setLoadError(true), 3000);
      return () => clearTimeout(timer);
    }

    if (savedTranscripts) {
      try {
        setTranscripts(JSON.parse(savedTranscripts));
      } catch (e) {
        console.error("Failed to parse transcripts", e);
      }
    }

    if (savedDuration) setDuration(savedDuration);
    if (savedDate) setDate(savedDate);
  }, []);

  const handleSendEmail = async () => {
    if (!email || !result) return;

    setIsSending(true);
    setEmailStatus("idle");

    try {
      const response = await fetch(`http://localhost:8000/api/interview/${result.session_id || 'default'}/email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email,
          score: result.score,
          strengths: result.strengths,
          weaknesses: result.weaknesses,
          qa_review: result.qa_review || [],
          job_recommendations: result.job_recommendations || [],
          transcripts: transcripts,
          interview_date: date,
          interview_duration: duration
        })
      });

      if (response.ok) {
        setEmailStatus("success");
      } else {
        setEmailStatus("error");
      }
    } catch (e) {
      console.error(e);
      setEmailStatus("error");
    } finally {
      setIsSending(false);
    }
  };

  if (loadError) {
    return (
      <main className="min-h-screen bg-neutral-50 p-6 sm:p-12 flex flex-col items-center justify-center">
        <div className="text-xl font-bold text-neutral-800 mb-4">리포트를 불러오지 못했습니다.</div>
        <p className="text-neutral-500 mb-6 text-center">면접 내용이 부족하거나 평가 중 오류가 발생했을 수 있습니다.<br />홈으로 돌아가서 다시 시도해주세요.</p>
        <Link href="/" className="px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-colors">
          홈으로 돌아가기
        </Link>
      </main>
    );
  }

  if (!result) {
    return (
      <main className="min-h-screen bg-neutral-50 p-6 sm:p-12 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <div className="text-xl font-bold text-neutral-500">리포트를 분석 중입니다...</div>
        </div>
      </main>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-emerald-500";
    if (score >= 50) return "text-blue-500";
    return "text-orange-500";
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return "bg-emerald-500";
    if (score >= 50) return "bg-blue-500";
    return "bg-orange-500";
  };

  const getScoreMessage = (score: number) => {
    if (score >= 80) return "우수한 면접 성과입니다!";
    if (score >= 60) return "충분히 가능성 있는 실력입니다.";
    if (score >= 40) return "조금 더 준비하면 좋겠어요.";
    return "집중적인 연습이 필요합니다.";
  };

  return (
    <main className="min-h-screen bg-neutral-50 py-12 px-4 sm:px-6 relative overflow-hidden">
      {/* Background Decoration */}
      <div className="absolute -top-24 -right-24 w-96 h-96 bg-blue-100/50 rounded-full opacity-50 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-emerald-100/50 rounded-full opacity-50 blur-3xl pointer-events-none" />

      <div className="max-w-5xl mx-auto space-y-8 relative z-10">

        {/* Header Section */}
        <div className="bg-white/80 backdrop-blur-xl rounded-[2.5rem] p-8 sm:p-10 shadow-xl shadow-neutral-200/50 border border-white flex flex-col md:flex-row md:items-center justify-between gap-8">
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-500 p-0.5 shadow-lg rotate-3 shrink-0">
                <div className="w-full h-full bg-white rounded-[14px] flex items-center justify-center overflow-hidden">
                  <img src="/logo.png" alt="Logo" className="w-3/4 h-3/4 object-contain" />
                </div>
              </div>
              <div className="px-4 py-1.5 bg-emerald-50 text-emerald-600 text-[10px] font-black rounded-full uppercase tracking-[0.2em] border border-emerald-100 animate-pulse">
                Analysis Intelligence
              </div>
            </div>
            <div>
              <h1 className="text-4xl font-black text-neutral-900 tracking-tight mb-2">면접 종합 평가 리포트</h1>
              <p className="text-neutral-500 text-lg font-medium">지원자님의 가상 면접 결과를 다각도로 분석했습니다.</p>
            </div>
          </div>

          <div className="flex items-center gap-6 bg-neutral-50/50 p-6 rounded-3xl border border-neutral-100 shadow-inner">
            <div className="text-right">
              <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-1">Total Score</p>
              <div className={`text-6xl font-black ${getScoreColor(result.score)} tabular-nums`}>
                {result.score}
                <span className="text-2xl text-neutral-300 font-bold ml-1">/100</span>
              </div>
              <p className={`text-sm font-bold mt-1 ${getScoreColor(result.score)}`}>{getScoreMessage(result.score)}</p>
            </div>

            {/* Simple Circular Progress with Glow */}
            <div className="relative w-28 h-28 group">
              <div className={`absolute inset-0 rounded-full blur-xl opacity-20 transition-all group-hover:opacity-40 ${getScoreBg(result.score)}`} />
              <svg className="w-full h-full -rotate-90 relative z-10" viewBox="0 0 100 100">
                <circle className="text-neutral-100" strokeWidth="8" stroke="currentColor" fill="transparent" r="42" cx="50" cy="50" />
                <circle className={`${getScoreColor(result.score)} transition-all duration-1000 ease-out`} strokeWidth="8" strokeDasharray={2 * Math.PI * 42} strokeDashoffset={2 * Math.PI * 42 * (1 - result.score / 100)} strokeLinecap="round" stroke="currentColor" fill="transparent" r="42" cx="50" cy="50" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center z-20">
                <div className={`w-2 h-2 rounded-full ${getScoreBg(result.score)} animate-ping mb-1`} />
                <span className="text-[10px] font-black text-neutral-400 uppercase tracking-tighter">Status</span>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">

          {/* Left Column: Feedback */}
          <div className="md:col-span-2 space-y-8">
            <div className="bg-white rounded-[2.5rem] p-8 sm:p-10 shadow-xl shadow-neutral-200/40 border border-neutral-100">
              <h2 className="text-xl font-black text-neutral-900 mb-8 flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-200">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                </div>
                주요 피드백
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
                <div className="space-y-4">
                  <h3 className="text-sm font-black text-emerald-600 uppercase tracking-widest flex items-center gap-2">
                    <span className="w-2 h-2 bg-emerald-500 rounded-full" />
                    ✅ 강점
                  </h3>
                  <ul className="space-y-4">
                    {result.strengths?.map((s, idx) => (
                      <li key={idx} className="flex items-start gap-3 p-4 rounded-2xl bg-emerald-50/50 border border-emerald-100/50 text-neutral-800 font-bold text-sm leading-relaxed transition-all hover:scale-[1.02]">
                        <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center shrink-0 shadow-md shadow-emerald-200">
                          <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={4}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                        </div>
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="space-y-4">
                  <h3 className="text-sm font-black text-orange-600 uppercase tracking-widest flex items-center gap-2">
                    <span className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" />
                    🚀 개선점
                  </h3>
                  <ul className="space-y-4">
                    {result.weaknesses?.map((w, idx) => (
                      <li key={idx} className="flex items-start gap-3 p-4 rounded-2xl bg-orange-50/50 border border-orange-100/50 text-neutral-800 font-bold text-sm leading-relaxed transition-all hover:scale-[1.02]">
                        <div className="w-6 h-6 rounded-full bg-orange-500 flex items-center justify-center shrink-0 shadow-md shadow-orange-200">
                          <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={4}><path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
                        </div>
                        {w}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {/* Q&A History Review */}
            <div className="bg-white rounded-[2.5rem] p-8 sm:p-10 shadow-xl shadow-neutral-200/40 border border-neutral-100">
              <h2 className="text-xl font-black text-neutral-900 mb-8 flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-200">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z" /></svg>
                </div>
                상세 답변 분석
              </h2>
              <div className="space-y-8">
                {result.qa_review?.map((qa, idx) => (
                  <div key={idx} className="relative pl-8 sm:pl-10 before:absolute before:left-0 before:top-4 before:bottom-0 before:w-1.5 before:bg-neutral-100/80 before:rounded-full">
                    <div className="bg-neutral-50/50 p-6 sm:p-8 rounded-[2rem] border border-neutral-100 hover:border-blue-200 transition-all hover:shadow-lg hover:shadow-blue-50 group/item">
                      <div className="flex gap-5 mb-5 relative">
                        <div className="w-10 h-10 rounded-2xl bg-white border border-neutral-100 flex items-center justify-center shrink-0 text-xs font-black text-neutral-400 shadow-sm transition-transform group-hover/item:-rotate-6">Q</div>
                        <p className="font-black text-neutral-900 text-lg leading-relaxed pt-1">{qa.question}</p>
                      </div>
                      <div className="flex gap-5 mb-8">
                        <div className="w-10 h-10 rounded-2xl bg-blue-600/5 border border-blue-100 flex items-center justify-center shrink-0 text-xs font-black text-blue-400 shadow-sm transition-transform group-hover/item:rotate-6">A</div>
                        <p className="text-neutral-600 font-bold text-base leading-relaxed pt-1">{qa.answer}</p>
                      </div>
                      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-[1px] rounded-2xl shadow-lg shadow-blue-100">
                        <div className="bg-white p-5 rounded-[15px] flex items-start gap-4">
                          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shrink-0 shadow-lg shadow-blue-200">
                            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                          </div>
                          <div>
                            <p className="text-[10px] font-black text-blue-600 uppercase tracking-[0.2em] mb-1">AI Recommendation</p>
                            <p className="text-neutral-900 text-sm font-bold leading-relaxed">{qa.feedback}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                {(!result.qa_review || result.qa_review.length === 0) && (
                  <div className="py-12 text-center">
                    <p className="text-neutral-400 font-bold">추출된 주요 질의응답이 없습니다.</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Recommendations & Actions */}
          <div className="space-y-8">
            {/* New: Restart Button */}
            <Link href="/" className="group relative w-full flex justify-center items-center py-5 px-6 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-lg font-black rounded-[2rem] shadow-xl shadow-blue-200 overflow-hidden transition-all active:scale-95">
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
              <span className="relative flex items-center gap-3">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                새로운 면접 보러가기
              </span>
            </Link>

            {/* Job Recommendations */}
            <div className="bg-white rounded-[2.5rem] p-8 shadow-xl shadow-neutral-200/40 border border-neutral-100">
              <h2 className="text-sm font-black text-neutral-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                🎯 맞춤 채용 공고
              </h2>
              <div className="space-y-4">
                {result.job_recommendations?.map((job, idx) => {
                  const content = (
                    <>
                      <div className="flex justify-between items-start mb-2">
                        <p className="text-[10px] font-black text-blue-600 uppercase bg-blue-50 px-2 py-0.5 rounded-md">{job.company}</p>
                        <svg className="w-4 h-4 text-neutral-300 group-hover:text-blue-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                      </div>
                      <h3 className="font-bold text-neutral-900 group-hover:text-blue-600 transition-colors text-sm line-clamp-2">{job.title}</h3>
                    </>
                  );

                  return job.url ? (
                    <a key={idx} href={job.url} target="_blank" rel="noopener noreferrer" className="block p-5 rounded-2xl border border-neutral-100 bg-neutral-50/30 hover:bg-white hover:border-blue-200 hover:shadow-lg hover:shadow-blue-100 transition-all cursor-pointer group">
                      {content}
                    </a>
                  ) : (
                    <div key={idx} className="block p-5 rounded-2xl border border-neutral-100 bg-neutral-50/30 cursor-default">
                      {content}
                    </div>
                  );
                })}
                {(!result.job_recommendations || result.job_recommendations.length === 0) && (
                  <div className="py-10 px-6 text-center bg-neutral-50 rounded-[2rem] border border-dashed border-neutral-200 group/empty">
                    <div className="w-12 h-12 rounded-full bg-white border border-neutral-100 flex items-center justify-center mx-auto mb-4 shadow-sm group-hover/empty:scale-110 transition-transform">
                      <svg className="w-6 h-6 text-neutral-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                    </div>
                    <p className="text-[11px] text-neutral-500 font-bold leading-relaxed">
                      현재 추천된 공고가 없습니다.<br />
                      <span className="text-blue-500 font-black">더 많은 면접 경험</span>을 쌓아보세요!
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Action Card */}
            <div className="bg-gradient-to-br from-neutral-900 via-neutral-800 to-neutral-900 rounded-[2.5rem] p-8 shadow-2xl text-white relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2 blur-2xl group-hover:scale-150 transition-transform duration-700" />

              <h2 className="text-xl font-black mb-2 relative z-10">리포트 소장하기</h2>
              <p className="text-neutral-400 text-sm mb-8 leading-relaxed font-medium relative z-10">
                입력하신 이메일로 상세 리포트와 채용 정보를 보내드립니다.
                <span className="block mt-1 text-xs text-blue-400 font-black tracking-tight">전체 대화 내용 포함 📦</span>
              </p>

              <div className="space-y-4 relative z-10">
                <div className="relative">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="example@email.com"
                    className="w-full px-5 py-4 rounded-2xl bg-white/5 border border-white/10 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all font-medium"
                  />
                </div>
                <button
                  onClick={handleSendEmail}
                  disabled={isSending || !email}
                  className="w-full py-4 px-6 bg-white text-neutral-900 text-lg font-black rounded-2xl hover:bg-blue-50 disabled:opacity-30 disabled:cursor-not-allowed transition-all active:scale-95 shadow-xl"
                >
                  {isSending ? (
                    <span className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-neutral-900 border-t-transparent rounded-full animate-spin" />
                      전송 중...
                    </span>
                  ) : "이메일로 받기"}
                </button>

                {emailStatus === "success" && (
                  <div className="bg-emerald-500/10 border border-emerald-500/20 py-2 rounded-xl">
                    <p className="text-emerald-400 text-xs font-black text-center">✅ 성공적으로 전송되었습니다!</p>
                  </div>
                )}
                {emailStatus === "error" && (
                  <div className="bg-red-500/10 border border-red-500/20 py-2 rounded-xl">
                    <p className="text-red-400 text-xs font-black text-center">❌ 전송에 실패했습니다.</p>
                  </div>
                )}

                <p className="text-[10px] text-neutral-500 font-bold mt-6 text-center leading-relaxed">
                  기록 저장을 위해 리포트는 반드시<br />본인의 이메일로 즉시 소장해 주시기 바랍니다.
                </p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </main>
  );
}
