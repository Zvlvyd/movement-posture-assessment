import { useEffect, useState, useRef, useCallback } from 'react';
import {
  Card, Select, List, Typography, Tag, Spin, Button, Space, Progress,
  Row, Col, Badge, Divider, Empty, message, Descriptions, Segmented,
} from 'antd';
import {
  PlayCircleOutlined, StopOutlined,
  TrophyOutlined, BulbOutlined, EyeOutlined, ArrowLeftOutlined,
  CheckCircleOutlined, CloseCircleOutlined, WarningOutlined,
} from '@ant-design/icons';
import { learningApi, createLearningWS } from '../services/api';
import type {
  ActionItem, LearnableAction, LearnableActionDetail, StandardAngles,
  AngleDiff, LearningFeedback, LearningComplete,
} from '../types';

const { Title, Text } = Typography;

type PageMode = 'list' | 'detail' | 'learning' | 'result';

const STATUS_COLORS: Record<string, string> = {
  good: '#52c41a',
  close: '#faad14',
  warning: '#fa8c16',
  bad: '#f5222d',
  unknown: '#d9d9d9',
};

const STATUS_LABELS: Record<string, string> = {
  good: '达标',
  close: '接近',
  warning: '偏差',
  bad: '严重偏差',
  unknown: '—',
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  good: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
  close: <WarningOutlined style={{ color: '#faad14' }} />,
  warning: <WarningOutlined style={{ color: '#fa8c16' }} />,
  bad: <CloseCircleOutlined style={{ color: '#f5222d' }} />,
};

export default function LearningPage() {
  // --- List mode ---
  const [mode, setMode] = useState<PageMode>('list');
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [learnable, setLearnable] = useState<LearnableAction[]>([]);
  const [category, setCategory] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);

  // --- Detail mode ---
  const [selectedAction, setSelectedAction] = useState<LearnableActionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // --- Learning mode ---
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [currentView, setCurrentView] = useState<string>('正面');
  const [standardAngles, setStandardAngles] = useState<StandardAngles>({});
  const [keyChecks, setKeyChecks] = useState<any[]>([]);
  const [instruction, setInstruction] = useState('');
  const [diffs, setDiffs] = useState<AngleDiff[]>([]);
  const [feedbacks, setFeedbacks] = useState<LearningFeedback[]>([]);
  const [overallScore, setOverallScore] = useState<number | null>(null);
  const [bestScore, setBestScore] = useState(0);
  const [frameCount, setFrameCount] = useState(0);
  const [isSessionActive, setIsSessionActive] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const intervalRef = useRef<number | null>(null);

  // --- Result mode ---
  const [result, setResult] = useState<LearningComplete | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera();
      closeWS();
    };
  }, []);

  // --- Data loading ---
  useEffect(() => {
    if (mode === 'list') {
      setLoading(true);
      Promise.all([
        learningApi.getActions(category),
        learningApi.getLearnable().catch(() => [] as LearnableAction[]),
      ]).then(([acts, learn]) => {
        setActions(acts);
        setLearnable(learn);
      }).finally(() => setLoading(false));
    }
  }, [category, mode]);

  // --- Camera ---
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      streamRef.current = stream;
    } catch (e) {
      message.error('无法访问摄像头，请检查权限设置');
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const closeWS = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setWs(null);
  }, []);

  // --- Frame capture and send ---
  const captureAndSend = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.6);
    wsRef.current.send(JSON.stringify({
      type: 'frame',
      data: dataUrl,
    }));
  }, []);

  // --- Enter learning mode ---
  const enterLearning = useCallback(async (actionName: string) => {
    setDetailLoading(true);
    try {
      const detail = await learningApi.getLearnableDetail(actionName);
      setSelectedAction(detail);

      // Switch to learning
      setMode('learning');
      await startCamera();

      const token = localStorage.getItem('token') || '';
      const socket = createLearningWS(token);
      wsRef.current = socket;
      setWs(socket);

      socket.onopen = () => {
        socket.send(JSON.stringify({
          type: 'start',
          action: actionName,
          view: detail.views?.[0] || '正面',
        }));
        setCurrentView(detail.views?.[0] || '正面');
        setIsSessionActive(true);

        // Start frame capture interval
        intervalRef.current = window.setInterval(() => {
          captureAndSend();
        }, 150); // ~6-7 fps, balanced
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWSMessage(data);
      };

      socket.onerror = () => {
        message.error('WebSocket 连接失败');
        setIsSessionActive(false);
      };

      socket.onclose = () => {
        setIsSessionActive(false);
      };
    } catch (e) {
      message.error('加载动作数据失败');
      setMode('list');
    } finally {
      setDetailLoading(false);
    }
  }, [startCamera, captureAndSend]);

  const handleWSMessage = useCallback((data: any) => {
    switch (data.type) {
      case 'session_ready':
        setStandardAngles(data.standard_angles || {});
        setKeyChecks(data.key_checks || []);
        setInstruction(data.instruction || '');
        setDiffs([]);
        setFeedbacks([]);
        setOverallScore(null);
        setBestScore(0);
        setFrameCount(0);
        break;

      case 'comparison':
        setDiffs(data.diffs || []);
        setFeedbacks(data.feedbacks || []);
        setOverallScore(data.overall_score);
        setBestScore(data.best_score || 0);
        setFrameCount(data.frame || 0);
        break;

      case 'view_switched':
        setCurrentView(data.view);
        setStandardAngles(data.standard_angles || {});
        setKeyChecks(data.key_checks || []);
        break;

      case 'learning_complete':
        setResult(data);
        setMode('result');
        stopCamera();
        closeWS();
        setIsSessionActive(false);
        break;

      case 'error':
        message.error(data.message);
        break;
    }
  }, [stopCamera, closeWS]);

  // --- End session ---
  const endSession = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'finish' }));
    }
  }, []);

  const switchView = useCallback((view: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'switch_view', view }));
    }
  }, []);

  // --- Render: List mode ---
  if (mode === 'list') {
    const learnableNames = new Set(learnable.map(l => l.name));
    return (
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <Title>标准动作学习</Title>

        {/* Learnable actions with standard learning mode */}
        {learnable.length > 0 && (
          <Card title="标准学习模式" style={{ marginBottom: 24 }}
            extra={<Tag color="blue">{learnable.length} 个可学习动作</Tag>}>
            <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
              以下动作支持实时对比学习：系统将逐帧对比您的动作与标准角度，给出精细化反馈。
            </Text>
            <List
              dataSource={learnable}
              renderItem={(item: LearnableAction) => (
                <List.Item
                  actions={[
                    <Button type="primary" icon={<PlayCircleOutlined />}
                      onClick={() => enterLearning(item.name)}>
                      进入标准学习
                    </Button>,
                  ]}>
                  <List.Item.Meta
                    title={<Space>{item.name}<Tag>{item.category}</Tag></Space>}
                    description={item.description}
                  />
                </List.Item>
              )}
            />
          </Card>
        )}

        {/* Full action library */}
        <Card title="全部动作库">
          <Select placeholder="筛选分类" allowClear style={{ width: 200, marginBottom: 16 }}
            onChange={setCategory}
            options={[
              { value: '下肢', label: '下肢' },
              { value: '上肢', label: '上肢' },
              { value: '核心', label: '核心' },
            ]} />
          {loading ? <Spin /> : (
            <List
              dataSource={actions}
              renderItem={(item: ActionItem) => (
                <List.Item actions={
                  learnableNames.has(item.name)
                    ? [<Button size="small" icon={<PlayCircleOutlined />}
                        onClick={() => enterLearning(item.name)}>标准学习</Button>]
                    : undefined
                }>
                  <List.Item.Meta
                    title={<Space>{item.name}<Tag>{item.category}</Tag></Space>}
                    description={
                      <Space>
                        <Tag color="blue">难度 {item.difficulty}</Tag>
                        {item.description && <Text type="secondary">{item.description}</Text>}
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Card>
      </div>
    );
  }

  // --- Render: Learning mode ---
  if (mode === 'learning') {
    return (
      <div style={{ height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
        {/* Top bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => {
              stopCamera();
              closeWS();
              setMode('list');
            }}>返回</Button>
            <Title>{selectedAction?.name || ''} — 标准学习</Title>
            {bestScore > 0 && (
              <Tag color="gold" icon={<TrophyOutlined />}>最佳 {bestScore} 分</Tag>
            )}
          </Space>
          <Space>
            <Text type="secondary">视角:</Text>
            <Segmented
              value={currentView}
              onChange={(val) => switchView(val as string)}
              options={(selectedAction?.views || ['正面']).map(v => ({ label: v, value: v }))}
            />
          </Space>
        </div>

        <Row gutter={16} style={{ flex: 1, overflow: 'hidden' }}>
          {/* Left: Video + skeleton */}
          <Col span={16} style={{ height: '100%' }}>
            <div style={{
              position: 'relative', background: '#000', borderRadius: 8,
              width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <video ref={videoRef} autoPlay playsInline muted
                style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              {/* Hidden canvas for frame capture */}
              <canvas ref={canvasRef} style={{ display: 'none' }} />

              {/* Status indicator */}
              {isSessionActive && (
                <div style={{ position: 'absolute', top: 12, left: 12, display: 'flex', gap: 8 }}>
                  <Badge status="processing" text="实时分析中" />
                  <Tag>{frameCount} 帧</Tag>
                </div>
              )}

              {/* Score overlay */}
              {overallScore !== null && (
                <div style={{
                  position: 'absolute', top: 12, right: 12,
                  background: 'rgba(0,0,0,0.7)', borderRadius: 12,
                  padding: '8px 16px', color: '#fff', textAlign: 'center',
                }}>
                  <div style={{ fontSize: 28, fontWeight: 'bold', color: overallScore >= 70 ? '#52c41a' : overallScore >= 40 ? '#faad14' : '#f5222d' }}>
                    {overallScore}
                  </div>
                  <div style={{ fontSize: 12 }}>当前得分</div>
                </div>
              )}

              {/* Instruction overlay */}
              {isSessionActive && instruction && (
                <div style={{
                  position: 'absolute', bottom: 12, left: 12, right: 12,
                  background: 'rgba(0,0,0,0.6)', borderRadius: 8,
                  padding: '8px 16px', color: '#fff', fontSize: 13,
                }}>
                  <BulbOutlined style={{ marginRight: 8 }} />{instruction}
                </div>
              )}
            </div>
          </Col>

          {/* Right: Analysis panel */}
          <Col span={8} style={{ height: '100%', overflow: 'auto' }}>
            {/* Action checks */}
            <Card size="small" title="动作要领检查" style={{ marginBottom: 12 }}>
              {keyChecks.map((check, i) => (
                <div key={i} style={{ marginBottom: 8, fontSize: 13 }}>
                  <EyeOutlined style={{ marginRight: 6, color: '#1890ff' }} />
                  {check.rule}
                  <Tag style={{ marginLeft: 8 }}>{check.threshold}{check.unit}</Tag>
                </div>
              ))}
              {keyChecks.length === 0 && <Text type="secondary">等待数据...</Text>}
            </Card>

            {/* Angle diffs chart */}
            <Card size="small" title="关节角度差异" style={{ marginBottom: 12 }}>
              {diffs.length > 0 ? (
                diffs.map((d: AngleDiff) => (
                  <div key={d.joint} style={{ marginBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 2 }}>
                      <Space size={4}>
                        {STATUS_ICONS[d.status]}
                        <span>{d.joint}</span>
                      </Space>
                      <span>
                        {d.user !== null ? `${d.user}°` : '—'} /
                        <Text type="secondary"> 标准 {d.standard_optimal}° ({d.standard_range})</Text>
                      </span>
                    </div>
                    <Progress
                      percent={d.user !== null ? Math.min(100, (d.user / d.standard_optimal) * 100) : 0}
                      strokeColor={STATUS_COLORS[d.status] || '#d9d9d9'}
                      size="small"
                      format={() => STATUS_LABELS[d.status]}
                    />
                  </div>
                ))
              ) : (
                <Empty description="等待动作数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>

            {/* Real-time feedback */}
            <Card size="small" title={
              <Space>
                <span>实时反馈</span>
                {feedbacks.length > 0 && <Tag color="error">{feedbacks.length}</Tag>}
              </Space>
            }>
              {feedbacks.length > 0 ? (
                feedbacks.map((fb: LearningFeedback, i) => (
                  <div key={i} style={{
                    padding: '8px 12px', marginBottom: 6, borderRadius: 6,
                    background: fb.severity === 'bad' ? '#fff2f0' : fb.severity === 'warning' ? '#fff7e6' : '#f6ffed',
                    border: `1px solid ${fb.severity === 'bad' ? '#ffccc7' : fb.severity === 'warning' ? '#ffd591' : '#b7eb8f'}`,
                    fontSize: 13,
                  }}>
                    <WarningOutlined style={{
                      color: fb.severity === 'bad' ? '#f5222d' : fb.severity === 'warning' ? '#fa8c16' : '#52c41a',
                      marginRight: 6,
                    }} />
                    {fb.message}
                  </div>
                ))
              ) : (
                <div style={{ padding: 12, textAlign: 'center', color: '#52c41a' }}>
                  <CheckCircleOutlined style={{ fontSize: 24, marginBottom: 8 }} />
                  <div>动作标准，继续保持！</div>
                </div>
              )}
            </Card>
          </Col>
        </Row>

        {/* Bottom controls */}
        <div style={{ textAlign: 'center', padding: '16px 0 8px' }}>
          <Space size="large">
            <Button type="primary" danger size="large" icon={<StopOutlined />}
              onClick={endSession} loading={!isSessionActive && mode === 'learning'}>
              结束学习
            </Button>
          </Space>
        </div>
      </div>
    );
  }

  // --- Render: Result mode ---
  if (mode === 'result' && result) {
    return (
      <div style={{ maxWidth: 700, margin: '0 auto' }}>
        <Card>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <TrophyOutlined style={{ fontSize: 48, color: '#faad14' }} />
            <Title>学习完成！</Title>
            <div style={{ fontSize: 48, fontWeight: 'bold', color: result.total_score >= 70 ? '#52c41a' : result.total_score >= 40 ? '#faad14' : '#f5222d' }}>
              {result.total_score} <span style={{ fontSize: 18 }}>分</span>
            </div>
            <Text type="secondary">动作标准度评分</Text>
          </div>

          <Descriptions bordered column={2} size="small" style={{ marginBottom: 16 }}>
            <Descriptions.Item label="最佳得分">{result.best_score} 分</Descriptions.Item>
            <Descriptions.Item label="学习时长">{result.duration} 秒</Descriptions.Item>
            <Descriptions.Item label="分析帧数">{result.frame_count} 帧</Descriptions.Item>
            <Descriptions.Item label="动作名称">{selectedAction?.name}</Descriptions.Item>
          </Descriptions>

          <Divider>分析总结</Divider>
          {result.summary.map((line, i) => (
            <div key={i} style={{ marginBottom: 8, fontSize: 14, lineHeight: 1.6 }}>
              <BulbOutlined style={{ marginRight: 8, color: '#1890ff' }} />
              {line}
            </div>
          ))}

          {Object.keys(result.feedback_counts).length > 0 && (
            <>
              <Divider>错误统计</Divider>
              {Object.entries(result.feedback_counts).map(([name, count]) => (
                <div key={name} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
                  <span>{name}</span>
                  <Tag>{count} 次</Tag>
                </div>
              ))}
            </>
          )}

          <div style={{ textAlign: 'center', marginTop: 24 }}>
            <Space>
              <Button type="primary" size="large" onClick={() => {
                setMode('list');
                setResult(null);
              }}>返回动作库</Button>
              <Button size="large" onClick={() => {
                if (selectedAction) enterLearning(selectedAction.name);
              }}>再练一次</Button>
            </Space>
          </div>
        </Card>
      </div>
    );
  }

  // Fallback / loading
  return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
}
