"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { apiPath } from "@/lib/api";

type LogSource = "IN" | "OUT" | "SYS" | "ERR";
type InterviewMode = "short" | "long";
type TranscriptRole = "ai" | "user";

interface CoreLogEntry {
  id: string;
  timestamp: string;
  source: LogSource;
  event: string;
  summary?: string;
}

interface TranscriptEntry {
  id: string;
  role: TranscriptRole;
  text: string;
  timestamp: string;
  isComplete: boolean;
}

interface DebugProfile {
  report_email: string;
  job_title: string;
  experience: string;
  education: string;
  resume: string;
  job_description: string;
  job_image: string | null;
  interview_mode: InterviewMode;
}

interface BackendJobPostingAnalysis {
  status?: string;
  source?: string;
  summary?: string;
  [key: string]: unknown;
}

interface GuidelineSelectionSummary {
  reflection_ids?: string[];
  policy_ids?: string[];
  text?: string;
  [key: string]: unknown;
}

const DEFAULT_PROFILE_TEXT = {
  resume:
    "지원자는 LLM 기반 AI Agent 개발 프로젝트를 진행했으며, FastAPI와 Next.js를 활용해 음성 면접 서비스의 입력, 세션 관리, 평가 리포트 흐름을 구현했습니다. LangGraph를 활용한 평가 워크플로우와 OpenAI Realtime 기반 음성 인터페이스 경험이 있습니다.",
  jobDescription:
    "AI Agent 개발자는 LLM 기반 서비스 설계, API 연동, 프롬프트 개선, 사용자 대화 흐름 디버깅 경험이 필요합니다. FastAPI, Next.js, LangGraph, OpenAI API 활용 경험을 우대합니다.",
};

function makeDefaultProfile(interviewMode: InterviewMode): DebugProfile {
  return {
    report_email: "debug@example.com",
    job_title: "AI Agent 개발자",
    experience: "신입",
    education: "학사(4년제)",
    resume: DEFAULT_PROFILE_TEXT.resume,
    job_description: DEFAULT_PROFILE_TEXT.jobDescription,
    job_image: null,
    interview_mode: interviewMode,
  };
}

function formatElapsed(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function getTimestamp() {
  return new Date().toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function safeJsonParse(value: string | null): DebugProfile | null {
  if (!value) return null;
  try {
    return JSON.parse(value) as DebugProfile;
  } catch {
    return null;
  }
}

function summarizeStartPayload(profile: DebugProfile) {
  return `${profile.job_title} · ${profile.experience} · ${profile.education} · resume ${profile.resume.length}자 · JD ${profile.job_description.length}자 · image ${profile.job_image ? "yes" : "no"}`;
}

function parseGuidelineBullets(text?: string) {
  return String(text || "")
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"))
    .map((line) => line.replace(/^[-*]\s*/, ""));
}

export default function DebugPage() {
  const [isRecording, setIsRecording] = useState(false);
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [interviewMode, setInterviewMode] = useState<InterviewMode>("short");
  const [statusText, setStatusText] = useState("대기 중");
  const [coreLogs, setCoreLogs] = useState<CoreLogEntry[]>([]);
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [profile, setProfile] = useState<DebugProfile | null>(null);
  const [backendJobAnalysis, setBackendJobAnalysis] = useState<BackendJobPostingAnalysis | null>(null);
  const [promptVariant, setPromptVariant] = useState("-");
  const [guidelineSelection, setGuidelineSelection] = useState<GuidelineSelectionSummary | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isCheckingInvite, setIsCheckingInvite] = useState(true);
  const [isInviteAuthenticated, setIsInviteAuthenticated] = useState(false);
  const [inviteCode, setInviteCode] = useState("");
  const [inviteError, setInviteError] = useState("");
  const [isVerifyingInvite, setIsVerifyingInvite] = useState(false);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);
  const audioElRef = useRef<HTMLAudioElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  const logsEndRef = useRef<HTMLDivElement | null>(null);
  const transcriptsEndRef = useRef<HTMLDivElement | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const jobImagePendingRef = useRef(false);
  const jobImageInjectedRef = useRef(false);
  const savedAiTranscriptKeysRef = useRef<Set<string>>(new Set());
  const savedAiTranscriptTextsRef = useRef<Set<string>>(new Set());
  const pendingAiTranscriptIdsRef = useRef<string[]>([]);
  const pendingUserTranscriptIdsRef = useRef<string[]>([]);

  const addCoreLog = useCallback((source: LogSource, event: string, summary?: string) => {
    setCoreLogs((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        timestamp: getTimestamp(),
        source,
        event,
        summary,
      },
    ]);
  }, []);

  const readStoredProfile = useCallback((): DebugProfile | null => {
    const stored = safeJsonParse(sessionStorage.getItem("interviewProfile")) ||
      safeJsonParse(localStorage.getItem("interviewProfile"));
    if (!stored) return null;
    return {
      ...makeDefaultProfile(stored.interview_mode === "long" ? "long" : interviewMode),
      ...stored,
      interview_mode: stored.interview_mode === "long" ? "long" : "short",
      job_image: stored.job_image || null,
    };
  }, [interviewMode]);

  const syncProfileFromStorage = useCallback(() => {
    const stored = readStoredProfile();
    if (!stored) return;
    setProfile(stored);
    setInterviewMode(stored.interview_mode);
  }, [readStoredProfile]);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const startTimer = useCallback(() => {
    stopTimer();
    const startedAt = Date.now();
    setElapsedSeconds(0);
    timerRef.current = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
  }, [stopTimer]);

  const cleanupSession = useCallback(() => {
    dcRef.current?.close();
    dcRef.current = null;
    pcRef.current?.close();
    pcRef.current = null;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    stopTimer();
    jobImagePendingRef.current = false;
    jobImageInjectedRef.current = false;
    setIsSessionActive(false);
    setIsRecording(false);
  }, [stopTimer]);

  useEffect(() => {
    syncProfileFromStorage();
    return () => cleanupSession();
  }, [cleanupSession, syncProfileFromStorage]);

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
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [coreLogs]);

  useEffect(() => {
    transcriptsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts]);

  const applyDefaultProfile = () => {
    const defaultProfile = makeDefaultProfile(interviewMode);
    sessionStorage.setItem("interviewProfile", JSON.stringify(defaultProfile));
    localStorage.removeItem("interviewProfile");
    setProfile(defaultProfile);
    setBackendJobAnalysis(null);
    setPromptVariant("-");
    setGuidelineSelection(null);
    setStatusText("Default 입력값 적용 완료");
    addCoreLog("SYS", "Default profile applied", summarizeStartPayload(defaultProfile));
  };

  const verifyInviteCode = async () => {
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
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "초대코드를 확인할 수 없습니다.");
      }
      setIsInviteAuthenticated(true);
      setInviteCode("");
      addCoreLog("SYS", "Invite verified", "debug session cookie ready");
    } catch (error) {
      const message = error instanceof Error ? error.message : "초대코드를 확인할 수 없습니다.";
      setInviteError(message);
      addCoreLog("ERR", "Invite verification failed", message);
    } finally {
      setIsVerifyingInvite(false);
    }
  };

  const updateInterviewMode = (mode: InterviewMode) => {
    setInterviewMode(mode);
    const nextProfile = {
      ...(profile || makeDefaultProfile(mode)),
      interview_mode: mode,
    };
    setProfile(nextProfile);
    sessionStorage.setItem("interviewProfile", JSON.stringify(nextProfile));
    localStorage.removeItem("interviewProfile");
    addCoreLog("SYS", "Interview mode changed", mode === "short" ? "빠른 연습" : "실전 연습");
  };

  const updateJobTitle = (jobTitle: string) => {
    const nextProfile = {
      ...(profile || makeDefaultProfile(interviewMode)),
      job_title: jobTitle,
    };
    setProfile(nextProfile);
    sessionStorage.setItem("interviewProfile", JSON.stringify(nextProfile));
    localStorage.removeItem("interviewProfile");
  };

  const createTranscriptSlot = useCallback((role: TranscriptRole) => {
    const id = `${role}-slot-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    if (role === "ai") {
      pendingAiTranscriptIdsRef.current.push(id);
    } else {
      pendingUserTranscriptIdsRef.current.push(id);
    }
    setTranscripts((prev) => [
      ...prev,
      {
        id,
        role,
        text: "",
        timestamp: getTimestamp(),
        isComplete: false,
      },
    ]);
  }, []);

  const completeTranscriptSlot = useCallback((role: TranscriptRole, itemId: string, text: string) => {
    const normalizedText = String(text || "").replace(/\s+/g, " ").trim();
    const queue = role === "ai" ? pendingAiTranscriptIdsRef.current : pendingUserTranscriptIdsRef.current;
    const slotId = queue.shift();

    if (!normalizedText) {
      if (slotId) {
        setTranscripts((prev) => prev.filter((item) => item.id !== slotId));
      }
      return;
    }

    setTranscripts((prev) => {
      const existingIndex = prev.findIndex((item) => item.id === itemId);
      if (existingIndex >= 0) {
        return prev.map((item, index) => (
          index === existingIndex
            ? { ...item, text: normalizedText, timestamp: getTimestamp(), isComplete: true }
            : item
        ));
      }

      if (slotId) {
        return prev.map((item) => (
          item.id === slotId
            ? { ...item, id: itemId, text: normalizedText, timestamp: getTimestamp(), isComplete: true }
            : item
        ));
      }

      return [
        ...prev,
        {
          id: itemId,
          role,
          text: normalizedText,
          timestamp: getTimestamp(),
          isComplete: true,
        },
      ];
    });
  }, []);

  const completeAiTranscript = useCallback((itemId: string, text: string) => {
    const aiText = String(text || "").replace(/\s+/g, " ").trim();
    if (!aiText) return;
    const textKey = aiText.toLocaleLowerCase("ko-KR");
    if (savedAiTranscriptKeysRef.current.has(itemId) || savedAiTranscriptTextsRef.current.has(textKey)) return;
    savedAiTranscriptKeysRef.current.add(itemId);
    savedAiTranscriptTextsRef.current.add(textKey);
    completeTranscriptSlot("ai", itemId, aiText);
  }, [completeTranscriptSlot]);

  const completeUserTranscript = useCallback((itemId: string, text: string) => {
    completeTranscriptSlot("user", itemId, text);
  }, [completeTranscriptSlot]);

  const startDebugSession = async () => {
    if (pcRef.current) return;
    if (!isInviteAuthenticated) {
      setStatusText("초대코드 인증이 필요합니다");
      addCoreLog("ERR", "Invite required", "상단에서 초대코드를 인증한 뒤 Start를 눌러주세요.");
      return;
    }

    const activeProfile = readStoredProfile() || profile || makeDefaultProfile(interviewMode);
    setProfile(activeProfile);
    sessionStorage.setItem("interviewProfile", JSON.stringify(activeProfile));
    localStorage.removeItem("interviewProfile");
    setCoreLogs([]);
    setTranscripts([]);
    savedAiTranscriptKeysRef.current = new Set();
    savedAiTranscriptTextsRef.current = new Set();
    pendingAiTranscriptIdsRef.current = [];
    pendingUserTranscriptIdsRef.current = [];
    startTimer();
    addCoreLog("SYS", "Session start requested", summarizeStartPayload(activeProfile));

    const audioEl = document.createElement("audio");
    audioEl.autoplay = true;
    audioElRef.current = audioEl;

    try {
      setStatusText("토큰 발급 중");
      jobImagePendingRef.current = Boolean(activeProfile.job_image);
      jobImageInjectedRef.current = false;
      setBackendJobAnalysis(null);
      setPromptVariant("-");
      setGuidelineSelection(null);

      const res = await fetch(apiPath("/interview/start"), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "debug@example.com",
          report_email: activeProfile.report_email,
          job_title: activeProfile.job_title,
          education: activeProfile.education,
          experience: activeProfile.experience,
          resume: activeProfile.resume,
          job_image: activeProfile.job_image,
          job_description: activeProfile.job_description,
          interview_mode: activeProfile.interview_mode,
        }),
      });

      if (!res.ok) {
        if (res.status === 401) {
          setIsInviteAuthenticated(false);
          throw new Error("초대코드 인증이 필요합니다. 상단에서 다시 인증해 주세요.");
        }
        throw new Error(`토큰 발급 API 오류 (${res.status})`);
      }
      const data = await res.json();
      const ephemeralKey = data.ephemeral_token;
      sessionIdRef.current = data.session_id;

      const jobPostingAnalysis = (
        data.job_posting_analysis &&
        typeof data.job_posting_analysis === "object" &&
        !Array.isArray(data.job_posting_analysis)
      ) ? data.job_posting_analysis as BackendJobPostingAnalysis : null;
      const responseGuidelineSelection = (
        data.guideline_selection &&
        typeof data.guideline_selection === "object" &&
        !Array.isArray(data.guideline_selection)
      ) ? data.guideline_selection as GuidelineSelectionSummary : null;

      setBackendJobAnalysis(jobPostingAnalysis);
      setPromptVariant(typeof data.prompt_variant === "string" ? data.prompt_variant : "-");
      setGuidelineSelection(responseGuidelineSelection);
      addCoreLog("IN", "Backend start response", `session ${data.session_id || "-"} · prompt ${data.prompt_variant || "-"} · JD ${jobPostingAnalysis?.status || "none"}`);
      const guidelineBullets = parseGuidelineBullets(responseGuidelineSelection?.text);
      addCoreLog(
        "IN",
        "Guidelines injected",
        guidelineBullets.length > 0
          ? guidelineBullets.map((item, index) => `${index + 1}. ${item}`).join("\n")
          : "주입된 reflection/policy 지침이 없습니다."
      );

      setStatusText("WebRTC 연결 중");
      const pc = new RTCPeerConnection();
      pcRef.current = pc;
      pc.ontrack = (event) => {
        if (audioElRef.current) audioElRef.current.srcObject = event.streams[0];
        addCoreLog("IN", "Remote audio track received", "OpenAI audio stream attached");
      };

      const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = mediaStream;
      pc.addTrack(mediaStream.getAudioTracks()[0]);
      mediaStream.getAudioTracks()[0].enabled = false;

      const dc = pc.createDataChannel("oai-events");
      dcRef.current = dc;

      const injectJobImageContext = () => {
        if (
          !jobImagePendingRef.current ||
          jobImageInjectedRef.current ||
          !activeProfile.job_image ||
          dc.readyState !== "open"
        ) return;

        const imageEvent = {
          type: "conversation.item.create",
          item: {
            type: "message",
            role: "user",
            content: [
              { type: "input_image", image_url: activeProfile.job_image },
              { type: "input_text", text: "이 이미지는 제가 지원하고자 하는 채용 공고입니다. 이후 질문에서 이 내용을 참고해 주세요." },
            ],
          },
        };

        jobImageInjectedRef.current = true;
        jobImagePendingRef.current = false;
        dc.send(JSON.stringify(imageEvent));
        addCoreLog("OUT", "Image context injected", "job_image conversation.item.create");
      };

      dc.addEventListener("open", () => {
        setIsSessionActive(true);
        setStatusText("첫 질문 요청 중");
        addCoreLog("SYS", "Data channel open", "Realtime event channel ready");
        const initialResponseEvent = { type: "response.create" };
        createTranscriptSlot("ai");
        dc.send(JSON.stringify(initialResponseEvent));
        addCoreLog("OUT", "Initial response.create", "첫 면접관 발화 요청");
      });

      dc.addEventListener("message", async (event) => {
        const realtimeEvent = JSON.parse(event.data);

        if (realtimeEvent.type === "response.audio_transcript.done" || realtimeEvent.type === "response.output_audio_transcript.done") {
          completeAiTranscript(String(realtimeEvent.item_id || realtimeEvent.response_id || `ai-${Date.now()}`), realtimeEvent.transcript || "");
          return;
        }

        if (realtimeEvent.type === "conversation.item.input_audio_transcription.completed") {
          completeUserTranscript(String(realtimeEvent.item_id || `user-${Date.now()}`), realtimeEvent.transcript || "");
          addCoreLog("IN", "User transcript completed", String(realtimeEvent.transcript || "").slice(0, 90));
          return;
        }

        if (realtimeEvent.type === "response.audio.delta") {
          setStatusText("AI 발화 중");
          return;
        }

        if (realtimeEvent.type === "response.done") {
          injectJobImageContext();
          setStatusText("스페이스바를 누른 채로 대답하세요");
          addCoreLog("IN", "Assistant response done", `output ${Array.isArray(realtimeEvent.response?.output) ? realtimeEvent.response.output.length : 0} item(s)`);
          return;
        }

        if (typeof realtimeEvent.type === "string" && realtimeEvent.type.includes("error")) {
          addCoreLog("ERR", realtimeEvent.type, realtimeEvent.error?.message || "Realtime error event");
        }
      });

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      addCoreLog("OUT", "SDP offer created", "local description set");

      const sdpResponse = await fetch("https://api.openai.com/v1/realtime/calls", {
        method: "POST",
        body: offer.sdp,
        headers: {
          Authorization: `Bearer ${ephemeralKey}`,
          "Content-Type": "application/sdp",
        },
      });

      if (!sdpResponse.ok) {
        throw new Error(`OpenAI SDP 오류 (${sdpResponse.status}) ${await sdpResponse.text()}`);
      }

      const answer = {
        type: "answer" as RTCSdpType,
        sdp: await sdpResponse.text(),
      };
      await pc.setRemoteDescription(answer);
      addCoreLog("IN", "SDP answer received", "remote description set");
      setStatusText("연결됨");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      addCoreLog("ERR", "Connection error", message);
      setStatusText("오류 발생");
      cleanupSession();
    }
  };

  const endSession = () => {
    cleanupSession();
    addCoreLog("SYS", "Session ended", "manual debug stop");
    setStatusText("종료됨");
  };

  const startRecording = useCallback(() => {
    if (streamRef.current && !isRecording && dcRef.current?.readyState === "open") {
      const audioTrack = streamRef.current.getAudioTracks()[0];
      audioTrack.enabled = true;
      setIsRecording(true);
      setStatusText("답변 중. 완료 후 손을 떼세요");
      dcRef.current.send(JSON.stringify({ type: "input_audio_buffer.clear" }));
      addCoreLog("SYS", "Push-to-Talk ON", "input_audio_buffer.clear");
    }
  }, [addCoreLog, isRecording]);

  const stopRecording = useCallback(() => {
    if (streamRef.current && isRecording && dcRef.current?.readyState === "open") {
      const audioTrack = streamRef.current.getAudioTracks()[0];
      audioTrack.enabled = false;
      setIsRecording(false);
      setStatusText("답변 전송 중");
      createTranscriptSlot("user");
      dcRef.current.send(JSON.stringify({ type: "input_audio_buffer.commit" }));
      const responseCreateEvent = { type: "response.create" };
      createTranscriptSlot("ai");
      dcRef.current.send(JSON.stringify(responseCreateEvent));
      addCoreLog("OUT", "User audio committed", "input_audio_buffer.commit → response.create");
      setStatusText("면접관 답변을 기다리는 중");
    }
  }, [addCoreLog, createTranscriptSlot, isRecording]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.code === "Space" && !event.repeat) {
        event.preventDefault();
        startRecording();
      }
    };
    const handleKeyUp = (event: KeyboardEvent) => {
      if (event.code === "Space") {
        event.preventDefault();
        stopRecording();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [startRecording, stopRecording]);

  const sourceColor = (source: LogSource) => {
    if (source === "OUT") return "border-blue-500/35 bg-blue-500/10 text-blue-200";
    if (source === "IN") return "border-emerald-500/35 bg-emerald-500/10 text-emerald-200";
    if (source === "ERR") return "border-red-500/35 bg-red-500/10 text-red-200";
    return "border-yellow-500/35 bg-yellow-500/10 text-yellow-100";
  };
  const visibleTranscripts: TranscriptEntry[] = [];
  for (const item of transcripts) {
    if (!item.isComplete) break;
    visibleTranscripts.push(item);
  }

  return (
    <main className="flex h-screen min-w-[1180px] flex-col overflow-hidden bg-[#101820] text-[#EAF4F7]">
      <header className="grid h-24 shrink-0 grid-cols-[1fr_auto_1.35fr] items-center border-b border-white/10 bg-[#17232B] px-6">
        <div>
          <h1 className="text-lg font-black tracking-tight text-white">TechTree Prompt Debugger</h1>
          <div className="mt-1 flex items-center gap-2 text-xs text-[#B7C3CA]">
            <span className={`h-2.5 w-2.5 rounded-full ${isSessionActive ? "bg-emerald-400" : "bg-[#7E8A92]"}`} />
            <span>{isSessionActive ? "CONNECTED" : "DISCONNECTED"}</span>
            <span className="text-white/25">/</span>
            <span>{interviewMode === "short" ? "빠른 연습" : "실전 연습"}</span>
          </div>
        </div>

        <div className="rounded-2xl border border-[#D7B56D]/45 bg-[#D7B56D]/10 px-8 py-3 text-center shadow-lg shadow-black/20">
          <p className="text-[10px] font-black uppercase tracking-[0.28em] text-[#D7B56D]">Elapsed</p>
          <p className="font-mono text-3xl font-black text-white tabular-nums">{formatElapsed(elapsedSeconds)}</p>
        </div>

        <div className="flex items-center justify-end gap-2">
          <div className="flex min-w-[360px] flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em] ${
                isInviteAuthenticated
                  ? "bg-emerald-500/15 text-emerald-200"
                  : "bg-red-500/15 text-red-200"
              }`}>
                {isCheckingInvite ? "checking" : isInviteAuthenticated ? "authorized" : "invite required"}
              </span>
              <input
                value={inviteCode}
                onChange={(event) => {
                  setInviteCode(event.target.value);
                  setInviteError("");
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    verifyInviteCode();
                  }
                }}
                disabled={isInviteAuthenticated || isVerifyingInvite || isSessionActive}
                placeholder={isInviteAuthenticated ? "인증 완료" : "초대코드 입력"}
                className="h-10 min-w-0 flex-1 rounded-xl border border-[#B7C3CA]/25 bg-black/20 px-3 text-sm font-bold text-white outline-none transition placeholder:text-[#7E8A92] focus:border-[#D7B56D]/55 disabled:cursor-not-allowed disabled:opacity-45"
              />
              <button
                type="button"
                disabled={isInviteAuthenticated || isVerifyingInvite || isSessionActive}
                onClick={verifyInviteCode}
                className="h-10 rounded-xl border border-[#D7B56D]/45 bg-[#D7B56D]/12 px-3 text-xs font-black text-[#F7FBFC] transition hover:bg-[#D7B56D]/22 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {isVerifyingInvite ? "확인 중" : "승인"}
              </button>
            </div>
            {inviteError && <p className="truncate text-xs font-bold text-red-300">{inviteError}</p>}
          </div>
          <button
            type="button"
            disabled={isSessionActive}
            onClick={applyDefaultProfile}
            className="rounded-xl border border-[#B7C3CA]/30 bg-white/8 px-4 py-2 text-sm font-bold text-[#EAF4F7] transition hover:bg-white/14 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Default Input
          </button>
          <button
            type="button"
            disabled={isSessionActive || !isInviteAuthenticated}
            onClick={startDebugSession}
            className="rounded-xl bg-[#4556D6] px-5 py-2 text-sm font-black text-white transition hover:bg-[#5d6cff] disabled:cursor-not-allowed disabled:opacity-40"
          >
            Start
          </button>
          <button
            type="button"
            disabled={!isSessionActive}
            onClick={endSession}
            className="rounded-xl bg-red-500 px-5 py-2 text-sm font-black text-white transition hover:bg-red-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            End
          </button>
        </div>
      </header>

      <section className="grid min-h-0 flex-1 grid-cols-[360px_1fr_420px] gap-4 p-4">
        <aside className="flex min-h-0 flex-col rounded-2xl border border-white/10 bg-[#17232B] p-4 shadow-2xl shadow-black/20">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-black uppercase tracking-[0.22em] text-[#D7B56D]">Input</h2>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-bold text-[#B7C3CA]">{statusText}</span>
          </div>

          <label className="mb-4 block rounded-xl border border-[#D7B56D]/20 bg-[#D7B56D]/8 p-3">
            <span className="text-[10px] font-black uppercase tracking-[0.18em] text-[#D7B56D]">Test Job Title</span>
            <input
              value={profile?.job_title || ""}
              onChange={(event) => updateJobTitle(event.target.value)}
              disabled={isSessionActive}
              placeholder="테스트할 직무를 입력하세요"
              className="mt-2 h-11 w-full rounded-lg border border-white/10 bg-black/25 px-3 text-sm font-bold text-white outline-none transition placeholder:text-[#7E8A92] focus:border-[#D7B56D]/60 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </label>

          <div className="grid grid-cols-2 gap-2">
            {[
              ["경력", profile?.experience || "-"],
              ["학력", profile?.education || "-"],
              ["이메일", profile?.report_email || "-"],
              ["이력서", profile ? `${profile.resume.length}자` : "-"],
              ["공고", profile ? `${profile.job_description.length}자` : "-"],
              ["공고 이미지", profile?.job_image ? "있음" : "없음"],
              ["세션 ID", sessionIdRef.current || "-"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl border border-white/8 bg-black/20 p-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7E8A92]">{label}</p>
                <p className="mt-1 truncate text-sm font-bold text-white" title={value}>{value}</p>
              </div>
            ))}
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2">
            <button
              type="button"
              disabled={isSessionActive}
              onClick={() => updateInterviewMode("short")}
              className={`rounded-xl border px-4 py-3 text-left transition disabled:cursor-not-allowed disabled:opacity-40 ${interviewMode === "short" ? "border-[#D7B56D]/55 bg-[#D7B56D]/12 text-white" : "border-white/10 bg-white/5 text-[#B7C3CA]"}`}
            >
              <p className="font-black">빠른 연습</p>
              <p className="mt-1 text-xs opacity-70">7분 내외</p>
            </button>
            <button
              type="button"
              disabled={isSessionActive}
              onClick={() => updateInterviewMode("long")}
              className={`rounded-xl border px-4 py-3 text-left transition disabled:cursor-not-allowed disabled:opacity-40 ${interviewMode === "long" ? "border-[#D7B56D]/55 bg-[#D7B56D]/12 text-white" : "border-white/10 bg-white/5 text-[#B7C3CA]"}`}
            >
              <p className="font-black">실전 연습</p>
              <p className="mt-1 text-xs opacity-70">20분 내외</p>
            </button>
          </div>

          <div className="mt-4 min-h-0 flex-1 overflow-y-auto rounded-xl border border-white/8 bg-black/20 p-3">
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-[#7E8A92]">Prompt Variant</p>
            <p className="mt-2 break-words text-sm font-bold text-[#EAF4F7]">{promptVariant}</p>

            <p className="mt-5 text-[10px] font-black uppercase tracking-[0.18em] text-[#7E8A92]">Reflection / Policy</p>
            <p className="mt-2 text-sm font-bold text-[#EAF4F7]">
              reflection {guidelineSelection?.reflection_ids?.length || 0}개 / policy {guidelineSelection?.policy_ids?.length || 0}개
            </p>
            <div className="mt-3 space-y-2">
              {parseGuidelineBullets(guidelineSelection?.text).length > 0 ? (
                parseGuidelineBullets(guidelineSelection?.text).map((guideline, index) => (
                  <div key={`${guideline}-${index}`} className="rounded-lg border border-[#D7B56D]/25 bg-[#D7B56D]/8 p-2">
                    <p className="text-[10px] font-black text-[#D7B56D]">GUIDELINE {index + 1}</p>
                    <p className="mt-1 whitespace-pre-wrap text-xs font-medium leading-relaxed text-[#EAF4F7]">{guideline}</p>
                  </div>
                ))
              ) : (
                <p className="rounded-lg border border-white/8 bg-white/5 p-2 text-xs font-medium text-[#7E8A92]">
                  주입된 reflection/policy 지침이 없습니다.
                </p>
              )}
            </div>

            <p className="mt-5 text-[10px] font-black uppercase tracking-[0.18em] text-[#7E8A92]">Backend JD Analysis</p>
            <p className="mt-2 rounded-lg border border-white/8 bg-white/5 px-3 py-2 text-xs font-bold text-[#D7B56D]">
              {backendJobAnalysis?.status || "WAITING"}
            </p>
            <p className="mt-3 whitespace-pre-wrap text-xs font-medium leading-relaxed text-[#B7C3CA]">
              {backendJobAnalysis?.summary || "Start 후 /api/interview/start 응답의 job_posting_analysis.summary가 여기에 표시됩니다."}
            </p>
          </div>
        </aside>

        <section className="flex min-h-0 flex-col rounded-2xl border border-white/10 bg-[#17232B] p-4 shadow-2xl shadow-black/20">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-black uppercase tracking-[0.22em] text-[#D7B56D]">Core Events</h2>
            <span className="text-xs font-bold text-[#7E8A92]">raw delta hidden</span>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto rounded-xl border border-white/8 bg-[#0B1117] p-4">
            {coreLogs.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm font-bold text-[#7E8A92]">
                Default 입력값 적용 후 Start를 누르면 핵심 이벤트만 표시됩니다.
              </div>
            ) : (
              coreLogs.map((log) => (
                <article key={log.id} className={`mb-3 rounded-xl border p-4 ${sourceColor(log.source)}`}>
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs opacity-70">{log.timestamp}</span>
                      <span className="rounded-md bg-black/25 px-2 py-1 text-[10px] font-black">{log.source}</span>
                      <h3 className="text-sm font-black text-white">{log.event}</h3>
                    </div>
                  </div>
                  {log.summary && <p className="mt-3 whitespace-pre-wrap text-sm font-medium leading-relaxed opacity-85">{log.summary}</p>}
                </article>
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        </section>

        <aside className="flex min-h-0 flex-col rounded-2xl border border-white/10 bg-[#17232B] p-4 shadow-2xl shadow-black/20">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-black uppercase tracking-[0.22em] text-[#D7B56D]">Live Script</h2>
            <span className={`rounded-full px-3 py-1 text-xs font-black ${isRecording ? "bg-red-500 text-white" : "bg-white/8 text-[#B7C3CA]"}`}>
              {isRecording ? "REC" : "PTT READY"}
            </span>
          </div>

          <div className="mb-4 rounded-xl border border-white/8 bg-black/20 p-3 text-center">
            <p className="text-xs font-bold text-[#B7C3CA]">Space를 누른 채 답변하고, 손을 떼면 전송됩니다.</p>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto rounded-xl border border-white/8 bg-[#0B1117] p-4">
            {visibleTranscripts.length === 0 ? (
              <div className="flex h-full items-center justify-center text-center text-sm font-bold leading-relaxed text-[#7E8A92]">
                면접관과 지원자의 실시간 스크립트가 여기에 표시됩니다.
              </div>
            ) : (
              <div className="space-y-3 font-mono text-sm leading-relaxed">
                {visibleTranscripts.map((item, index) => (
                  <div key={`${item.id}-${index}`} className="grid grid-cols-[58px_92px_1fr] gap-3 border-b border-white/8 pb-3 last:border-b-0">
                    <span className="text-xs text-[#7E8A92]">{item.timestamp}</span>
                    <span className={`text-xs font-black uppercase tracking-[0.12em] ${item.role === "ai" ? "text-[#8390D6]" : "text-emerald-300"}`}>
                      {item.role === "ai" ? "AI" : "USER"}
                    </span>
                    <p className="whitespace-pre-wrap break-words font-sans text-sm font-medium text-[#EAF4F7]">{item.text}</p>
                  </div>
                ))}
              </div>
            )}
            <div ref={transcriptsEndRef} />
          </div>
        </aside>
      </section>
    </main>
  );
}
