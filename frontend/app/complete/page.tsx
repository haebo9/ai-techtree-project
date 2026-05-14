"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";

export default function CompletePage() {
  const [email] = useState(() => {
    if (typeof window === "undefined") return "";
    const savedProfile = sessionStorage.getItem("interviewProfile");
    const profile = savedProfile ? JSON.parse(savedProfile) : null;
    return profile?.report_email || "";
  });

  const reuseProfile = () => {
    sessionStorage.setItem("reuseInterviewProfile", "true");
  };

  const clearProfile = () => {
    sessionStorage.removeItem("interviewProfile");
    sessionStorage.removeItem("reuseInterviewProfile");
    sessionStorage.removeItem("lastInterviewEndedAt");
    sessionStorage.removeItem("interviewTranscriptsForEmail");
    localStorage.removeItem("interviewProfile");
    localStorage.removeItem("interviewResult");
    localStorage.removeItem("interviewTranscripts");
    localStorage.removeItem("interviewDuration");
    localStorage.removeItem("interviewDate");
  };

  return (
    <main className="min-h-screen bg-neutral-50 px-4 py-12 flex items-center justify-center">
      <div className="w-full max-w-2xl rounded-[2.5rem] bg-white border border-neutral-100 shadow-2xl shadow-neutral-200/60 p-8 sm:p-12 text-center">
        <div className="mx-auto mb-6 w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-500 p-0.5 shadow-lg rotate-3">
          <div className="w-full h-full bg-white rounded-[14px] flex items-center justify-center overflow-hidden">
            <Image src="/logo.png" alt="Logo" width={48} height={48} className="w-3/4 h-3/4 object-contain" priority />
          </div>
        </div>

        <p className="mb-3 text-xs font-black uppercase tracking-[0.22em] text-emerald-600">Interview Completed</p>
        <h1 className="text-3xl sm:text-4xl font-black text-neutral-950 tracking-tight mb-4">면접이 종료되었습니다</h1>
        <p className="text-neutral-600 font-bold leading-relaxed mb-8">
          분석 리포트는 비동기로 생성된 뒤 입력하신 이메일로 전송됩니다.
          {email && (
            <span className="block mt-2 text-blue-600">{email}</span>
          )}
        </p>

        <div className="rounded-3xl bg-blue-50 border border-blue-100 p-5 text-left mb-8">
          <p className="text-sm font-black text-blue-700 mb-1">잠시만 기다려 주세요</p>
          <p className="text-sm font-medium text-blue-900/70 leading-relaxed">
            리포트 생성에는 답변 분량과 이메일 발송 상태에 따라 시간이 조금 걸릴 수 있습니다.
            입력하신 이력서와 공고 원문은 DB에 저장하지 않습니다.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Link
            href="/"
            onClick={reuseProfile}
            className="rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-4 text-white text-base font-black shadow-xl shadow-blue-100 transition-all active:scale-95"
          >
            같은 정보로 다시 연습하기
          </Link>
          <Link
            href="/"
            onClick={clearProfile}
            className="rounded-2xl bg-neutral-100 px-5 py-4 text-neutral-900 text-base font-black transition-all hover:bg-neutral-200 active:scale-95"
          >
            새 정보로 시작하기
          </Link>
        </div>
      </div>
    </main>
  );
}
