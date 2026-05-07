"use client";

import { useState } from "react";
import Link from "next/link";

export default function InterviewPage() {
  const [isRecording, setIsRecording] = useState(false);

  return (
    <main className="min-h-screen bg-neutral-900 flex flex-col items-center justify-center p-4 relative">
      {/* Top Header */}
      <div className="absolute top-0 w-full p-6 flex justify-between items-center z-10 max-w-5xl">
        <div className="flex items-center space-x-3 text-white">
          <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
          <span className="font-medium">면접 진행 중 (12:45)</span>
        </div>
        <Link href="/result" className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-white rounded-lg text-sm font-medium transition-colors border border-neutral-700">
          면접 종료하기
        </Link>
      </div>

      {/* Main AI Avatar/Visual Area */}
      <div className="flex-1 w-full max-w-5xl flex flex-col items-center justify-center">
        {/* Dynamic Voice Visualizer Placeholder */}
        <div className="relative w-64 h-64 mb-12 flex items-center justify-center">
          <div className="absolute inset-0 bg-blue-500/20 rounded-full blur-3xl animate-pulse"></div>
          <div className="w-32 h-32 bg-gradient-to-tr from-blue-600 to-indigo-500 rounded-full shadow-[0_0_40px_rgba(59,130,246,0.5)] flex items-center justify-center relative z-10">
            <svg className="w-12 h-12 text-white/80" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
        </div>

        {/* Subtitles / AI Dialogue */}
        <div className="max-w-2xl text-center mb-16 space-y-4">
          <p className="text-blue-400 font-medium text-sm tracking-widest uppercase">AI 면접관</p>
          <p className="text-2xl sm:text-3xl font-medium text-white leading-relaxed">
            "프론트엔드 개발에서 상태 관리를 위해 주로 어떤 라이브러리를 사용하셨나요? 그리고 그 라이브러리를 선택한 이유는 무엇인가요?"
          </p>
        </div>
      </div>

      {/* Bottom Controls */}
      <div className="w-full max-w-3xl pb-10">
        <div className="bg-neutral-800/50 backdrop-blur-md border border-neutral-700 rounded-3xl p-4 flex flex-col items-center">
          
          <button 
            onClick={() => setIsRecording(!isRecording)}
            className={`w-20 h-20 rounded-full flex items-center justify-center transition-all shadow-lg ${
              isRecording 
                ? 'bg-red-500 hover:bg-red-600 shadow-red-500/30' 
                : 'bg-white hover:bg-gray-100 text-neutral-900'
            }`}
          >
            {isRecording ? (
              <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
            ) : (
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            )}
          </button>
          
          <p className="mt-4 text-neutral-400 text-sm">
            {isRecording ? '말씀해주세요. 듣고 있습니다...' : '버튼을 눌러 답변을 시작하세요'}
          </p>
        </div>
      </div>
    </main>
  );
}
