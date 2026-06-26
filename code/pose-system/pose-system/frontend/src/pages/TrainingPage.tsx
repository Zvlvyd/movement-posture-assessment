import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Select, Button, Typography, Space, Tag, message, List, Progress } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, WarningOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useAuthStore } from '../store/auth';
import { trainingApi } from '../services/api';

// COCO pose skeleton connections (0-indexed)
const SKELETON: [number, number][] = [
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16]
];

// 动作选项
const ACTION_OPTIONS = [
  { value: 'squat', label: '深蹲' },
  { value: 'lunge', label: '弓步蹲' },
  { value: 'pushup', label: '俯卧撑' },
  { value: 'plank', label: '平板支撑' },
  { value: 'shoulder_press', label: '肩部推举' },
  { value: 'jumping_jack', label: '开合跳' },
  { value: 'deadlift', label: '硬拉' },
];

// 错误严重程度对应的颜色
const SEVERITY_COLORS: Record<string, string> = {
  high: '#ff4d4f',
  medium: '#faad14',
  low: '#1890ff',
};

export default function TrainingPage() {
  const navigate = useNavigate();
  const token = useAuthStore(s => s.token);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const frameIntervalRef = useRef<number>(0);
  const [mode, setMode] = useState<'basic' | 'advanced'>('basic');
  const [actionName, setActionName] = useState<string>('squat');
  const [isTraining, setIsTraining] = useState(false);
  const isTrainingRef = useRef(false);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<any>(null);
  const [guidance, setGuidance] = useState('');
  const [score, setScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [count, setCount] = useState(0);
  const [errorHistory, setErrorHistory] = useState<string[]>([]);

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

  const cleanup = useCallback(() => {
    clearInterval(frameIntervalRef.current);
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'end', score: null }));
      wsRef.current.close();
    }
    setIsTraining(false);
    isTrainingRef.current = false;
  }, []);

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
      message.error('摄像头不可用：请使用 localhost 或 HTTPS 访问');
      return;
    }
    // Step 1: Open camera
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
    } catch (e: any) {
      message.error('无法访问摄像头: ' + (e.message || ''));
      return;
    }
    streamRef.current = stream;
    if (videoRef.current) { videoRef.current.srcObject = stream; } else {
      const retry = setInterval(() => {
        if (videoRef.current) { videoRef.current.srcObject = stream; clearInterval(retry); }
      }, 50);
    }

    try {
      const record = await trainingApi.start({ prescription_id: null, mode });
      setSessionId(record.id);
      setIsTraining(true);
      isTrainingRef.current = true;
      setCount(0);
      setErrorHistory([]);
      setScore(null);
      setFeedback(null);

      const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const ws = new WebSocket(`${wsProtocol}://${window.location.host}/api/training/ws?token=${token}`);
      ws.onopen = () => {
        ws.send(JSON.stringify({
          type: 'start',
          prescription_id: null,
          mode,
          action_name: actionName
        }));
      };
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'started') {
          setSessionId(data.session_id);
          setGuidance(data.guidance || '准备开始训练');
        } else if (data.type === 'result') {
          if (data.keypoints && data.keypoints.length > 0) {
            const kps = Array.isArray(data.keypoints[0]) ? data.keypoints : data.keypoints;
            drawSkeleton(kps);
          }
          if (data.guidance) setGuidance(data.guidance);
          if (data.fsm_state === 'complete') {
            setCount(prev => prev + 1);
          }
          if (data.mode === 'basic' && data.warnings) {
            const newErrors = data.warnings
              .filter((w: any) => w.severity === 'high')
              .map((w: any) => w.message);
            if (newErrors.length > 0) {
              setErrorHistory(prev => {
                const combined = [...new Set([...newErrors, ...prev])];
                return combined.slice(0, 10);
              });
            }
          } else if (data.mode === 'advanced' && data.penalties) {
            const newErrors = data.penalties.map((p: any) => p.message);
            if (newErrors.length > 0) {
              setErrorHistory(prev => {
                const combined = [...new Set([...newErrors, ...prev])];
                return combined.slice(0, 10);
              });
            }
          }
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

      const tryStartCapture = () => {
        const video = videoRef.current;
        if (video && video.videoWidth > 0 && video.videoHeight > 0) {
          console.log('[Training] Video ready, starting frame capture');
          startFrameCapture();
        } else {
          console.log('[Training] Waiting for video to be ready...');
          setTimeout(tryStartCapture, 200);
        }
      };
      setTimeout(tryStartCapture, 200);
    } catch (e: any) {
      message.error('启动训练失败: ' + (e.response?.data?.detail || e.message || ''));
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

      const b64 = canvas.toDataURL('image/jpeg', 0.6);
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'frame',
          action_name: actionName,
          image: b64
        }));
      }
    }, 200);
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
      const record = await trainingApi.end(sessionId, score || undefined);
      setLoading(false);
      message.success('训练已结束');
      navigate(`/training/report/${sessionId}`, {
        state: {
          trainingResult: record,
          extraData: { count, errorHistory, actionName },
        }
      });
    }
  };

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'excellent': return '#52c41a';
      case 'good': return '#1890ff';
      case 'fair': return '#faad14';
      case 'needs_improvement': return '#ff4d4f';
      default: return '#999';
    }
  };

  return (
    <div>
      <Card title="实时训练" style={{ maxWidth: 800, margin: '0 auto' }}>
        <Space style={{ marginBottom: 16, width: '100%' }} direction="vertical">
          <Space style={{ width: '100%' }}>
            <Select value={actionName} onChange={setActionName} style={{ flex: 1 }}
              options={ACTION_OPTIONS} />
            <Select value={mode} onChange={setMode} style={{ flex: 1 }}
              options={[{ value: 'basic', label: '基础模式' }, { value: 'advanced', label: '进阶模式' }]} />
          </Space>
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

          {isTraining && (
            <div style={{
              position: 'absolute', top: 12, right: 12,
              background: 'rgba(0,0,0,0.75)', color: '#fff',
              padding: '6px 16px', borderRadius: 16,
              fontSize: 18, fontWeight: 'bold',
              pointerEvents: 'none'
            }}>
              完成: {count} 次
            </div>
          )}

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
          <div style={{ marginTop: 12 }}>
            {feedback.mode === 'basic' && (
              <Card size="small" style={{ marginBottom: 8 }}>
                <Space>
                  {feedback.passed ? (
                    <Tag icon={<CheckCircleOutlined />} color="success">安全</Tag>
                  ) : (
                    <Tag icon={<CloseCircleOutlined />} color="error">有风险</Tag>
                  )}
                  <Tag color="blue">{ACTION_OPTIONS.find(a => a.value === actionName)?.label || actionName}</Tag>
                  {feedback.fsm_state && <Tag color="purple">状态: {feedback.fsm_state}</Tag>}
                </Space>
                {feedback.warnings && feedback.warnings.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <Typography.Text strong style={{ color: '#ff4d4f' }}>
                      <WarningOutlined /> 检测到以下问题：
                    </Typography.Text>
                    <List
                      size="small"
                      dataSource={feedback.warnings}
                      renderItem={(w: any) => (
                        <List.Item style={{ padding: '4px 0' }}>
                          <Tag color={SEVERITY_COLORS[w.severity] || '#faad14'} style={{ whiteSpace: 'normal', height: 'auto', lineHeight: '20px', padding: '2px 8px' }}>
                            {w.message}
                          </Tag>
                        </List.Item>
                      )}
                    />
                  </div>
                )}
              </Card>
            )}

            {feedback.mode === 'advanced' && (
              <Card size="small" style={{ marginBottom: 8 }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space>
                    <Typography.Title level={4} style={{ margin: 0 }}>
                      评分: {feedback.score} / 100
                    </Typography.Title>
                    <Tag color={getQualityColor(feedback.quality)} style={{ fontSize: 14, padding: '2px 12px' }}>
                      {feedback.quality === 'excellent' ? '优秀' :
                       feedback.quality === 'good' ? '良好' :
                       feedback.quality === 'fair' ? '一般' : '需改进'}
                    </Tag>
                    <Tag color="blue">{ACTION_OPTIONS.find(a => a.value === actionName)?.label || actionName}</Tag>
                    {feedback.fsm_state && <Tag color="purple">状态: {feedback.fsm_state}</Tag>}
                  </Space>
                  <Progress
                    percent={feedback.score}
                    strokeColor={getQualityColor(feedback.quality)}
                    format={(p) => `${p}分`}
                    size="small"
                  />
                  {feedback.penalties && feedback.penalties.length > 0 && (
                    <div>
                      <Typography.Text strong style={{ color: '#faad14' }}>
                        <WarningOutlined /> 扣分项：
                      </Typography.Text>
                      <List
                        size="small"
                        dataSource={feedback.penalties}
                        renderItem={(p: any) => (
                          <List.Item style={{ padding: '4px 0' }}>
                            <Space>
                              <Tag color="orange" style={{ whiteSpace: 'normal', height: 'auto', lineHeight: '20px', padding: '2px 8px' }}>
                                {p.message}
                              </Tag>
                              <Typography.Text type="danger" style={{ fontSize: 12 }}>
                                -{p.penalty}分
                              </Typography.Text>
                            </Space>
                          </List.Item>
                        )}
                      />
                    </div>
                  )}
                </Space>
              </Card>
            )}

            {errorHistory.length > 0 && (
              <Card size="small" title="错误记录" style={{ marginTop: 8 }}>
                <List
                  size="small"
                  dataSource={errorHistory}
                  renderItem={(err, idx) => (
                    <List.Item style={{ padding: '2px 0' }}>
                      <Tag color="red" style={{ whiteSpace: 'normal', height: 'auto', lineHeight: '20px', padding: '2px 8px' }}>
                        #{idx + 1} {err}
                      </Tag>
                    </List.Item>
                  )}
                />
              </Card>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
