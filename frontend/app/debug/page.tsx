"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { apiPath } from "@/lib/api";

interface LogEntry {
  id: string;
  timestamp: string;
  source: 'IN' | 'OUT' | 'SYS' | 'TOOL';
  event: string;
  data?: unknown;
}

interface JobSearchResult {
  company?: string;
  title?: string;
}

type ImageInjectionStatus = "none" | "pending" | "injected";
type InterviewMode = "short" | "long";

interface DebugProfileSummary {
  jobTitle: string;
  interviewMode: InterviewMode;
  hasJobImage: boolean;
  jobDescriptionChars: number;
  resumeChars: number;
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

export default function DebugPage() {
  const [isRecording, setIsRecording] = useState(false);
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [interviewMode, setInterviewMode] = useState<InterviewMode>("short");
  const [statusText, setStatusText] = useState("대기 중...");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [imageInjectionStatus, setImageInjectionStatus] = useState<ImageInjectionStatus>("none");
  const [profileSummary, setProfileSummary] = useState<DebugProfileSummary | null>(null);
  const [backendJobAnalysis, setBackendJobAnalysis] = useState<BackendJobPostingAnalysis | null>(null);
  const [promptVariant, setPromptVariant] = useState<string>("-");
  const [guidelineSelection, setGuidelineSelection] = useState<GuidelineSelectionSummary | null>(null);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);
  const audioElRef = useRef<HTMLAudioElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const logsEndRef = useRef<HTMLDivElement | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const jobImagePendingRef = useRef(false);
  const jobImageInjectedRef = useRef(false);

  const [transcripts, setTranscripts] = useState<{ id: string, role: string, text: string }[]>([]);

  const addLog = (source: 'IN' | 'OUT' | 'SYS' | 'TOOL', event: string, data?: unknown) => {
    setLogs(prev => [...prev, {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString().split('T')[1].slice(0, -2), // HH:mm:ss.SS
      source,
      event,
      data
    }]);
  };

  // 자동 스크롤
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  useEffect(() => {
    const savedProfile = sessionStorage.getItem("interviewProfile") || localStorage.getItem("interviewProfile");
    if (!savedProfile) return;

    try {
      const profileData = JSON.parse(savedProfile);
      if (profileData.interview_mode === "long" || profileData.interview_mode === "short") {
        setInterviewMode(profileData.interview_mode);
      }
    } catch {
      // 디버그 페이지에서는 손상된 저장값을 조용히 무시합니다.
    }
  }, []);

  const updateInterviewMode = (mode: InterviewMode) => {
    setInterviewMode(mode);

    const savedProfile = sessionStorage.getItem("interviewProfile") || localStorage.getItem("interviewProfile");
    if (!savedProfile) return;

    try {
      const profileData = JSON.parse(savedProfile);
      sessionStorage.setItem("interviewProfile", JSON.stringify({
        ...profileData,
        interview_mode: mode
      }));
      localStorage.removeItem("interviewProfile");
      setProfileSummary(prev => prev ? { ...prev, interviewMode: mode } : prev);
      addLog('SYS', 'Debug interview mode updated', { interview_mode: mode });
    } catch {
      addLog('SYS', 'Failed to update interview mode in browser storage');
    }
  };

  const startDebugSession = async () => {
    if (pcRef.current) return;

    addLog('SYS', 'Init WebRTC Debug Session');
    const audioEl = document.createElement("audio");
    audioEl.autoplay = true;
    audioElRef.current = audioEl;

    try {
      setStatusText("토큰 발급 중...");
      addLog('SYS', 'Fetching Ephemeral Token from /api/interview/start');

      const savedProfile = sessionStorage.getItem("interviewProfile") || localStorage.getItem("interviewProfile");
      const profileData = savedProfile ? JSON.parse(savedProfile) : {
        report_email: "debug@example.com",
        job_title: "직무 미상",
        education: "학사(4년제)",
        experience: "신입",
        resume: "정보 없음"
      };
      const selectedInterviewMode: InterviewMode = interviewMode;
      jobImagePendingRef.current = Boolean(profileData.job_image);
      jobImageInjectedRef.current = false;
      setImageInjectionStatus(profileData.job_image ? "pending" : "none");
      setBackendJobAnalysis(null);
      setPromptVariant("-");
      setProfileSummary({
        jobTitle: profileData.job_title || "직무 미상",
        interviewMode: selectedInterviewMode,
        hasJobImage: Boolean(profileData.job_image),
        jobDescriptionChars: String(profileData.job_description || "").length,
        resumeChars: String(profileData.resume || "").length
      });
      addLog('SYS', 'Loaded profile from browser storage', {
        job_title: profileData.job_title || "직무 미상",
        interview_mode: selectedInterviewMode,
        has_job_image: Boolean(profileData.job_image),
        job_description_chars: String(profileData.job_description || "").length,
        resume_chars: String(profileData.resume || "").length
      });

      const res = await fetch(apiPath("/interview/start"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "debug@example.com",
          report_email: profileData.report_email || "debug@example.com",
          job_title: profileData.job_title || "직무 미상",
          education: profileData.education || "학사(4년제)",
          experience: profileData.experience || "신입",
          resume: profileData.resume || "정보 없음",
          job_image: profileData.job_image || null,
          job_description: profileData.job_description || "",
          interview_mode: selectedInterviewMode
        })
      });

      if (!res.ok) throw new Error("토큰 발급 API 오류");
      const data = await res.json();
      const EPHEMERAL_KEY = data.ephemeral_token;
      sessionIdRef.current = data.session_id;
      const responsePromptVariant = typeof data.prompt_variant === "string" ? data.prompt_variant : "-";
      const responseGuidelineSelection = (
        data.guideline_selection &&
        typeof data.guideline_selection === "object" &&
        !Array.isArray(data.guideline_selection)
      )
        ? data.guideline_selection as GuidelineSelectionSummary
        : null;
      const jobPostingAnalysis = (
        data.job_posting_analysis &&
        typeof data.job_posting_analysis === "object" &&
        !Array.isArray(data.job_posting_analysis)
      )
        ? data.job_posting_analysis as BackendJobPostingAnalysis
        : null;
      setBackendJobAnalysis(jobPostingAnalysis);
      setPromptVariant(responsePromptVariant);
      setGuidelineSelection(responseGuidelineSelection);
      addLog('SYS', 'Token Received', { session_id: data.session_id });
      addLog('SYS', 'Backend start response mode', {
        interview_mode: data.interview_mode || selectedInterviewMode,
        prompt_variant: responsePromptVariant,
        guideline_reflection_count: responseGuidelineSelection?.reflection_ids?.length || 0,
        guideline_policy_count: responseGuidelineSelection?.policy_ids?.length || 0,
        guideline_reflection_ids: responseGuidelineSelection?.reflection_ids?.slice(0, 3) || [],
        guideline_policy_ids: responseGuidelineSelection?.policy_ids?.slice(0, 3) || [],
      });
      addLog('SYS', 'Backend job posting analysis received', jobPostingAnalysis || { status: "missing" });

      setStatusText("WebRTC 연결 중...");

      const pc = new RTCPeerConnection();
      pcRef.current = pc;

      pc.ontrack = (e) => {
        addLog('SYS', 'Audio Track Received from OpenAI');
        if (audioElRef.current) {
          audioElRef.current.srcObject = e.streams[0];
        }
      };

      const ms = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = ms;
      pc.addTrack(ms.getTracks()[0]);
      ms.getAudioTracks()[0].enabled = false; // Push-To-Talk를 위해 기본 마이크 송출 차단
      addLog('SYS', 'Microphone Track Added (Muted by default)');

      const dc = pc.createDataChannel("oai-events");
      dcRef.current = dc;

      const injectJobImageContext = () => {
        if (
          !jobImagePendingRef.current ||
          jobImageInjectedRef.current ||
          !profileData.job_image ||
          dc.readyState !== "open"
        ) {
          return;
        }

        const imageEvent = {
          type: "conversation.item.create",
          item: {
            type: "message",
            role: "user",
            content: [
              { type: "input_image", image_url: profileData.job_image },
              { type: "input_text", text: "이 이미지는 제가 지원하고자 하는 채용 공고입니다. 이후 질문에서 이 내용을 참고해 주세요." }
            ]
          }
        };

        jobImageInjectedRef.current = true;
        jobImagePendingRef.current = false;
        setImageInjectionStatus("injected");
        dc.send(JSON.stringify(imageEvent));
        addLog('OUT', 'conversation.item.create (image after first response)', imageEvent);
      };

      dc.addEventListener("open", () => {
        addLog('SYS', 'Data Channel Opened');
        setIsSessionActive(true);

        const initialResponseEvent = { type: "response.create" };
        dc.send(JSON.stringify(initialResponseEvent));
        addLog('OUT', 'response.create (initial greeting before image)', initialResponseEvent);
      });

      dc.addEventListener("message", async (e) => {
        const realtimeEvent = JSON.parse(e.data);

        // 너무 많은 오디오 델타는 로그를 덮으므로 필터링 옵션 (여기선 그냥 보여줌)
        if (realtimeEvent.type !== 'response.audio.delta') {
          addLog('IN', realtimeEvent.type, realtimeEvent);
        }

        if (realtimeEvent.type === "response.function_call_arguments.done") {
          const callId = realtimeEvent.call_id;
          const name = realtimeEvent.name;
          const args = JSON.parse(realtimeEvent.arguments);

          if (name === "search_job_postings") {
            setStatusText("🔍 툴 실행 중 (채용 검색)...");
            addLog('TOOL', 'Executing search_job_postings', args);

            try {
              const t1 = Date.now();
              const toolRes = await fetch(apiPath(`/interview/${sessionIdRef.current}/tools/search_job`), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  query: args.query
                })
              });
              const searchData = await toolRes.json();
              const t2 = Date.now();

              addLog('TOOL', `Search Tool Completed (${t2 - t1}ms)`, searchData);

              // 검색 결과를 좌측 요약 패널에도 예쁘게 표시
              const resultText = Array.isArray(searchData.result)
                ? searchData.result.map((job: JobSearchResult) => `- ${job.company || "회사명 미상"}: ${job.title || "공고명 미상"}`).join("\n")
                : String(searchData.result || "");
              setTranscripts(prev => [...prev, {
                id: `sys-${Date.now()}`,
                role: "sys",
                text: `[🔍 Tavily 검색 완료]\n${resultText}`
              }]);

              const outputEvent = {
                type: "conversation.item.create",
                item: {
                  type: "function_call_output",
                  call_id: callId,
                  output: JSON.stringify(searchData.result)
                }
              };
              dc.send(JSON.stringify(outputEvent));
              addLog('OUT', 'conversation.item.create (function output)', outputEvent);

              const responseCreateEvent = { type: "response.create" };
              dc.send(JSON.stringify(responseCreateEvent));
              addLog('OUT', 'response.create', responseCreateEvent);

            } catch (err: unknown) {
              addLog('TOOL', 'Tool Execution Error', { error: err instanceof Error ? err.message : String(err) });
            }
          }
        }

        if (realtimeEvent.type === "conversation.item.created") {
          const item = realtimeEvent.item;
          const itemRecord = typeof item === "object" && item !== null ? item as Record<string, unknown> : {};
          const content = Array.isArray(itemRecord.content) ? itemRecord.content : [];
          const hasAudioInput = content.some((part) => {
            const partRecord = typeof part === "object" && part !== null ? part as Record<string, unknown> : {};
            return partRecord.type === "input_audio";
          });
          if (itemRecord.role === "user" && hasAudioInput) {
            // 유저 답변 시작 시 플레이스홀더 생성 (나중에 텍스트가 도착하면 업데이트)
            setTranscripts(prev => [...prev, { id: String(itemRecord.id || `user-${Date.now()}`), role: "user", text: "(음성 인식 중...)" }]);
          }
        }

        if (realtimeEvent.type === "response.audio_transcript.done") {
          setTranscripts(prev => [...prev, { id: realtimeEvent.item_id, role: "ai", text: realtimeEvent.transcript }]);
        }
        if (realtimeEvent.type === "conversation.item.input_audio_transcription.completed") {
          // 서버에서 텍스트 변환이 완료되면 해당 ID의 플레이스홀더를 실제 텍스트로 교체
          setTranscripts(prev => prev.map(t =>
            t.id === realtimeEvent.item_id ? { ...t, text: realtimeEvent.transcript } : t
          ));
        }
        if (realtimeEvent.type === "response.audio.delta") {
          setStatusText("AI 발화 중...");
        }
        if (realtimeEvent.type === "response.done") {
          injectJobImageContext();
          setStatusText("🟢 스페이스바를 누른 채로 대답하세요.");
        }
      });

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      addLog('OUT', 'WebRTC SDP Offer Sent');

      const baseUrl = "https://api.openai.com/v1/realtime";
      const model = "gpt-realtime-mini-2025-12-15";

      const sdpResponse = await fetch(`${baseUrl}?model=${model}`, {
        method: "POST",
        body: offer.sdp,
        headers: {
          Authorization: `Bearer ${EPHEMERAL_KEY}`,
          "Content-Type": "application/sdp"
        },
      });

      const answer = {
        type: "answer" as RTCSdpType,
        sdp: await sdpResponse.text(),
      };
      await pc.setRemoteDescription(answer);
      addLog('IN', 'WebRTC SDP Answer Received');

      setIsRecording(false);
      setStatusText("🟢 스페이스바를 누른 채로 대답하세요.");

    } catch (error: unknown) {
      addLog('SYS', 'Connection Error', { error: error instanceof Error ? error.message : String(error) });
      setStatusText("오류 발생");
    }
  };

  const endSession = () => {
    dcRef.current?.close();
    dcRef.current = null;
    pcRef.current?.close();
    pcRef.current = null;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    jobImagePendingRef.current = false;
    jobImageInjectedRef.current = false;
    setIsSessionActive(false);
    setIsRecording(false);
    addLog('SYS', 'Session Ended manually');
    setStatusText("종료됨");
  };

  const startRecording = useCallback(() => {
    if (streamRef.current && !isRecording && dcRef.current?.readyState === "open") {
      const audioTrack = streamRef.current.getAudioTracks()[0];
      audioTrack.enabled = true;
      setIsRecording(true);
      setStatusText("🔴 답변 완료 후 손을 떼세요");
      dcRef.current.send(JSON.stringify({ type: "input_audio_buffer.clear" }));
      addLog('SYS', 'Push-To-Talk: Microphone ON');
    }
  }, [isRecording]);

  const stopRecording = useCallback(() => {
    if (streamRef.current && isRecording && dcRef.current?.readyState === "open") {
      const audioTrack = streamRef.current.getAudioTracks()[0];
      audioTrack.enabled = false;
      setIsRecording(false);
      setStatusText("답변을 전송 중입니다...");

      dcRef.current.send(JSON.stringify({ type: "input_audio_buffer.commit" }));
      const responseCreateEvent = { type: "response.create" };
      dcRef.current.send(JSON.stringify(responseCreateEvent));
      addLog('SYS', 'Push-To-Talk: Microphone OFF, Buffer Committed');
      addLog('OUT', 'response.create (after user answer)', responseCreateEvent);
      setStatusText("면접관 답변을 기다리는 중입니다...");
    }
  }, [isRecording]);

  // 스페이스바 단축키 (Push-To-Talk)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === "Space" && !e.repeat) {
        e.preventDefault();
        startRecording();
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === "Space") {
        e.preventDefault();
        stopRecording();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    }
  }, [startRecording, stopRecording]);

  const loadDummyData = async () => {
    try {
      setStatusText("더미 데이터 로드 중...");
      const resumeRes = await fetch("/dummy/dummy_resume.pdf");
      const resumeBlob = await resumeRes.blob();
      const resumeFile = new File([resumeBlob], "dummy_resume.pdf", { type: "application/pdf" });

      const formData = new FormData();
      formData.append("file", resumeFile);
      const parseRes = await fetch(apiPath("/upload/parse-pdf"), {
        method: "POST",
        body: formData,
      });
      let resumeText = "";
      if (parseRes.ok) {
        const data = await parseRes.json();
        resumeText = data.text;
      }

      const jdRes = await fetch("/dummy/dummy_position.png");
      const jdBlob = await jdRes.blob();
      const jdFile = new File([jdBlob], "dummy_position.png", { type: "image/png" });

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

            sessionStorage.setItem("interviewProfile", JSON.stringify({
              report_email: "debug@example.com",
              job_title: "AI Engineer",
              experience: "신입",
              education: "학사(4년제)",
              resume: resumeText || "특별한 이력 없음",
              job_description: "",
              job_image: compressedBase64,
              interview_mode: interviewMode
            }));
            localStorage.removeItem("interviewProfile");
            setStatusText("더미 데이터 설정 완료!");
            setImageInjectionStatus("pending");
            setBackendJobAnalysis(null);
            setPromptVariant("-");
            setProfileSummary({
              jobTitle: "AI Engineer",
              interviewMode,
              hasJobImage: true,
              jobDescriptionChars: 0,
              resumeChars: resumeText.length
            });
            addLog('SYS', 'Dummy data loaded into sessionStorage', {
              interview_mode: interviewMode,
              has_job_image: true,
              resume_chars: resumeText.length
            });
          }
        };
        if (event.target?.result) {
          img.src = event.target.result as string;
        }
      };
      reader.readAsDataURL(jdFile);
    } catch (error) {
      console.error("더미 데이터 로드 중 오류:", error);
      setStatusText("더미 데이터 로드 실패");
    }
  };

  return (
    <div className="flex h-screen bg-[#1e1e1e] text-white font-mono text-sm">
      {/* Left Panel: Controls & Status */}
      <div className="w-1/3 border-r border-gray-700 flex flex-col p-4 bg-[#252526]">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-xl font-bold text-blue-400">Techtree Agent Debugger</h1>
          <button
            onClick={loadDummyData}
            className="px-3 py-1 bg-gray-600 hover:bg-gray-500 text-xs rounded transition-colors"
          >
            ⚙️ 테스트 데이터 사용
          </button>
        </div>

        <div className="bg-[#1e1e1e] p-4 rounded-lg mb-4 border border-gray-700">
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-400">Status</span>
            <span className={`px-2 py-1 rounded text-xs ${isSessionActive ? 'bg-green-900 text-green-300' : 'bg-gray-700'}`}>
              {isSessionActive ? 'CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>
          <p className="text-lg font-semibold">{statusText}</p>
        </div>

        <div className="bg-[#1e1e1e] p-4 rounded-lg mb-4 border border-gray-700">
          <div className="flex justify-between items-center mb-3">
            <span className="text-gray-400">Interview Mode</span>
            <span className="rounded bg-black/30 px-2 py-1 text-xs text-gray-300">
              {interviewMode === "short" ? "빠른 연습" : "실전 연습"}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              disabled={isSessionActive}
              onClick={() => updateInterviewMode("short")}
              className={`rounded border px-3 py-2 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                interviewMode === "short"
                  ? "border-violet-400 bg-violet-900/50 text-violet-100"
                  : "border-gray-700 bg-black/20 text-gray-400 hover:border-gray-500"
              }`}
            >
              <p className="font-bold">빠른 연습</p>
              <p className="mt-1 text-xs opacity-75">7분 내외, 꼬리 질문 최소화</p>
            </button>
            <button
              type="button"
              disabled={isSessionActive}
              onClick={() => updateInterviewMode("long")}
              className={`rounded border px-3 py-2 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                interviewMode === "long"
                  ? "border-blue-400 bg-blue-900/50 text-blue-100"
                  : "border-gray-700 bg-black/20 text-gray-400 hover:border-gray-500"
              }`}
            >
              <p className="font-bold">실전 연습</p>
              <p className="mt-1 text-xs opacity-75">20분 내외, 깊이 있는 검증</p>
            </button>
          </div>
          <div className="mt-3 rounded bg-black/30 p-2 text-xs text-gray-300">
            <p className="text-gray-500">백엔드 프롬프트 variant</p>
            <p className="mt-1 break-words">{promptVariant}</p>
            <p className="mt-3 text-gray-500">주입된 reflection/policy</p>
            <p className="mt-1">
              reflection {guidelineSelection?.reflection_ids?.length || 0}개 / policy {guidelineSelection?.policy_ids?.length || 0}개
            </p>
            <p className="mt-1 break-words text-gray-500">
              {[...(guidelineSelection?.policy_ids || []), ...(guidelineSelection?.reflection_ids || [])].slice(0, 4).join(", ") || "없음"}
            </p>
          </div>
        </div>

        <div className="bg-[#1e1e1e] p-4 rounded-lg mb-4 border border-gray-700">
          <div className="flex justify-between items-center mb-3">
            <span className="text-gray-400">Realtime Image Test</span>
            <span className={`px-2 py-1 rounded text-xs ${
              imageInjectionStatus === "injected"
                ? 'bg-green-900 text-green-300'
                : imageInjectionStatus === "pending"
                  ? 'bg-yellow-900 text-yellow-300'
                  : 'bg-gray-700 text-gray-300'
            }`}>
              {imageInjectionStatus === "injected" ? "IMAGE INJECTED" : imageInjectionStatus === "pending" ? "IMAGE PENDING" : "NO IMAGE"}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs text-gray-300">
            <div className="rounded bg-black/30 p-2">
              <p className="text-gray-500">직무</p>
              <p className="truncate">{profileSummary?.jobTitle || "-"}</p>
            </div>
            <div className="rounded bg-black/30 p-2">
              <p className="text-gray-500">면접 모드</p>
              <p>{profileSummary?.interviewMode === "long" ? "실전 연습" : "빠른 연습"}</p>
            </div>
            <div className="rounded bg-black/30 p-2">
              <p className="text-gray-500">공고 이미지</p>
              <p>{profileSummary?.hasJobImage ? "있음" : "없음"}</p>
            </div>
            <div className="rounded bg-black/30 p-2">
              <p className="text-gray-500">공고 텍스트</p>
              <p>{profileSummary ? `${profileSummary.jobDescriptionChars}자` : "-"}</p>
            </div>
            <div className="rounded bg-black/30 p-2">
              <p className="text-gray-500">이력서</p>
              <p>{profileSummary ? `${profileSummary.resumeChars}자` : "-"}</p>
            </div>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-gray-500">
            기대 순서: response.create (initial greeting before image) → response.done → conversation.item.create (image after first response)
          </p>
        </div>

        <div className="bg-[#1e1e1e] p-4 rounded-lg mb-4 border border-gray-700">
          <div className="flex justify-between items-center mb-3">
            <span className="text-gray-400">Backend JD Analysis</span>
            <span className={`px-2 py-1 rounded text-xs ${
              backendJobAnalysis?.status === "image_analysis_failed"
                ? 'bg-red-900 text-red-300'
                : backendJobAnalysis?.status
                  ? 'bg-blue-900 text-blue-300'
                  : 'bg-gray-700 text-gray-300'
            }`}>
              {backendJobAnalysis?.status || "WAITING FOR START"}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs text-gray-300">
            <div className="rounded bg-black/30 p-2">
              <p className="text-gray-500">소스</p>
              <p>{backendJobAnalysis?.source || "-"}</p>
            </div>
            <div className="rounded bg-black/30 p-2">
              <p className="text-gray-500">분석 요약 길이</p>
              <p>{backendJobAnalysis?.summary ? `${backendJobAnalysis.summary.length}자` : "-"}</p>
            </div>
          </div>
          <pre className="mt-3 max-h-36 overflow-y-auto whitespace-pre-wrap rounded bg-black/30 p-3 text-xs leading-relaxed text-gray-300">
            {backendJobAnalysis?.summary || "Start WebRTC를 누르면 /api/interview/start 응답의 job_posting_analysis.summary가 여기에 표시됩니다."}
          </pre>
        </div>

        <div className="flex space-x-2 mb-6">
          <button
            onClick={startDebugSession}
            disabled={isSessionActive}
            className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 py-2 rounded font-bold"
          >
            Start WebRTC
          </button>
          <button
            onClick={endSession}
            disabled={!isSessionActive}
            className="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-50 py-2 rounded font-bold"
          >
            End Session
          </button>
        </div>

        <div className="flex-1 overflow-y-auto bg-[#1e1e1e] p-4 rounded-lg border border-gray-700">
          <h2 className="text-gray-400 mb-2 border-b border-gray-700 pb-1">Transcript / Event Summary</h2>
          <ul className="space-y-3 text-xs">
            {transcripts.map((t, idx) => (
              <li key={idx} className={
                t.role === 'ai' ? 'text-green-300' :
                  t.role === 'sys' ? 'text-purple-300 bg-purple-900/20 p-2 rounded' : 'text-blue-300'
              }>
                <strong>[{t.role.toUpperCase()}]</strong> {t.text}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Right Panel: Event Logs */}
      <div className="w-2/3 flex flex-col p-4 bg-[#1e1e1e]">
        <h2 className="text-gray-400 mb-2">Realtime Data Channel Logs</h2>
        <div className="flex-1 overflow-y-auto bg-[#000000] p-4 rounded-lg border border-gray-700 font-mono text-[13px] shadow-inner">
          {logs.map((log) => {
            let colorClass = 'text-gray-300';
            if (log.source === 'SYS') colorClass = 'text-yellow-400';
            if (log.source === 'OUT') colorClass = 'text-blue-400';
            if (log.source === 'IN') colorClass = 'text-green-400';
            if (log.source === 'TOOL') colorClass = 'text-purple-400';

            return (
              <div key={log.id} className="mb-3 border-b border-gray-800 pb-2">
                <div className="flex space-x-3 mb-1 opacity-80">
                  <span className="text-gray-500">[{log.timestamp}]</span>
                  <span className={`font-bold ${colorClass}`}>[{log.source}]</span>
                  <span className="font-semibold text-white">{log.event}</span>
                </div>
                {log.data !== undefined && (
                  <pre className="mt-1 pl-4 border-l-2 border-gray-700 text-gray-400 overflow-x-auto whitespace-pre-wrap break-words">
                    {JSON.stringify(log.data, null, 2)}
                  </pre>
                )}
              </div>
            )
          })}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
}
