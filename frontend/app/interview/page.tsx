"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function InterviewPage() {
  const router = useRouter();
  
  const [isRecording, setIsRecording] = useState(false); 
  const [isSpeaking, setIsSpeaking] = useState(false);   
  const [statusText, setStatusText] = useState("마이크 권한을 확인 중입니다...");
  
  // WebRTC 및 Media 참조
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);
  const audioElRef = useRef<HTMLAudioElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  
  // 세션 정보 및 대화 기록(Transcript) 임시 저장소
  const [sessionId, setSessionId] = useState<string | null>(null);
  const transcriptRef = useRef<{role: string, text: string}[]>([]);

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
            experience: "신입",
            resume: "정보 없음"
        };

        // 2) 우리 백엔드 API를 호출해 OpenAI 일회용 접속 토큰(ephemeral_token) 발급
        const res = await fetch("http://localhost:8000/api/interview/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: "test@example.com",
            job_title: profileData.job_title,
            experience: profileData.experience,
            resume: profileData.resume
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

        // 4) 데이터 채널 열기 (이벤트를 주고받기 위함)
        const dc = pc.createDataChannel("oai-events");
        dcRef.current = dc;
        
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
                     // 백엔드 API 호출하여 검색 실행
                     const res = await fetch("http://localhost:8000/api/tools/search_job", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({ query: args.query })
                     });
                     const searchData = await res.json();
                     console.log("[Tool] 검색 결과 수신 완료", searchData.result);
                     
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
             setStatusText("스페이스바 또는 버튼을 눌러 답변하세요");
          }
        });

        // 5) WebRTC 통신 규약(SDP) 오퍼 생성 및 OpenAI로 전송
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const baseUrl = "https://api.openai.com/v1/realtime";
        const model = "gpt-4o-realtime-preview-2024-12-17";
        
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
        
        // 연결 성공!
        setIsRecording(true); 
        setStatusText("스페이스바 또는 버튼을 눌러 답변하세요");

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

  // 2. 마이크 ON/OFF (Mute 제어) 핸들러
  const toggleRecording = () => {
    if (streamRef.current) {
       // 오디오 트랙의 enabled 속성을 토글하여 Mute 처리
       const audioTrack = streamRef.current.getAudioTracks()[0];
       audioTrack.enabled = !audioTrack.enabled;
       setIsRecording(audioTrack.enabled);
       
       if (audioTrack.enabled) {
          setStatusText("듣고 있습니다...");
       } else {
          setStatusText("마이크 꺼짐 (잠시 멈춤)");
       }
    }
  };

  // 스페이스바 단축키
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === "Space") {
        e.preventDefault();
        if (e.repeat) return;
        toggleRecording();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isRecording]);

  // 3. 면접 종료 시 대화 기록을 백엔드로 넘기고 결과창으로 이동
  const endInterview = async () => {
     if (!sessionId) {
       router.push("/result");
       return;
     }
     
     try {
       setStatusText("대화 내용을 평가하고 있습니다...");
       // 텍스트 변환된 transcriptRef.current 를 백엔드의 평가 노드로 전송합니다.
       await fetch(`http://localhost:8000/api/interview/${sessionId}/end`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          // body: JSON.stringify({ transcripts: transcriptRef.current }) -> 이후 백엔드 업데이트 필요
       });
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
        <div className="flex items-center space-x-3 text-white">
          <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
          <span className="font-medium">면접 진행 중</span>
        </div>
        <button onClick={endInterview} className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-white rounded-lg text-sm font-medium transition-colors border border-neutral-700">
          면접 종료하기
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
            onClick={toggleRecording}
            className={`w-20 h-20 rounded-full flex items-center justify-center transition-all shadow-lg ${
              isRecording 
                ? 'bg-red-500 hover:bg-red-600 shadow-red-500/30' 
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
