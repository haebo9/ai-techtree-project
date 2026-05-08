"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

interface LogEntry {
  id: number;
  timestamp: string;
  source: 'IN' | 'OUT' | 'SYS' | 'TOOL';
  event: string;
  data?: any;
}

let logIdCounter = 0;

export default function DebugPage() {
  const router = useRouter();

  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [statusText, setStatusText] = useState("대기 중...");
  const [logs, setLogs] = useState<LogEntry[]>([]);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);
  const audioElRef = useRef<HTMLAudioElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const logsEndRef = useRef<HTMLDivElement | null>(null);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [transcripts, setTranscripts] = useState<{ id: string, role: string, text: string }[]>([]);

  const addLog = (source: 'IN' | 'OUT' | 'SYS' | 'TOOL', event: string, data?: any) => {
    setLogs(prev => [...prev, {
      id: logIdCounter++,
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

  const startDebugSession = async () => {
    if (pcRef.current) return;

    addLog('SYS', 'Init WebRTC Debug Session');
    const audioEl = document.createElement("audio");
    audioEl.autoplay = true;
    audioElRef.current = audioEl;

    try {
      setStatusText("토큰 발급 중...");
      addLog('SYS', 'Fetching Ephemeral Token from /api/interview/start');

      const savedProfile = localStorage.getItem("interviewProfile");
      const profileData = savedProfile ? JSON.parse(savedProfile) : {
        job_title: "직무 미상",
        education: "학사(4년제)",
        experience: "신입",
        resume: "정보 없음"
      };

      const res = await fetch("http://localhost:8000/api/interview/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "debug@example.com",
          job_title: profileData.job_title || "직무 미상",
          education: profileData.education || "학사(4년제)",
          experience: profileData.experience || "신입",
          resume: profileData.resume || "정보 없음"
        })
      });

      if (!res.ok) throw new Error("토큰 발급 API 오류");
      const data = await res.json();
      const EPHEMERAL_KEY = data.ephemeral_token;
      setSessionId(data.session_id);
      addLog('SYS', 'Token Received', { session_id: data.session_id });

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

      dc.addEventListener("open", () => {
        addLog('SYS', 'Data Channel Opened');
        dc.send(JSON.stringify({ type: "response.create" }));
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
              const toolRes = await fetch("http://localhost:8000/api/interview/tools/search_job", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: args.query })
              });
              const searchData = await toolRes.json();
              const t2 = Date.now();

              addLog('TOOL', `Search Tool Completed (${t2 - t1}ms)`, searchData);

              // 검색 결과를 좌측 요약 패널에도 예쁘게 표시
              setTranscripts(prev => [...prev, {
                id: `sys-${Date.now()}`,
                role: "sys",
                text: `[🔍 Tavily 검색 완료] ${searchData.result}`
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

            } catch (err: any) {
              addLog('TOOL', 'Tool Execution Error', { error: err.message });
            }
          }
        }

        if (realtimeEvent.type === "conversation.item.created") {
          const item = realtimeEvent.item;
          if (item.role === "user") {
            // 유저 답변 시작 시 플레이스홀더 생성 (나중에 텍스트가 도착하면 업데이트)
            setTranscripts(prev => [...prev, { id: item.id, role: "user", text: "(음성 인식 중...)" }]);
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
          setIsSpeaking(true);
          setStatusText("AI 발화 중...");
        }
        if (realtimeEvent.type === "response.done") {
          setIsSpeaking(false);
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

    } catch (error: any) {
      addLog('SYS', 'Connection Error', { error: error.message });
      setStatusText("오류 발생");
    }
  };

  const endSession = () => {
    pcRef.current?.close();
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
    }
    addLog('SYS', 'Session Ended manually');
    setStatusText("종료됨");
  };

  const startRecording = () => {
    if (streamRef.current && !isRecording && dcRef.current?.readyState === "open") {
      const audioTrack = streamRef.current.getAudioTracks()[0];
      audioTrack.enabled = true;
      setIsRecording(true);
      setStatusText("🔴 답변 완료 후 손을 떼세요");
      dcRef.current.send(JSON.stringify({ type: "input_audio_buffer.clear" }));
      addLog('SYS', 'Push-To-Talk: Microphone ON');
    }
  };

  const stopRecording = () => {
    if (streamRef.current && isRecording && dcRef.current?.readyState === "open") {
      const audioTrack = streamRef.current.getAudioTracks()[0];
      audioTrack.enabled = false;
      setIsRecording(false);
      setStatusText("답변 제출 중...");

      dcRef.current.send(JSON.stringify({ type: "input_audio_buffer.commit" }));
      dcRef.current.send(JSON.stringify({ type: "response.create" }));
      addLog('SYS', 'Push-To-Talk: Microphone OFF, Buffer Committed');
    }
  };

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
  }, [isRecording]);

  return (
    <div className="flex h-screen bg-[#1e1e1e] text-white font-mono text-sm">
      {/* Left Panel: Controls & Status */}
      <div className="w-1/3 border-r border-gray-700 flex flex-col p-4 bg-[#252526]">
        <h1 className="text-xl font-bold mb-4 text-blue-400">Techtree Agent Debugger</h1>

        <div className="bg-[#1e1e1e] p-4 rounded-lg mb-4 border border-gray-700">
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-400">Status</span>
            <span className={`px-2 py-1 rounded text-xs ${isRecording ? 'bg-green-900 text-green-300' : 'bg-gray-700'}`}>
              {isRecording ? 'CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>
          <p className="text-lg font-semibold">{statusText}</p>
        </div>

        <div className="flex space-x-2 mb-6">
          <button
            onClick={startDebugSession}
            disabled={isRecording}
            className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 py-2 rounded font-bold"
          >
            Start WebRTC
          </button>
          <button
            onClick={endSession}
            disabled={!isRecording}
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
                {log.data && (
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