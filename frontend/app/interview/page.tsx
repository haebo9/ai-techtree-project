"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";

interface JobSearchResult {
  company?: string;
  title?: string;
  url?: string;
  content?: string;
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
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [startTime, setStartTime] = useState<number | null>(null);
  const transcriptRef = useRef<{ role: string, text: string }[]>([]);
  const savedJobsRef = useRef<JobSearchResult[]>([]);

  // 1. 컴포넌트 마운트 시 WebRTC 직접 연결 시도
  useEffect(() => {
    // 상대방(AI)의 음성을 재생할 숨겨진 오디오 엘리먼트 생성
    const audioEl = document.createElement("audio");
    audioEl.autoplay = true;
    audioElRef.current = audioEl;

    const initWebRTC = async () => {
      try {
        setStatusText("서버에서 보안 토큰을 발급받고 있습니다...");

        // 1) 로컬 스토리지에서 사용자가 입력한 프로필 가져오기
        const savedProfile = localStorage.getItem("interviewProfile");
        const profileData = savedProfile ? JSON.parse(savedProfile) : {
          job_title: "직무 미상",
          education: "학사(4년제)",
          experience: "신입",
          resume: "정보 없음"
        };

        // 2) 우리 백엔드 API를 호출해 OpenAI 일회용 접속 토큰(ephemeral_token) 발급
        const res = await fetch("http://localhost:8000/api/interview/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: "test@example.com",
            job_title: profileData.job_title || "직무 미상",
            education: profileData.education || "학사(4년제)",
            experience: profileData.experience || "신입",
            resume: profileData.resume || "정보 없음",
            job_description: profileData.job_description || "",
            job_image: profileData.job_image || null
          })
        });

        if (!res.ok) throw new Error("토큰 발급 API 오류");
        const data = await res.json();
        const EPHEMERAL_KEY = data.ephemeral_token;
        setSessionId(data.session_id);

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
        streamRef.current = ms;
        pc.addTrack(ms.getTracks()[0]);
        // Push-To-Talk를 위해 기본 마이크 송출 차단
        ms.getAudioTracks()[0].enabled = false;

        // 4) 데이터 채널 열기 (이벤트를 주고받기 위함)
        const dc = pc.createDataChannel("oai-events");
        dcRef.current = dc;

        dc.addEventListener("open", () => {
          setStartTime(Date.now());
          
          // 이미지가 업로드된 경우, 초기 컨텍스트로 전달 (올바른 Realtime API 포맷 사용)
          if (profileData.job_image) {
            // "data:image/jpeg;base64,..." 그대로 사용
            const base64Data = profileData.job_image;
            
            dc.send(JSON.stringify({
              type: "conversation.item.create",
              item: {
                type: "message",
                role: "user",
                content: [
                  { 
                    type: "input_image", 
                    image_url: base64Data
                  },
                  { 
                    type: "input_text", 
                    text: "이 이미지는 제가 지원하고자 하는 채용 공고입니다. 이 내용을 바탕으로 맞춤형 면접 질문을 해주세요." 
                  }
                ]
              }
            }));
          }

          // VAD가 꺼져 있으므로 연결 직후 첫 인사 생성을 수동 요청
          dc.send(JSON.stringify({ type: "response.create" }));
        });

        dc.addEventListener("message", async (e) => {
          const realtimeEvent = JSON.parse(e.data);

          // --- 에이전틱 툴(Function Calling) 처리 ---
          if (realtimeEvent.type === "response.function_call_arguments.done") {
            const callId = realtimeEvent.call_id;
            const name = realtimeEvent.name;
            const args = JSON.parse(realtimeEvent.arguments);

            if (name === "search_job_postings") {
              setStatusText("🔍 최신 채용 정보를 검색 중입니다...");
              console.log("[Tool] 검색 요청:", args.query);

              try {
                // 백엔드 API 호출하여 검색 실행 (prefix 주의: /api/interview/tools/search_job)
                const res = await fetch("http://localhost:8000/api/interview/tools/search_job", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ query: args.query })
                });
                const searchData = await res.json();
                console.log("[Tool] 검색 결과 수신 완료", searchData.result);
                
                // 실제 검색 결과를 LLM 환각 방지를 위해 별도로 저장
                if (Array.isArray(searchData.result)) {
                  savedJobsRef.current = [...savedJobsRef.current, ...searchData.result];
                }

                // 검색 결과를 OpenAI Realtime API 컨텍스트에 추가
                dc.send(JSON.stringify({
                  type: "conversation.item.create",
                  item: {
                    type: "function_call_output",
                    call_id: callId,
                    output: JSON.stringify(searchData.result)
                  }
                }));

                // 결과를 바탕으로 AI에게 다시 말하도록 트리거
                dc.send(JSON.stringify({
                  type: "response.create"
                }));

              } catch (err) {
                console.error("검색 툴 실행 에러:", err);
              }
            }
          }

          // 텍스트 변환 기록(Transcript) 가로채기 -> 추후 DB 저장을 위해 배열에 푸시
          if (realtimeEvent.type === "response.audio_transcript.done") {
            transcriptRef.current.push({ role: "ai", text: realtimeEvent.transcript });
            console.log("[AI 답변]:", realtimeEvent.transcript);
          }
          if (realtimeEvent.type === "conversation.item.input_audio_transcription.completed") {
            transcriptRef.current.push({ role: "user", text: realtimeEvent.transcript });
            console.log("[내 답변]:", realtimeEvent.transcript);
          }

          // 파형 애니메이션을 위한 상태 업데이트
          if (realtimeEvent.type === "response.audio.delta") {
            setIsSpeaking(true);
            setStatusText("AI가 말하는 중...");
          }
          if (realtimeEvent.type === "response.done") {
            setIsSpeaking(false);
            setStatusText("🟢 스페이스바를 누른 채로 대답하세요.");
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
        setIsRecording(false);
        setStatusText("🟢 스페이스바를 누른 채로 대답하세요.");

      } catch (error) {
        console.error("WebRTC 연결 에러:", error);
        setStatusText("면접관 연결에 실패했습니다.");
      }
    };

    initWebRTC();

    return () => {
      pcRef.current?.close();
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
      }
    };
  }, []);

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
      setStatusText("답변을 분석 중입니다...");

      // 수동으로 오디오 버퍼 커밋 및 AI 응답 요청
      dcRef.current.send(JSON.stringify({ type: "input_audio_buffer.commit" }));
      dcRef.current.send(JSON.stringify({ type: "response.create" }));
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

  // 3. 면접 종료 시 대화 기록을 백엔드로 넘기고 결과창으로 이동
  const endInterview = async () => {
    if (!sessionId) {
      router.push("/result");
      return;
    }

    setIsEnding(true);

    try {
      setStatusText("대화 내용을 평가하고 있습니다...");
      
      // 시간 계산
      const endTime = Date.now();
      const diffMs = startTime ? endTime - startTime : 0;
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

      // 텍스트 변환된 transcriptRef.current 를 백엔드의 평가 노드로 전송합니다.
      // 더불어 환각 방지를 위해 수집된 실제 채용 공고(savedJobsRef.current)도 함께 보냅니다.
      const response = await fetch(`http://localhost:8000/api/interview/${sessionId}/end`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          transcripts: transcriptRef.current,
          saved_jobs: savedJobsRef.current
        })
      });
      const resultData = await response.json();
      
      localStorage.setItem("interviewResult", JSON.stringify(resultData));
      localStorage.setItem("interviewTranscripts", JSON.stringify(transcriptRef.current));
      localStorage.setItem("interviewDuration", durationStr);
      localStorage.setItem("interviewDate", dateStr);
      
      router.push("/result");
    } catch (err) {
      console.error("종료 에러:", err);
      router.push("/result");
    }
  };

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
