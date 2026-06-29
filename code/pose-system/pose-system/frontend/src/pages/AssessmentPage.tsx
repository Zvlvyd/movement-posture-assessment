import { useState, useRef, useEffect, useCallback } from "react";
import { Card, Button, Typography, Tag, Progress, message, Space, Spin, Result, Steps, Upload } from "antd";
import {
  CameraOutlined, ExperimentOutlined, ArrowRightOutlined,
  ForwardOutlined, CheckCircleOutlined, LoadingOutlined,
  UploadOutlined, ReloadOutlined, SwapOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import MovementDemo from "../components/MovementDemo";
import { playStartBeep, playEndBeep, playCountdownBeep, playFinalBeep } from "../utils/audio";
import { getAssessmentItem, type AssessmentItem, type MovementStep } from "../config/assessmentSteps";
import AssessmentDashboard from "./assessment/AssessmentDashboard";

interface Movement {
  index: number;
  name: string;
  instruction: string;
  duration_hint: string;
}

interface StaticFinding {
  flag: string;
  name: string;
  severity: string;
  value: number;
  unit: string;
  normal_range: string;
  source_views: string[];
}

const SKELETON: [number, number][] = [
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16]
];

const CAPTURE_VIEWS = ["front", "back", "side"] as const;
const CAPTURE_LABELS: Record<string, string> = { front: "正面", back: "背面", side: "侧面" };

type Phase = "idle" | "connecting" | "capturing" | "analyzing_capture" | "preparing" | "countdown" | "running" | "between_steps" | "movement_done" | "done";

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

  // 三视角捕获
  const [captureViewIdx, setCaptureViewIdx] = useState(0);
  const [captureView, setCaptureView] = useState("");
  const [captureInstruction, setCaptureInstruction] = useState("");
  const [captureError, setCaptureError] = useState("");
  const [capturedPreviews, setCapturedPreviews] = useState<Record<string, string>>({});
  const [staticFindings, setStaticFindings] = useState<StaticFinding[]>([]);
  const [staticSummary, setStaticSummary] = useState("");
  const [verificationPlan, setVerificationPlan] = useState<any[]>([]);

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
    const displayW = canvas.getBoundingClientRect().width || video?.videoWidth || 640;
    const displayH = canvas.getBoundingClientRect().height || video?.videoHeight || 480;
    if (displayW === 0 || displayH === 0) return;
    if (canvas.width !== displayW || canvas.height !== displayH) {
      canvas.width = displayW; canvas.height = displayH;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const scaleX = displayW / (video?.videoWidth || 640);
    const scaleY = displayH / (video?.videoHeight || 480);
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
            ctx.beginPath(); ctx.arc(x * scaleX, y * scaleY, 4, 0, Math.PI * 2); ctx.fill();
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
    if (wsRef.current) { wsRef.current.onclose = null; wsRef.current.close(); wsRef.current = null; }
    setStream(null);
  }, []);
  useEffect(() => () => cleanup(), [cleanup]);

  const videoCallbackRef = useCallback((el: HTMLVideoElement | null) => {
    (videoRef as React.MutableRefObject<HTMLVideoElement | null>).current = el;
    if (el && stream) el.srcObject = stream;
  }, [stream]);

  const startCamera = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) { message.error("摄像头不可用"); return false; }
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: "user" } });
      streamRef.current = s; setStream(s); return true;
    } catch (e: any) { message.error("无法访问摄像头: " + (e.message || "")); return false; }
  }, []);

  const startFrameCapture = useCallback(() => {
    clearInterval(intervalRef.current);
    const canvas = canvasRef.current; const video = videoRef.current;
    if (!canvas || !video || !video.videoWidth) return false;
    const ctx = canvas.getContext("2d"); if (!ctx) return false;
    intervalRef.current = window.setInterval(() => {
      if (!video.videoWidth) return;
      if (wsRef.current?.readyState !== WebSocket.OPEN) return;
      canvas.width = video.videoWidth; canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);
      wsRef.current.send(JSON.stringify({ type: "frame", data: canvas.toDataURL("image/jpeg", 0.6) }));
    }, 150);
    return true;
  }, []);

  // ─── 三视角捕获 ────────────────────────────────────
  const captureSnapshot = useCallback(() => {
    const canvas = canvasRef.current; const video = videoRef.current;
    if (!canvas || !video || !video.videoWidth) { message.error("摄像头未就绪"); return; }
    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    const b64 = canvas.toDataURL("image/jpeg", 0.85);
    setCapturedPreviews(prev => ({ ...prev, [captureView]: b64 }));
    setCaptureError("");
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "capture_view", view: captureView, data: b64 }));
    }
    setPhase("analyzing_capture");
  }, [captureView]);

  const handleFileUpload = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      const b64 = reader.result as string;
      setCapturedPreviews(prev => ({ ...prev, [captureView]: b64 }));
      setCaptureError("");
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "capture_view", view: captureView, data: b64 }));
      }
      setPhase("analyzing_capture");
    };
    reader.readAsDataURL(file);
    return false;
  }, [captureView]);

  const skipCapture = useCallback(() => {
    setPhase("connecting");
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "skip_capture" }));
    }
  }, []);

  const retryView = useCallback(() => {
    setCaptureError("");
    setPhase("capturing");
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "retry_view", view: captureView }));
    }
  }, [captureView]);

  const startCountdown = useCallback(() => {
    setCountdown(3); setPhase("countdown");
    let tick = 3;
    const timer = setInterval(() => {
      tick--; if (tick <= 0) { clearInterval(timer); playStartBeep(); setCountdown(0); setPhase("running"); setTimeout(() => startFrameCapture(), 100); }
      else { playCountdownBeep(); setCountdown(tick); }
    }, 1000);
  }, [startFrameCapture]);

  const advanceStep = useCallback(() => {
    if (!assessmentItem) return;
    const nextStep = currentStep + 1;
    if (nextStep >= assessmentItem.steps.length) {
      playEndBeep(); setTransitionHint(""); setPhase("movement_done");
      if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify({ type: "movement_done" }));
    } else {
      playEndBeep(); const step = assessmentItem.steps[nextStep];
      setCurrentStep(nextStep); setAngles({}); setPlateau(false); setGuidance(step.instruction); setTransitionHint(""); setPhase("running");
    }
  }, [assessmentItem, currentStep]);

  // ─── 开始评估 / WS ─────────────────────────────────
  const startAssessment = useCallback(async () => {
    setError(""); setPhase("connecting");
    const ok = await startCamera(); if (!ok) { setPhase("idle"); return; }
    if (!token) { setError("请先登录"); setPhase("idle"); return; }
    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${wsProtocol}://${window.location.host}/api/assessment/ws?token=${token}`;
    const ws = new WebSocket(wsUrl); wsRef.current = ws;

    ws.onopen = () => { ws.send(JSON.stringify({ type: "start" })); };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        // Capture phase
        if (msg.type === "capture_ready") {
          setCaptureViewIdx(msg.view_index || 0); setCaptureView(msg.view); setCaptureInstruction(msg.instruction || ""); setCaptureError(""); setPhase("capturing"); clearInterval(intervalRef.current);
        } else if (msg.type === "capture_ok") {
          setPhase("capturing"); if (msg.keypoints) drawSkeleton([{ keypoints: msg.keypoints, confidences: Array(17).fill(1) }]);
        } else if (msg.type === "capture_error") {
          setCaptureError(msg.message || "检测失败"); setPhase("capturing");
        } else if (msg.type === "static_analysis") {
          setStaticFindings(msg.findings || []); setStaticSummary(msg.summary || "");
        } else if (msg.type === "verification_plan") {
          setVerificationPlan(msg.movements || []); setMovements(msg.movements || []);
        }
        // Standard + movement
        else if (msg.type === "assessment_started") {
          setMovements(msg.movements || []);
        } else if (msg.type === "movement_ready") {
          setCurrentIdx(msg.index); setCurrentStep(0); setAngles({}); setPlateau(false); setTransitionHint(""); setGuidance(msg.instruction || "");
          const item = getAssessmentItem(msg.index); setAssessmentItem(item || null); setPhase("preparing");
        } else if (msg.type === "angles_update") {
          if (phaseRef.current !== "running" && phaseRef.current !== "between_steps") return;
          const item = getAssessmentItem(currentIdxRef.current); const step = item?.steps[currentStepRef.current];
          if (step?.highlightAngles?.length) {
            const filtered: Record<string, number> = {};
            for (const key of step.highlightAngles) { if (msg.angles && msg.angles[key] !== undefined) filtered[key] = msg.angles[key]; }
            setAngles(Object.keys(filtered).length > 0 ? filtered : (msg.angles || {}));
          } else { setAngles(msg.angles || {}); }
          setPlateau(msg.plateau_detected);
          if (msg.keypoints) drawSkeleton(msg.keypoints);
        } else if (msg.type === "movement_completed") {
          setPhase("movement_done");
        } else if (msg.type === "assessment_complete") {
          playFinalBeep(); setResult(msg); setPhase("done"); cleanup();
        } else if (msg.type === "error") { message.error(msg.message); }
      } catch (e) { console.error("[Assessment] Parse error:", e); }
    };

    ws.onerror = () => { setError("WebSocket 连接失败"); setPhase("idle"); };
    ws.onclose = (e) => {
      if (phaseRef.current !== "done" && phaseRef.current !== "idle" && e.code !== 1000 && e.code !== 1005) {
        setError((prev) => prev || `WebSocket 断开 (code: ${e.code})`); setPhase("idle");
      }
    };
  }, [token, startCamera, cleanup, drawSkeleton]);

  const skipStep = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify({ type: "movement_done" }));
    setAngles({}); setTransitionHint(""); setPhase("movement_done");
  }, []);

  const finishAssessment = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify({ type: "finish" }));
  }, []);

  const itemProgress = movements.length > 0 ? Math.round(((currentIdx + 1) / movements.length) * 100) : 0;
  const currentItem = assessmentItem;
  const currentStepData: MovementStep | undefined = currentItem?.steps[currentStep];
  const showVideo = phase !== "idle" && phase !== "done";
  const showDemo = phase === "preparing" || phase === "countdown";
  const showRunningUI = phase === "running" || phase === "between_steps" || phase === "movement_done";

  if (phase === "done" && result) {
    return (
      <div style={{ padding: 24, maxWidth: 700, margin: "0 auto" }}>
        <Result status="success" title="评估完成"
          subTitle={`综合评分 ${result.overall_score ?? "N/A"} / 100  风险等级: ${result.risk_level}`}
          extra={[
            <Button type="primary" key="report" onClick={() => navigate(`/assessment/report/${result.record_id}`, { state: { result } })}>查看详细报告</Button>,
            <Button key="retry" onClick={() => { setResult(null); setPhase("idle"); setCurrentIdx(-1); setCurrentStep(0); setCapturedPreviews({}); setStaticFindings([]); setVerificationPlan([]); }}>重新评估</Button>,
          ]}
        />
      </div>
    );
  }

  const nextItem = phase === "movement_done" ? getAssessmentItem(currentIdx + 1) : null;

  return (
    <div style={{ maxWidth: 750, margin: "0 auto" }}>
      <Card title={<Space><ExperimentOutlined />体态评估</Space>}>
        {/* Idle */}
        {phase === "idle" && !error && (
          <div style={{ textAlign: "center", padding: 24 }}>
            <CameraOutlined style={{ fontSize: 48, color: "#4ECDC4", marginBottom: 16 }} />
            <Typography.Title level={4}>准备开始体态评估</Typography.Title>
            <Typography.Paragraph>先拍摄<strong>正面、背面、侧面</strong>三张照片进行静态分析，再针对问题定向验证。也可跳过直接评估。</Typography.Paragraph>
            <Typography.Paragraph type="secondary">全身可见，光线充足。可用摄像头拍摄或上传照片。</Typography.Paragraph>
            <Button type="primary" size="large" icon={<CameraOutlined />} onClick={startAssessment}>开启摄像头，开始评估</Button>
          </div>
        )}

        {/* Connecting */}
        {phase === "connecting" && (
          <div style={{ textAlign: "center", padding: 48 }}><Spin size="large" /><Typography.Paragraph style={{ marginTop: 16 }}>正在连接...</Typography.Paragraph></div>
        )}

        {/* Video */}
        {showVideo && (
          <div style={{ position: "relative", width: "100%", background: "#000", borderRadius: 8, overflow: "hidden", isolation: "isolate" }}>
            <video ref={videoCallbackRef} autoPlay playsInline muted style={{ width: "100%", borderRadius: 8, position: "relative", zIndex: 1 }} />
            <canvas ref={overlayCanvasRef} style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none", zIndex: 10 }} />
            <canvas ref={canvasRef} style={{ display: "none" }} />
          </div>
        )}

        {/* ── 三视角捕获阶段 ── */}
        {(phase === "capturing" || phase === "analyzing_capture") && (
          <div style={{ marginTop: 12 }}>
            <Progress percent={Math.round((CAPTURE_VIEWS.indexOf(captureView as any) + 1) / 3 * 100)} style={{ marginBottom: 8 }} />
            <div style={{ marginBottom: 12, textAlign: "center" }}>
              {CAPTURE_VIEWS.map((v, i) => (
                <Tag key={v} color={capturedPreviews[v] ? "success" : CAPTURE_VIEWS.indexOf(captureView as any) === i ? "processing" : "default"}>
                  {i + 1}. {CAPTURE_LABELS[v]}{capturedPreviews[v] ? " ✓" : ""}
                </Tag>
              ))}
            </div>
            <Card size="small" style={{ textAlign: "center", background: "#f0f5ff", marginBottom: 12 }}>
              <Typography.Title level={5} style={{ margin: 0 }}><SwapOutlined /> {CAPTURE_LABELS[captureView]}照</Typography.Title>
              <Typography.Paragraph type="secondary" style={{ margin: "8px 0 0" }}>{captureInstruction}</Typography.Paragraph>
            </Card>
            {captureError && (
              <div style={{ textAlign: "center", marginBottom: 12, padding: 8, background: "#fff2f0", borderRadius: 8 }}>
                <Typography.Text type="danger">{captureError}</Typography.Text>
              </div>
            )}
            {capturedPreviews[captureView] && (
              <div style={{ textAlign: "center", marginBottom: 12 }}>
                <img src={capturedPreviews[captureView]} alt={captureView} style={{ maxHeight: 200, borderRadius: 8, border: "2px solid #4ECDC4" }} />
              </div>
            )}
            <div style={{ textAlign: "center" }}>
              <Space size="middle" wrap>
                <Button type="primary" size="large" icon={<CameraOutlined />} onClick={captureSnapshot}>拍摄照片</Button>
                <Upload accept="image/*" showUploadList={false} beforeUpload={handleFileUpload}>
                  <Button size="large" icon={<UploadOutlined />}>上传照片</Button>
                </Upload>
                {captureError && <Button size="large" icon={<ReloadOutlined />} onClick={retryView}>重试</Button>}
                <Button size="large" onClick={skipCapture}>跳过拍照</Button>
              </Space>
            </div>
          </div>
        )}

        {/* ── 静态分析结果 ── */}
        {staticFindings.length > 0 && verificationPlan.length > 0 && (
          <Card size="small" style={{ marginTop: 12, background: "#f6ffed" }}>
            <Typography.Text strong>静态分析完成</Typography.Text>
            <Typography.Paragraph type="secondary" style={{ margin: "4px 0" }}>{staticSummary}</Typography.Paragraph>
            <Space wrap style={{ marginTop: 8 }}>
              {staticFindings.map(f => (
                <Tag key={f.flag} color={f.severity === "severe" ? "red" : f.severity === "moderate" ? "orange" : "blue"}>
                  {f.name}: {f.severity === "severe" ? "严重" : f.severity === "moderate" ? "中度" : "轻度"}
                </Tag>
              ))}
            </Space>
            <div style={{ marginTop: 8 }}><Typography.Text type="secondary">将进行 {verificationPlan.length} 项定向验证</Typography.Text></div>
          </Card>
        )}

        {/* Movement progress */}
        {phase !== "idle" && phase !== "connecting" && phase !== "capturing" && phase !== "analyzing_capture" && phase !== "done" && movements.length > 0 && (
          <>
            <Progress percent={itemProgress} style={{ marginBottom: 8 }} />
            <div style={{ marginBottom: 12 }}>
              {movements.map((m, i) => (
                <Tag key={i} color={i < currentIdx ? "success" : i === currentIdx ? "processing" : "default"}>{i + 1}. {m.name}</Tag>
              ))}
            </div>
          </>
        )}

        {/* Step progress */}
        {currentItem && currentItem.steps.length > 1 && showDemo && (
          <div style={{ marginBottom: 8 }}>
            <Steps size="small" current={currentStep}
              items={currentItem.steps.map((s, i) => ({ title: i < currentStep ? '✓' : s.name, status: i < currentStep ? 'finish' : i === currentStep ? 'process' : 'wait' }))} />
          </div>
        )}

        {/* Demo + prepare */}
        {showDemo && currentItem && currentStepData && (
          <div>
            <MovementDemo movementName={currentItem.name} stepName={currentStepData.name} instruction={currentStepData.instruction}
              stepIndex={currentStep + 1} totalSteps={currentItem.steps.length} durationHint={currentItem.durationHint}
              countdown={phase === "countdown" ? countdown : 0}
              imageUrl={currentStepData.imageUrl} videoUrl={currentStepData.videoUrl} />
            {phase === "preparing" && (
              <div style={{ textAlign: "center", marginTop: 4 }}>
                <Button type="primary" size="large" icon={<ArrowRightOutlined />} onClick={startCountdown}>准备好了，开始检测</Button>
              </div>
            )}
          </div>
        )}

        {/* Running */}
        {showRunningUI && currentIdx >= 0 && currentItem && (
          <>
            {currentItem.steps.length > 1 && (
              <Steps size="small" current={currentStep} style={{ marginBottom: 8 }}
                items={currentItem.steps.map((s, i) => ({ title: s.name, status: i < currentStep ? 'finish' : i === currentStep ? 'process' : 'wait' }))} />
            )}
            {transitionHint && (
              <div style={{ textAlign: "center", padding: "8px 0", marginBottom: 8, background: "#fff7e6", borderRadius: 8, border: "1px solid #ffd591" }}>
                <Typography.Text strong style={{ color: "#ad6800", fontSize: 15 }}>⏭ {transitionHint}</Typography.Text>
              </div>
            )}
            {phase === "movement_done" && !transitionHint && (
              <div style={{ textAlign: "center", padding: "16px 0" }}>
                <Tag icon={<CheckCircleOutlined />} color="success" style={{ fontSize: 16, padding: "6px 20px" }}>本项评估完成 ✓</Tag>
                {nextItem && <div style={{ marginTop: 12 }}><Typography.Text type="secondary">下一项：<strong>{nextItem.name}</strong>（{nextItem.steps.length} 个步骤）</Typography.Text></div>}
              </div>
            )}
            {guidance && phase === "running" && (
              <div style={{ background: "rgba(0,0,0,0.75)", color: "#fff", padding: "8px 20px", borderRadius: 20, fontSize: 16, textAlign: "center", marginBottom: 8 }}>{guidance}</div>
            )}
            {phase === "running" && currentStepData && (
              <Card size="small">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <Typography.Text strong>{currentItem.name} · 步骤 {currentStep + 1}/{currentItem.steps.length}：{currentStepData.name}</Typography.Text>
                  <Button size="small" icon={<ForwardOutlined />} onClick={skipStep}>跳过此项</Button>
                </div>
                <Typography.Text type="secondary">{currentStepData.instruction}</Typography.Text>
                {Object.keys(angles).length > 0 && (
                  <div style={{ marginTop: 8 }}><Space wrap>
                    {Object.entries(angles).map(([key, val]) => <Tag key={key} color={plateau ? "success" : "processing"}>{key}: {String(val)}°</Tag>)}
                  </Space>
                  {plateau && <Tag color="success" style={{ marginLeft: 8 }}>已达到目标</Tag>}
                  </div>
                )}
                <div style={{ marginTop: 12, textAlign: "center" }}>
                  <Space>
                    {currentStep < currentItem.steps.length - 1 ? (
                      <Button type="primary" icon={<ArrowRightOutlined />} onClick={() => {
                        setTransitionHint(currentItem.steps[currentStep].transitionHint); setPhase("between_steps"); setTimeout(() => advanceStep(), 1500);
                      }}>完成此步骤，继续下一步</Button>
                    ) : (
                      <Button type="primary" icon={<CheckCircleOutlined />} onClick={() => {
                        playEndBeep(); setTransitionHint(""); setPhase("movement_done");
                        if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify({ type: "movement_done" }));
                      }}>完成此评估项</Button>
                    )}
                    <Button onClick={finishAssessment}>结束评估</Button>
                  </Space>
                </div>
              </Card>
            )}
          </>
        )}

        {/* Error */}
        {error && <Result status="error" title="连接失败" subTitle={error}
          extra={<Button onClick={() => { setError(""); setPhase("idle"); cleanup(); }}>重试</Button>} />}
      </Card>
      <AssessmentDashboard />
    </div>
  );
}
