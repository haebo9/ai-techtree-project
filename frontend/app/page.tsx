"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  const [jobTitle, setJobTitle] = useState("");
  const [experience, setExperience] = useState("신입");
  const [education, setEducation] = useState("학사(4년제)");
  const [resume, setResume] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // 로컬 스토리지에 프로필 저장
    localStorage.setItem("interviewProfile", JSON.stringify({
      job_title: jobTitle || "직무 미상",
      experience: experience,
      education: education,
      resume: resume || "특별한 이력 없음"
    }));

    // 면접 페이지로 이동
    router.push("/interview");
  };

  return (
    <main className="min-h-screen bg-neutral-50 flex items-center justify-center p-6">
      <div className="max-w-xl w-full bg-white rounded-3xl shadow-sm border border-neutral-100 p-8 sm:p-10">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50 mb-6">
            <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-neutral-900 tracking-tight mb-3">TechTree 시작하기</h1>
          <p className="text-neutral-500 text-sm">개발자, 기획자, 마케터 등 모든 직군을 위한 실전 AI 가상 면접입니다. 지원자님의 프로필을 알려주세요.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="jobTitle" className="block text-sm font-medium text-neutral-700 mb-2">지원 직무</label>
            <input
              type="text"
              id="jobTitle"
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              placeholder="예: AI 엔지니어, QA, 데이터 애널리스트, 게임 기획자"
              className="w-full px-4 py-3 rounded-xl border border-neutral-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-neutral-900"
              required
            />
          </div>

          <div>
            <label htmlFor="experience" className="block text-sm font-medium text-neutral-700 mb-2">경력</label>
            <select
              id="experience"
              value={experience}
              onChange={(e) => setExperience(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-neutral-200 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-neutral-900"
            >
              <option value="신입">신입</option>
              <option value="1~3년차">1~3년차</option>
              <option value="3~5년차">3~5년차</option>
              <option value="5년차 이상">5년차 이상</option>
            </select>
          </div>

          <div>
            <label htmlFor="education" className="block text-sm font-medium text-neutral-700 mb-2">최종 학력</label>
            <select
              id="education"
              value={education}
              onChange={(e) => setEducation(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-neutral-200 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-neutral-900"
            >
              <option value="고졸">고졸</option>
              <option value="전문학사(2~3년제)">전문학사(2~3년제)</option>
              <option value="학사(4년제)">학사(4년제)</option>
              <option value="석사">석사</option>
              <option value="박사">박사</option>
            </select>
          </div>

          <div>
            <label htmlFor="resume" className="block text-sm font-medium text-neutral-700 mb-2">간단한 이력 및 자기소개 요약</label>
            <textarea
              id="resume"
              value={resume}
              onChange={(e) => setResume(e.target.value)}
              placeholder="예: 핀테크 앱 런칭 경험이 있습니다. 주로 사용자 데이터를 분석하여 리텐션을 높이는 업무를 담당했습니다."
              rows={4}
              className="w-full px-4 py-3 rounded-xl border border-neutral-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-neutral-900 resize-none"
              required
            />
          </div>

          <div className="pt-4">
            <button type="submit" className="w-full flex justify-center items-center py-4 px-4 border border-transparent rounded-xl shadow-sm text-base font-semibold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors">
              AI 면접 시작하기
              <svg className="ml-2 w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}