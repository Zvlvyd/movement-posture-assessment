import { useState, useEffect, useRef, useCallback } from 'react';
import { Card, Select, Button, Typography, Space, Tag, message, Spin, List } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons';
import { useAuthStore } from '../store/auth';
import { prescriptionApi, trainingApi } from '../services/api';
import type { Prescription } from '../types';

// COCO pose skeleton connections (0-indexed)
const SKELETON: [number, number][] = [
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16]
];

export default function TrainingPage() {
  const token = useAuthStore(s => s.token);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const frameIntervalRef = useRef<number>(0);
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [selectedRx, setSelectedRx] = useState<number | null>(null);
  const [mode, setMode] = useState<'basic' | 'advanced'>('basic');
  const [isTraining, setIsTraining] = useState(false);
  const isTrainingRef = useRef(false);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<any>(null);
  const [guidance, setGuidance] = useState('');
  const [score, setScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    prescriptionApi.list().then(setPrescriptions).catch(() => {});
  }, []);

  // 绘制骨骼关键点到 overlay canvas
  const drawSkeleton = useCallback((keypoints: number[][]) => {
    const canvas = overlayCanvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video || !video.videoWidth) return;
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!keypoints || keypoints.length === 0) return;

    // Draw skeleton lines
    ctx.strokeStyle = '#00ff88';
    ctx.lineWidth = 2;
    for (const [i, j] of SKELETON) {
      if (i < keypoints.length && j < keypoints.length) {
        const [x1, y1] = keypoints[i]; const [x2, y2] = keypoints[j];
        if (x1 > 0 && y1 > 0 && x2 > 0 && y2 > 0) {
          ctx.beginPath();
          ctx.moveTo(x1, y1); ctx.lineTo(x2, y2);
          ctx.stroke();
        }
      }
    }

    // Draw keypoints
    for (let i = 0; i < keypoints.length; i++) {
      const [x, y] = keypoints[i];
      if (x > 0 && y > 0) {
        ctx.fillStyle = '#ff4466';
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }, []);

  // 统一的清理函数
  const cleanup = useCallback(() => {
    clearInterval(frameIntervalRef.current);
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'end', score }));
      wsRef.current.close();
    }
    setIsTraining(false);
  }, [score]);

  // 关闭标签页/浏览器时自动释放摄像头和 WebSocket
  useEffect(() => {
    window.addEventListener('beforeunload', cleanup);
    window.addEventListener('pagehide', cleanup);
    return () => {
      cleanup();
      window.removeEventListener('beforeunload', cleanup);
      window.removeEventListener('pagehide', cleanup);
    };
  }, [cleanup]);

  const startTraining = async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      message.error('摄像头不可用：请使用 localhost 或 HTTPS 访问，或在 Chrome 中启用不安全源。chrome://flags/#unsafely-treat-insecure-origin-as-secure');
      return;
    }
    if (!selectedRx) { message.warning('请选择训练处方'); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      streamRef.current = stream;
      if (videoRef.current) { videoRef.current.srcObject = stream; } else {
        // video 元素尚不可用，延迟重试
        const retry = setInterval(() => {
          if (videoRef.current) { videoRef.current.srcObject = stream; clearInterval(retry); }
        }, 50);
      }
      
      const record = await trainingApi.start({ prescription_id: selectedRx, mode });
      setSessionId(record.id);
      setIsTraining(true);
      isTrainingRef.current = true;

      const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const ws = new WebSocket(`${wsProtocol}://${window.location.host}/api/training/ws?token=${token}`);
      ws.onopen = () => { ws.send(JSON.stringify({ type: 'start', prescription_id: selectedRx, mode })); };
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'started') {
          setSessionId(data.session_id);
          setGuidance(data.guidance || '准备开始训练');
        } else if (data.type === 'result') {
          // Draw keypoints
          if (data.keypoints && data.keypoints.length > 0) {
            const kps = Array.isArray(data.keypoints[0]) ? data.keypoints : data.keypoints;
            drawSkeleton(kps);
          }
          
          if (data.guidance) setGuidance(data.guidance);
          
          setFeedback(data);
          if (data.score) setScore(data.score);
        } else if (data.type === 'ended') {
          setGuidance('训练结束');
        } else if (data.type === 'error') {
          message.error(data.message);
        }
      };
      ws.onerror = () => message.error('WebSocket连接失败');
      wsRef.current = ws;
      // 延迟启动帧捕获，等待 React 渲染 video 元素并绑定 stream
      setTimeout(() => startFrameCapture(), 100);
    } catch (e: any) {
      message.error('无法访问摄像头: ' + (e.message || ''));
    }
  };

  const startFrameCapture = () => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    frameIntervalRef.current = window.setInterval(() => {
      if (!isTrainingRef.current) return;
      if (!video.videoWidth) return;
      
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);
      
      // Send as base64 JPEG for YOLO processing
      const b64 = canvas.toDataURL('image/jpeg', 0.6);
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'frame',
          action_name: 'squat',
          image: b64
        }));
      }
    }, 200);  // ~5fps
  };

  const stopTraining = async () => {
    clearInterval(frameIntervalRef.current);
    setIsTraining(false);
    isTrainingRef.current = false;
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: 'end', score }));
      wsRef.current.close();
    }
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    if (sessionId) {
      setLoading(true);
      await trainingApi.end(sessionId, score || undefined);
      setLoading(false);
      message.success('训练已结束');
    }
  };

  return (
    <div>
      <Card title="实时训练" style={{ maxWidth: 800, margin: '0 auto' }}>
        <Space style={{ marginBottom: 16, width: '100%' }} direction="vertical">
          <Select placeholder="选择训练处方" style={{ width: '100%' }} value={selectedRx} onChange={setSelectedRx}
                            options={prescriptions.map(r => ({ value: r.id, label: `处方 #${r.id} —— ${r.phase}阶段 (${r.status})` }))} />
          <Select value={mode} onChange={setMode} style={{ width: '100%' }}
            options={[{ value: 'basic', label: '基础模式（仅危险警告）' }, { value: 'advanced', label: '进阶模式（精细评分）' }]} />
          {!isTraining ? (
            <Button type="primary" icon={<PlayCircleOutlined />} block size="large" onClick={startTraining}>
              开始训练
            </Button>
          ) : (
            <Button danger icon={<PauseCircleOutlined />} block size="large" onClick={stopTraining} loading={loading}>
              结束训练
            </Button>
          )}
        </Space>

        <div className="video-container" style={{ position: 'relative' }}>
          <video ref={videoRef} autoPlay playsInline muted style={{ width: '100%', borderRadius: 8, background: '#000' }} />
          <canvas
            ref={overlayCanvasRef}
            style={{
              position: 'absolute', top: 0, left: 0,
              width: '100%', height: '100%', borderRadius: 8,
              pointerEvents: 'none'
            }}
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} />
          
          {/* Guidance overlay */}
          {guidance && isTraining && (
            <div style={{
              position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)',
              background: 'rgba(0,0,0,0.75)', color: '#fff', padding: '8px 20px',
              borderRadius: 20, fontSize: 16, fontWeight: 500,
              whiteSpace: 'nowrap', pointerEvents: 'none'
            }}>
              {guidance}
            </div>
          )}
        </div>

        {feedback && (
          <Card className="feedback-panel" size="small">
            {feedback.mode === 'basic' ? (
              <div>
                <Tag color={feedback.passed ? 'green' : 'red'}>{feedback.result}</Tag>
                {feedback.warnings?.map((w: any, i: number) => <Tag color="red" key={i}>{w.message}</Tag>)}
              </div>
            ) : (
              <div>
                <Typography.Title level={4}>评分: {feedback.score} / 100</Typography.Title>
                <Tag color={feedback.score >= 90 ? 'green' : feedback.score >= 60 ? 'orange' : 'red'}>{feedback.quality}</Tag>
                {feedback.penalties?.map((p: any, i: number) => <Tag color="orange" key={i}>{p.message}</Tag>)}
              </div>
            )}
            {feedback.fsm_state && (
              <div style={{ marginTop: 8 }}>
                <Tag color="blue">状态: {feedback.fsm_state}</Tag>
                {feedback.fsm_progress !== undefined && (
                  <Tag>进度: {Math.round(feedback.fsm_progress * 100)}%</Tag>
                )}
              </div>
            )}
          </Card>
        )}
      </Card>
    </div>
  );
}
