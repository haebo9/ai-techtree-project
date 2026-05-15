"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import NextImage from "next/image";
import { apiPath } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [jobTitle, setJobTitle] = useState("");
  const [experience, setExperience] = useState("");
  const [education, setEducation] = useState("");
  const [interviewMode, setInterviewMode] = useState<"short" | "long">("long");
  const [reportEmail, setReportEmail] = useState("");
  const [inputResetKey, setInputResetKey] = useState(0);
  const [isCheckingInvite, setIsCheckingInvite] = useState(true);
  const [isInviteAuthenticated, setIsInviteAuthenticated] = useState(false);
  const [inviteCode, setInviteCode] = useState("");
  const [inviteError, setInviteError] = useState("");
  const [isVerifyingInvite, setIsVerifyingInvite] = useState(false);

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
    let cancelled = false;

    const checkInviteSession = async () => {
      try {
        const res = await fetch(apiPath("/invite/session"), {
          credentials: "include",
          cache: "no-store",
        });
        const data = await res.json();
        if (cancelled) return;
        setIsInviteAuthenticated(Boolean(data.authenticated));
      } catch (error) {
        if (!cancelled) {
          console.error("Failed to check invite session", error);
          setIsInviteAuthenticated(false);
        }
      } finally {
        if (!cancelled) setIsCheckingInvite(false);
      }
    };

    checkInviteSession();
    return () => {
      cancelled = true;
    };
  }, []);

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
        const res = await fetch(apiPath("/upload/parse-pdf"), {
          method: "POST",
          credentials: "include",
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
      const res = await fetch(apiPath("/upload/analyze-jd"), {
        method: "POST",
        credentials: "include",
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

  const handleJdPaste = (e: React.ClipboardEvent<HTMLDivElement>) => {
    if (jdMode !== "image") return;

    const imageItem = Array.from(e.clipboardData.items).find((item) => item.type.startsWith("image/"));
    if (!imageItem) return;

    const file = imageItem.getAsFile();
    if (!file) return;

    e.preventDefault();
    setJdMode("image");
    const extension = file.type.split("/")[1] || "png";
    const pastedFile = new File([file], `pasted-job-posting.${extension}`, { type: file.type });
    processJdImage(pastedFile);
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

  const handleDragEnter = (e: React.DragEvent, type: 'resume' | 'jd') => {
    e.preventDefault();
    e.stopPropagation();
    if (type === 'resume') setIsDraggingResume(true);
    else setIsDraggingJd(true);
  };

  const handleDragLeave = (e: React.DragEvent, type: 'resume' | 'jd') => {
    e.preventDefault();
    e.stopPropagation();
    const nextTarget = e.relatedTarget as Node | null;
    if (nextTarget && e.currentTarget.contains(nextTarget)) return;
    if (type === 'resume') setIsDraggingResume(false);
    else setIsDraggingJd(false);
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

  const handleInviteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const code = inviteCode.trim();
    if (!code) {
      setInviteError("초대코드를 입력해 주세요.");
      return;
    }

    setIsVerifyingInvite(true);
    setInviteError("");
    try {
      const res = await fetch(apiPath("/invite/verify"), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.authenticated) {
        throw new Error(data.detail || "초대코드를 확인할 수 없습니다.");
      }
      setIsInviteAuthenticated(true);
      setInviteCode("");
    } catch (error) {
      const message = error instanceof Error ? error.message : "초대코드를 확인할 수 없습니다.";
      setInviteError(message);
    } finally {
      setIsVerifyingInvite(false);
    }
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
    <main className="theme-page min-h-screen overflow-hidden">
      <div className="mx-auto w-full max-w-[1500px] px-8 py-7">
        <nav className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 overflow-hidden rounded-xl border border-[#4556D6]/25 bg-white shadow-sm">
              <NextImage src="/logo.png" alt="TechTree Logo" width={44} height={44} className="h-full w-full object-contain" priority />
            </div>
            <span className="text-lg font-black tracking-tight text-[#17232B]">TechTree</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/debug" className="theme-silver-pill rounded-full border px-4 py-2 text-xs font-black text-[#243844] transition hover:text-[#17232B]" title="개발자 디버그 페이지">
              Debug
            </Link>
            <button
              onClick={resetInterviewInputs}
              className="theme-silver-pill rounded-full border px-4 py-2 text-xs font-black text-[#243844] transition hover:text-[#17232B]"
              type="button"
            >
              입력 초기화
            </button>
          </div>
        </nav>

        <section className="grid min-h-[620px] grid-cols-[0.82fr_1.18fr] items-center gap-12 py-16">
          <div>
            <p className="text-sm font-black uppercase tracking-[0.34em] text-[#B88A3A]">AI Mock Interview</p>
            <h1 className="mt-7 text-[88px] font-black leading-[0.92] tracking-tight text-[#101820]">
              면접 준비를<br />대화로.
            </h1>
            <p className="mt-8 max-w-xl text-xl font-bold leading-relaxed text-[#243844]">
              TechTree는 이력서와 채용 공고를 읽고, 실제 면접처럼 묻고,
              끝난 뒤에는 다시 연습할 수 있는 리포트로 정리합니다.
            </p>
            <div className="mt-10 flex items-center gap-3">
              <a href="#interview-workspace" className="rounded-full bg-[#101820] px-6 py-3 text-sm font-black text-white shadow-xl shadow-[#4556D6]/20 transition hover:bg-[#243844]">
                면접 준비하기
              </a>
              <a href="#product-story" className="rounded-full border border-[#B7C3CA]/70 bg-white/62 px-6 py-3 text-sm font-black text-[#17232B] transition hover:border-[#B88A3A]/70">
                서비스 보기
              </a>
            </div>
          </div>

          <div className="home-art-panel relative min-h-[560px] overflow-hidden rounded-2xl">
            <div className="absolute left-10 top-10 rounded-full border border-white/40 bg-white/35 px-4 py-2 text-xs font-black text-[#17232B] backdrop-blur">
              Realtime Voice Interview
            </div>
            <div className="absolute left-1/2 top-20 h-24 w-24 -translate-x-1/2 overflow-hidden rounded-2xl border border-white/60 bg-white p-3 shadow-2xl shadow-[#4556D6]/20">
              <NextImage src="/logo.png" alt="TechTree visual placeholder" width={96} height={96} className="h-full w-full object-contain" priority />
            </div>
            <div className="absolute bottom-14 left-14 w-[58%] rounded-2xl border border-white/50 bg-white/90 p-6 shadow-2xl shadow-[#17232B]/20">
              <div className="mb-5 flex gap-2">
                <span className="h-3 w-3 rounded-full bg-red-500" />
                <span className="h-3 w-3 rounded-full bg-[#D7B56D]" />
                <span className="h-3 w-3 rounded-full bg-[#4556D6]" />
              </div>
              <div className="space-y-3">
                <div className="h-4 w-2/3 rounded-full bg-[#17232B]/80" />
                <div className="h-3 w-full rounded-full bg-[#B7C3CA]/70" />
                <div className="h-3 w-5/6 rounded-full bg-[#B7C3CA]/55" />
                <div className="mt-6 rounded-xl border border-[#D7B56D]/45 bg-[#D7B56D]/12 px-4 py-3 text-sm font-black text-[#17232B]">
                  점수, 강점, 개선점, Q&A 피드백
                </div>
              </div>
            </div>
            <div className="absolute bottom-24 right-12 w-[34%] rounded-2xl border border-white/45 bg-[#101820]/88 p-5 text-white shadow-2xl shadow-[#17232B]/30">
              <p className="text-xs font-black uppercase tracking-[0.22em] text-[#D7B56D]">Push to Talk</p>
              <p className="mt-4 text-3xl font-black leading-tight">말하고,<br />바로 이어가기.</p>
            </div>
          </div>
        </section>

        <section id="interview-workspace" className="theme-shell rounded-2xl border p-5 sm:p-8">

        {isCheckingInvite ? (
          <div className="theme-card flex flex-col items-center justify-center rounded-2xl border px-6 py-14 text-center">
            <div className="mb-4 h-10 w-10 animate-spin rounded-full border-4 border-[#4556D6] border-t-transparent" />
            <p className="text-sm font-bold text-[#243844]">접속 권한을 확인하고 있습니다.</p>
          </div>
        ) : !isInviteAuthenticated ? (
          <form onSubmit={handleInviteSubmit} className="theme-card mx-auto max-w-md rounded-2xl border p-6">
            <div className="mb-5 text-center">
              <h2 className="text-xl font-black text-[#17232B]">초대코드 입력</h2>
              <p className="mt-2 text-sm font-medium leading-relaxed text-[#243844]">
                TechTree는 초대받은 사용자에게만 면접 연습을 제공합니다.
              </p>
            </div>
            <label htmlFor="inviteCode" className="mb-2 block text-xs font-bold uppercase tracking-widest text-[#4556D6]">
              Invite Code
            </label>
            <input
              id="inviteCode"
              value={inviteCode}
              onChange={(e) => {
                setInviteCode(e.target.value);
                setInviteError("");
              }}
              placeholder="초대코드를 입력하세요"
              className="theme-input w-full rounded-2xl border px-5 py-4 text-center text-base font-black tracking-wide outline-none transition-all focus:border-[#8390D6] focus:ring-4 focus:ring-[#8390D6]/20"
              autoComplete="off"
            />
            {inviteError && (
              <p className="mt-3 rounded-xl border border-[#B7C3CA]/35 bg-[#E2E8EC]/35 px-4 py-3 text-center text-sm font-bold text-[#7E8A92]">
                {inviteError}
              </p>
            )}
            <button
              type="submit"
              disabled={isVerifyingInvite}
              className="theme-cta mt-5 w-full rounded-2xl px-5 py-4 text-sm font-black text-white transition-all disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isVerifyingInvite ? "확인 중..." : "입장하기"}
            </button>
          </form>
        ) : (
        <form onSubmit={handleSubmit} className="space-y-7">
          {/* Section 1: JD & Resume Analysis - Two Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Left: Job Description */}
            <div className="theme-card flex flex-col h-full p-5 sm:p-6 rounded-2xl border transition-shadow relative">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-sm font-bold text-[#8390D6] uppercase tracking-widest mb-1 flex items-center gap-2">
                    <span className="w-2 h-2 bg-[#8390D6] rounded-full animate-pulse" />
                    STEP 1. 공고 분석
                  </h2>
                  <p className="text-xs text-[#243844] font-medium ml-4">채용 공고를 기반으로 한 맞춤 면접</p>
                </div>
                <div className="flex bg-[#E2E8EC]/60 p-1 rounded-xl border border-[#B7C3CA]/45">
                  <button type="button" onClick={() => setJdMode("none")} className={`px-2.5 py-1 text-[10px] font-bold rounded-lg transition-all ${jdMode === "none" ? "bg-white/80 shadow-sm text-[#17232B]" : "text-[#243844]"}`}>없음</button>
                  <button type="button" onClick={() => setJdMode("text")} className={`px-2.5 py-1 text-[10px] font-bold rounded-lg transition-all ${jdMode === "text" ? "bg-white/80 shadow-sm text-[#17232B]" : "text-[#243844]"}`}>텍스트</button>
                  <button type="button" onClick={() => setJdMode("image")} className={`px-2.5 py-1 text-[10px] font-bold rounded-lg transition-all ${jdMode === "image" ? "bg-white/80 shadow-sm text-[#17232B]" : "text-[#243844]"}`}>이미지</button>
                </div>
              </div>

              <div className="flex-grow flex flex-col min-h-[140px]">
                {jdMode === "text" && (
                  <textarea
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    placeholder="채용 공고 내용을 붙여넣어 주세요..."
                    className="theme-input flex-grow w-full px-4 py-3 rounded-xl border focus:bg-white/80 focus:ring-4 focus:ring-[#8390D6]/15 focus:border-[#8390D6] outline-none resize-none text-sm leading-relaxed"
                  />
                )}

                {jdMode === "image" && (
                  <div
                    className={`flex-grow border-2 border-dashed rounded-xl p-6 text-center flex flex-col items-center justify-center transition-all ${isDraggingJd ? 'border-[#8390D6] bg-[#8390D6]/10' : 'border-[#B7C3CA]/50 bg-[#EAF4F7]/45'}`}
                    tabIndex={0}
                    onDragOver={handleDragOver}
                    onDragEnter={(e) => handleDragEnter(e, 'jd')}
                    onDragLeave={(e) => handleDragLeave(e, 'jd')}
                    onDrop={(e) => handleDrop(e, 'jd')}
                    onPaste={handleJdPaste}
                    onClick={(e) => e.currentTarget.focus()}
                  >
                    <input key={`jd-${inputResetKey}`} type="file" id="jdImageFile" accept="image/*" onChange={handleJdImageChange} className="hidden" />
                    <label htmlFor="jdImageFile" className="cursor-pointer group flex flex-col items-center">
                      <div className="w-10 h-10 bg-white/75 rounded-full flex items-center justify-center shadow-sm border border-[#B7C3CA]/45 mb-2 group-hover:scale-110 transition-transform">
                        <svg className="w-5 h-5 text-[#8390D6]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                      </div>
                      <span className="text-xs font-bold text-[#8390D6]">Paste, drop, or click to add files</span>
                      <span className="text-[10px] text-[#243844] mt-1 font-bold">PNG, JPG, JPEG, HEIC</span>
                    </label>
                    {jdFileName && <p className="text-[11px] font-bold text-[#8390D6] mt-3 bg-[#8390D6]/20 px-2 py-1 rounded-md">✓ {jdFileName}</p>}
                  </div>
                )}

                {jdMode === "none" && (
                  <div className="flex-grow flex flex-col items-center justify-center p-6 text-center bg-[#EAF4F7]/45 rounded-xl border border-dashed border-[#B7C3CA]/50">
                    <svg className="w-8 h-8 text-white/80 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    <p className="text-xs text-[#243844] font-medium leading-tight">선택한 공고가 없습니다.<br />직무 기반 일반 면접으로 진행합니다.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Right: Resume */}
            <div className="theme-card flex flex-col h-full p-5 sm:p-6 rounded-2xl border transition-shadow">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-sm font-bold text-[#4556D6] uppercase tracking-widest mb-1 flex items-center gap-2">
                    <span className="w-2 h-2 bg-[#4556D6] rounded-full" />
                    STEP 2. 이력서 분석
                  </h2>
                  <p className="text-xs text-[#243844] font-medium ml-4">제출하신 이력서를 바탕으로 심층 질문</p>
                </div>
                <div className="flex bg-[#E2E8EC]/60 p-1 rounded-xl border border-[#B7C3CA]/45">
                  <button type="button" onClick={() => setResumeMode("none")} className={`px-2.5 py-1 text-[10px] font-bold rounded-lg transition-all ${resumeMode === "none" ? "bg-white/80 shadow-sm text-[#17232B]" : "text-[#243844]"}`}>없음</button>
                  <button type="button" onClick={() => setResumeMode("text")} className={`px-2.5 py-1 text-[10px] font-bold rounded-lg transition-all ${resumeMode === "text" ? "bg-white/80 shadow-sm text-[#17232B]" : "text-[#243844]"}`}>입력</button>
                  <button type="button" onClick={() => setResumeMode("file")} className={`px-2.5 py-1 text-[10px] font-bold rounded-lg transition-all ${resumeMode === "file" ? "bg-white/80 shadow-sm text-[#17232B]" : "text-[#243844]"}`}>파일</button>
                </div>
              </div>

              <div className="flex-grow flex flex-col min-h-[140px]">
                {resumeMode === "text" ? (
                  <textarea
                    value={resumeText}
                    onChange={(e) => setResumeText(e.target.value)}
                    placeholder="자기소개 또는 주요 경력을 입력하세요..."
                    className="theme-input flex-grow w-full px-4 py-3 rounded-xl border focus:bg-white/80 focus:ring-4 focus:ring-[#8390D6]/15 focus:border-[#4556D6] outline-none resize-none text-sm leading-relaxed"
                    required
                  />
                ) : resumeMode === "file" ? (
                  <div
                    className={`flex-grow border-2 border-dashed rounded-xl p-6 text-center flex flex-col items-center justify-center transition-all ${isDraggingResume ? 'border-[#8390D6] bg-[#8390D6]/10' : 'border-[#B7C3CA]/50 bg-[#EAF4F7]/45'}`}
                    onDragOver={handleDragOver}
                    onDragEnter={(e) => handleDragEnter(e, 'resume')}
                    onDragLeave={(e) => handleDragLeave(e, 'resume')}
                    onDrop={(e) => handleDrop(e, 'resume')}
                  >
                    <input key={`resume-${inputResetKey}`} type="file" id="resumeFile" accept=".pdf,.txt" onChange={handleResumeFileChange} className="hidden" />
                    <label htmlFor="resumeFile" className="cursor-pointer group flex flex-col items-center">
                      <div className="w-10 h-10 bg-white/75 rounded-full flex items-center justify-center shadow-sm border border-[#B7C3CA]/45 mb-2 group-hover:scale-110 transition-transform">
                        <svg className="w-5 h-5 text-[#4556D6]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                      </div>
                      <span className="text-xs font-bold text-[#4556D6]">Drop or click to add files</span>
                      <span className="text-[10px] text-[#243844] mt-1 font-bold">PDF, TXT</span>
                    </label>
                    {resumeFile && <p className="text-[11px] font-bold text-[#4556D6] mt-3 bg-[#8390D6]/20 px-2 py-1 rounded-md truncate max-w-full">✓ {resumeFile.name}</p>}
                    {isParsingResume && <p className="text-[10px] text-[#4556D6] mt-2 animate-pulse font-bold">분석 중...</p>}
                  </div>
                ) : (
                  <div className="flex-grow flex flex-col items-center justify-center p-6 text-center bg-[#EAF4F7]/45 rounded-xl border border-dashed border-[#B7C3CA]/50">
                    <svg className="w-8 h-8 text-white/80 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
                    <p className="text-xs text-[#243844] font-medium leading-tight">이력서 없이 진행합니다.<br />일반적인 지원자 수준에 맞춰 질문합니다.</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Section 3: Basic Info - Now at the Bottom */}
          <div className="theme-card-soft p-5 sm:p-6 rounded-2xl border relative overflow-hidden">
            {isAnalyzingJd && (
              <div className="absolute inset-0 bg-white/45 backdrop-blur-[2px] flex items-center justify-center z-10 transition-all">
                <div className="bg-white/85 px-4 py-2 rounded-full shadow-lg border border-[#B7C3CA]/45 flex items-center gap-3">
                  <div className="w-4 h-4 border-2 border-[#4556D6] border-t-transparent rounded-full animate-spin" />
                  <span className="text-xs font-bold text-[#4556D6]">공고에서 직무 탐지 중...</span>
                </div>
              </div>
            )}
            <h2 className="text-sm font-bold text-[#4556D6] uppercase tracking-widest mb-4 flex items-center gap-2">
              <span className="w-2 h-2 bg-[#4556D6] rounded-full" />
              STEP 3. 기본 프로필
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
              <div className="lg:col-span-2">
                <label htmlFor="jobTitle" className="block text-xs font-bold text-[#243844] mb-2 ml-1">지원 직무</label>
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
                    className={`theme-input w-full px-5 py-3.5 rounded-2xl border ${!jobTitle ? 'border-[#B7C3CA] bg-[#EAF4F7]/55' : ''} focus:ring-4 focus:ring-[#8390D6]/20 focus:border-[#8390D6] outline-none text-base font-semibold transition-all`}
                    required
                  />
                  {jobTitle && isAutoFilled && !isAnalyzingJd && (
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-1.5 px-2 py-1 bg-[#8390D6]/10 rounded-lg border border-[#8390D6]/20">
                      <span className="text-[10px] font-black text-[#8390D6]">AUTO</span>
                      <svg className="w-3 h-3 text-[#8390D6]" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                    </div>
                  )}
                </div>
              </div>
              <div>
                <label htmlFor="experience" className="block text-xs font-bold text-[#243844] mb-2 ml-1">경력</label>
                <select id="experience" value={experience} onChange={(e) => setExperience(e.target.value)} className={`theme-input w-full px-5 py-3.5 rounded-2xl border ${!experience ? 'border-[#B7C3CA] bg-[#EAF4F7]/55' : ''} outline-none cursor-pointer focus:ring-4 focus:ring-[#8390D6]/20 transition-all appearance-none font-bold`}>
                  <option value="" disabled>선택하기</option>
                  <option value="신입">신입 (0년)</option>
                  <option value="1~3년차">1~3년차</option>
                  <option value="3~5년차">3~5년차</option>
                  <option value="5년차 이상">5년차 이상</option>
                </select>
              </div>
              <div>
                <label htmlFor="education" className="block text-xs font-bold text-[#243844] mb-2 ml-1">최종 학력</label>
                <select id="education" value={education} onChange={(e) => setEducation(e.target.value)} className={`theme-input w-full px-5 py-3.5 rounded-2xl border ${!education ? 'border-[#B7C3CA] bg-[#EAF4F7]/55' : ''} outline-none cursor-pointer focus:ring-4 focus:ring-[#8390D6]/20 transition-all appearance-none font-bold`}>
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

          <div className="theme-card p-5 sm:p-6 rounded-2xl border">
            <h2 className="text-sm font-bold text-[#7E8A92] uppercase tracking-widest mb-4 flex items-center gap-2">
              <span className="w-2 h-2 bg-[#7E8A92] rounded-full" />
              STEP 4. 리포트 이메일
            </h2>
            <div>
              <label htmlFor="reportEmail" className="block text-xs font-bold text-[#243844] mb-2 ml-1">리포트 받을 이메일</label>
              <input
                type="email"
                id="reportEmail"
                value={reportEmail}
                onChange={(e) => setReportEmail(e.target.value)}
                placeholder="example@email.com"
                className={`theme-input w-full px-5 py-3.5 rounded-2xl border ${!reportEmail ? 'border-[#B7C3CA] bg-[#EAF4F7]/55' : ''} focus:ring-4 focus:ring-[#B7C3CA]/30 focus:border-[#7E8A92] outline-none text-base font-semibold transition-all`}
                required
              />
              <p className="mt-2 text-xs font-medium text-[#243844]">
                면접 종료 후 분석 리포트와 전체 대화 내용이 이 주소로 자동 발송됩니다.
              </p>
            </div>
          </div>

          {/* Action Footer */}
          <div className="pt-5 border-t border-[#B7C3CA]/40 flex flex-col items-center gap-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-3xl">
              <button
                type="button"
                disabled={isParsingResume || isAnalyzingJd}
                onClick={() => {
                  setInterviewMode("short");
                  startInterview("short");
                }}
                className="theme-cta group relative min-h-[112px] overflow-hidden rounded-2xl px-6 py-5 text-left text-white transition-all active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
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
                className="theme-cta group relative min-h-[112px] overflow-hidden rounded-2xl px-6 py-5 text-left text-white transition-all active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
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
              <p className="text-[12px] text-[#17232B] font-black">
                원하는 연습 방식을 누르면 바로 AI 면접이 시작됩니다.
              </p>
              <p className="text-[12px] text-[#17232B] font-bold">
                🛡️ 데이터는 개인정보 보호를 위해 현재 세션 중에만 임시로 유지되며, 창을 닫는 즉시 모든 기록이 사라집니다.
              </p>
              <p className="text-[11px] text-[#243844] font-medium">
                면접 대화 원문은 저장하지 않으며, 종료 후 AI 면접관 개선을 위한 익명화된 운영 지침만 생성될 수 있습니다.
              </p>
            </div>
          </div>
        </form>
        )}

        </section>

        <section id="product-story" className="home-section mt-24 space-y-28 pt-20">
          <div className="grid grid-cols-[0.72fr_1.28fr] items-center gap-16">
            <div className="home-copy">
              <p className="text-sm font-black uppercase tracking-[0.32em] text-[#4556D6]">Designed for Practice</p>
              <h2 className="mt-5 text-5xl font-black leading-tight tracking-tight">
                실제로 말해봐야<br />보이는 것들.
              </h2>
              <p className="mt-7 text-lg font-bold leading-relaxed text-[#243844]">
                글로 정리한 답변은 괜찮아 보여도, 면접 자리에서는 흐름과 속도, 근거가 함께 드러납니다.
                TechTree는 사용자가 준비한 자료를 질문으로 바꾸고, 음성 대화 속에서 답변의 구조를 점검합니다.
              </p>
            </div>
            <div className="home-art-panel relative min-h-[470px] overflow-hidden rounded-2xl">
              <div className="absolute left-12 top-12 rounded-2xl border border-white/45 bg-white/88 p-6 shadow-2xl shadow-[#4556D6]/18">
                <p className="text-xs font-black uppercase tracking-[0.22em] text-[#B88A3A]">Input</p>
                <p className="mt-4 text-3xl font-black text-[#17232B]">공고와 이력서를<br />면접 맥락으로</p>
              </div>
              <div className="absolute bottom-10 right-12 w-[58%] overflow-hidden rounded-2xl border border-white/55 bg-white/90 p-10 shadow-2xl shadow-[#17232B]/20">
                <NextImage src="/logo.png" alt="TechTree service screen placeholder" width={260} height={260} className="mx-auto h-64 w-64 object-contain" />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-[1.22fr_0.78fr] items-center gap-16">
            <div className="home-art-panel relative min-h-[540px] overflow-hidden rounded-2xl">
              <div className="absolute left-1/2 top-12 h-24 w-24 -translate-x-1/2 overflow-hidden rounded-2xl border border-white/55 bg-white p-3 shadow-2xl">
                <NextImage src="/logo.png" alt="TechTree interview placeholder" width={96} height={96} className="h-full w-full object-contain" />
              </div>
              <div className="absolute bottom-16 left-1/2 w-[72%] -translate-x-1/2 rounded-2xl border border-white/45 bg-[#101820]/90 p-7 text-white shadow-2xl shadow-[#17232B]/25">
                <div className="mb-6 flex items-center justify-between">
                  <span className="text-xs font-black uppercase tracking-[0.24em] text-[#D7B56D]">Interview Flow</span>
                  <span className="interview-live-dot h-2.5 w-2.5 rounded-full" />
                </div>
                <div className="grid grid-cols-4 gap-3">
                  {["정보 입력", "질문 준비", "음성 답변", "리포트"].map((item, index) => (
                    <div key={item} className="rounded-xl border border-white/12 bg-white/8 p-4">
                      <p className="text-xs font-black text-[#D7B56D]">0{index + 1}</p>
                      <p className="mt-5 text-sm font-black">{item}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="home-copy">
              <p className="text-sm font-black uppercase tracking-[0.32em] text-[#B88A3A]">Voice First</p>
              <h2 className="mt-5 text-5xl font-black leading-tight tracking-tight">
                읽는 연습이 아니라,<br />대화하는 연습.
              </h2>
              <p className="mt-7 text-lg font-bold leading-relaxed text-[#243844]">
                Push-to-Talk 방식으로 답변 타이밍을 직접 제어합니다.
                잡음 유입을 줄이고, 질문을 듣고 생각한 뒤 말하는 실제 면접 흐름에 집중할 수 있습니다.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-[0.8fr_1.2fr] items-start gap-12">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.32em] text-[#4556D6]">What You Get</p>
              <h2 className="mt-5 text-6xl font-black leading-[0.98] tracking-tight text-[#101820]">
                끝나면,<br />다음 연습이<br />보입니다.
              </h2>
            </div>
            <div className="grid grid-cols-2 gap-5">
              {[
                ["종합 점수", "면접 전체 흐름을 한눈에 파악합니다."],
                ["강점", "잘 전달된 경험과 역량을 분리해 보여줍니다."],
                ["개선점", "답변 구조, 근거, 말하기 습관을 다시 볼 수 있습니다."],
                ["Q&A 피드백", "주요 질문과 답변을 기준으로 다음 답변을 준비합니다."],
              ].map(([title, body]) => (
                <div key={title} className="rounded-2xl border border-[#B7C3CA]/45 bg-white/72 p-7 shadow-sm">
                  <p className="text-2xl font-black text-[#17232B]">{title}</p>
                  <p className="mt-5 text-base font-bold leading-relaxed text-[#243844]">{body}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="theme-deep rounded-2xl p-12 text-white">
            <div className="grid grid-cols-[0.88fr_1.12fr] gap-14">
              <div>
                <p className="text-sm font-black uppercase tracking-[0.3em] text-[#D7B56D]">Builder Note</p>
                <h3 className="mt-5 text-6xl font-black leading-tight">제작자의 말</h3>
              </div>
              <div className="space-y-5 text-xl font-bold leading-relaxed text-white/90">
                <p>
                  면접 준비에서 가장 답답한 순간은 무엇을 더 고쳐야 하는지 모를 때라고 생각했습니다.
                  그래서 TechTree는 질문 목록보다 실제 대화와 이후의 피드백에 더 집중했습니다.
                </p>
                <p>
                  답변을 대신 만들어주는 서비스가 아니라, 사용자가 자신의 경험을 더 정확하고 설득력 있게 말하도록 돕는 연습 도구를 목표로 합니다.
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl bg-gradient-to-br from-[#DCEBF1] via-[#A9BBFF] to-[#4556D6] px-12 py-20 text-center shadow-2xl shadow-[#4556D6]/18">
            <h3 className="text-6xl font-black tracking-tight text-[#101820]">지금 바로 면접을 시작하세요</h3>
            <p className="mx-auto mt-6 max-w-2xl text-lg font-bold leading-relaxed text-[#17232B]">
              위 입력 영역에 준비한 자료를 넣고 빠른 연습 또는 실전 연습을 선택하면,
              AI 면접관이 당신의 맥락에 맞춰 대화를 시작합니다.
            </p>
            <a href="#interview-workspace" className="mt-9 inline-flex rounded-full bg-[#101820] px-7 py-3 text-sm font-black text-white transition hover:bg-[#243844]">
              입력 영역으로 이동
            </a>
          </div>
        </section>
      </div>

      <div className="mt-12 flex justify-center opacity-30 grayscale hover:opacity-100 hover:grayscale-0 transition-all duration-500">
        {/* Placeholder for partner logos or tech stack icons if needed */}
      </div>
    </main>
  );
}
