"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import NextImage from "next/image";

export default function Home() {
  const router = useRouter();
  const [jobTitle, setJobTitle] = useState("");
  const [experience, setExperience] = useState("");
  const [education, setEducation] = useState("");
  const [interviewMode, setInterviewMode] = useState<"short" | "long">("long");
  const [reportEmail, setReportEmail] = useState("");
  const [inputResetKey, setInputResetKey] = useState(0);

  // 이력서 관련 상태
  const [resumeMode, setResumeMode] = useState<"none" | "text" | "file">("file");
  const [resumeText, setResumeText] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [isParsingResume, setIsParsingResume] = useState(false);

  // 채용 공고 관련 상태
  const [jdMode, setJdMode] = useState<"none" | "text" | "image">("image");
  const [jdText, setJdText] = useState("");
  const [jdImageBase64, setJdImageBase64] = useState<string | null>(null);
  const [jdFileName, setJdFileName] = useState("");
  const [isDraggingResume, setIsDraggingResume] = useState(false);
  const [isDraggingJd, setIsDraggingJd] = useState(false);
  const [isAnalyzingJd, setIsAnalyzingJd] = useState(false);
  const [isAutoFilled, setIsAutoFilled] = useState(false);

  useEffect(() => {
    const shouldReuseProfile = sessionStorage.getItem("reuseInterviewProfile") === "true";
    sessionStorage.removeItem("reuseInterviewProfile");

    if (!shouldReuseProfile) return;

    const savedProfile = sessionStorage.getItem("interviewProfile");
    if (!savedProfile) return;

    try {
      const profile = JSON.parse(savedProfile);
      setJobTitle(profile.job_title || "");
      setExperience(profile.experience || "");
      setEducation(profile.education || "");
      setReportEmail(profile.report_email || "");
      setInterviewMode(profile.interview_mode === "short" ? "short" : "long");
      if (profile.resume && profile.resume !== "이력서 없음") {
        setResumeMode("text");
        setResumeText(profile.resume);
      }
      if (profile.job_description) {
        setJdMode("text");
        setJdText(profile.job_description);
      } else if (profile.job_image) {
        setJdMode("image");
        setJdImageBase64(profile.job_image);
        setJdFileName("이전 공고 이미지");
      }
    } catch (error) {
      console.error("Failed to restore interview profile", error);
    }
  }, []);

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

  const startInterview = (mode: "short" | "long") => {
    if (!jobTitle || !experience || !education) {
      alert("지원 직무, 경력, 최종 학력을 모두 입력 및 선택해 주세요.");
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(reportEmail.trim())) {
      alert("리포트를 받을 이메일을 올바르게 입력해 주세요.");
      return;
    }

    if (isParsingResume || isAnalyzingJd) {
      alert("분석 작업이 진행 중입니다. 잠시만 기다려주세요.");
      return;
    }

    const profile = {
      report_email: reportEmail.trim(),
      job_title: jobTitle || "직무 미상",
      experience: experience,
      education: education,
      resume: resumeMode === "none" ? "이력서 없음" : (resumeText || "특별한 이력 없음"),
      job_description: jdMode === "text" ? jdText : "",
      job_image: jdMode === "image" ? jdImageBase64 : null,
      interview_mode: mode
    };

    // 같은 브라우저 세션에서 재면접할 수 있도록 세션 스토리지에 입력값을 유지합니다.
    sessionStorage.setItem("interviewProfile", JSON.stringify(profile));
    localStorage.removeItem("interviewProfile");

    // 면접 페이지로 이동
    router.push("/interview");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    startInterview(interviewMode);
  };

  const resetInterviewInputs = () => {
    setJobTitle("");
    setExperience("");
    setEducation("");
    setInterviewMode("long");
    setReportEmail("");
    setResumeMode("file");
    setResumeText("");
    setResumeFile(null);
    setIsParsingResume(false);
    setJdMode("image");
    setJdText("");
    setJdImageBase64(null);
    setJdFileName("");
    setIsDraggingResume(false);
    setIsDraggingJd(false);
    setIsAnalyzingJd(false);
    setIsAutoFilled(false);
    setInputResetKey((key) => key + 1);
    sessionStorage.removeItem("interviewProfile");
    sessionStorage.removeItem("reuseInterviewProfile");
    sessionStorage.removeItem("lastInterviewEndedAt");
    localStorage.removeItem("interviewProfile");
  };

  return (
    <main className="min-h-screen bg-neutral-50 py-6 px-4 sm:px-6">
      <div className="max-w-4xl mx-auto w-full bg-white rounded-[2rem] shadow-xl border border-neutral-100 p-5 sm:p-8 relative overflow-hidden">
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

        <div className="absolute top-6 right-6 flex flex-wrap justify-end gap-2">
          <button
            onClick={resetInterviewInputs}
            className="px-3 py-2 bg-white hover:bg-neutral-100 text-neutral-500 hover:text-neutral-900 text-xs font-bold rounded-full transition-all border border-neutral-200"
            type="button"
          >
            입력 초기화
          </button>
        </div>

        <div className="flex flex-col items-center text-center mb-8 pt-6">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-emerald-400 p-0.5 mb-4 shadow-lg rotate-3">
            <div className="w-full h-full bg-white rounded-[14px] flex items-center justify-center overflow-hidden">
              <NextImage src="/logo.png" alt="TechTree Logo" width={64} height={64} className="w-4/5 h-4/5 object-contain" priority />
            </div>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-neutral-900 tracking-tight mb-3">
            AI 가상 면접 서비스 <span className="text-blue-600">: TechTree</span>
          </h1>
          <p className="text-neutral-600 text-base sm:text-lg max-w-lg font-medium">
            당신만을 위한 맞춤형 질문과 피드백으로<br />
            꿈꾸는 직무에 한 걸음 더 가까이 다가가세요.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-7">
          {/* Section 1: JD & Resume Analysis - Two Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Left: Job Description */}
            <div className="flex flex-col h-full bg-white p-5 sm:p-6 rounded-[2rem] border border-neutral-100 shadow-sm hover:shadow-md transition-shadow relative">
              <div className="flex justify-between items-start mb-4">
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

              <div className="flex-grow flex flex-col min-h-[140px]">
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
                    <input key={`jd-${inputResetKey}`} type="file" id="jdImageFile" accept="image/*" onChange={handleJdImageChange} className="hidden" />
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
            <div className="flex flex-col h-full bg-white p-5 sm:p-6 rounded-[2rem] border border-neutral-100 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-4">
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

              <div className="flex-grow flex flex-col min-h-[140px]">
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
                    <input key={`resume-${inputResetKey}`} type="file" id="resumeFile" accept=".pdf,.txt" onChange={handleResumeFileChange} className="hidden" />
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
          <div className="bg-neutral-50/50 p-5 sm:p-6 rounded-[2rem] border border-neutral-100 shadow-inner relative overflow-hidden">
            {isAnalyzingJd && (
              <div className="absolute inset-0 bg-white/40 backdrop-blur-[2px] flex items-center justify-center z-10 transition-all">
                <div className="bg-white px-4 py-2 rounded-full shadow-lg border border-neutral-100 flex items-center gap-3">
                  <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                  <span className="text-xs font-bold text-blue-600">공고에서 직무 탐지 중...</span>
                </div>
              </div>
            )}
            <h2 className="text-sm font-bold text-blue-600 uppercase tracking-widest mb-4 flex items-center gap-2">
              <span className="w-2 h-2 bg-blue-600 rounded-full" />
              STEP 3. 기본 프로필
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
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

          <div className="bg-white p-5 sm:p-6 rounded-[2rem] border border-neutral-100 shadow-sm">
            <h2 className="text-sm font-bold text-rose-600 uppercase tracking-widest mb-4 flex items-center gap-2">
              <span className="w-2 h-2 bg-rose-600 rounded-full" />
              STEP 4. 리포트 이메일
            </h2>
            <div>
              <label htmlFor="reportEmail" className="block text-xs font-bold text-neutral-600 mb-2 ml-1">리포트 받을 이메일</label>
              <input
                type="email"
                id="reportEmail"
                value={reportEmail}
                onChange={(e) => setReportEmail(e.target.value)}
                placeholder="example@email.com"
                className={`w-full px-5 py-3.5 rounded-2xl border ${!reportEmail ? 'border-red-200 bg-red-50/30' : 'border-neutral-200 bg-white'} focus:ring-4 focus:ring-rose-100 focus:border-rose-500 outline-none text-base font-semibold transition-all`}
                required
              />
              <p className="mt-2 text-xs font-medium text-neutral-500">
                면접 종료 후 분석 리포트와 전체 대화 내용이 이 주소로 자동 발송됩니다.
              </p>
            </div>
          </div>

          {/* Action Footer */}
          <div className="pt-5 border-t border-neutral-100 flex flex-col items-center gap-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-3xl">
              <button
                type="button"
                disabled={isParsingResume || isAnalyzingJd}
                onClick={() => {
                  setInterviewMode("short");
                  startInterview("short");
                }}
                className="group relative min-h-[112px] overflow-hidden rounded-[2rem] bg-gradient-to-r from-violet-600 to-fuchsia-600 px-6 py-5 text-left text-white shadow-2xl shadow-violet-200 transition-all hover:from-violet-700 hover:to-fuchsia-700 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
              >
                <div className="absolute inset-0 bg-white/15 translate-y-full transition-transform duration-300 group-hover:translate-y-0" />
                <div className="relative flex h-full flex-col justify-between gap-4">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-2xl font-black">빠른 연습 시작하기</span>
                    <span className="shrink-0 rounded-xl border border-white/25 bg-white/15 px-3 py-1 text-sm font-black text-white">
                      7분 내외
                    </span>
                  </div>
                  <p className="text-sm font-bold leading-relaxed text-white/85">
                    대표 경험과 핵심 직무 질문을 짧고 밀도 있게 점검합니다.
                  </p>
                </div>
              </button>
              <button
                type="button"
                disabled={isParsingResume || isAnalyzingJd}
                onClick={() => {
                  setInterviewMode("long");
                  startInterview("long");
                }}
                className="group relative min-h-[112px] overflow-hidden rounded-[2rem] bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-5 text-left text-white shadow-2xl shadow-blue-200 transition-all hover:from-blue-700 hover:to-indigo-700 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
              >
                <div className="absolute inset-0 bg-white/15 translate-y-full transition-transform duration-300 group-hover:translate-y-0" />
                <div className="relative flex h-full flex-col justify-between gap-4">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-2xl font-black">실전 연습 시작하기</span>
                    <span className="shrink-0 rounded-xl border border-white/25 bg-white/15 px-3 py-1 text-sm font-black text-white">
                      20분 내외
                    </span>
                  </div>
                  <p className="text-sm font-bold leading-relaxed text-white/85">
                    직무 역량, 프로젝트, 협업/문제 해결까지 깊게 진행합니다.
                  </p>
                </div>
              </button>
            </div>
            <div className="text-center space-y-2">
              <p className="text-[12px] text-neutral-700 font-black">
                원하는 연습 방식을 누르면 바로 AI 면접이 시작됩니다.
              </p>
              <p className="text-[12px] text-neutral-700 font-bold">
                🛡️ 데이터는 개인정보 보호를 위해 현재 세션 중에만 임시로 유지되며, 창을 닫는 즉시 모든 기록이 사라집니다.
              </p>
              <p className="text-[11px] text-neutral-600 font-medium">
                면접 대화 원문은 저장하지 않으며, 종료 후 AI 면접관 개선을 위한 익명화된 운영 지침만 생성될 수 있습니다.
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
