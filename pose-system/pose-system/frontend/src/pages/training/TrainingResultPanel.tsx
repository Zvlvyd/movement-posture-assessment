import { useRef, useEffect } from "react";
import { Card, Button, Row, Col, Statistic, Typography, Space, Divider, Tag, Progress } from "antd";
import {
  TrophyOutlined, ArrowLeftOutlined, RightOutlined, OrderedListOutlined,
  AimOutlined, CheckCircleOutlined, WarningOutlined, CloseCircleOutlined, BulbOutlined,
} from "@ant-design/icons";
import type { LearningComplete, PlanV2, AngleDiff, LearningFeedback } from "../../types";

const { Title, Text } = Typography;

// COCO 17 关键点骨架连线
const SKELETON: [number, number][] = [
  [0, 1], [0, 2], [1, 3], [2, 4],
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  [5, 11], [6, 12], [11, 12],
  [11, 13], [13, 15], [12, 14], [14, 16],
];

// 关节角度中文名映射
const JOINT_LABELS: Record<string, string> = {
  left_knee: "左膝", right_knee: "右膝",
  left_hip: "左髋", right_hip: "右髋",
  left_elbow: "左肘", right_elbow: "右肘",
  left_shoulder: "左肩", right_shoulder: "右肩",
  trunk_tilt: "躯干倾斜", neck_tilt: "颈部倾斜",
};

// 状态图标映射
function statusIcon(status: string) {
  if (status === "good") return <CheckCircleOutlined style={{ color: "#52c41a" }} />;
  if (status === "close") return <WarningOutlined style={{ color: "#faad14" }} />;
  if (status === "warning") return <WarningOutlined style={{ color: "#fa8c16" }} />;
  if (status === "bad") return <CloseCircleOutlined style={{ color: "#f5222d" }} />;
  return null;
}

function statusColor(status: string): string {
  if (status === "good") return "#52c41a";
  if (status === "close") return "#faad14";
  if (status === "warning") return "#fa8c16";
  if (status === "bad") return "#f5222d";
  return "#d9d9d9";
}

interface Props {
  result: LearningComplete;
  plan: PlanV2;
  completedCount: number;
  totalCount: number;
  onBackToPlan: () => void;
  onNextExercise: () => void;
  onAllPlans: () => void;
}

export default function TrainingResultPanel({
  result, plan, completedCount, totalCount, onBackToPlan, onNextExercise, onAllPlans,
}: Props) {
  const isHold = result.exercise_type === "hold";
  const feedbackTotal = Object.values(result.feedback_counts || {}).reduce((a: number, b: number) => a + b, 0);
  const scoreColor = (s: number) => s >= 85 ? "#52c41a" : s >= 60 ? "#faad14" : "#f5222d";

  // ── 最佳帧骨架绘制 ──
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const hasBestFrame = result.best_frame_kp && Array.isArray(result.best_frame_kp) && result.best_frame_kp.length >= 17;

  useEffect(() => {
    if (!hasBestFrame || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const kp = result.best_frame_kp!;
    const fw = result.best_frame_fw || 640;
    const fh = result.best_frame_fh || 480;

    // 深色背景
    ctx.fillStyle = "#1a1a2e";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 计算可见关键点范围，用于自动缩放
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (let i = 0; i < kp.length; i++) {
      const [x, y] = kp[i];
      if (x > 0 && y > 0) {
        minX = Math.min(minX, x); maxX = Math.max(maxX, x);
        minY = Math.min(minY, y); maxY = Math.max(maxY, y);
      }
    }
    const padX = (maxX - minX) * 0.25;
    const padY = (maxY - minY) * 0.25;
    const bodyW = maxX - minX + padX * 2;
    const bodyH = maxY - minY + padY * 2;
    const bodyScale = Math.min(canvas.width / bodyW, canvas.height / bodyH);

    function tx(x: number) { return (x - minX + padX) * bodyScale; }
    function ty(y: number) { return (y - minY + padY) * bodyScale; }

    // 绘制骨架连线
    ctx.strokeStyle = "#52c41a";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    for (const [a, b] of SKELETON) {
      if (a >= kp.length || b >= kp.length) continue;
      const [ax, ay] = kp[a]; const [bx, by] = kp[b];
      if (ax <= 0 || ay <= 0 || bx <= 0 || by <= 0) continue;
      const confA = (result.best_frame_conf || [])[a] ?? 1;
      const confB = (result.best_frame_conf || [])[b] ?? 1;
      if (confA < 0.15 || confB < 0.15) continue;
      ctx.beginPath();
      ctx.moveTo(tx(ax), ty(ay));
      ctx.lineTo(tx(bx), ty(by));
      ctx.stroke();
    }

    // 绘制关节圆点
    for (let i = 0; i < kp.length; i++) {
      const [x, y] = kp[i];
      if (x <= 0 || y <= 0) continue;
      const conf = (result.best_frame_conf || [])[i] ?? 1;
      if (conf < 0.15) continue;
      ctx.fillStyle = "#ff4d4f";
      ctx.beginPath();
      ctx.arc(tx(x), ty(y), 4, 0, Math.PI * 2);
      ctx.fill();
    }
  }, [hasBestFrame, result.best_frame_kp, result.best_frame_conf, result.best_frame_fw, result.best_frame_fh]);

  const bestFrameAngles = result.best_frame_angles || {};
  const bestFrameDiffs = (result.best_frame_diffs || []) as AngleDiff[];
  const bestFrameFeedbacks = (result.best_frame_feedbacks || []) as LearningFeedback[];

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: 24 }}>
      <Card>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <TrophyOutlined style={{ fontSize: 48, color: "var(--color-cyan)" }} />
          <Title level={3} style={{ color: "var(--color-text-primary)" }}>训练完成！</Title>
        </div>

        {/* 最佳得分 */}
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <Statistic title="最佳得分" value={result.best_score} suffix="分"
            valueStyle={{ color: scoreColor(result.best_score), fontSize: 48, fontWeight: 700 }} />
          <Text type="secondary" style={{ fontSize: 12 }}>训练过程中单帧最高质量</Text>
        </div>

        <Row gutter={16} style={{ marginBottom: 16 }}>
          {isHold && result.hold_time !== undefined && result.hold_time > 0 && (
            <Col span={8}>
              <Statistic title="保持时长"
                value={Math.floor(result.hold_time / 60)}
                suffix={`分 ${Math.floor(result.hold_time % 60)} 秒`}
                valueStyle={{ color: "var(--color-accent)" }} />
            </Col>
          )}
          {!isHold && result.rep_count !== undefined && result.rep_count > 0 && (
            <Col span={8}>
              <Statistic title="完成次数" value={result.rep_count} suffix="次"
                valueStyle={{ color: "var(--color-accent)" }} />
            </Col>
          )}
          <Col span={8}>
            <Statistic title="训练时长" value={(result.duration / 60).toFixed(1)} suffix="分钟" />
          </Col>
          <Col span={8}>
            <Statistic title="训练帧数" value={result.frame_count} />
          </Col>
          <Col span={8}>
            <Statistic title="纠正反馈" value={feedbackTotal} suffix="条" />
          </Col>
        </Row>

        {/* ── 最佳帧分析卡片 ── */}
        {hasBestFrame && (
          <Card
            size="small"
            title={
              <Space>
                <AimOutlined style={{ color: "var(--color-primary)" }} />
                <span>最佳帧分析</span>
                <Tag color="green">最高得分帧</Tag>
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            <Row gutter={[16, 16]}>
              {/* 左侧：骨架图 */}
              <Col xs={24} md={10}>
                <canvas
                  ref={canvasRef}
                  width={320}
                  height={380}
                  style={{
                    borderRadius: 8,
                    width: "100%",
                    height: "auto",
                    background: "#1a1a2e",
                  }}
                />
              </Col>

              {/* 右侧：角度 + 偏差 + 建议 */}
              <Col xs={24} md={14}>
                {/* 关节角度标签 */}
                {Object.keys(bestFrameAngles).length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <Text strong style={{ fontSize: 13 }}>关节角度：</Text>
                    <div style={{ marginTop: 6, display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {Object.entries(bestFrameAngles).map(([joint, val]) => (
                        <Tag key={joint} color="blue" style={{ margin: 0 }}>
                          {JOINT_LABELS[joint] || joint}: {val}°
                        </Tag>
                      ))}
                    </div>
                  </div>
                )}

                {/* 角度偏差进度条 */}
                {bestFrameDiffs.length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <Text strong style={{ fontSize: 13 }}>角度偏差（与标准对比）：</Text>
                    <div style={{ marginTop: 6 }}>
                      {bestFrameDiffs.map((d, i) => {
                        const pct = d.user != null
                          ? Math.round(Math.min(100, (d.user / d.standard_optimal) * 100))
                          : 0;
                        return (
                          <div key={i} style={{ marginBottom: 8 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                              <Space size={4}>
                                {statusIcon(d.status)}
                                <Text style={{ fontSize: 12 }}>
                                  {JOINT_LABELS[d.joint] || d.joint}
                                </Text>
                              </Space>
                              <Text style={{ fontSize: 12 }}>
                                {d.user != null ? `${d.user}°` : "—"} / 标准 {d.standard_optimal}°
                              </Text>
                            </div>
                            <Progress
                              percent={pct}
                              size="small"
                              strokeColor={statusColor(d.status)}
                              format={() => `${pct}%`}
                              status={d.status === "bad" ? "exception" : d.status === "good" ? "success" : "normal"}
                            />
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* 纠错建议 */}
                {bestFrameFeedbacks.length > 0 && (
                  <div>
                    <Text strong style={{ fontSize: 13 }}>
                      <BulbOutlined style={{ marginRight: 4 }} />
                      纠错建议：
                    </Text>
                    <div style={{ marginTop: 6 }}>
                      {bestFrameFeedbacks.map((fb, i) => (
                        <div key={i} style={{
                          marginBottom: 6,
                          padding: "6px 10px",
                          borderRadius: 6,
                          background: fb.severity === "bad" || fb.severity === "warning"
                            ? "#fff2f0" : "#f6ffed",
                          border: `1px solid ${fb.severity === "bad" || fb.severity === "warning" ? "#ffccc7" : "#b7eb8f"}`,
                        }}>
                          <Text style={{ fontSize: 12 }}>{fb.message}</Text>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </Col>
            </Row>
          </Card>
        )}

        {result.summary?.length > 0 && (
          <Card size="small" title="总结建议" style={{ marginBottom: 16 }}>
            {result.summary.map((s: string, i: number) => (
              <div key={i} style={{ marginBottom: 6 }}><Text>• {s}</Text></div>
            ))}
          </Card>
        )}

        <div style={{ textAlign: "center", marginBottom: 16 }}>
          <Text type="secondary">已完成 {completedCount}/{totalCount} 个动作</Text>
        </div>

        <Divider />

        <Space size="middle" style={{ width: "100%", justifyContent: "center" }}>
          <Button size="large" icon={<ArrowLeftOutlined />} onClick={onBackToPlan}>返回计划</Button>
          {completedCount < totalCount && (
            <Button type="primary" size="large" icon={<RightOutlined />} onClick={onNextExercise}>下一个动作</Button>
          )}
          <Button size="large" icon={<OrderedListOutlined />} onClick={onAllPlans}>所有计划</Button>
        </Space>
      </Card>
    </div>
  );
}
