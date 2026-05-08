import Link from "next/link";

export default function ResultPage() {
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
            <div className="text-5xl font-extrabold text-blue-600">85<span className="text-2xl text-neutral-400 font-medium">/100</span></div>
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
                  <p className="text-neutral-600 leading-relaxed">
                    프론트엔드 상태 관리 도구(Redux, Zustand 등)의 차이점을 명확히 인지하고 있으며, 
                    프로젝트 규모에 맞는 적절한 기술 선택 능력이 돋보입니다. 특히 답변을 구조화하여 설명하는 논리력이 우수합니다.
                  </p>
                </div>
                <div className="h-px w-full bg-neutral-100"></div>
                <div>
                  <h3 className="text-lg font-semibold text-orange-600 mb-2">🚀 개선점 (Areas for Improvement)</h3>
                  <p className="text-neutral-600 leading-relaxed">
                    SSR(Server-Side Rendering)과 관련하여 Next.js의 동작 원리에 대한 깊이 있는 이해가 다소 부족해 보입니다. 
                    하이드레이션(Hydration) 과정과 최적화 기법에 대해 보완한다면 더 좋은 평가를 받을 수 있습니다.
                  </p>
                </div>
              </div>
            </div>

            {/* Q&A History Review */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-neutral-100">
              <h2 className="text-xl font-bold text-neutral-900 mb-6">📝 상세 답변 분석</h2>
              <div className="space-y-6">
                <div className="p-5 rounded-2xl bg-neutral-50 border border-neutral-100">
                  <p className="font-medium text-neutral-900 mb-2">Q. 프론트엔드 개발에서 상태 관리를 위해 주로 어떤 라이브러리를 사용하셨나요?</p>
                  <p className="text-neutral-600 text-sm mb-4">A. 주로 Zustand를 사용했습니다. 보일러플레이트가 적어... (답변 내용)</p>
                  <div className="flex items-start bg-blue-50 p-4 rounded-xl text-sm">
                    <span className="text-blue-600 font-bold mr-2">AI 코멘트:</span>
                    <span className="text-blue-900">현업 트렌드에 맞는 답변이었습니다. 다만, 복잡한 상태에서의 한계점을 같이 언급했다면 완벽했을 것입니다.</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Recommendations & Actions */}
          <div className="space-y-8">
            {/* Job Recommendations */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-neutral-100">
              <h2 className="text-lg font-bold text-neutral-900 mb-5">🎯 맞춤 채용 공고</h2>
              <div className="space-y-4">
                <div className="block p-4 rounded-xl border border-neutral-200 hover:border-blue-500 transition-colors cursor-pointer group">
                  <p className="text-xs text-blue-600 font-semibold mb-1">토스 (Toss)</p>
                  <h3 className="font-bold text-neutral-900 group-hover:text-blue-600 transition-colors">Frontend Developer (React)</h3>
                  <p className="text-xs text-neutral-500 mt-2">경력 3년 이상 · 판교</p>
                </div>
                <div className="block p-4 rounded-xl border border-neutral-200 hover:border-blue-500 transition-colors cursor-pointer group">
                  <p className="text-xs text-blue-600 font-semibold mb-1">카카오 (Kakao)</p>
                  <h3 className="font-bold text-neutral-900 group-hover:text-blue-600 transition-colors">웹 프론트엔드 개발자</h3>
                  <p className="text-xs text-neutral-500 mt-2">신입/경력 · 제주/성남</p>
                </div>
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
