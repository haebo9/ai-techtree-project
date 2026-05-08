"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function Home() {
  const router = useRouter();
  const [jobTitle, setJobTitle] = useState("");
  const [experience, setExperience] = useState("");
  const [education, setEducation] = useState("");

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
  const [isAnalyzingJd, setIsAnalyzingJd] = useState(false);
  const [isAutoFilled, setIsAutoFilled] = useState(false);

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

  const analyzeJdContent = async (text?: string, image?: string) => {
    if (!text && !image) return;
    setIsAnalyzingJd(true);
    try {
      const res = await fetch("http://localhost:8000/api/upload/analyze-jd", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, image }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.job_title) {
          setJobTitle(data.job_title);
          setIsAutoFilled(true);
        }
      }
    } catch (error) {
      console.error("JD 분석 에러:", error);
    } finally {
      setIsAnalyzingJd(false);
    }
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

  // jdImageBase64가 변경될 때 자동 분석
  useEffect(() => {
    if (jdImageBase64) {
      analyzeJdContent(undefined, jdImageBase64);
    }
  }, [jdImageBase64]);

  // jdText가 일정 길이 이상일 때 자동 분석 (디바운스 고려)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (jdText && jdText.length > 20) {
        analyzeJdContent(jdText);
      }
    }, 1000);
    return () => clearTimeout(timer);
  }, [jdText]);

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

    if (!jobTitle || !experience || !education) {
      alert("지원 직무, 경력, 최종 학력을 모두 입력 및 선택해 주세요.");
      return;
    }

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
    <main className="min-h-screen bg-neutral-50 py-12 px-4 sm:px-6">
      <div className="max-w-4xl mx-auto w-full bg-white rounded-[2rem] shadow-xl border border-neutral-100 p-8 sm:p-12 relative overflow-hidden">
        {/* Background Decoration */}
        <div className="absolute -top-24 -right-24 w-64 h-64 bg-blue-50 rounded-full opacity-50 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-emerald-50 rounded-full opacity-50 blur-3xl pointer-events-none" />

        <div className="absolute top-10 left-10 flex items-center gap-4">
          <Link href="/debug" className="text-neutral-400 hover:text-neutral-600 transition-colors p-2 hover:bg-neutral-50 rounded-full" title="개발자 디버그 페이지">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </Link>
        </div>

        <button
          onClick={loadDummyData}
          className="absolute top-10 right-10 px-4 py-2 bg-neutral-100 hover:bg-blue-50 hover:text-blue-600 text-neutral-600 text-xs font-bold rounded-full transition-all border border-neutral-200 hover:border-blue-200"
          type="button"
        >
          ✨ 테스트 데이터 로드
        </button>

        <div className="flex flex-col items-center text-center mb-12">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-emerald-400 p-0.5 mb-6 shadow-lg rotate-3">
            <div className="w-full h-full bg-white rounded-[14px] flex items-center justify-center overflow-hidden">
              <img src="/logo.png" alt="TechTree Logo" className="w-4/5 h-4/5 object-contain" />
            </div>
          </div>
          <h1 className="text-4xl font-extrabold text-neutral-900 tracking-tight mb-4">
            AI 가상 면접 서비스 <span className="text-blue-600">: TechTree</span>
          </h1>
          <p className="text-neutral-600 text-lg max-w-lg font-medium">
            당신만을 위한 맞춤형 질문과 피드백으로<br />
            꿈꾸는 직무에 한 걸음 더 가까이 다가가세요.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-12">
          {/* Section 1: JD & Resume Analysis - Two Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left: Job Description */}
            <div className="flex flex-col h-full bg-white p-6 sm:p-8 rounded-[2rem] border border-neutral-100 shadow-sm hover:shadow-md transition-shadow relative">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-sm font-bold text-emerald-600 uppercase tracking-widest mb-1 flex items-center gap-2">
                    <span className="w-2 h-2 bg-emerald-600 rounded-full animate-pulse" />
                    STEP 1. 공고 분석
                  </h2>
                  <p className="text-xs text-neutral-600 font-medium ml-4">채용 공고를 기반으로 한 맞춤 면접</p>
                </div>
                <div className="flex bg-neutral-100 p-1 rounded-xl">
                  <button type="button" onClick={() => setJdMode("none")} className={`px-2.5 py-1 text-[10px] font-bold rounded-lg transition-all ${jdMode === "none" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500"}`}>없음</button>
                  <button type="button" onClick={() => setJdMode("text")} className={`px-2.5 py-1 text-[10px] font-bold rounded-lg transition-all ${jdMode === "text" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500"}`}>텍스트</button>
                  <button type="button" onClick={() => setJdMode("image")} className={`px-2.5 py-1 text-[10px] font-bold rounded-lg transition-all ${jdMode === "image" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500"}`}>이미지</button>
                </div>
              </div>

              <div className="flex-grow flex flex-col min-h-[160px]">
                {jdMode === "text" && (
                  <textarea
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    placeholder="채용 공고 내용을 붙여넣어 주세요..."
                    className="flex-grow w-full px-4 py-3 rounded-xl border border-neutral-100 bg-neutral-50 focus:bg-white focus:ring-4 focus:ring-emerald-50 focus:border-emerald-200 outline-none resize-none text-sm leading-relaxed"
                  />
                )}

                {jdMode === "image" && (
                  <div
                    className={`flex-grow border-2 border-dashed rounded-xl p-6 text-center flex flex-col items-center justify-center transition-all ${isDraggingJd ? 'border-emerald-500 bg-emerald-50' : 'border-neutral-100 bg-neutral-50'}`}
                    onDragOver={handleDragOver}
                    onDragEnter={(e) => { e.preventDefault(); setIsDraggingJd(true); }}
                    onDragLeave={(e) => { e.preventDefault(); setIsDraggingJd(false); }}
                    onDrop={(e) => handleDrop(e, 'jd')}
                  >
                    <input type="file" id="jdImageFile" accept="image/*" onChange={handleJdImageChange} className="hidden" />
                    <label htmlFor="jdImageFile" className="cursor-pointer group flex flex-col items-center">
                      <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center shadow-sm border border-neutral-100 mb-2 group-hover:scale-110 transition-transform">
                        <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                      </div>
                      <span className="text-xs font-bold text-emerald-600">공고 이미지 업로드</span>
                      <span className="text-[10px] text-neutral-600 mt-1 font-bold">PNG, JPG, JPEG, HEIC 지원</span>
                    </label>
                    {jdFileName && <p className="text-[11px] font-bold text-emerald-700 mt-3 bg-emerald-100/50 px-2 py-1 rounded-md">✓ {jdFileName}</p>}
                  </div>
                )}

                {jdMode === "none" && (
                  <div className="flex-grow flex flex-col items-center justify-center p-6 text-center bg-neutral-50/50 rounded-xl border border-dashed border-neutral-100">
                    <svg className="w-8 h-8 text-neutral-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    <p className="text-xs text-neutral-600 font-medium leading-tight">선택한 공고가 없습니다.<br />직무 기반 일반 면접으로 진행합니다.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Right: Resume */}
            <div className="flex flex-col h-full bg-white p-6 sm:p-8 rounded-[2rem] border border-neutral-100 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-sm font-bold text-indigo-600 uppercase tracking-widest mb-1 flex items-center gap-2">
                    <span className="w-2 h-2 bg-indigo-600 rounded-full" />
                    STEP 2. 이력서 분석
                  </h2>
                  <p className="text-xs text-neutral-600 font-medium ml-4">제출하신 이력서를 바탕으로 심층 질문</p>
                </div>
                <div className="flex bg-neutral-100 p-1 rounded-xl">
                  <button type="button" onClick={() => setResumeMode("none")} className={`px-2.5 py-1 text-[10px] font-bold rounded-lg transition-all ${resumeMode === "none" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500"}`}>없음</button>
                  <button type="button" onClick={() => setResumeMode("text")} className={`px-2.5 py-1 text-[10px] font-bold rounded-lg transition-all ${resumeMode === "text" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500"}`}>입력</button>
                  <button type="button" onClick={() => setResumeMode("file")} className={`px-2.5 py-1 text-[10px] font-bold rounded-lg transition-all ${resumeMode === "file" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500"}`}>파일</button>
                </div>
              </div>

              <div className="flex-grow flex flex-col min-h-[160px]">
                {resumeMode === "text" ? (
                  <textarea
                    value={resumeText}
                    onChange={(e) => setResumeText(e.target.value)}
                    placeholder="자기소개 또는 주요 경력을 입력하세요..."
                    className="flex-grow w-full px-4 py-3 rounded-xl border border-neutral-100 bg-neutral-50 focus:bg-white focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 outline-none resize-none text-sm leading-relaxed"
                    required
                  />
                ) : resumeMode === "file" ? (
                  <div
                    className={`flex-grow border-2 border-dashed rounded-xl p-6 text-center flex flex-col items-center justify-center transition-all ${isDraggingResume ? 'border-indigo-500 bg-indigo-50' : 'border-neutral-100 bg-neutral-50'}`}
                    onDragOver={handleDragOver}
                    onDragEnter={(e) => { e.preventDefault(); setIsDraggingResume(true); }}
                    onDragLeave={(e) => { e.preventDefault(); setIsDraggingResume(false); }}
                    onDrop={(e) => handleDrop(e, 'resume')}
                  >
                    <input type="file" id="resumeFile" accept=".pdf,.txt" onChange={handleResumeFileChange} className="hidden" />
                    <label htmlFor="resumeFile" className="cursor-pointer group flex flex-col items-center">
                      <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center shadow-sm border border-neutral-100 mb-2 group-hover:scale-110 transition-transform">
                        <svg className="w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                      </div>
                      <span className="text-xs font-bold text-indigo-600">이력서 파일 업로드</span>
                      <span className="text-[10px] text-neutral-600 mt-1 font-bold">PDF, TXT 파일 지원</span>
                    </label>
                    {resumeFile && <p className="text-[11px] font-bold text-indigo-700 mt-3 bg-indigo-100/50 px-2 py-1 rounded-md truncate max-w-full">✓ {resumeFile.name}</p>}
                    {isParsingResume && <p className="text-[10px] text-indigo-600 mt-2 animate-pulse font-bold">분석 중...</p>}
                  </div>
                ) : (
                  <div className="flex-grow flex flex-col items-center justify-center p-6 text-center bg-neutral-50/50 rounded-xl border border-dashed border-neutral-100">
                    <svg className="w-8 h-8 text-neutral-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
                    <p className="text-xs text-neutral-600 font-medium leading-tight">이력서 없이 진행합니다.<br />일반적인 지원자 수준에 맞춰 질문합니다.</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Section 3: Basic Info - Now at the Bottom */}
          <div className="bg-neutral-50/50 p-6 sm:p-8 rounded-[2rem] border border-neutral-100 shadow-inner relative overflow-hidden">
            {isAnalyzingJd && (
              <div className="absolute inset-0 bg-white/40 backdrop-blur-[2px] flex items-center justify-center z-10 transition-all">
                <div className="bg-white px-4 py-2 rounded-full shadow-lg border border-neutral-100 flex items-center gap-3">
                  <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                  <span className="text-xs font-bold text-blue-600">공고에서 직무 탐지 중...</span>
                </div>
              </div>
            )}
            <h2 className="text-sm font-bold text-blue-600 uppercase tracking-widest mb-6 flex items-center gap-2">
              <span className="w-2 h-2 bg-blue-600 rounded-full" />
              STEP 3. 기본 프로필
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              <div className="lg:col-span-2">
                <label htmlFor="jobTitle" className="block text-xs font-bold text-neutral-600 mb-2 ml-1">지원 직무</label>
                <div className="relative">
                  <input
                    type="text"
                    id="jobTitle"
                    value={jobTitle}
                    onChange={(e) => {
                      setJobTitle(e.target.value);
                      setIsAutoFilled(false);
                    }}
                    placeholder="공고 분석 시 자동으로 입력됩니다"
                    className={`w-full px-5 py-3.5 rounded-2xl border ${!jobTitle ? 'border-red-200 bg-red-50/30' : 'border-neutral-200 bg-white'} focus:ring-4 focus:ring-blue-100 focus:border-blue-500 outline-none text-base font-semibold transition-all`}
                    required
                  />
                  {jobTitle && isAutoFilled && !isAnalyzingJd && (
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-1.5 px-2 py-1 bg-emerald-50 rounded-lg border border-emerald-100">
                      <span className="text-[10px] font-black text-emerald-600">AUTO</span>
                      <svg className="w-3 h-3 text-emerald-500" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                    </div>
                  )}
                </div>
              </div>
              <div>
                <label htmlFor="experience" className="block text-xs font-bold text-neutral-600 mb-2 ml-1">경력</label>
                <select id="experience" value={experience} onChange={(e) => setExperience(e.target.value)} className={`w-full px-5 py-3.5 rounded-2xl border ${!experience ? 'border-red-200 bg-red-50/30' : 'border-neutral-200 bg-white'} outline-none cursor-pointer focus:ring-4 focus:ring-blue-100 transition-all appearance-none font-bold`}>
                  <option value="" disabled>선택하기</option>
                  <option value="신입">신입 (0년)</option>
                  <option value="1~3년차">1~3년차</option>
                  <option value="3~5년차">3~5년차</option>
                  <option value="5년차 이상">5년차 이상</option>
                </select>
              </div>
              <div>
                <label htmlFor="education" className="block text-xs font-bold text-neutral-600 mb-2 ml-1">최종 학력</label>
                <select id="education" value={education} onChange={(e) => setEducation(e.target.value)} className={`w-full px-5 py-3.5 rounded-2xl border ${!education ? 'border-red-200 bg-red-50/30' : 'border-neutral-200 bg-white'} outline-none cursor-pointer focus:ring-4 focus:ring-blue-100 transition-all appearance-none font-bold`}>
                  <option value="" disabled>선택하기</option>
                  <option value="고졸">고졸</option>
                  <option value="전문학사">전문학사</option>
                  <option value="학사(4년제)">학사(4년제)</option>
                  <option value="석사">석사</option>
                  <option value="박사">박사</option>
                </select>
              </div>
            </div>
          </div>

          {/* Action Footer */}
          <div className="pt-8 border-t border-neutral-100 flex flex-col items-center gap-6">
            <button
              type="submit"
              disabled={isParsingResume}
              className="group relative w-full sm:w-auto sm:min-w-[320px] flex justify-center items-center py-5 px-10 rounded-[2rem] shadow-2xl text-xl font-black text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 transition-all active:scale-95 overflow-hidden"
            >
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
              <span className="relative flex items-center gap-3">
                AI 면접 시작하기
                <svg className="w-6 h-6 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </span>
            </button>

            <div className="text-center space-y-2">
              <p className="text-[12px] text-neutral-700 font-bold">
                🛡️ 입력하신 데이터(이력서, 공고 등)는 분석 직후 즉시 파기되며 절대 저장되지 않습니다.
              </p>
              <p className="text-[11px] text-neutral-600 font-medium">
                단, 면접 대화 내용은 AI 모델의 품질 향상을 위한 학습 데이터로 활용될 수 있습니다.
              </p>
            </div>
          </div>
        </form>
      </div>

      <div className="mt-12 flex justify-center opacity-30 grayscale hover:opacity-100 hover:grayscale-0 transition-all duration-500">
        {/* Placeholder for partner logos or tech stack icons if needed */}
      </div>
    </main>
  );
}