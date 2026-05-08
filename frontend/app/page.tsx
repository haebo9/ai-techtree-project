"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function Home() {
  const router = useRouter();
  const [jobTitle, setJobTitle] = useState("");
  const [experience, setExperience] = useState("신입");
  const [education, setEducation] = useState("학사(4년제)");

  // 이력서 관련 상태
  const [resumeMode, setResumeMode] = useState<"none" | "text" | "file">("none");
  const [resumeText, setResumeText] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [isParsingResume, setIsParsingResume] = useState(false);

  // 채용 공고 관련 상태
  const [jdMode, setJdMode] = useState<"none" | "text" | "image">("none");
  const [jdText, setJdText] = useState("");
  const [jdImageBase64, setJdImageBase64] = useState<string | null>(null);
  const [jdFileName, setJdFileName] = useState("");
  const [isDraggingResume, setIsDraggingResume] = useState(false);
  const [isDraggingJd, setIsDraggingJd] = useState(false);

  const processResumeFile = async (file: File) => {
    // 파일이 PDF나 TXT인지 확인하고 서버로 파싱 요청
    if (file.type === "application/pdf") {
      setResumeFile(file);
      setIsParsingResume(true);
      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch("http://localhost:8000/api/upload/parse-pdf", {
          method: "POST",
          body: formData,
        });

        if (res.ok) {
          const data = await res.json();
          setResumeText(data.text);
        } else {
          alert("PDF 파싱에 실패했습니다. 텍스트로 직접 입력해주세요.");
          setResumeMode("text");
          setResumeFile(null);
        }
      } catch (error) {
        console.error("PDF 파싱 에러:", error);
        alert("오류가 발생했습니다. 텍스트로 직접 입력해주세요.");
        setResumeMode("text");
        setResumeFile(null);
      } finally {
        setIsParsingResume(false);
      }
    } else if (file.type === "text/plain" || file.name.toLowerCase().endsWith(".txt")) {
      setResumeFile(file);
      const text = await file.text();
      setResumeText(text);
    } else {
      alert("지원하지 않는 파일 형식입니다. 이력서에는 PDF 또는 TXT 파일만 업로드 가능합니다.");
      setResumeFile(null);
    }
  };

  const processJdImage = async (file: File) => {
    let targetFile = file;

    // HEIC 파일 처리 (iPhone 등에서 주로 사용)
    if (file.name.toLowerCase().endsWith(".heic") || file.type === "image/heic" || file.type === "image/heif") {
      try {
        const heic2any = (await import("heic2any")).default;
        const blob = await heic2any({
          blob: file,
          toType: "image/jpeg",
          quality: 0.7
        });
        const convertedBlob = Array.isArray(blob) ? blob[0] : blob;
        targetFile = new File([convertedBlob], file.name.replace(/\.(heic|heif)$/i, ".jpg"), { type: "image/jpeg" });
      } catch (err) {
        console.error("HEIC 변환 에러:", err);
        alert("HEIC 파일 변환에 실패했습니다. JPG 또는 PNG 파일을 사용해 주세요.");
        return;
      }
    }

    if (!targetFile.type.startsWith("image/")) {
      alert("이미지 파일만 업로드 가능합니다.");
      return;
    }
    setJdFileName(targetFile.name);

    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement("canvas");
        const MAX_WIDTH = 800;
        let width = img.width;
        let height = img.height;

        if (width > MAX_WIDTH) {
          height = Math.round((height * MAX_WIDTH) / width);
          width = MAX_WIDTH;
        }

        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.drawImage(img, 0, 0, width, height);
          const compressedBase64 = canvas.toDataURL("image/jpeg", 0.6);
          setJdImageBase64(compressedBase64);
        }
      };
      if (event.target?.result) {
        img.src = event.target.result as string;
      }
    };
    reader.readAsDataURL(targetFile);
  };

  const handleResumeFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processResumeFile(e.target.files[0]);
    }
  };

  const handleJdImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processJdImage(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent, type: 'resume' | 'jd') => {
    e.preventDefault();
    e.stopPropagation();
    if (type === 'resume') setIsDraggingResume(false);
    else setIsDraggingJd(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (type === 'resume') processResumeFile(file);
      else processJdImage(file);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (isParsingResume) {
      alert("이력서 파일을 분석 중입니다. 잠시만 기다려주세요.");
      return;
    }

    // 로컬 스토리지에 프로필 저장
    localStorage.setItem("interviewProfile", JSON.stringify({
      job_title: jobTitle || "직무 미상",
      experience: experience,
      education: education,
      resume: resumeMode === "none" ? "이력서 없음" : (resumeText || "특별한 이력 없음"),
      job_description: jdMode === "text" ? jdText : "",
      job_image: jdMode === "image" ? jdImageBase64 : null
    }));

    // 면접 페이지로 이동
    router.push("/interview");
  };

  const loadDummyData = async () => {
    try {
      setJobTitle("AI Engineer");
      setExperience("신입");
      setEducation("학사(4년제)");

      // Load dummy resume PDF
      setResumeMode("file");
      setIsParsingResume(true);
      const resumeRes = await fetch("/dummy/dummy_resume.pdf");
      const resumeBlob = await resumeRes.blob();
      const resumeFile = new File([resumeBlob], "dummy_resume.pdf", { type: "application/pdf" });
      setResumeFile(resumeFile);

      const formData = new FormData();
      formData.append("file", resumeFile);
      const parseRes = await fetch("http://localhost:8000/api/upload/parse-pdf", {
        method: "POST",
        body: formData,
      });
      if (parseRes.ok) {
        const data = await parseRes.json();
        setResumeText(data.text);
      }
      setIsParsingResume(false);

      // Load dummy job posting PNG
      setJdMode("image");
      const jdRes = await fetch("/dummy/dummy_position.png");
      const jdBlob = await jdRes.blob();
      const jdFile = new File([jdBlob], "dummy_position.png", { type: "image/png" });
      setJdFileName(jdFile.name);

      const reader = new FileReader();
      reader.onload = (event) => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.createElement("canvas");
          const MAX_WIDTH = 800;
          let width = img.width;
          let height = img.height;
          if (width > MAX_WIDTH) {
            height = Math.round((height * MAX_WIDTH) / width);
            width = MAX_WIDTH;
          }
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext("2d");
          if (ctx) {
            ctx.drawImage(img, 0, 0, width, height);
            const compressedBase64 = canvas.toDataURL("image/jpeg", 0.6);
            setJdImageBase64(compressedBase64);
          }
        };
        if (event.target?.result) {
          img.src = event.target.result as string;
        }
      };
      reader.readAsDataURL(jdFile);

    } catch (error) {
      console.error("더미 데이터 로드 중 오류:", error);
      alert("더미 데이터 로드 실패");
      setIsParsingResume(false);
    }
  };

  return (
    <main className="min-h-screen bg-neutral-50 py-12 px-6">
      <div className="max-w-2xl mx-auto w-full bg-white rounded-3xl shadow-sm border border-neutral-100 p-8 sm:p-10 relative">
        <div className="absolute top-8 left-8">
          <Link href="/debug" className="text-neutral-200 hover:text-neutral-400 transition-colors" title="개발자 디버그 페이지">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </Link>
        </div>

        <button
          onClick={loadDummyData}
          className="absolute top-8 right-8 px-4 py-2 bg-neutral-100 hover:bg-neutral-200 text-neutral-700 text-sm font-medium rounded-lg transition-colors"
          type="button"
        >
          ⚙️ 테스트 데이터 사용
        </button>
        <div className="text-center mb-10 mt-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50 mb-6">
            <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-neutral-900 tracking-tight mb-3">
            마지막 승부 <span className="text-blue-600 font-medium text-2xl ml-1">TechTree</span>
          </h1>
          <p className="text-neutral-500 text-sm">지원자님의 프로필과 공고를 기반으로 맞춤형 면접을 생성합니다.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">

          {/* 1. 기본 정보 */}
          <div className="space-y-5">
            <h2 className="text-lg font-bold text-neutral-800 border-b pb-2">1. 기본 정보</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div className="sm:col-span-2">
                <label htmlFor="jobTitle" className="block text-sm font-medium text-neutral-700 mb-2">지원 직무</label>
                <input
                  type="text"
                  id="jobTitle"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  placeholder="예: AI 엔지니어, 프론트엔드 개발자"
                  className="w-full px-4 py-3 rounded-xl border border-neutral-200 focus:ring-2 focus:ring-blue-500 outline-none"
                  required
                />
              </div>
              <div>
                <label htmlFor="experience" className="block text-sm font-medium text-neutral-700 mb-2">경력</label>
                <select id="experience" value={experience} onChange={(e) => setExperience(e.target.value)} className="w-full px-4 py-3 rounded-xl border border-neutral-200 bg-white outline-none">
                  <option value="신입">신입</option>
                  <option value="1~3년차">1~3년차</option>
                  <option value="3~5년차">3~5년차</option>
                  <option value="5년차 이상">5년차 이상</option>
                </select>
              </div>
              <div>
                <label htmlFor="education" className="block text-sm font-medium text-neutral-700 mb-2">최종 학력</label>
                <select id="education" value={education} onChange={(e) => setEducation(e.target.value)} className="w-full px-4 py-3 rounded-xl border border-neutral-200 bg-white outline-none">
                  <option value="고졸">고졸</option>
                  <option value="전문학사(2~3년제)">전문학사(2~3년제)</option>
                  <option value="학사(4년제)">학사(4년제)</option>
                  <option value="석사">석사</option>
                  <option value="박사">박사</option>
                </select>
              </div>
            </div>
          </div>

          {/* 2. 이력서 입력 */}
          <div className="space-y-4">
            <div className="flex justify-between items-center border-b pb-2">
              <h2 className="text-lg font-bold text-neutral-800">2. 이력서 (선택)</h2>
              <div className="flex bg-neutral-100 p-1 rounded-lg">
                <button type="button" onClick={() => setResumeMode("none")} className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${resumeMode === "none" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500 hover:text-neutral-700"}`}>사용 안 함</button>
                <button type="button" onClick={() => setResumeMode("text")} className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${resumeMode === "text" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500 hover:text-neutral-700"}`}>직접 입력</button>
                <button type="button" onClick={() => setResumeMode("file")} className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${resumeMode === "file" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500 hover:text-neutral-700"}`}>파일 업로드</button>
              </div>
            </div>

            {resumeMode === "none" ? (
              <div className="text-sm text-neutral-500 p-4 bg-neutral-50 rounded-xl text-center">
                이력서 없이 직무 기반의 일반적인 면접을 진행합니다.
              </div>
            ) : resumeMode === "text" ? (
              <textarea
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                placeholder="간단한 이력 및 자기소개를 입력해주세요."
                rows={4}
                className="w-full px-4 py-3 rounded-xl border border-neutral-200 focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                required
              />
            ) : (
              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${isDraggingResume ? 'border-blue-500 bg-blue-50' : 'border-neutral-200 bg-neutral-50'}`}
                onDragOver={handleDragOver}
                onDragEnter={(e) => { e.preventDefault(); setIsDraggingResume(true); }}
                onDragLeave={(e) => { e.preventDefault(); setIsDraggingResume(false); }}
                onDrop={(e) => handleDrop(e, 'resume')}
              >
                <input type="file" id="resumeFile" accept=".pdf,.txt" onChange={handleResumeFileChange} className="hidden" />
                <div className={isDraggingResume ? "pointer-events-none" : ""}>
                  <label htmlFor="resumeFile" className="cursor-pointer text-blue-600 font-medium hover:underline inline-block mb-1">
                    파일을 여기에 드래그하거나 선택하세요
                  </label>
                  <p className="text-xs text-neutral-400">PDF 또는 TXT 파일 업로드</p>
                  {resumeFile && <p className="text-sm font-medium text-neutral-700 mt-4">✅ {resumeFile.name}</p>}
                  {isParsingResume && <p className="text-sm text-blue-600 mt-2 font-medium">텍스트 추출 중... ⏳</p>}
                  {!isParsingResume && resumeText && resumeMode === "file" && <p className="text-xs text-green-600 mt-2">성공적으로 텍스트를 추출했습니다.</p>}
                </div>
              </div>
            )}
          </div>

          {/* 3. 채용 공고 (선택) */}
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2 sm:gap-0 justify-between items-center border-b pb-2">
              <h2 className="text-lg font-bold text-neutral-800">3. 지원 공고 역량 (선택)</h2>
              <div className="flex bg-neutral-100 p-1 rounded-lg">
                <button type="button" onClick={() => setJdMode("none")} className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${jdMode === "none" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500 hover:text-neutral-700"}`}>사용 안함</button>
                <button type="button" onClick={() => setJdMode("text")} className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${jdMode === "text" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500 hover:text-neutral-700"}`}>텍스트 붙여넣기</button>
                <button type="button" onClick={() => setJdMode("image")} className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${jdMode === "image" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500 hover:text-neutral-700"}`}>이미지 캡처</button>
              </div>
            </div>

            {jdMode === "text" && (
              <textarea
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                placeholder="채용 공고의 자격 요건, 우대 사항 등을 붙여넣어 주세요."
                rows={4}
                className="w-full px-4 py-3 rounded-xl border border-neutral-200 focus:ring-2 focus:ring-blue-500 outline-none resize-none"
              />
            )}

            {jdMode === "image" && (
              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${isDraggingJd ? 'border-blue-500 bg-blue-50' : 'border-neutral-200 bg-neutral-50'}`}
                onDragOver={handleDragOver}
                onDragEnter={(e) => { e.preventDefault(); setIsDraggingJd(true); }}
                onDragLeave={(e) => { e.preventDefault(); setIsDraggingJd(false); }}
                onDrop={(e) => handleDrop(e, 'jd')}
              >
                <input type="file" id="jdImageFile" accept="image/*" onChange={handleJdImageChange} className="hidden" />
                <div className={isDraggingJd ? "pointer-events-none" : ""}>
                  <label htmlFor="jdImageFile" className="cursor-pointer text-blue-600 font-medium hover:underline inline-block mb-1">
                    파일을 여기에 드래그하거나 선택하세요
                  </label>
                  <p className="text-xs text-neutral-400">PNG, JPG, JPEG, HEIC 지원</p>
                  {jdFileName && <p className="text-sm font-medium text-neutral-700 mt-4">✅ {jdFileName}</p>}
                </div>
              </div>
            )}

            {jdMode === "none" && (
              <p className="text-sm text-neutral-500 py-4 bg-neutral-50 rounded-xl text-center border border-neutral-100">
                특정 공고 없이 일반적인 직무 면접으로 진행합니다.
              </p>
            )}
          </div>

          <div className="pt-6">
            <button type="submit" disabled={isParsingResume} className="w-full flex justify-center items-center py-4 px-4 border border-transparent rounded-xl shadow-sm text-base font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors">
              AI 면접 시작하기
              <svg className="ml-2 w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
        </form>
      </div>

      <footer className="mt-8 text-center text-xs text-neutral-400 max-w-md mx-auto leading-relaxed">
        <p>제공해주신 모든 데이터(이력서, 채용 공고 등)는 실시간 면접 분석을 위해서만 사용되며,<br />면접 종료 후 별도로 저장되지 않습니다.</p>
      </footer>
    </main>
  );
}