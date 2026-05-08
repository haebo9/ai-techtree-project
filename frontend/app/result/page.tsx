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
  score: number;
  strengths: string[];
  weaknesses: string[];
  qa_review: QnAReview[];
  job_recommendations: JobRecommendation[];
}

export default function ResultPage() {
  const [result, setResult] = useState<EvaluationResult | null>(null);

  useEffect(() => {
    const savedResult = localStorage.getItem("interviewResult");
    if (savedResult) {
      try {
        setResult(JSON.parse(savedResult));
      } catch (e) {
        console.error("Failed to parse result", e);
      }
    }
  }, []);

  if (!result) {
    return (
      <main className="min-h-screen bg-neutral-50 p-6 sm:p-12 flex items-center justify-center">
        <div className="text-xl font-bold text-neutral-500 animate-pulse">리포트를 불러오는 중입니다...</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-neutral-50 p-6 sm:p-12">
      <div className="max-w-4xl mx-auto space-y-8">
        
        {/* Header Section */}
        <div className="bg-white rounded-3xl p-8 shadow-sm border border-neutral-100 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="inline-block px-3 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full mb-3">
              분석 완료
            </div>
            <h1 className="text-3xl font-bold text-neutral-900 mb-2">면접 종합 평가 리포트</h1>
            <p className="text-neutral-500">지원자님의 가상 면접 결과를 다각도로 분석했습니다.</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-neutral-500 mb-1">종합 점수</p>
            <div className="text-5xl font-extrabold text-blue-600">{result.score}<span className="text-2xl text-neutral-400 font-medium">/100</span></div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          
          {/* Left Column: Feedback */}
          <div className="md:col-span-2 space-y-8">
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-neutral-100">
              <h2 className="text-xl font-bold text-neutral-900 mb-6 flex items-center">
                <span className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center mr-3 text-sm">💡</span>
                주요 피드백
              </h2>
              
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-green-700 mb-2">✅ 강점 (Strengths)</h3>
                  <ul className="list-disc list-inside text-neutral-600 leading-relaxed space-y-1">
                    {result.strengths?.map((s, idx) => (
                      <li key={idx}>{s}</li>
                    ))}
                  </ul>
                </div>
                <div className="h-px w-full bg-neutral-100"></div>
                <div>
                  <h3 className="text-lg font-semibold text-orange-600 mb-2">🚀 개선점 (Areas for Improvement)</h3>
                  <ul className="list-disc list-inside text-neutral-600 leading-relaxed space-y-1">
                    {result.weaknesses?.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {/* Q&A History Review */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-neutral-100">
              <h2 className="text-xl font-bold text-neutral-900 mb-6">📝 상세 답변 분석</h2>
              <div className="space-y-6">
                {result.qa_review?.map((qa, idx) => (
                  <div key={idx} className="p-5 rounded-2xl bg-neutral-50 border border-neutral-100">
                    <p className="font-medium text-neutral-900 mb-2">Q. {qa.question}</p>
                    <p className="text-neutral-600 text-sm mb-4">A. {qa.answer}</p>
                    <div className="flex items-start bg-blue-50 p-4 rounded-xl text-sm">
                      <span className="text-blue-600 font-bold mr-2 whitespace-nowrap">AI 코멘트:</span>
                      <span className="text-blue-900">{qa.feedback}</span>
                    </div>
                  </div>
                ))}
                {(!result.qa_review || result.qa_review.length === 0) && (
                  <p className="text-neutral-500 text-sm">추출된 주요 질의응답이 없습니다.</p>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Recommendations & Actions */}
          <div className="space-y-8">
            {/* Job Recommendations */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-neutral-100">
              <h2 className="text-lg font-bold text-neutral-900 mb-5">🎯 맞춤 채용 공고</h2>
              <div className="space-y-4">
                {result.job_recommendations?.map((job, idx) => {
                  const content = (
                    <>
                      <p className="text-xs text-blue-600 font-semibold mb-1">{job.company}</p>
                      <h3 className="font-bold text-neutral-900 group-hover:text-blue-600 transition-colors">{job.title}</h3>
                    </>
                  );
                  
                  return job.url ? (
                    <a key={idx} href={job.url} target="_blank" rel="noopener noreferrer" className="block p-4 rounded-xl border border-neutral-200 hover:border-blue-500 transition-colors cursor-pointer group">
                      {content}
                    </a>
                  ) : (
                    <div key={idx} className="block p-4 rounded-xl border border-neutral-200 transition-colors cursor-default">
                      {content}
                    </div>
                  );
                })}
                {(!result.job_recommendations || result.job_recommendations.length === 0) && (
                  <p className="text-neutral-500 text-sm">추천된 공고가 없습니다.</p>
                )}
              </div>
            </div>

            {/* Action Card */}
            <div className="bg-gradient-to-br from-neutral-900 to-neutral-800 rounded-3xl p-8 shadow-lg text-white">
              <h2 className="text-lg font-bold mb-2">리포트 소장하기</h2>
              <p className="text-neutral-300 text-sm mb-6">입력하신 이메일로 상세 리포트와 채용 정보를 보내드립니다.</p>
              <div className="space-y-3">
                <input type="email" placeholder="이메일 주소 입력" className="w-full px-4 py-3 rounded-xl bg-neutral-800 border border-neutral-600 text-white placeholder-neutral-400 focus:outline-none focus:border-white transition-colors" />
                <button className="w-full py-3 px-4 bg-white text-neutral-900 font-bold rounded-xl hover:bg-neutral-100 transition-colors">
                  이메일로 받기
                </button>
              </div>
              
              <div className="mt-6 pt-6 border-t border-neutral-700">
                <Link href="/" className="block text-center text-neutral-300 hover:text-white text-sm font-medium transition-colors">
                  홈으로 돌아가기
                </Link>
              </div>
            </div>
          </div>

        </div>
      </div>
    </main>
  );
}
