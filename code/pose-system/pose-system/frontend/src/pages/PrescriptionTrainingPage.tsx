import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Select, Button, Typography, Space, Tag, message, List, Progress, Steps, Divider, Modal, Result } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, WarningOutlined, CheckCircleOutlined, CloseCircleOutlined, AimOutlined, OrderedListOutlined, SwapRightOutlined } from '@ant-design/icons';
import { useAuthStore } from '../store/auth';
import { prescriptionApi, trainingApi } from '../services/api';
import type { Prescription, PrescriptionItem } from '../types';

// COCO pose skeleton connections (0-indexed)
const SKELETON: [number, number][] = [
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16]
];

// 动作名称映射
const ACTION_NAME_MAP: Record<string, string> = {
  squat: '深蹲', lunge: '弓步蹲', pushup: '俯卧撑',
  plank: '平板支撑', shoulder_press: '肩部推举',
  jumping_jack: '开合跳', deadlift: '硬拉',
};

// 错误严重程度对应的颜色
const SEVERITY_COLORS: Record<string, string> = {
  high: '#ff4d4f',
  medium: '#faad14',
  low: '#1890ff',
};

export default function PrescriptionTrainingPage() {
  const navigate = useNavigate();
  const token = useAuthStore(s => s.token);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const frameIntervalRef = useRef<number>(0);
  const isTrainingRef = useRef(false);

  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [selectedRx, setSelectedRx] = useState<number | null>(null);
  const [rxDetail, setRxDetail] = useState<Prescription | null>(null);
  const [mode, setMode] = useState<'basic' | 'advanced'>('basic');

  // 训练状态
  const [isTraining, setIsTraining] = useState(false);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  // 当前动作索引（按处方顺序）
  const [currentActionIndex, setCurrentActionIndex] = useState(0);
  const currentActionIndexRef = useRef(0);

  // 每个动作的训练结果
  const [actionResults, setActionResults] = useState<Array<{ action_name: string; score: number | null; quality?: string; errors: string[]; count: number }>>([]);

  // 当前帧反馈
  const [feedback, setFeedback] = useState<any>(null);
  const [guidance, setGuidance] = useState('');
  const [count, setCount] = useState(0); // 当前动作完成次数
  const [errorHistory, setErrorHistory] = useState<string[]>([]);

  // 训练完成弹窗
  const [showComplete, setShowComplete] = useState(false);

  useEffect(() => {
    prescriptionApi.list().then(setPrescriptions).catch(() => {});
  }, []);

  // 选择处方时加载详情
  useEffect(() => {
    if (selectedRx) {
      prescriptionApi.get(selectedRx).then(setRxDetail).catch(() => setRxDetail(null));
    } else {
      setRxDetail(null);
    }
  }, [selectedRx]);

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
    ctx.strokeStyle = '#00ff88';
    ctx.lineWidth = 2;
    for (const [i, j] of SKELETON) {
      if (i < keypoints.length && j < keypoints.length) {
        const [x1, y1] = keypoints[i]; const [x2, y2] = keypoints[j];
        if (x1 > 0 && y1 > 0 && x2 > 0 && y2 > 0) {
          ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
        }
      }
    }
    for (let i = 0; i < keypoints.length; i++) {
      const [x, y] = keypoints[i];
      if (x > 0 && y > 0) {
        ctx.fillStyle = '#ff4466'; ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2); ctx.fill();
      }
    }
  }, []);

  // 清理
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
    return () => { cleanup(); window.removeEventListener('beforeunload', cleanup); window.removeEventListener('pagehide', cleanup); };
  }, [cleanup]);

  // 获取当前动作名称
  const getCurrentActionName = useCallback(() => {
    if (!rxDetail || !rxDetail.items[currentActionIndexRef.current]) return 'squat';
    return rxDetail.items[currentActionIndexRef.current].action_name;
  }, [rxDetail]);

  // 开始训练
  const startTraining = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      message.error('摄像头不可用：请使用 localhost 或 HTTPS 访问');
      return;
    }
    if (!selectedRx || !rxDetail) { message.warning('请选择训练处方'); return; }
    if (!rxDetail.items || rxDetail.items.length === 0) { message.warning('处方中没有训练动作'); return; }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      streamRef.current = stream;
      if (videoRef.current) { videoRef.current.srcObject = stream; } else {
        const retry = setInterval(() => {
          if (videoRef.current) { videoRef.current.srcObject = stream; clearInterval(retry); }
        }, 50);
      }

      // 初始化训练状态
      setCurrentActionIndex(0);
      currentActionIndexRef.current = 0;
      setActionResults(rxDetail.items.map(item => ({ action_name: item.action_name, score: null, errors: [], count: 0 })));
      setShowComplete(false);
      setIsTraining(true);
      isTrainingRef.current = true;
      setCount(0);
      setErrorHistory([]);
      setScore(null);
      setFeedback(null);

      // 开始第一个动作
      await startAction(0, rxDetail);
    } catch (e: any) {
      message.error('无法访问摄像头: ' + (e.message || ''));
    }
  };

  // 开始某个动作的训练
  const startAction = async (actionIndex: number, rx: Prescription) => {
    const actionName = rx.items[actionIndex].action_name;
    setGuidance(`准备开始: ${ACTION_NAME_MAP[actionName] || actionName}`);
    setCount(0);
    setErrorHistory([]);
    setFeedback(null);

    const record = await trainingApi.start({ prescription_id: rx.id, mode });
    setSessionId(record.id);

    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${wsProtocol}://${window.location.host}/api/training/ws?token=${token}`);
    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'start', prescription_id: rx.id, mode, action_name: actionName }));
    };
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'started') {
        setGuidance(data.guidance || `开始${ACTION_NAME_MAP[actionName] || actionName}`);
      } else if (data.type === 'result') {
        if (data.keypoints && data.keypoints.length > 0) {
          drawSkeleton(data.keypoints);
        }
        if (data.guidance) setGuidance(data.guidance);
        if (data.fsm_state === 'complete') {
          setCount(prev => prev + 1);
        }
        // 收集错误
        if (data.mode === 'basic' && data.warnings) {
          const newErrors = data.warnings.filter((w: any) => w.severity === 'high').map((w: any) => w.message);
          if (newErrors.length > 0) {
            setErrorHistory(prev => { const c = [...new Set([...newErrors, ...prev])]; return c.slice(0, 10); });
          }
        } else if (data.mode === 'advanced' && data.penalties) {
          const newErrors = data.penalties.map((p: any) => p.message);
          if (newErrors.length > 0) {
            setErrorHistory(prev => { const c = [...new Set([...newErrors, ...prev])]; return c.slice(0, 10); });
          }
        }
        setFeedback(data);
        if (data.score) setScore(data.score);
      } else if (data.type === 'ended') {
        setGuidance('动作完成！');
      } else if (data.type === 'error') {
        message.error(data.message);
      }
    };
    ws.onerror = () => message.error('WebSocket连接失败');
    wsRef.current = ws;

    // 开始帧捕获
    const tryStartCapture = () => {
      const video = videoRef.current;
      if (video && video.videoWidth > 0 && video.videoHeight > 0) {
        startFrameCapture();
      } else {
        setTimeout(tryStartCapture, 200);
      }
    };
    setTimeout(tryStartCapture, 200);
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
        const actionName = getCurrentActionName();
        wsRef.current.send(JSON.stringify({ type: 'frame', action_name: actionName, image: b64 }));
      }
    }, 200);
  };

  // 完成当前动作，进入下一个
  const completeCurrentAction = async () => {
    // 结束当前 WebSocket 会话
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'end', score }));
      wsRef.current.close();
    }
    if (sessionId) {
      await trainingApi.end(sessionId, score || undefined);
    }

    // 保存当前动作结果（包含完成次数）
    const updatedResults = actionResults.map((item, idx) => {
      if (idx === currentActionIndexRef.current) {
        return { ...item, score, errors: errorHistory, count };
      }
      return item;
    });
    setActionResults(updatedResults);

    // 检查是否还有下一个动作
    if (rxDetail && currentActionIndexRef.current < rxDetail.items.length - 1) {
      const nextIndex = currentActionIndexRef.current + 1;
      currentActionIndexRef.current = nextIndex;
      setCurrentActionIndex(nextIndex);
      // 短暂延迟后开始下一个动作
      setTimeout(() => {
        if (rxDetail) startAction(nextIndex, rxDetail);
      }, 500);
    } else {
      // 所有动作完成
      setIsTraining(false);
      isTrainingRef.current = false;
      streamRef.current?.getTracks().forEach(t => t.stop());
      streamRef.current = null;
      // 跳转到处方训练报告页面
      navigate(`/prescription-training/report/${sessionId}`, {
        state: {
          trainingResult: { id: sessionId, total_score: score, mode, start_time: new Date().toISOString(), end_time: new Date().toISOString() },
          extraData: {
            actionResults: updatedResults,
            rxDetail,
            totalDuration: 0,
            startTime: new Date().toLocaleString('zh-CN'),
            endTime: new Date().toLocaleString('zh-CN'),
          }
        }
      });
    }
  };

  // 停止训练
  const stopTraining = async () => {
    clearInterval(frameIntervalRef.current);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
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
      // 保存当前动作的完成次数
      const finalResults = actionResults.map((item, idx) => {
        if (idx === currentActionIndexRef.current) {
          return { ...item, score, errors: errorHistory, count };
        }
        return item;
      });
      // 跳转到处方训练报告页面
      navigate(`/prescription-training/report/${sessionId}`, {
        state: {
          trainingResult: record,
          extraData: {
            actionResults: finalResults,
            rxDetail,
            totalDuration: 0,
            startTime: record.start_time ? new Date(record.start_time).toLocaleString('zh-CN') : '',
            endTime: new Date().toLocaleString('zh-CN'),
          }
        }
      });
    }
    setIsTraining(false);
    isTrainingRef.current = false;
  };

  const [score, setScore] = useState<number | null>(null);

  // 获取质量对应的颜色
  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'excellent': return '#52c41a';
      case 'good': return '#1890ff';
      case 'fair': return '#faad14';
      case 'needs_improvement': return '#ff4d4f';
      default: return '#999';
    }
  };

  // 计算总进度
  const totalActions = rxDetail?.items?.length || 0;
  const progressPercent = totalActions > 0 ? Math.round((currentActionIndex / totalActions) * 100) : 0;

  return (
    <div>
      <Card title={<Space><OrderedListOutlined />处方训练</Space>} style={{ maxWidth: 800, margin: '0 auto' }}>
        <Space style={{ marginBottom: 16, width: '100%' }} direction="vertical">
          <Select placeholder="选择训练处方" style={{ width: '100%' }} value={selectedRx} onChange={setSelectedRx}
            options={prescriptions.map(r => ({ value: r.id, label: `处方 #${r.id} —— ${r.phase}阶段 (${r.status})` }))} />

          {/* 处方详情 */}
          {rxDetail && !isTraining && (
            <Card size="small" title="处方详情" style={{ width: '100%', background: '#fafafa' }}>
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                <Space>
                  <Tag color="blue">处方 #{rxDetail.id}</Tag>
                  <Tag color={rxDetail.status === 'unlocked' ? 'green' : rxDetail.status === 'completed' ? 'purple' : 'default'}>
                    {rxDetail.status === 'unlocked' ? '已解锁' : rxDetail.status === 'completed' ? '已完成' : '锁定'}
                  </Tag>
                  <Tag color="orange">阶段 {rxDetail.phase}</Tag>
                  <Tag color="cyan">难度: {'★'.repeat(rxDetail.difficulty)}{'☆'.repeat(5 - rxDetail.difficulty)}</Tag>
                </Space>
                <Divider style={{ margin: '4px 0' }} />
                <Typography.Text strong style={{ fontSize: 13, color: '#666' }}>
                  <AimOutlined style={{ marginRight: 4 }} />训练计划（共 {rxDetail.items.length} 个动作）：
                </Typography.Text>
                <Steps
                  direction="vertical"
                  size="small"
                  current={-1}
                  items={rxDetail.items.map((item, idx) => ({
                    title: `${idx + 1}. ${ACTION_NAME_MAP[item.action_name] || item.action_name}`,
                    description: `${item.sets}组 × ${item.duration > 0 ? `${item.duration}秒` : `${item.reps}次`}`,
                    status: 'wait' as const,
                  }))}
                />
              </Space>
            </Card>
          )}

          {/* 训练中 - 进度和当前动作 */}
          {isTraining && (
            <Card size="small" style={{ width: '100%', background: '#e6f7ff' }}>
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                <Space>
                  <Tag color="blue" style={{ fontSize: 14, padding: '2px 12px' }}>
                    动作 {currentActionIndex + 1}/{totalActions}
                  </Tag>
                  <Tag color="green" style={{ fontSize: 14, padding: '2px 12px' }}>
                    {ACTION_NAME_MAP[rxDetail?.items[currentActionIndex]?.action_name || ''] || rxDetail?.items[currentActionIndex]?.action_name}
                  </Tag>
                  <Tag color="orange">完成: {count}/{rxDetail?.items[currentActionIndex]?.reps || rxDetail?.items[currentActionIndex]?.duration || 0}</Tag>
                </Space>
                <Progress percent={progressPercent} size="small" format={() => `${currentActionIndex}/${totalActions}`} />
                <Button type="primary" size="small" icon={<SwapRightOutlined />} onClick={completeCurrentAction}>
                  完成当前动作，进入下一个
                </Button>
              </Space>
            </Card>
          )}

          <Select value={mode} onChange={setMode} style={{ width: '100%' }}
            options={[{ value: 'basic', label: '基础模式（安全检测）' }, { value: 'advanced', label: '进阶模式（评分系统）' }]} />

          {!isTraining ? (
            <Button type="primary" icon={<PlayCircleOutlined />} block size="large" onClick={startTraining}>
              开始处方训练
            </Button>
          ) : (
            <Button danger icon={<PauseCircleOutlined />} block size="large" onClick={stopTraining} loading={loading}>
              结束训练
            </Button>
          )}
        </Space>

        <div className="video-container" style={{ position: 'relative' }}>
          <video ref={videoRef} autoPlay playsInline muted style={{ width: '100%', borderRadius: 8, background: '#000' }} />
          <canvas ref={overlayCanvasRef} style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', borderRadius: 8, pointerEvents: 'none' }} />
          <canvas ref={canvasRef} style={{ display: 'none' }} />

          {isTraining && (
            <div style={{ position: 'absolute', top: 12, right: 12, background: 'rgba(0,0,0,0.75)', color: '#fff', padding: '6px 16px', borderRadius: 16, fontSize: 18, fontWeight: 'bold', pointerEvents: 'none' }}>
              完成: {count} 次
            </div>
          )}
          {guidance && isTraining && (
            <div style={{ position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)', background: 'rgba(0,0,0,0.75)', color: '#fff', padding: '8px 20px', borderRadius: 20, fontSize: 16, fontWeight: 500, whiteSpace: 'nowrap', pointerEvents: 'none' }}>
              {guidance}
            </div>
          )}
        </div>

        {/* 训练反馈 */}
        {feedback && (
          <div style={{ marginTop: 12 }}>
            {feedback.mode === 'basic' && (
              <Card size="small" style={{ marginBottom: 8 }}>
                <Space>
                  {feedback.passed ? <Tag icon={<CheckCircleOutlined />} color="success">安全</Tag> : <Tag icon={<CloseCircleOutlined />} color="error">有风险</Tag>}
                  {feedback.fsm_state && <Tag color="purple">状态: {feedback.fsm_state}</Tag>}
                </Space>
                {feedback.warnings && feedback.warnings.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <Typography.Text strong style={{ color: '#ff4d4f' }}><WarningOutlined /> 检测到以下问题：</Typography.Text>
                    <List size="small" dataSource={feedback.warnings} renderItem={(w: any) => (
                      <List.Item style={{ padding: '4px 0' }}>
                        <Tag color={SEVERITY_COLORS[w.severity] || '#faad14'} style={{ whiteSpace: 'normal', height: 'auto', lineHeight: '20px', padding: '2px 8px' }}>{w.message}</Tag>
                      </List.Item>
                    )} />
                  </div>
                )}
              </Card>
            )}
            {feedback.mode === 'advanced' && (
              <Card size="small" style={{ marginBottom: 8 }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space>
                    <Typography.Title level={4} style={{ margin: 0 }}>评分: {feedback.score} / 100</Typography.Title>
                    <Tag color={getQualityColor(feedback.quality)} style={{ fontSize: 14, padding: '2px 12px' }}>
                      {feedback.quality === 'excellent' ? '优秀' : feedback.quality === 'good' ? '良好' : feedback.quality === 'fair' ? '一般' : '需改进'}
                    </Tag>
                    {feedback.fsm_state && <Tag color="purple">状态: {feedback.fsm_state}</Tag>}
                  </Space>
                  <Progress percent={feedback.score} strokeColor={getQualityColor(feedback.quality)} format={(p) => `${p}分`} size="small" />
                  {feedback.penalties && feedback.penalties.length > 0 && (
                    <div>
                      <Typography.Text strong style={{ color: '#faad14' }}><WarningOutlined /> 扣分项：</Typography.Text>
                      <List size="small" dataSource={feedback.penalties} renderItem={(p: any) => (
                        <List.Item style={{ padding: '4px 0' }}>
                          <Space><Tag color="orange" style={{ whiteSpace: 'normal', height: 'auto', lineHeight: '20px', padding: '2px 8px' }}>{p.message}</Tag><Typography.Text type="danger" style={{ fontSize: 12 }}>-{p.penalty}分</Typography.Text></Space>
                        </List.Item>
                      )} />
                    </div>
                  )}
                </Space>
              </Card>
            )}
            {errorHistory.length > 0 && (
              <Card size="small" title="错误记录" style={{ marginTop: 8 }}>
                <List size="small" dataSource={errorHistory} renderItem={(err, idx) => (
                  <List.Item style={{ padding: '2px 0' }}><Tag color="red" style={{ whiteSpace: 'normal', height: 'auto', lineHeight: '20px', padding: '2px 8px' }}>#{idx + 1} {err}</Tag></List.Item>
                )} />
              </Card>
            )}
          </div>
        )}

        {/* 训练完成弹窗 */}
        <Modal
          title="🎉 处方训练完成！"
          open={showComplete}
          footer={[
            <Button key="close" type="primary" onClick={() => setShowComplete(false)}>关闭</Button>
          ]}
          onCancel={() => setShowComplete(false)}
          width={500}
        >
          <Result
            status="success"
            title="恭喜完成所有训练动作！"
            subTitle={`共完成 ${totalActions} 个动作`}
          />
          <Divider />
          <List
            size="small"
            header={<Typography.Text strong>各动作完成情况</Typography.Text>}
            dataSource={actionResults}
            renderItem={(item, idx) => (
              <List.Item>
                <Space>
                  <Tag color="blue">{idx + 1}</Tag>
                  <Typography.Text strong>{ACTION_NAME_MAP[item.action_name] || item.action_name}</Typography.Text>
                  {item.score !== null ? (
                    <Tag color={item.score >= 80 ? 'green' : item.score >= 60 ? 'orange' : 'red'}>{item.score}分</Tag>
                  ) : (
                    <Tag color="default">未评分</Tag>
                  )}
                  {item.errors.length > 0 && <Tag color="red">{item.errors.length}个错误</Tag>}
                </Space>
              </List.Item>
            )}
          />
        </Modal>
      </Card>
    </div>
  );
}
