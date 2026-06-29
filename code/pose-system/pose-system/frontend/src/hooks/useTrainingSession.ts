import { useState, useRef, useCallback, useEffect } from "react";
import { message } from "antd";
import { createLearningWS } from "../services/api";
import { useAuthStore } from "../store/auth";
import type {
  StandardAngles, AngleDiff, LearningFeedback, LearningComplete,
} from "../types";

// ---------- Types ----------

interface UseTrainingSessionOptions {
  /** Action name to train */
  actionName: string;
  /** Called when session completes normally */
  onComplete?: (data: LearningComplete) => void;
  /** Called on WS or camera error */
  onError?: (msg: string) => void;
}

export interface TrainingSessionState {
  isSessionActive: boolean;
  currentView: string;
  standardAngles: StandardAngles;
  keyChecks: any[];
  instruction: string;
  diffs: AngleDiff[];
  feedbacks: LearningFeedback[];
  overallScore: number | null;
  bestScore: number;
  frameCount: number;
}

export interface TrainingSessionActions {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  startSession: () => Promise<boolean>;
  endSession: () => void;
  switchView: (view: string) => void;
}

// ---------- Hook ----------

export function useTrainingSession(
  options: UseTrainingSessionOptions
): [TrainingSessionState, TrainingSessionActions] {
  const { actionName, onComplete, onError } = options;

  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<number | null>(null);

  // State
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [currentView, setCurrentView] = useState("正面");
  const [standardAngles, setStandardAngles] = useState<StandardAngles>({});
  const [keyChecks, setKeyChecks] = useState<any[]>([]);
  const [instruction, setInstruction] = useState("");
  const [diffs, setDiffs] = useState<AngleDiff[]>([]);
  const [feedbacks, setFeedbacks] = useState<LearningFeedback[]>([]);
  const [overallScore, setOverallScore] = useState<number | null>(null);
  const [bestScore, setBestScore] = useState(0);
  const [frameCount, setFrameCount] = useState(0);

  // --- Camera ---
  const startCamera = useCallback(async (): Promise<boolean> => {
    if (!navigator.mediaDevices?.getUserMedia) {
      message.error("摄像头不可用，请使用 HTTPS 或 localhost");
      return false;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      return true;
    } catch {
      message.error("无法访问摄像头");
      return false;
    }
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  }, []);

  // --- WebSocket ---
  const closeWS = useCallback(() => {
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
    const socket = wsRef.current;
    if (socket) {
      socket.onmessage = null;
      socket.onclose = null;
      socket.onerror = null;
      if (socket.readyState === WebSocket.OPEN) socket.close();
      wsRef.current = null;
    }
  }, []);

  // Frame capture
  const captureAndSend = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const socket = wsRef.current;
    if (!video || !canvas || !socket || socket.readyState !== WebSocket.OPEN) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    try {
      socket.send(JSON.stringify({ type: "frame", data: canvas.toDataURL("image/jpeg", 0.7) }));
      setFrameCount(prev => prev + 1);
    } catch { /* ignore */ }
  }, []);

  // --- Start Session ---
  const startSession = useCallback(async (): Promise<boolean> => {
    const ok = await startCamera();
    if (!ok) return false;

    const token = useAuthStore.getState().token || "";
    const socket = createLearningWS(token);
    wsRef.current = socket;

    return new Promise(resolve => {
      socket.onopen = () => {
        socket.send(JSON.stringify({
          type: "start",
          action: actionName,
          view: "正面",
        }));
        setIsSessionActive(true);
        setFrameCount(0);
        setDiffs([]);
        setFeedbacks([]);
        setOverallScore(null);

        // Frame capture starts after session_ready response
        resolve(true);
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        switch (data.type) {
          case "session_ready":
            setStandardAngles(data.standard_angles || {});
            setKeyChecks(data.key_checks || []);
            setInstruction(data.instruction || "");
            setBestScore(0);
            // Start frame capture now that session is ready
            if (intervalRef.current) clearInterval(intervalRef.current);
            intervalRef.current = window.setInterval(() => {
              captureAndSend();
            }, 150);
            break;
          case "comparison":
            setDiffs(data.diffs || []);
            setFeedbacks(data.feedbacks || []);
            setOverallScore(data.overall_score);
            setBestScore(data.best_score || 0);
            break;
          case "view_switched":
            setCurrentView(data.view);
            setStandardAngles(data.standard_angles || {});
            setKeyChecks(data.key_checks || []);
            break;
          case "learning_complete":
            stopCamera();
            closeWS();
            setIsSessionActive(false);
            onComplete?.(data as LearningComplete);
            break;
          case "error":
            onError?.(data.message);
            break;
        }
      };

      socket.onerror = () => {
        onError?.("WebSocket 连接失败");
        setIsSessionActive(false);
        resolve(false);
      };

      socket.onclose = () => {
        setIsSessionActive(false);
      };
    });
  }, [actionName, startCamera, captureAndSend, closeWS, stopCamera, onComplete, onError]);

  // --- End Session ---
  const endSession = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "finish" }));
    }
  }, []);

  // --- Switch View ---
  const switchView = useCallback((view: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "switch_view", view }));
    }
  }, []);

  // --- Cleanup ---
  useEffect(() => {
    return () => {
      stopCamera();
      closeWS();
    };
  }, [stopCamera, closeWS]);

  const state: TrainingSessionState = {
    isSessionActive, currentView, standardAngles, keyChecks,
    instruction, diffs, feedbacks, overallScore, bestScore, frameCount,
  };

  const actions: TrainingSessionActions = {
    videoRef, canvasRef,
    startSession, endSession, switchView,
  };

  return [state, actions];
}
