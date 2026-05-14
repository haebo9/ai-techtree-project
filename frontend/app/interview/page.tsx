"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { apiPath } from "@/lib/api";
import { isInterviewClosingTranscript } from "@/lib/interviewClosing";

interface JobSearchResult {
  company?: string;
  title?: string;
  url?: string;
  content?: string;
  deadline_status?: string;
}

interface ToolTrace {
  tool_name?: string;
  query?: string;
  status?: string;
  reason?: string;
  raw_count?: number;
  filtered_count?: number;
}

interface TranscriptEntry {
  role: "user" | "ai";
  text: string;
  pending?: boolean;
}

let globalInterviewConnectionId = 0;

const USER_ENDING_PATTERNS = [
  /\bbye\b/i,
  /그만\s*(하겠습니다|할게요|하죠)?/,
  /(면접|인터뷰)(을|를)?\s*(끝내|마치|종료)/,
  /(끝|종료|마무리)\s*(하겠습니다|할게요|해주세요|해\s*주세요)/,
];

function isUserEndingTranscript(text: string) {
  const normalized = String(text || "").replace(/\s+/g, " ").trim();
  return USER_ENDING_PATTERNS.some((pattern) => pattern.test(normalized));
}

async function readApiError(response: Response, fallback: string): Promise<string> {
  try {
    const data = await response.json();
    if (typeof data?.detail === "string") return data.detail;
    if (typeof data?.message === "string") return data.message;
  } catch {
    // Ignore non-JSON error responses.
  }
  return fallback;
}

export default function InterviewPage() {
  const router = useRouter();

  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [statusText, setStatusText] = useState("마이크 권한을 확인 중입니다...");
  const [isEnding, setIsEnding] = useState(false);

  // WebRTC 및 Media 참조
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);
  const audioElRef = useRef<HTMLAudioElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // 세션 정보 및 대화 기록(Transcript) 임시 저장소
  const transcriptRef = useRef<TranscriptEntry[]>([]);
  const pendingUserTranscriptIndexesRef = useRef<number[]>([]);
  const savedJobsRef = useRef<JobSearchResult[]>([]);
  const toolTracesRef = useRef<ToolTrace[]>([]);
  const sessionIdRef = useRef<string | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const isEndingRef = useRef(false);
  const autoEndTimerRef = useRef<number | null>(null);
  const pendingAutoEndRef = useRef(false);
  const isSpeakingRef = useRef(false);
  const activeConnectionIdRef = useRef(0);
  const initStartTimerRef = useRef<number | null>(null);
  const initialResponseRequestedRef = useRef(false);
  const jobImagePendingRef = useRef(false);
  const jobImageInjectedRef = useRef(false);
  const interviewModeRef = useRef<"short" | "long">("long");
  const userRequestedEndRef = useRef(false);

  const createTimedResponseEvent = useCallback(() => {
    return {
      type: "response.create"
    };
  }, []);

  const cleanupRealtimeSession = useCallback(() => {
    if (initStartTimerRef.current) {
      window.clearTimeout(initStartTimerRef.current);
      initStartTimerRef.current = null;
    }
    if (autoEndTimerRef.current) {
      window.clearTimeout(autoEndTimerRef.current);
      autoEndTimerRef.current = null;
    }
    pendingAutoEndRef.current = false;
    pendingUserTranscriptIndexesRef.current = [];
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    dcRef.current?.close();
    dcRef.current = null;
    pcRef.current?.close();
    pcRef.current = null;
  }, []);

  const endInterview = useCallback(async () => {
    if (isEndingRef.current) return;
    isEndingRef.current = true;
    setIsEnding(true);
    cleanupRealtimeSession();

    const currentSessionId = sessionIdRef.current;
    if (!currentSessionId) {
      router.push("/complete");
      return;
    }

    try {
      setStatusText("대화 내용을 평가하고 있습니다...");
      
      // 시간 계산
      const endTime = Date.now();
      const diffMs = startTimeRef.current ? endTime - startTimeRef.current : 0;
      const minutes = Math.floor(diffMs / 60000);
      const seconds = Math.floor((diffMs % 60000) / 1000);
      const durationStr = `${minutes}분 ${seconds}초`;
      const dateStr = new Date().toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });

      // 텍스트 변환된 transcriptRef.current 는 평가와 reflection 생성에 사용합니다.
      // 이메일 리포트 발송을 위해 브라우저 세션에만 임시 보관하고 DB에는 저장하지 않습니다.
      // 더불어 환각 방지를 위해 수집된 실제 채용 공고(savedJobsRef.current)도 함께 보냅니다.
      const orderedTranscripts = transcriptRef.current
        .filter((item) => item.text.trim())
        .map(({ role, text }) => ({ role, text }));
      const response = await fetch(apiPath(`/interview/${currentSessionId}/end`), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          transcripts: orderedTranscripts,
          saved_jobs: savedJobsRef.current,
          tool_traces: toolTracesRef.current,
          interview_date: dateStr,
          interview_duration: durationStr
        })
      });
      if (!response.ok) throw new Error("면접 종료 API 오류");
      
      localStorage.removeItem("interviewTranscripts");
      sessionStorage.removeItem("interviewTranscriptsForEmail");
      sessionStorage.setItem("lastInterviewEndedAt", dateStr);
      
      router.push("/complete");
    } catch (err) {
      console.error("종료 에러:", err);
      router.push("/complete");
    }
  }, [cleanupRealtimeSession, router]);

  const scheduleAutoEndInterview = useCallback(() => {
    if (isEndingRef.current || autoEndTimerRef.current) return;
    if (!userRequestedEndRef.current) {
      const elapsedMs = startTimeRef.current ? Date.now() - startTimeRef.current : 0;
      const minimumMs = interviewModeRef.current === "short" ? 7 * 60 * 1000 : 15 * 60 * 1000;
      if (elapsedMs < minimumMs) {
        pendingAutoEndRef.current = false;
        setStatusText("면접이 계속 진행됩니다. 스페이스바를 누른 채로 대답하세요.");
        return;
      }
    }
    setStatusText("면접관의 마무리 멘트가 끝나면 리포트를 생성합니다...");
    autoEndTimerRef.current = window.setTimeout(() => {
      autoEndTimerRef.current = null;
      endInterview();
    }, 6500);
  }, [endInterview]);

  const markInterviewClosingDetected = useCallback(() => {
    if (isEndingRef.current) return;
    pendingAutoEndRef.current = true;
    setStatusText("면접관이 마무리 중입니다. 잠시만 기다려 주세요...");
    if (!isSpeakingRef.current) {
      pendingAutoEndRef.current = false;
      scheduleAutoEndInterview();
    }
  }, [scheduleAutoEndInterview]);

  // 1. 컴포넌트 마운트 시 WebRTC 직접 연결 시도
  useEffect(() => {
    let isEffectCancelled = false;
    
    const connectionId = ++globalInterviewConnectionId;
    activeConnectionIdRef.current = connectionId;
    initialResponseRequestedRef.current = false;
    jobImagePendingRef.current = false;
    jobImageInjectedRef.current = false;

    const isActiveConnection = () => (
      !isEffectCancelled && activeConnectionIdRef.current === connectionId
    );

    // 상대방(AI)의 음성을 재생할 숨겨진 오디오 엘리먼트 생성
    const audioEl = document.createElement("audio");
    audioEl.autoplay = true;
    audioElRef.current = audioEl;

    const initWebRTC = async () => {
      try {
        setStatusText("지원 정보와 모집중인 채용 공고를 분석해 면접을 준비 중입니다...");

        // 1) 로컬 스토리지에서 사용자가 입력한 프로필 가져오기
        const savedProfile = sessionStorage.getItem("interviewProfile") || localStorage.getItem("interviewProfile");
        const profileData = savedProfile ? JSON.parse(savedProfile) : {
          report_email: "test@example.com",
          job_title: "직무 미상",
          education: "학사(4년제)",
          experience: "신입",
          resume: "정보 없음"
        };
        interviewModeRef.current = profileData.interview_mode === "short" ? "short" : "long";
        jobImagePendingRef.current = Boolean(profileData.job_image);
        jobImageInjectedRef.current = false;

        // 2) 우리 백엔드 API를 호출해 OpenAI 일회용 접속 토큰(ephemeral_token) 발급
        const res = await fetch(apiPath("/interview/start"), {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: "test@example.com",
            report_email: profileData.report_email || "test@example.com",
            job_title: profileData.job_title || "직무 미상",
            education: profileData.education || "학사(4년제)",
            experience: profileData.experience || "신입",
            resume: profileData.resume || "정보 없음",
            job_description: profileData.job_description || "",
            job_image: profileData.job_image || null,
            interview_mode: profileData.interview_mode || "long"
          })
        });

        if (!res.ok) {
          const detail = await readApiError(res, "토큰 발급 API 오류");
          if (res.status === 401) {
            setStatusText("초대코드 인증이 필요합니다. 메인 화면에서 다시 입장해 주세요.");
            router.replace("/");
            return;
          }
          setStatusText(`면접 세션을 시작하지 못했습니다. (${res.status}) ${detail}`);
          console.warn("Interview start API failed:", { status: res.status, detail });
          return;
        }
        const data = await res.json();
        if (!isActiveConnection()) return;

        const EPHEMERAL_KEY = data.ephemeral_token;
        sessionIdRef.current = data.session_id;
        savedJobsRef.current = Array.isArray(data.prepared_jobs) ? data.prepared_jobs : [];

        setStatusText("면접관과 통신을 연결 중입니다...");

        // 2) WebRTC Peer Connection 객체 생성
        const pc = new RTCPeerConnection();
        pcRef.current = pc;

        // 상대방(OpenAI)에서 오디오 스트림이 들어오면 재생
        pc.ontrack = (e) => {
          if (audioElRef.current) {
            audioElRef.current.srcObject = e.streams[0];
          }
        };

        // 3) 내 마이크 스트림 가져오기 및 WebRTC에 추가
        const ms = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (!isActiveConnection()) {
          ms.getTracks().forEach(t => t.stop());
          return;
        }
        streamRef.current = ms;
        pc.addTrack(ms.getTracks()[0]);
        // Push-To-Talk를 위해 기본 마이크 송출 차단
        ms.getAudioTracks()[0].enabled = false;

        // 4) 데이터 채널 열기 (이벤트를 주고받기 위함)
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

          jobImageInjectedRef.current = true;
          jobImagePendingRef.current = false;

          dc.send(JSON.stringify({
            type: "conversation.item.create",
            item: {
              type: "message",
              role: "user",
              content: [
                {
                  type: "input_image",
                  image_url: profileData.job_image
                },
                {
                  type: "input_text",
                  text: "이 이미지는 제가 지원하고자 하는 채용 공고입니다. 이후 질문에서 이 내용을 참고해 주세요."
                }
              ]
            }
          }));
          console.log("[Realtime] 첫 응답 이후 공고 이미지 context를 주입했습니다.");
        };

        dc.addEventListener("open", () => {
          if (!isActiveConnection()) return;

          const openedAt = Date.now();
          startTimeRef.current = openedAt;

          // VAD가 꺼져 있으므로 연결 직후 첫 인사 생성을 수동 요청
          if (!initialResponseRequestedRef.current) {
            initialResponseRequestedRef.current = true;
            dc.send(JSON.stringify(createTimedResponseEvent()));
          }
        });

        dc.addEventListener("message", async (e) => {
          if (!isActiveConnection()) return;

          const realtimeEvent = JSON.parse(e.data);

          // 텍스트 변환 기록(Transcript) 가로채기 -> 추후 DB 저장을 위해 배열에 푸시
          if (realtimeEvent.type === "response.audio_transcript.done") {
            const aiText = realtimeEvent.transcript || "";
            transcriptRef.current.push({ role: "ai", text: aiText });
            console.log("[AI 답변]:", aiText);
            if (isInterviewClosingTranscript(aiText)) {
              markInterviewClosingDetected();
            }
          }
          if (realtimeEvent.type === "conversation.item.input_audio_transcription.completed") {
            const userText = realtimeEvent.transcript || "";
            const pendingIndex = pendingUserTranscriptIndexesRef.current.shift();
            if (
              pendingIndex !== undefined &&
              transcriptRef.current[pendingIndex]?.role === "user" &&
              transcriptRef.current[pendingIndex]?.pending
            ) {
              transcriptRef.current[pendingIndex] = { role: "user", text: userText };
            } else {
              transcriptRef.current.push({ role: "user", text: userText });
            }
            console.log("[내 답변]:", userText);
            if (isUserEndingTranscript(userText)) {
              userRequestedEndRef.current = true;
              markInterviewClosingDetected();
            }
          }

          // 파형 애니메이션을 위한 상태 업데이트
          if (realtimeEvent.type === "response.audio.delta") {
            isSpeakingRef.current = true;
            setIsSpeaking(true);
            setStatusText("AI가 말하는 중...");
          }
          if (realtimeEvent.type === "response.done") {
            isSpeakingRef.current = false;
            setIsSpeaking(false);
            injectJobImageContext();
            if (pendingAutoEndRef.current) {
              pendingAutoEndRef.current = false;
              scheduleAutoEndInterview();
              return;
            }
            if (!isEndingRef.current) {
              setStatusText("🟢 스페이스바를 누른 채로 대답하세요.");
            }
          }
        });

        // 5) WebRTC 통신 규약(SDP) 오퍼 생성 및 OpenAI로 전송
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const baseUrl = "https://api.openai.com/v1/realtime";
        // 백엔드에서 생성한 토큰의 모델과 프론트엔드의 요청 모델이 일치해야 합니다.
        const model = "gpt-realtime-mini-2025-12-15";

        const sdpResponse = await fetch(`${baseUrl}?model=${model}`, {
          method: "POST",
          body: offer.sdp,
          headers: {
            Authorization: `Bearer ${EPHEMERAL_KEY}`,
            "Content-Type": "application/sdp"
          },
        });

        if (!sdpResponse.ok) {
          const errorText = await sdpResponse.text();
          console.error("SDP Fetch Error:", errorText);
          throw new Error(`OpenAI SDP Error: ${errorText}`);
        }

        const answer = {
          type: "answer" as RTCSdpType,
          sdp: await sdpResponse.text(),
        };
        await pc.setRemoteDescription(answer);

        // 연결 성공!
        if (!isActiveConnection()) return;
        setIsRecording(false);
        setStatusText("🟢 스페이스바를 누른 채로 대답하세요.");

      } catch (error) {
        console.error("WebRTC 연결 에러:", error);
        setStatusText("면접관 연결에 실패했습니다.");
      }
    };

    initStartTimerRef.current = window.setTimeout(() => {
      initStartTimerRef.current = null;
      initWebRTC();
    }, 0);

    return () => {
      isEffectCancelled = true;
      activeConnectionIdRef.current = 0;
      initialResponseRequestedRef.current = false;
      jobImagePendingRef.current = false;
      jobImageInjectedRef.current = false;
      cleanupRealtimeSession();
    };
  }, [cleanupRealtimeSession, createTimedResponseEvent, markInterviewClosingDetected, router, scheduleAutoEndInterview]);

  // 2. 마이크 Push-To-Talk 핸들러
  const startRecording = useCallback(() => {
    if (streamRef.current && !isRecording && dcRef.current?.readyState === "open") {
      const audioTrack = streamRef.current.getAudioTracks()[0];
      audioTrack.enabled = true;
      setIsRecording(true);
      setStatusText("🔴 답변중... (답변 완료 후 손을 떼세요.)");
      // 잔여 버퍼 비우기
      dcRef.current.send(JSON.stringify({ type: "input_audio_buffer.clear" }));
    }
  }, [isRecording]);

  const stopRecording = useCallback(() => {
    if (streamRef.current && isRecording && dcRef.current?.readyState === "open") {
      const audioTrack = streamRef.current.getAudioTracks()[0];
      audioTrack.enabled = false;
      setIsRecording(false);
      setStatusText("답변을 전송 중입니다...");

      // 수동으로 오디오 버퍼 커밋 및 AI 응답 요청
      const pendingIndex = transcriptRef.current.length;
      transcriptRef.current.push({ role: "user", text: "", pending: true });
      pendingUserTranscriptIndexesRef.current.push(pendingIndex);
      dcRef.current.send(JSON.stringify({ type: "input_audio_buffer.commit" }));
      dcRef.current.send(JSON.stringify(createTimedResponseEvent()));
      setStatusText("면접관 답변을 기다리는 중입니다...");
    }
  }, [createTimedResponseEvent, isRecording]);

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

  const visualizerScale = isSpeaking ? "scale-110 animate-pulse bg-gradient-to-tr from-purple-600 to-indigo-500"
    : isRecording ? "scale-100 animate-pulse bg-gradient-to-tr from-red-500 to-pink-500"
      : "scale-100 bg-gradient-to-tr from-blue-600 to-indigo-500 hover:scale-105";

  return (
    <main className="min-h-screen bg-neutral-900 flex flex-col items-center justify-center p-4 relative">
      <div className="absolute top-0 w-full p-6 flex justify-between items-center z-10 max-w-5xl">
        <div className="flex items-center space-x-4">
          <div className="w-8 h-8 rounded-lg overflow-hidden border border-neutral-700">
            <Image src="/logo.png" alt="Logo" width={32} height={32} className="w-full h-full object-cover" priority />
          </div>
          <div className="flex items-center space-x-2 text-white">
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
            <span className="text-sm font-medium opacity-80">면접 진행 중</span>
          </div>
        </div>
        <button 
          onClick={endInterview} 
          disabled={isEnding}
          className={`px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-white rounded-lg text-sm font-medium transition-colors border border-neutral-700 ${isEnding ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          {isEnding ? "종료중" : "면접 종료하기"}
        </button>
      </div>

      <div className="flex-1 w-full max-w-5xl flex flex-col items-center justify-center">
        <div className="relative w-64 h-64 mb-16 flex items-center justify-center">
          <div className={`absolute inset-0 rounded-full blur-3xl opacity-30 transition-all duration-700 ${isSpeaking ? 'bg-purple-500 scale-125' : isRecording ? 'bg-red-500 scale-110' : 'bg-blue-500 scale-100'}`}></div>
          <div className={`w-40 h-40 rounded-full flex items-center justify-center relative z-10 transition-all duration-300 shadow-[0_0_50px_rgba(0,0,0,0.3)] ${visualizerScale}`}>
            <svg className="w-16 h-16 text-white/90" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {isSpeaking ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              )}
            </svg>
          </div>
        </div>
      </div>

      <div className="w-full max-w-3xl pb-10">
        <div className="bg-neutral-800/50 backdrop-blur-md border border-neutral-700 rounded-3xl p-6 flex flex-col items-center">
          <button
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            onTouchStart={startRecording}
            onTouchEnd={stopRecording}
            className={`w-20 h-20 rounded-full flex items-center justify-center transition-all shadow-lg select-none ${isRecording
              ? 'bg-red-500 shadow-red-500/50 scale-110'
              : 'bg-white hover:bg-gray-100 text-neutral-900'
              }`}
          >
            {isRecording ? (
              <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
            ) : (
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            )}
          </button>
          <p className="mt-6 text-neutral-400 text-sm font-medium tracking-wide">
            {statusText}
          </p>
        </div>
      </div>
    </main>
  );
}
