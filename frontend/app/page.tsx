import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-neutral-50 flex items-center justify-center p-6">
      <div className="max-w-lg w-full bg-white rounded-3xl shadow-sm border border-neutral-100 p-8 sm:p-10">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50 mb-6">
            <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-neutral-900 tracking-tight mb-3">TechTree 시작하기</h1>
          <p className="text-neutral-500 text-sm">실전 같은 AI 가상 면접을 위해 지원자님의 프로필을 알려주세요.</p>
        </div>

        <form className="space-y-6">
          <div>
            <label htmlFor="field" className="block text-sm font-medium text-neutral-700 mb-2">희망 분야</label>
            <select id="field" className="w-full px-4 py-3 rounded-xl border border-neutral-200 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-neutral-900">
              <option value="">분야를 선택해주세요</option>
              <option value="frontend">프론트엔드 (Frontend)</option>
              <option value="backend">백엔드 (Backend)</option>
              <option value="ai">AI / 머신러닝</option>
              <option value="data">데이터 엔지니어링</option>
            </select>
          </div>

          <div>
            <label htmlFor="job" className="block text-sm font-medium text-neutral-700 mb-2">상세 직무</label>
            <input type="text" id="job" placeholder="예: React 프론트엔드 개발자" className="w-full px-4 py-3 rounded-xl border border-neutral-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-neutral-900" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="experience" className="block text-sm font-medium text-neutral-700 mb-2">경력</label>
              <select id="experience" className="w-full px-4 py-3 rounded-xl border border-neutral-200 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-neutral-900">
                <option value="newcomer">신입</option>
                <option value="1-3">1~3년차</option>
                <option value="3-5">3~5년차</option>
                <option value="5+">5년차 이상</option>
              </select>
            </div>
            <div>
              <label htmlFor="major" className="block text-sm font-medium text-neutral-700 mb-2">전공 여부</label>
              <select id="major" className="w-full px-4 py-3 rounded-xl border border-neutral-200 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-neutral-900">
                <option value="cs">전공 (컴퓨터 공학 등)</option>
                <option value="non-cs">비전공</option>
              </select>
            </div>
          </div>

          <div className="pt-4">
            <Link href="/interview" className="w-full flex justify-center items-center py-4 px-4 border border-transparent rounded-xl shadow-sm text-base font-semibold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors">
              AI 면접 시작하기
              <svg className="ml-2 w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </Link>
          </div>
        </form>
      </div>
    </main>
  );
}