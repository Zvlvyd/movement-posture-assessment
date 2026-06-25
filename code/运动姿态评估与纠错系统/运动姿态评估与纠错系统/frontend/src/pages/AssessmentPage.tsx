import { useState, useRef, useEffect, useCallback } from "react";
import { Card, Button, Typography, Tag, Progress, message, Space, Spin, Result, Steps } from "antd";
import {
  CameraOutlined, ExperimentOutlined, ArrowRightOutlined,
  ForwardOutlined, CheckCircleOutlined, LoadingOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import MovementDemo from "../components/MovementDemo";
import { playStartBeep, playEndBeep, playCountdownBeep, playFinalBeep } from "../utils/audio";
import { getAssessmentItem, type AssessmentItem, type MovementStep } from "../config/assessmentSteps";

interface Movement {
  index: number;
  name: string;
  instruction: string;
  duration_hint: string;
}

const SKELETON: [number, number][] = [
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16]
];

type Phase = "idle" | "connecting" | "preparing" | "countdown" | "running" | "between_steps" | "movement_done" | "done";

export default function AssessmentPage() {
  const navigate = useNavigate();
  const token = useAuthStore(s => s.token);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const intervalRef = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);
  const phaseRef = useRef<Phase>("idle");
  const currentStepRef = useRef(0);
  const currentIdxRef = useRef(-1);

  const [stream, setStream] = useState<MediaStream | null>(null);
  const [movements, setMovements] = useState<Movement[]>([]);
  const [currentIdx, setCurrentIdx] = useState(-1);
  const [phase, setPhase] = useState<Phase>("idle");
  const [angles, setAngles] = useState<Record<string, number>>({});
  const [plateau, setPlateau] = useState(false);
  const [guidance, setGuidance] = useState("");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [countdown, setCountdown] = useState(0);

  // 子步骤追踪
  const [assessmentItem, setAssessmentItem] = useState<AssessmentItem | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [transitionHint, setTransitionHint] = useState("");

  useEffect(() => { phaseRef.current = phase; }, [phase]);
  useEffect(() => { currentStepRef.current = currentStep; }, [currentStep]);
  useEffect(() => { currentIdxRef.current = currentIdx; }, [currentIdx]);

  // ─── 骨架绘制 ───────────────────────────────────────
  const drawSkeleton = useCallback((keypointsList: any[]) => {
    const canvas = overlayCanvasRef.current;
    if (!canvas || !keypointsList?.length) return;
    const video = videoRef.current;
    if (!video?.videoWidth) return;

    const rect = canvas.getBoundingClientRect();
    const displayW = rect.width || video.videoWidth || 640;
    const displayH = rect.height || video.videoHeight || 480;
    if (displayW === 0 || displayH === 0) return;

    if (canvas.width !== displayW || canvas.height !== displayH) {
      canvas.width = displayW;
      canvas.height = displayH;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const scaleX = displayW / (video.videoWidth || 640);
    const scaleY = displayH / (video.videoHeight || 480);

    for (const person of keypointsList) {
      const kps = person.keypoints || [];
      const confs = person.confidences || Array(kps.length).fill(1);
      if (kps.length < 17) continue;
      ctx.strokeStyle = "#00ff88"; ctx.lineWidth = 2;
      for (const [i, j] of SKELETON) {
        if (i < kps.length && j < kps.length && confs[i] > 0.3 && confs[j] > 0.3) {
          const [x1, y1] = kps[i]; const [x2, y2] = kps[j];
          if (x1 > 0 && y1 > 0 && x2 > 0 && y2 > 0) {
            ctx.beginPath();
            ctx.moveTo(x1 * scaleX, y1 * scaleY);
            ctx.lineTo(x2 * scaleX, y2 * scaleY);
            ctx.stroke();
          }
        }
      }
      for (let i = 0; i < kps.length; i++) {
        if (confs[i] > 0.3) {
          const [x, y] = kps[i];
          if (x > 0 && y > 0) {
            ctx.fillStyle = "#ff4466";
            ctx.beginPath();
            ctx.arc(x * scaleX, y * scaleY, 4, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
    }
  }, []);

  // ─── 清理 ───────────────────────────────────────────
  const cleanup = useCallback(() => {
    clearInterval(intervalRef.current);
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
    setStream(null);
  }, []);

  useEffect(() => () => cleanup(), [cleanup]);

  // ─── callback ref ──────────────────────────────────
  const videoCallbackRef = useCallback((el: HTMLVideoElement | null) => {
    (videoRef as React.MutableRefObject<HTMLVideoElement | null>).current = el;
    if (el && stream) el.srcObject = stream;
  }, [stream]);

  const startCamera = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      message.error("摄像头不可用，请使用 localhost 或 HTTPS 访问");
      return false;
    }
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" }
      });
      streamRef.current = s;
      setStream(s);
      return true;
    } catch (e: any) {
      message.error("无法访问摄像头: " + (e.message || ""));
      return false;
    }
  }, []);

  // ─── 帧捕获 ─────────────────────────────────────────
  const startFrameCapture = useCallback(() => {
    clearInterval(intervalRef.current);
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video || !video.videoWidth) return false;
    const ctx = canvas.getContext("2d");
    if (!ctx) return false;
    intervalRef.current = window.setInterval(() => {
      if (!video.videoWidth) return;
      if (wsRef.current?.readyState !== WebSocket.OPEN) return;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);
      const b64 = canvas.toDataURL("image/jpeg", 0.6);
      wsRef.current.send(JSON.stringify({ type: "frame", data: b64 }));
    }, 150);
    return true;
  }, []);

  // ─── 倒计时（每项评估开始前） ──────────────────────
  const startCountdown = useCallback(() => {
    setCountdown(3);
    setPhase("countdown");
    let tick = 3;
    const timer = setInterval(() => {
      tick--;
      if (tick <= 0) {
        clearInterval(timer);
        playStartBeep();
        setCountdown(0);
        setPhase("running");
        // 延迟启动帧捕获，等待 React 完成渲染（video 从 visibility:hidden 变为 visible）
        setTimeout(() => startFrameCapture(), 100);
      } else {
        playCountdownBeep();
        setCountdown(tick);
      }
    }, 1000);
  }, [startFrameCapture]);

  // ─── 推进到下一步（步骤间） ────────────────────────
  const advanceStep = useCallback(() => {
    if (!assessmentItem) return;
    const nextStep = currentStep + 1;
    if (nextStep >= assessmentItem.steps.length) {
      // 所有步骤完成 → 当前评估项完成
      playEndBeep();
      setTransitionHint("");
      setPhase("movement_done");
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "movement_done" }));
      }
    } else {
      // 进入下一步骤
      playEndBeep();
      const step = assessmentItem.steps[nextStep];
      setCurrentStep(nextStep);
      setAngles({});
      setPlateau(false);
      setGuidance(step.instruction);
      setTransitionHint("");
      setPhase("running"); // 直接进入运行态，无需再倒计时
    }
  }, [assessmentItem, currentStep]);

  // ─── 开始评估 / WS ─────────────────────────────────
  const startAssessment = useCallback(async () => {
    setError("");
    setPhase("connecting");

    const ok = await startCamera();
    if (!ok) { setPhase("idle"); return; }

    if (!token) {
      setError("请先登录");
      setPhase("idle");
      return;
    }

    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${wsProtocol}://${window.location.host}/api/assessment/ws?token=${token}`;
    console.log("[Assessment] Connecting to:", wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[Assessment] WS connected");
      ws.send(JSON.stringify({ type: "start" }));
      startFrameCapture();
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        console.log("[Assessment] WS msg:", msg.type);
        if (msg.type === "assessment_started") {
          setMovements(msg.movements || []);
        } else if (msg.type === "movement_ready") {
          // 新评估项开始
          setCurrentIdx(msg.index);
          setCurrentStep(0);
          setAngles({});
          setPlateau(false);
          setTransitionHint("");
          setGuidance(msg.instruction || "");

          // 加载前端子步骤配置
          const item = getAssessmentItem(msg.index);
          setAssessmentItem(item || null);
          setPhase("preparing");
        } else if (msg.type === "angles_update") {
          if (phaseRef.current !== "running" && phaseRef.current !== "between_steps") {
            console.log("[Assessment] angles_update dropped, phase:", phaseRef.current);
            return;
          }
          // 过滤：仅展示当前步骤关注的关节角度
          const item = getAssessmentItem(currentIdxRef.current);
          const step = item?.steps[currentStepRef.current];
          if (step?.highlightAngles?.length) {
            const filtered: Record<string, number> = {};
            for (const key of step.highlightAngles) {
              if (msg.angles && msg.angles[key] !== undefined) {
                filtered[key] = msg.angles[key];
              }
            }
            setAngles(Object.keys(filtered).length > 0 ? filtered : (msg.angles || {}));
          } else {
            setAngles(msg.angles || {});
          }
          setPlateau(msg.plateau_detected);
          if (msg.keypoints) drawSkeleton(msg.keypoints);
        } else if (msg.type === "movement_completed") {
          // 后端通知当前评估项完成
          setPhase("movement_done");
        } else if (msg.type === "assessment_complete") {
          playFinalBeep();
          setResult(msg);
          setPhase("done");
          cleanup();
        } else if (msg.type === "error") {
          message.error(msg.message);
        }
      } catch (e) {
        console.error("[Assessment] Parse error:", e);
      }
    };

    ws.onerror = (e) => {
      console.error("[Assessment] WS error:", e);
      setError("WebSocket 连接失败，请检查后端服务是否启动");
      setPhase("idle");
    };

    ws.onclose = (e) => {
      console.log("[Assessment] WS closed:", e.code, e.reason);
      if (phaseRef.current !== "done" && phaseRef.current !== "idle") {
        if (e.code !== 1000 && e.code !== 1005) {
          setError((prev) => prev || `WebSocket 断开 (code: ${e.code})`);
          setPhase("idle");
        }
      }
    };
  }, [token, startCamera, cleanup, drawSkeleton, startFrameCapture]);

  // ─── 跳过当前步骤 ──────────────────────────────────
  const skipStep = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "movement_done" }));
    }
    setAngles({});
    setTransitionHint("");
    setPhase("movement_done");
  }, []);

  const finishAssessment = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "finish" }));
    }
  }, []);

  // ─── 派生 ───────────────────────────────────────────
  const itemProgress = movements.length > 0 ? Math.round(((currentIdx + 1) / movements.length) * 100) : 0;
  const currentItem = assessmentItem;
  const currentStepData: MovementStep | undefined = currentItem?.steps[currentStep];
  const stepProgressPercent = currentItem ? Math.round(((currentStep + 1) / currentItem.steps.length) * 100) : 0;

  // ─── 完成页 ─────────────────────────────────────────
  if (phase === "done" && result) {
    return (
      <div style={{ padding: 24, maxWidth: 700, margin: "0 auto" }}>
        <Result
          status="success" title="评估完成"
          subTitle={`综合评分 ${result.overall_score ?? "N/A"} / 100  风险等级: ${result.risk_level}`}
          extra={[
            <Button type="primary" key="report" onClick={() => navigate(`/assessment/report/${result.record_id}`, { state: { result } })}>查看详细报告</Button>,
            <Button key="retry" onClick={() => { setResult(null); setPhase("idle"); setCurrentIdx(-1); setCurrentStep(0); }}>重新评估</Button>,
          ]}
        />
      </div>
    );
  }

  // ─── 辅助渲染 ──────────────────────────────────────
  const showVideo = phase !== "idle" && phase !== "done";
  const videoVisible = phase === "running" || phase === "between_steps";
  const showDemo = phase === "preparing" || phase === "countdown";
  const showRunningUI = phase === "running" || phase === "between_steps" || phase === "movement_done";

  // 查找下一个评估项（用于 movement_done 阶段的预告）
  const nextItem = phase === "movement_done" ? getAssessmentItem(currentIdx + 1) : null;

  return (
    <div style={{ maxWidth: 750, margin: "0 auto" }}>
      <Card title={<Space><ExperimentOutlined />体态评估</Space>}>
        {/* ── 空闲 ──────────────────────────────────── */}
        {phase === "idle" && !error && (
          <div style={{ textAlign: "center", padding: 24 }}>
            <CameraOutlined style={{ fontSize: 48, color: "#4ECDC4", marginBottom: 16 }} />
            <Typography.Title level={4}>准备开始体态评估</Typography.Title>
            <Typography.Paragraph>通过摄像头采集 5 组引导动作，每组包含多个步骤，全程约 2-3 分钟。</Typography.Paragraph>
            <Typography.Paragraph type="secondary">请确保处于光线充足的环境，全身可见。每一步都会有示范和语音引导。</Typography.Paragraph>
            <Button type="primary" size="large" icon={<CameraOutlined />} onClick={startAssessment}>开启摄像头，开始评估</Button>
          </div>
        )}

        {/* ── 连接中 ────────────────────────────────── */}
        {phase === "connecting" && (
          <div style={{ textAlign: "center", padding: 48 }}>
            <Spin size="large" />
            <Typography.Paragraph style={{ marginTop: 16 }}>正在连接摄像头和服务器...</Typography.Paragraph>
          </div>
        )}

        {/* ── 视频区域 — 始终保留在 DOM 中，isolation:isolate 确保 canvas 在 video 上方 ── */}
        {showVideo && (
          <div style={{
            position: "relative",
            width: "100%",
            background: "#000",
            borderRadius: 8,
            overflow: "hidden",
            isolation: "isolate",
          }}>
            <video ref={videoCallbackRef} autoPlay playsInline muted style={{
              width: "100%", borderRadius: 8, background: "#000",
              position: "relative", zIndex: 1,
            }} />
            <canvas ref={overlayCanvasRef} style={{
              position: "absolute", top: 0, left: 0,
              width: "100%", height: "100%", borderRadius: 8,
              pointerEvents: "none", zIndex: 10,
            }} />
            <canvas ref={canvasRef} style={{ display: "none" }} />
          </div>
        )}

        {/* ══════════════════════════════════════════════
            ── 项目进度条（始终显示在评估过程中） ──
            ══════════════════════════════════════════════ */}
        {phase !== "idle" && phase !== "connecting" && phase !== "done" && movements.length > 0 && (
          <>
            <Progress percent={itemProgress} style={{ marginBottom: 8 }} />
            <div style={{ marginBottom: 12 }}>
              {movements.map((m, i) => (
                <Tag key={i} color={i < currentIdx ? "success" : i === currentIdx ? "processing" : "default"}>
                  {i + 1}. {m.name}
                </Tag>
              ))}
            </div>
          </>
        )}

        {/* ── 步骤进度条（当前评估项内的子步骤） ──────── */}
        {currentItem && currentItem.steps.length > 1 && showDemo && (
          <div style={{ marginBottom: 8 }}>
            <Steps
              size="small"
              current={currentStep}
              items={currentItem.steps.map((s, i) => ({
                title: i < currentStep ? '✓' : s.name,
                status: i < currentStep ? 'finish' : i === currentStep ? 'process' : 'wait',
              }))}
            />
          </div>
        )}

        {/* ══════════════════════════════════════════════
            ── 示范 + 准备阶段 ──
            ══════════════════════════════════════════════ */}
        {showDemo && currentItem && currentStepData && (
          <div>
            <MovementDemo
              movementName={currentItem.name}
              stepName={currentStepData.name}
              instruction={currentStepData.instruction}
              stepIndex={currentStep + 1}
              totalSteps={currentItem.steps.length}
              durationHint={currentItem.durationHint}
              countdown={phase === "countdown" ? countdown : 0}
              onCountdownEnd={() => {}}
              imageUrl={currentStepData.imageUrl}
              videoUrl={currentStepData.videoUrl}
            />
            {phase === "preparing" && (
              <div style={{ textAlign: "center", marginTop: 4 }}>
                <Button type="primary" size="large" icon={<ArrowRightOutlined />} onClick={startCountdown}>
                  准备好了，开始检测
                </Button>
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════
            ── 检测运行中 ──
            ══════════════════════════════════════════════ */}
        {showRunningUI && currentIdx >= 0 && currentItem && (
          <>
            {/* 步骤进度 */}
            {currentItem.steps.length > 1 && (
              <Steps
                size="small"
                current={currentStep}
                style={{ marginBottom: 8 }}
                items={currentItem.steps.map((s, i) => ({
                  title: s.name,
                  status: i < currentStep ? 'finish' : i === currentStep ? 'process' : 'wait',
                }))}
              />
            )}

            {/* 过渡提示 */}
            {transitionHint && (
              <div style={{
                textAlign: "center", padding: "8px 0", marginBottom: 8,
                background: "#fff7e6", borderRadius: 8, border: "1px solid #ffd591",
                animation: "fadeInUp 0.4s ease-out",
              }}>
                <Typography.Text strong style={{ color: "#ad6800", fontSize: 15 }}>
                  ⏭ {transitionHint}
                </Typography.Text>
              </div>
            )}

            {/* 完成提示 */}
            {phase === "movement_done" && !transitionHint && (
              <div style={{ textAlign: "center", padding: "16px 0" }}>
                <Tag icon={<CheckCircleOutlined />} color="success" style={{ fontSize: 16, padding: "6px 20px" }}>
                  本项评估完成 ✓
                </Tag>
                {nextItem && (
                  <div style={{ marginTop: 12 }}>
                    <Typography.Text type="secondary">
                      下一项：<strong>{nextItem.name}</strong>（{nextItem.steps.length} 个步骤）
                    </Typography.Text>
                  </div>
                )}
              </div>
            )}

            {/* 当前步骤指导语浮层 */}
            {guidance && phase === "running" && (
              <div style={{
                background: "rgba(0,0,0,0.75)", color: "#fff", padding: "8px 20px",
                borderRadius: 20, fontSize: 16, textAlign: "center", marginBottom: 8,
              }}>
                {guidance}
              </div>
            )}

            {/* 实时数据卡片 */}
            {phase === "running" && currentStepData && (
              <Card size="small">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <Typography.Text strong>
                    {currentItem.name} · 步骤 {currentStep + 1}/{currentItem.steps.length}：{currentStepData.name}
                  </Typography.Text>
                  <Button size="small" icon={<ForwardOutlined />} onClick={skipStep}>跳过此项</Button>
                </div>
                <Typography.Text type="secondary">{currentStepData.instruction}</Typography.Text>

                {/* 关节角度 */}
                {Object.keys(angles).length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <Space wrap>
                      {Object.entries(angles).map(([key, val]) => (
                        <Tag key={key} color={plateau ? "success" : "processing"}>{key}: {String(val)}°</Tag>
                      ))}
                    </Space>
                    {plateau && <Tag color="success" style={{ marginLeft: 8 }}>已达到目标</Tag>}
                  </div>
                )}

                {/* 步骤间操作按钮 */}
                <div style={{ marginTop: 12, textAlign: "center" }}>
                  <Space>
                    {currentStep < currentItem.steps.length - 1 ? (
                      <Button type="primary" icon={<ArrowRightOutlined />} onClick={() => {
                        // 显示过渡提示后进入下一步
                        const step = currentItem.steps[currentStep];
                        setTransitionHint(step.transitionHint);
                        setPhase("between_steps");
                        // 短暂延迟后自动进入下一步
                        setTimeout(() => advanceStep(), 1500);
                      }}>
                        完成此步骤，继续下一步
                      </Button>
                    ) : (
                      <Button type="primary" icon={<CheckCircleOutlined />} onClick={() => {
                        playEndBeep();
                        setTransitionHint("");
                        setPhase("movement_done");
                        if (wsRef.current?.readyState === WebSocket.OPEN) {
                          wsRef.current.send(JSON.stringify({ type: "movement_done" }));
                        }
                      }}>
                        完成此评估项
                      </Button>
                    )}
                    <Button onClick={finishAssessment}>结束评估</Button>
                  </Space>
                </div>
              </Card>
            )}
          </>
        )}

        {/* ── 错误 ──────────────────────────────────── */}
        {error && (
          <Result status="error" title="连接失败" subTitle={error}
            extra={<Button onClick={() => { setError(""); setPhase("idle"); cleanup(); }}>重试</Button>}
          />
        )}
      </Card>
    </div>
  );
}
