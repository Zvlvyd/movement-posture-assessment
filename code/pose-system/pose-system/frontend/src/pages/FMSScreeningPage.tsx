import { useState, useRef, useEffect, useCallback } from 'react';
import { Card, Button, Typography, Tag, Progress, message, Space, Spin, Result, Upload, List, Divider } from 'antd';
import { CameraOutlined, ExperimentOutlined, CheckCircleOutlined, ArrowRightOutlined, TrophyOutlined, ForwardOutlined, WarningOutlined, UploadOutlined, VideoCameraAddOutlined, CheckOutlined, CloseCircleOutlined, FileOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import MovementDemo from '../components/MovementDemo';
import { playStartBeep, playEndBeep, playCountdownBeep, playFinalBeep } from '../utils/audio';
import { fmsApi } from '../services/api';
import FMSDashboard from "./fms/FMSDashboard";

const FMS_TESTS = [
  { id: 0, name: '闭眼单腿站立', instruction: '闭上双眼，抬起单腿，尽量保持平衡（站立越久分数越高，满分60秒）' },
  { id: 1, name: '徒手过头深蹲', instruction: '双手举过头顶，做深蹲至最低点保持（膝盖弯曲角度越小分数越高）' },
  { id: 2, name: '肩关节活动度', instruction: '一手从肩上、一手从腰后向背后靠拢（双手距离越近分数越高）' },
  { id: 3, name: '平板支撑', instruction: '保持平板支撑姿势，尽量坚持（坚持越久分数越高，满分120秒）' },
  { id: 4, name: '弓步蹲对称', instruction: '先做左侧弓步蹲，再做右侧弓步蹲（左右角度越对称分数越高）' },
];

// COCO pose skeleton connections (0-indexed)
const SKELETON: [number, number][] = [
  [0, 1], [0, 2], [1, 3], [2, 4],
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  [5, 11], [6, 12], [11, 12],
  [11, 13], [13, 15], [12, 14], [14, 16],
];

type TestPhase = 'preparing' | 'countdown' | 'running' | 'completed' | 'skipped';

export default function FMSScreeningPage() {
  const navigate = useNavigate();
  const token = useAuthStore(s => s.token);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const intervalRef = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);
  const currentTestRef = useRef<number>(-1);
  const testPhaseRef = useRef<TestPhase>('preparing');

  const [currentTest, setCurrentTest] = useState(-1);
  useEffect(() => { currentTestRef.current = currentTest; }, [currentTest]);
  const [testPhase, setTestPhase] = useState<TestPhase>('preparing');
  useEffect(() => { testPhaseRef.current = testPhase; }, [testPhase]);
  const [testMessage, setTestMessage] = useState('');
  const [guidance, setGuidance] = useState('');
  const [testScore, setTestScore] = useState<number | null>(null);
  const [fmsResult, setFmsResult] = useState<any>(null);
  const [progress, setProgress] = useState(0);
  const [allScores, setAllScores] = useState<Record<number,number>>({});
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [countdown, setCountdown] = useState(0);
  const [noPersonWarning, setNoPersonWarning] = useState(false);

  // ─── 视频上传模式（每个动作单独上传） ──────────────
  const [uploadMode, setUploadMode] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState('');
  const [uploadingTestIndex, setUploadingTestIndex] = useState<number | null>(null);
  const [uploadedResults, setUploadedResults] = useState<Record<number, any>>({});

  const handleSingleTestUpload = useCallback(async (testIndex: number, file: File) => {
    if (!file) return false;
    setUploadingTestIndex(testIndex);
    setUploading(true);
    setUploadProgress(0);
    setUploadStatus(`正在上传「${FMS_TESTS[testIndex].name}」视频...`);
    try {
      const result = await fmsApi.uploadSingleTestVideo(testIndex, file, (pct) => {
        setUploadProgress(pct);
        if (pct >= 100) setUploadStatus('正在分析视频（逐帧处理中，请稍候）...');
      });
      setUploadStatus(`「${FMS_TESTS[testIndex].name}」分析完成！`);
      setUploadedResults(prev => ({
        ...prev,
        [testIndex]: result,
      }));
      message.success(`「${FMS_TESTS[testIndex].name}」评分: ${result.score} 分`);
      return true;
    } catch (e: any) {
      const errMsg = e?.response?.data?.detail || e.message || '上传失败';
      message.error(`「${FMS_TESTS[testIndex].name}」${errMsg}`);
      return false;
    } finally {
      setUploading(false);
      setUploadingTestIndex(null);
      setUploadProgress(0);
      setUploadStatus('');
    }
  }, []);

  const handleCombineResults = useCallback(async () => {
    setUploadStatus('正在生成综合报告...');
    setUploading(true);
    try {
      const result = await fmsApi.combineResults();
      playFinalBeep();
      setFmsResult(result);
    } catch (e: any) {
      const errMsg = e?.response?.data?.detail || e.message || '生成报告失败';
      message.error(errMsg);
    } finally {
      setUploading(false);
      setUploadStatus('');
    }
  }, []);

  // ─── 清理 ──────────────────────────────────────────
  const stopCamera = useCallback(() => {
    clearInterval(intervalRef.current);
    streamRef.current?.getTracks().forEach(t => t.stop());
    wsRef.current?.close();
    setStream(null);
    streamRef.current = null;
  }, []);

  useEffect(() => {
    window.addEventListener('beforeunload', stopCamera);
    window.addEventListener('pagehide', stopCamera);
    return () => {
      stopCamera();
      window.removeEventListener('beforeunload', stopCamera);
      window.removeEventListener('pagehide', stopCamera);
    };
  }, [stopCamera]);

  // ─── 骨架绘制 ──────────────────────────────────────
  const drawSkeleton = useCallback((keypointsList: any[]) => {
    const canvas = overlayCanvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) { console.log('[drawSkeleton] no canvas or video'); return; }

    const rect = canvas.getBoundingClientRect();
    const displayW = rect.width || video.videoWidth || 640;
    const displayH = rect.height || video.videoHeight || 480;
    if (displayW === 0 || displayH === 0) { console.log('[drawSkeleton] zero size', {rectW: rect.width, rectH: rect.height, vw: video.videoWidth, vh: video.videoHeight}); return; }

    canvas.width = displayW;
    canvas.height = displayH;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const scaleX = displayW / (video.videoWidth || 640);
    const scaleY = displayH / (video.videoHeight || 480);

    let personsDrawn = 0;
    for (const person of keypointsList) {
      const kps = person.keypoints || [];
      const confs = person.confidences || Array(kps.length).fill(1);
      if (kps.length < 17) { console.log('[drawSkeleton] skip: kps.length=', kps.length); continue; }

      ctx.strokeStyle = '#00ff88';
      ctx.lineWidth = 2;
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
            ctx.fillStyle = '#ff4466';
            ctx.beginPath();
            ctx.arc(x * scaleX, y * scaleY, 4, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
      personsDrawn++;
    }
    if (personsDrawn > 0 && personsDrawn % 30 === 1) {
      console.log('[drawSkeleton] drew', personsDrawn, 'persons, canvas:', canvas.width, 'x', canvas.height, 'scale:', scaleX.toFixed(2), scaleY.toFixed(2));
    }
  }, []);

  // ─── 摄像头 ────────────────────────────────────────
  const startCamera = async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      message.error('摄像头不可用：请使用 localhost 或 HTTPS 访问');
      return false;
    }
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: 'user' } });
      setStream(s);
      streamRef.current = s;
      if (videoRef.current) {
        videoRef.current.srcObject = s;
        console.log('[FMS] Camera stream attached to video element immediately');
      }
      return true;
    } catch (e: any) {
      message.error('无法访问摄像头: ' + (e.message || ''));
      return false;
    }
  };

  // ─── 帧捕获 ────────────────────────────────────────
  const startFrameCapture = useCallback(() => {
    clearInterval(intervalRef.current);
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video || !video.videoWidth) {
      // Retry after 200ms if video not ready yet
      setTimeout(() => startFrameCapture(), 200);
      return false;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return false;
    console.log('[FMS] Frame capture started');
    intervalRef.current = window.setInterval(() => {
      if (!video.videoWidth) return;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);
      const b64 = canvas.toDataURL('image/jpeg', 0.6);
      const ws = wsRef.current;
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'frame', image: b64 }));
      }
    }, 200);
    return true;
  }, []);

  const stopFrameCapture = useCallback(() => {
    clearInterval(intervalRef.current);
    console.log('[FMS] Frame capture stopped');
  }, []);

  // ─── 倒计时 → 开始检测 ──
  const startCountdown = useCallback(() => {
    setCountdown(3);
    setTestPhase('countdown');
    setNoPersonWarning(false);
    let tick = 3;
    const timer = setInterval(() => {
      tick--;
      if (tick <= 0) {
        clearInterval(timer);
        playStartBeep();
        setCountdown(0);
        setTestPhase('running');
        // 通知后端用户已准备好，开始评估帧
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'start_test' }));
        }
      } else {
        playCountdownBeep();
        setCountdown(tick);
      }
    }, 1000);
  }, []);

  // ─── 开始筛查 ──────────────────────────────────────
  const startScreening = async () => {
    setCurrentTest(0);
    setTestPhase('preparing');
    const ok = await startCamera();
    if (!ok) return;
    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${wsProtocol}://${window.location.host}/api/fms/ws?token=${token}`);
    wsRef.current = ws;
    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'start' }));
      // 连接后立即开始帧捕获，保持持续运行。前端根据 phase 决定是否处理结果。
      setTimeout(() => startFrameCapture(), 300);
    };
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      handleWSMessage(data);
    };
    ws.onerror = () => message.error('WebSocket 连接失败');
  };

  // ─── WS 消息处理 ──────────────────────────────────
  const handleWSMessage = useCallback((data: any) => {
    console.log("[FMS] WS message:", data.type, data.fms_status || data);

    if (data.type === 'test_ready') {
      // 后端通知新测试就绪
      setCurrentTest(data.test);
      setTestMessage(data.instruction || '');
      setGuidance(data.instruction || '准备开始');
      setTestScore(null);
      setNoPersonWarning(false);
      setProgress((data.test / 5) * 100);
      // 所有测试统一：用户手动点击"准备好了"才开始
      setTestPhase('preparing');

    } else if (data.type === 'test_skipped') {
      // 后端确认跳过，同步本地状态
      if (testPhaseRef.current !== 'skipped') {
        setTestPhase('skipped');
        playEndBeep();
      }

    } else if (data.type === 'frame_result') {
      // ── 无人检测：任何阶段都显示警告 ──
      if (data.fms_status === 'no_person') {
        setNoPersonWarning(true);
        if (testPhaseRef.current === 'running') {
          setTestMessage('未检测到人体，请站在摄像头正前方');
        }
        return; // 不做任何状态转换
      }

      // 有人检测到后清除警告
      setNoPersonWarning(false);

      // ── 骨架绘制（仅运行/完成阶段） ──
      if (testPhaseRef.current === 'running' || testPhaseRef.current === 'completed') {
        if (data.keypoints?.length) {
          drawSkeleton(data.keypoints);
        } else {
          console.log('[FMS] no keypoints in frame_result, keys:', Object.keys(data).filter(k => k !== 'keypoints'));
        }
        if (data.guidance) setGuidance(data.guidance);
      }

      // ── started / running ── 仅在倒计时或已运行时才推进
      if (data.fms_status === 'started' || data.fms_status === 'running') {
        if (testPhaseRef.current === 'countdown' || testPhaseRef.current === 'running') {
          if (testPhaseRef.current !== 'running') setTestPhase('running');
          setTestMessage(data.guidance || data.message || '检测中...');
        }
      }

      // ── completed ──
      else if (data.fms_status === 'completed') {
        if (testPhaseRef.current !== 'running') return;
        playEndBeep();
        setTestPhase('completed');
        setTestScore(data.score);
        setAllScores(prev => ({...prev, [currentTestRef.current]: data.score}));
        if (data.duration) setTestMessage(`保持时间: ${data.duration}秒`);
        else if (data.depth_angle) setTestMessage(`深蹲深度: ${data.depth_angle}°, 躯干倾斜: ${data.trunk_tilt}°`);
        else if (data.hand_distance) setTestMessage(`双手距离: ${data.hand_distance}cm`);
        else if (data.score) setTestMessage(`得分: ${data.score}`);
      }

      // ── step_complete ──
      else if (data.fms_status === 'step_complete') {
        setTestMessage(data.guidance || '换边继续');
      }

    } else if (data.type === 'all_tests_complete') {
      setProgress(100);
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'finish' }));
      }
    } else if (data.type === 'fms_result') {
      playFinalBeep();
      console.log('[FMS] Got fms_result, setting state:', data);
      setFmsResult(data);
      stopCamera();
    } else if (data.type === 'error') {
      message.error(data.message);
    }
  }, [drawSkeleton, stopCamera]);

  // ─── 跳过 ──────────────────────────────────────────
  const skipTest = useCallback(() => {
    playEndBeep();
    setTestPhase('skipped');
    setNoPersonWarning(false);
    message.info('已跳过当前测试');
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'skip_test' }));
    }
    // 不再自动推进 — 用户手动点击"进入下一个动作"按钮
  }, []);

  // ─── 手动推进到下一个测试 ──────────────────────────
  const advanceToNextTest = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'next_test' }));
    } else {
      message.warning('WebSocket 已断开，请刷新页面重试');
    }
  }, []);

  // ─── callback ref ──────────────────────────────────
  const videoCallbackRef = useCallback((el: HTMLVideoElement | null) => {
    (videoRef as React.MutableRefObject<HTMLVideoElement | null>).current = el;
    if (el && stream) el.srcObject = stream;
  }, [stream]);

  useEffect(() => {
    return () => { stopCamera(); };
  }, [stopCamera]);

  // ─── 结果页 ────────────────────────────────────────
  if (fmsResult) {
    return (
      <Result
        status="success"
        icon={<TrophyOutlined />}
        title="FMS 筛查完成！"
        subTitle={`综合评分: ${fmsResult.overall_score} 分 | 风险等级: ${fmsResult.risk_level}`}
        extra={[
          <Button type="primary" key="report" onClick={() => navigate('/fms/report/0', { state: { fmsResult } })}>查看详细报告</Button>,
          <Button key="done" onClick={() => navigate('/home')}>返回首页</Button>,
        ]}
      >
        <div style={{ maxWidth: 400, margin: '0 auto' }}>
          {fmsResult.scores?.map((s: any) => (
            <div key={s.dimension} style={{ margin: '4px 0', display: 'flex', justifyContent: 'space-between' }}>
              <span>{s.label || s.dimension}</span>
              <Tag color={s.score >= 60 ? 'green' : 'orange'}>{s.score}分</Tag>
            </div>
          ))}
          {fmsResult.problem_tags?.map((t: any, i: number) => (
            <Tag key={i} color="orange">{t.name}</Tag>
          ))}
        </div>
      </Result>
    );
  }

  const currentTestData = FMS_TESTS[currentTest];
  const showPreparing = testPhase === 'preparing' || testPhase === 'countdown';
  const showVideo = testPhase === 'running' || testPhase === 'completed';

  // ─── 主界面 ────────────────────────────────────────
  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <Card title={<Space><ExperimentOutlined />FMS 功能运动能力筛查</Space>}>
        {/* ── 初始页 ─────────────────────────────── */}
        {currentTest === -1 && !uploadMode && (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Typography.Title level={4}>准备开始 FMS 筛查</Typography.Title>
            <Typography.Paragraph>系统将通过摄像头实时检测您的5项运动能力指标，全程约2-3分钟。</Typography.Paragraph>
            <Typography.Paragraph type="secondary">请确保您处于光线充足的环境，全身可见。每一项检测前都会展示动作示范，请准备好后再开始。</Typography.Paragraph>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button type="primary" size="large" icon={<CameraOutlined />} onClick={startScreening}>开启摄像头，开始筛查</Button>
              <Typography.Text type="secondary" style={{ display: 'block' }}>— 或 —</Typography.Text>
              <Button size="large" icon={<VideoCameraAddOutlined />} onClick={() => setUploadMode(true)}>
                上传视频进行筛查
              </Button>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                为每个动作分别上传视频，系统将逐帧分析并评分
              </Typography.Text>
            </Space>
          </div>
        )}

        {/* ── 视频上传模式（每个动作单独上传） ──────────── */}
        {uploadMode && !fmsResult && (
          <div style={{ padding: 16 }}>
            <Typography.Title level={5}>上传各动作视频</Typography.Title>
            <Typography.Paragraph type="secondary">
              请为以下5个FMS动作分别上传对应的视频。每个视频请只包含该动作的完整过程。
            </Typography.Paragraph>

            <List
              dataSource={FMS_TESTS}
              renderItem={(test) => {
                const isUploading = uploading && uploadingTestIndex === test.id;
                const isDone = !!uploadedResults[test.id];
                const result = uploadedResults[test.id];

                return (
                  <List.Item
                    actions={[
                      <Upload
                        key="upload"
                        accept="video/mp4,video/avi,video/mov,video/webm"
                        showUploadList={false}
                        beforeUpload={(file) => {
                          handleSingleTestUpload(test.id, file);
                          return false;
                        }}
                        disabled={uploading || isDone}
                      >
                        <Button
                          size="small"
                          icon={isDone ? <CheckOutlined /> : <UploadOutlined />}
                          type={isDone ? 'default' : 'primary'}
                          disabled={uploading || isDone}
                        >
                          {isDone ? '已上传' : '上传视频'}
                        </Button>
                      </Upload>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <span>第 {test.id + 1} 项</span>
                          <Tag>{test.name}</Tag>
                          {isDone && <Tag color="green">评分: {result.score} 分</Tag>}
                        </Space>
                      }
                      description={test.instruction}
                    />
                  </List.Item>
                );
              }}
            />

            {/* 上传进度 */}
            {uploading && uploadingTestIndex !== null && (
              <div style={{ textAlign: 'center', padding: 16, background: '#fafafa', borderRadius: 8, marginTop: 8 }}>
                <Spin size="small" />
                <Typography.Text style={{ marginLeft: 8 }}>{uploadStatus}</Typography.Text>
                {uploadProgress > 0 && uploadProgress < 100 && (
                  <Progress percent={uploadProgress} size="small" style={{ maxWidth: 400, margin: '8px auto 0' }} />
                )}
              </div>
            )}

            <Divider />

            {/* 已上传结果汇总 */}
            <div style={{ marginBottom: 16 }}>
              <Typography.Text strong>已上传: {Object.keys(uploadedResults).length} / 5 项</Typography.Text>
              {Object.keys(uploadedResults).length > 0 && (
                <div style={{ marginTop: 8 }}>
                  {Object.entries(uploadedResults).map(([idx, res]) => (
                    <Tag key={idx} color="green" style={{ marginBottom: 4 }}>
                      {FMS_TESTS[Number(idx)].name}: {res.score}分
                    </Tag>
                  ))}
                </div>
              )}
            </div>

            {/* 生成报告按钮 */}
            <Button
              type="primary"
              size="large"
              block
              icon={<TrophyOutlined />}
              onClick={handleCombineResults}
              disabled={Object.keys(uploadedResults).length === 0 || uploading}
            >
              生成综合报告
            </Button>

            <Button
              style={{ marginTop: 8 }}
              block
              onClick={() => {
                setUploadMode(false);
                setUploadedResults({});
              }}
            >
              返回
            </Button>
          </div>
        )}

        {/* ── 检测中 ─────────────────────────────── */}
        {currentTest >= 0 && currentTestData && (
          <div>
            <Progress percent={Math.round(progress)} style={{ marginBottom: 16 }} />

            {/* 准备阶段：动作示范 + 准备按钮 / 倒计时 */}
            {showPreparing && (
              <div>
                <MovementDemo
                  movementName={currentTestData.name}
                  instruction={currentTestData.instruction}
                  countdown={testPhase === 'countdown' ? countdown : 0}
                />
                {testPhase === 'preparing' && (
                  <div style={{ textAlign: 'center', marginTop: 4 }}>
                    <Button type="primary" size="large" icon={<ArrowRightOutlined />} onClick={startCountdown}>
                      准备好了，开始检测
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* 无人检测警告 — 独立于视频可见性，始终可显示 */}
            {noPersonWarning && (
              <div style={{
                background: 'rgba(255,77,79,0.12)', border: '1px solid rgba(255,77,79,0.35)',
                borderRadius: 8, padding: '12px 20px', marginBottom: 8,
                display: 'flex', alignItems: 'center', gap: 10,
                animation: 'fadeInUp 0.4s ease-out',
              }}>
                <WarningOutlined style={{ fontSize: 20, color: '#ff4d4f' }} />
                <Typography.Text type="danger" strong>未检测到人体，请站在摄像头正前方，确保全身可见</Typography.Text>
              </div>
            )}

            {/* 视频区域 — isolation:isolate 创建独立层叠上下文 */}
            <div style={{
              position: 'relative',
              width: '100%',
              background: '#000',
              borderRadius: 8,
              overflow: 'hidden',
              isolation: 'isolate',
            }}>
              <video ref={videoCallbackRef} autoPlay playsInline muted style={{
                width: '100%', borderRadius: 8, background: '#000',
                visibility: showVideo ? 'visible' : 'hidden',
                position: 'relative', zIndex: 1,
              }} />
              <canvas ref={overlayCanvasRef} style={{
                position: 'absolute', top: 0, left: 0,
                width: '100%', height: '100%', borderRadius: 8,
                pointerEvents: 'none', zIndex: 10,
                visibility: showVideo ? 'visible' : 'hidden',
              }} />

              {/* 实时指导语浮层 */}
              {guidance && (
                <div style={{
                  position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)',
                  background: 'rgba(0,0,0,0.75)', color: '#fff', padding: '8px 20px',
                  borderRadius: 20, fontSize: 16, fontWeight: 500,
                  whiteSpace: 'nowrap', pointerEvents: 'none', zIndex: 20,
                }}>
                  {guidance}
                </div>
              )}
            </div>
            {/* 帧捕获 canvas — 独立于视频容器，始终可用于 toDataURL 发送帧 */}
            <canvas ref={canvasRef} style={{ display: 'none' }} />

            {/* 控制卡片 */}
            <Card size="small" style={{ marginTop: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography.Text strong>
                    第 {currentTest + 1} 项 / 共 5 项: {currentTestData.name}
                  </Typography.Text>
                  <Button size="small" icon={<ForwardOutlined />} onClick={skipTest}
                    disabled={testPhase === 'completed' || testPhase === 'skipped'}>
                    跳过此项
                  </Button>
                </div>
                <Typography.Text>{testMessage}</Typography.Text>
                {testPhase === 'preparing' && <Tag color="blue">查看示范，准备好后点击按钮</Tag>}
                {testPhase === 'countdown' && <Tag color="processing">{countdown > 0 ? `倒计时 ${countdown} 秒...` : '即将开始'}</Tag>}
                {testPhase === 'running' && (
                  noPersonWarning
                    ? <Tag icon={<WarningOutlined />} color="red">等待人体入框</Tag>
                    : <Spin indicator={<CameraOutlined style={{ fontSize: 24 }} spin />} />
                )}
                {testPhase === 'completed' && testScore !== null && (
                  <Tag icon={<CheckCircleOutlined />} color="green">完成！得分: {testScore}</Tag>
                )}
                {testPhase === 'skipped' && <Tag color="default">已跳过</Tag>}
              </Space>
            </Card>

            {/* 完成/跳过后：进入下一个动作 */}
            {testPhase === 'completed' && currentTest < 4 && (
              <Button type="primary" block style={{ marginTop: 16 }}
                icon={<ArrowRightOutlined />}
                onClick={advanceToNextTest}>
                完成此动作，进入下一个
              </Button>
            )}
            {testPhase === 'skipped' && currentTest < 4 && (
              <Button type="primary" block style={{ marginTop: 16 }}
                icon={<ArrowRightOutlined />}
                onClick={advanceToNextTest}>
                进入下一个动作
              </Button>
            )}

            {/* 最后一个动作完成/跳过后：查看结果 */}
            {(testPhase === 'completed' || testPhase === 'skipped') && currentTest === 4 && (
              <Button type="primary" block style={{ marginTop: 16 }} onClick={() => {
                if (wsRef.current?.readyState === WebSocket.OPEN) {
                  wsRef.current.send(JSON.stringify({ type: 'finish' }));
                } else {
                  const dims = ['balance','flexibility','upper_limb','core','symmetry'];
                  const scoreList = dims.map((d,i) => ({dimension:d,label:d,score:allScores[i]||0}));
                  const avg = scoreList.reduce((a,b)=>a+b.score,0)/scoreList.length;
                  const risk = avg>=70?'low':avg>=40?'medium':'high';
                  setFmsResult({overall_score:Math.round(avg),risk_level:risk,scores:scoreList,problem_tags:[],posture_report:{}});
                  stopCamera();
                }
              }}>查看结果</Button>
            )}
          </div>
        )}
      </Card>
      <FMSDashboard />
    </div>
  );
}



