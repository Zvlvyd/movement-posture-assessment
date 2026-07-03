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
  /** Initial view for the session (default: "正面"). Server will auto-fallback if unavailable. */
  initialView?: string;
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
  /** 自动完成触发标志（用于显示庆祝模态框） */
  autoCompleted: boolean;
  /** 用户关键点坐标 [[x,y], ...] 用于骨架叠加 */
  userKeypoints: number[][] | null;
  /** 各关键点置信度 [conf, ...] 用于骨架过滤 */
  userConfidences: number[] | null;
  /** YOLO 推理时帧的实际宽度 */
  frameWidth: number;
  /** YOLO 推理时帧的实际高度 */
  frameHeight: number;
  /** 当前会话阶段: waiting_for_body | body_confirmed | learning */
  sessionPhase: string;
  /** 动作次数计数（FSM 状态机计算） */
  repCount: number;
  /** 动作类型: "rep" 计数 / "hold" 计时 */
  exerciseType: string;
  /** FSM 当前状态 */
  fsmState: string;
  /** 静态保持类动作的累计保持时长（秒） */
  holdTime: number;
  /** 当前帧检测到的有效关键点数 */
  validKpCount: number;
}

export interface TrainingSessionActions {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  startSession: (viewOverride?: string, actionOverride?: string) => Promise<boolean>;
  endSession: () => void;
  switchView: (view: string) => void;
  /** 关闭自动完成模态框，触发 onComplete 回调 */
  confirmAutoComplete: () => void;
}

// ---------- Hook ----------

export function useTrainingSession(
  options: UseTrainingSessionOptions
): [TrainingSessionState, TrainingSessionActions] {
  const { actionName, initialView, onComplete, onError } = options;

  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<number | null>(null);
  // 存储自动完成结果，在用户关闭模态框后才触发 onComplete
  const resultRef = useRef<LearningComplete | null>(null);

  // State
  const [isSessionActive, setIsSessionActive] = useState(false);
  const defaultViewRef = useRef(initialView || "正面");
  // Keep ref in sync (useEffect avoids render-phase ref update issues)
  defaultViewRef.current = initialView || "正面";
  const [currentView, setCurrentView] = useState(defaultViewRef.current);
  const [standardAngles, setStandardAngles] = useState<StandardAngles>({});
  const [keyChecks, setKeyChecks] = useState<any[]>([]);
  const [instruction, setInstruction] = useState("");
  const [diffs, setDiffs] = useState<AngleDiff[]>([]);
  const [feedbacks, setFeedbacks] = useState<LearningFeedback[]>([]);
  const [overallScore, setOverallScore] = useState<number | null>(null);
  const [bestScore, setBestScore] = useState(0);
  const [frameCount, setFrameCount] = useState(0);
  const [autoCompleted, setAutoCompleted] = useState(false);
  const [userKeypoints, setUserKeypoints] = useState<number[][] | null>(null);
  const [userConfidences, setUserConfidences] = useState<number[] | null>(null);
  const [frameWidth, setFrameWidth] = useState(640);
  const [frameHeight, setFrameHeight] = useState(480);
  const [sessionPhase, setSessionPhase] = useState("waiting_for_body");
  const [exerciseType, setExerciseType] = useState("rep");
  const [repCount, setRepCount] = useState(0);
  const [holdTime, setHoldTime] = useState(0);
  const [fsmState, setFsmState] = useState("");
  const [validKpCount, setValidKpCount] = useState(0);

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
      socket.send(JSON.stringify({ type: "frame", data: canvas.toDataURL("image/jpeg", 0.6) }));
      setFrameCount(prev => prev + 1);
    } catch { /* ignore */ }
  }, []);

  // --- Start Session ---
  const startSession = useCallback(async (viewOverride?: string, actionOverride?: string): Promise<boolean> => {
    const ok = await startCamera();
    if (!ok) return false;

    const token = useAuthStore.getState().token || "";
    const socket = createLearningWS(token);
    wsRef.current = socket;

    const view = viewOverride || defaultViewRef.current;
    const action = actionOverride || actionName;

    return new Promise(resolve => {
      socket.onopen = () => {
        socket.send(JSON.stringify({
          type: "start",
          action: action,
          view: view,
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
            setSessionPhase("waiting_for_body");
            setUserKeypoints(null);
            setUserConfidences(null);
            if (data.exercise_type) setExerciseType(data.exercise_type);
            if (data.rep_count !== undefined) setRepCount(data.rep_count);
            if (data.hold_time !== undefined) setHoldTime(data.hold_time);
            if (data.fsm_state !== undefined) setFsmState(data.fsm_state);
            // 同步服务器实际使用的视角（可能因 fallback 与客户端请求不同）
            if (data.current_view) setCurrentView(data.current_view);
            // Start frame capture now that session is ready
            if (intervalRef.current) clearInterval(intervalRef.current);
            intervalRef.current = window.setInterval(() => {
              captureAndSend();
            }, 200);  // 200ms = 5fps，与 FMS 对齐
            break;
          case "comparison":
            setDiffs(data.diffs || []);
            setFeedbacks(data.feedbacks || []);
            setOverallScore(data.overall_score);
            setBestScore(data.best_score || 0);
            if (data.user_keypoints !== undefined) setUserKeypoints(data.user_keypoints);
            if (data.user_confidences !== undefined) setUserConfidences(data.user_confidences);
            if (data.frame_width) setFrameWidth(data.frame_width);
            if (data.frame_height) setFrameHeight(data.frame_height);
            if (data.session_phase) setSessionPhase(data.session_phase);
            if (data.exercise_type) setExerciseType(data.exercise_type);
            if (data.rep_count !== undefined) setRepCount(data.rep_count);
            if (data.hold_time !== undefined) setHoldTime(data.hold_time);
            if (data.fsm_state !== undefined) setFsmState(data.fsm_state);
            if (data.valid_kp_count !== undefined) setValidKpCount(data.valid_kp_count);
            break;
          case "body_confirmed":
            setSessionPhase(data.session_phase || "body_confirmed");
            setInstruction(data.message || "已确认人体，请开始动作");
            break;
          case "view_switched":
            setCurrentView(data.view);
            setStandardAngles(data.standard_angles || {});
            setKeyChecks(data.key_checks || []);
            setSessionPhase("waiting_for_body");
            setUserKeypoints(null);
            setUserConfidences(null);
            break;
          case "learning_complete":
            stopCamera();
            closeWS();
            setIsSessionActive(false);
            if (data.auto_triggered) {
              // 自动完成：先展示庆祝模态框，用户点击后再回调
              setAutoCompleted(true);
              resultRef.current = data as LearningComplete;
            } else {
              // 手动完成：直接回调
              onComplete?.(data as LearningComplete);
            }
            break;
          case "error":
            // 错误时清理资源
            stopCamera();
            closeWS();
            setIsSessionActive(false);
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

  // --- Confirm Auto Complete ---
  const confirmAutoComplete = useCallback(() => {
    setAutoCompleted(false);
    if (resultRef.current) {
      onComplete?.(resultRef.current);
      resultRef.current = null;
    }
  }, [onComplete]);

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
    autoCompleted, userKeypoints, userConfidences, frameWidth, frameHeight, sessionPhase,
    repCount, fsmState, exerciseType, holdTime, validKpCount,
  };

  const actions: TrainingSessionActions = {
    videoRef, canvasRef,
    startSession, endSession, switchView,
    confirmAutoComplete,
  };

  return [state, actions];
}
