import React from "react";
import { Row, Col, Card, Tag, Space, Badge, Progress, Button, Typography, Descriptions, Segmented, Empty } from "antd";
import {
  TrophyOutlined, BulbOutlined, EyeOutlined,
  CheckCircleOutlined, CloseCircleOutlined, WarningOutlined,
  StopOutlined,
} from "@ant-design/icons";
import type { AngleDiff, LearningFeedback } from "../types";
import type { TrainingSessionState, TrainingSessionActions } from "../hooks/useTrainingSession";

const { Text, Title } = Typography;

// ---------- Constants ----------

const STATUS_ICONS: Record<string, React.ReactNode> = {
  good: <CheckCircleOutlined style={{ color: "#52c41a" }} />,
  close: <WarningOutlined style={{ color: "#faad14" }} />,
  warning: <WarningOutlined style={{ color: "#fa8c16" }} />,
  bad: <CloseCircleOutlined style={{ color: "#f5222d" }} />,
  unknown: <EyeOutlined style={{ color: "#d9d9d9" }} />,
};
const STATUS_COLORS: Record<string, string> = {
  good: "#52c41a", close: "#faad14", warning: "#fa8c16", bad: "#f5222d", unknown: "#d9d9d9",
};
const STATUS_LABELS: Record<string, string> = {
  good: "优秀", close: "接近", warning: "注意", bad: "偏差", unknown: "未知",
};

// ---------- Props ----------

interface TrainingSessionPanelProps {
  state: TrainingSessionState;
  actions: TrainingSessionActions;
  /** Optional: display info about current exercise */
  exerciseInfo?: {
    name: string;
    sets?: number;
    reps?: number;
    durationSeconds?: number;
    notes?: string;
  };
  /** Available views for the segmented control */
  views?: string[];
  /** Called when user clicks "退出" */
  onExit: () => void;
}

// ---------- Component ----------

export default function TrainingSessionPanel({
  state, actions, exerciseInfo, views, onExit,
}: TrainingSessionPanelProps) {
  const {
    isSessionActive, currentView, standardAngles, keyChecks,
    instruction, diffs, feedbacks, overallScore, bestScore, frameCount,
  } = state;
  const { videoRef, canvasRef, endSession, switchView } = actions;

  const availableViews = views?.length ? views : ["正面"];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 80px)", padding: "0 16px 16px" }}>
      {/* Top bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0" }}>
        <Space>
          <Button size="small" onClick={onExit}>退出</Button>
          <Title level={5} style={{ margin: 0, color: "var(--color-text-primary)" }}>
            {exerciseInfo?.name || "训练中"}
          </Title>
          {bestScore > 0 && (
            <Tag color="gold" icon={<TrophyOutlined />}>最佳 {bestScore} 分</Tag>
          )}
        </Space>
        <Space>
          <Text type="secondary">视角:</Text>
          <Segmented
            value={currentView}
            onChange={(val) => switchView(val as string)}
            options={availableViews.map(v => ({ label: v, value: v }))}
          />
        </Space>
      </div>

      {/* Main: Video + Analysis */}
      <Row gutter={16} style={{ flex: 1, overflow: "hidden" }}>
        {/* Video */}
        <Col span={16} style={{ height: "100%" }}>
          <div style={{
            position: "relative", background: "#000", borderRadius: "var(--radius-md)",
            width: "100%", height: "100%", display: "flex", alignItems: "center",
            justifyContent: "center", overflow: "hidden",
          }}>
            <video ref={videoRef as React.RefObject<HTMLVideoElement>} autoPlay playsInline muted
              style={{ width: "100%", height: "100%", objectFit: "contain" }} />
            <canvas ref={canvasRef as React.RefObject<HTMLCanvasElement>} style={{ display: "none" }} />

            {isSessionActive && (
              <div style={{ position: "absolute", top: 12, left: 12, display: "flex", gap: 8 }}>
                <Badge status="processing" text="实时分析中" />
                <Tag>{frameCount} 帧</Tag>
              </div>
            )}

            {overallScore !== null && (
              <div style={{
                position: "absolute", top: 12, right: 12,
                background: "rgba(0,0,0,0.7)", borderRadius: 12,
                padding: "8px 16px", color: "#fff", textAlign: "center",
              }}>
                <div style={{
                  fontSize: 28, fontWeight: "bold",
                  color: overallScore >= 70 ? "#52c41a" : overallScore >= 40 ? "#faad14" : "#f5222d",
                }}>{overallScore}</div>
                <div style={{ fontSize: 12 }}>当前得分</div>
              </div>
            )}

            {isSessionActive && instruction && (
              <div style={{
                position: "absolute", bottom: 12, left: 12, right: 12,
                background: "rgba(0,0,0,0.6)", borderRadius: 8,
                padding: "8px 16px", color: "#fff", fontSize: 13,
              }}>
                <BulbOutlined style={{ marginRight: 8 }} />{instruction}
              </div>
            )}
          </div>
        </Col>

        {/* Analysis Panel */}
        <Col span={8} style={{ height: "100%", overflow: "auto" }}>
          {exerciseInfo && (
            <Card size="small" style={{ marginBottom: 12 }}>
              <Descriptions size="small" column={1}>
                <Descriptions.Item label="动作">{exerciseInfo.name}</Descriptions.Item>
                {exerciseInfo.sets !== undefined && exerciseInfo.reps !== undefined && (
                  <Descriptions.Item label="组数">{exerciseInfo.sets} 组 x {exerciseInfo.reps} 次</Descriptions.Item>
                )}
                {exerciseInfo.durationSeconds !== undefined && (
                  <Descriptions.Item label="时长">{exerciseInfo.durationSeconds}s</Descriptions.Item>
                )}
              </Descriptions>
              {exerciseInfo.notes && (
                <Text type="secondary" style={{ fontSize: 12 }}>备注: {exerciseInfo.notes}</Text>
              )}
            </Card>
          )}

          {/* Key checks */}
          <Card size="small" title="动作要点" style={{ marginBottom: 12 }}>
            {keyChecks.length > 0 ? (
              keyChecks.map((check, i) => (
                <div key={i} style={{ marginBottom: 8, fontSize: 13 }}>
                  <EyeOutlined style={{ marginRight: 6, color: "var(--color-cyan)" }} />
                  {check.rule}
                  <Tag style={{ marginLeft: 8 }}>{check.threshold}{check.unit}</Tag>
                </div>
              ))
            ) : (
              <Text type="secondary">等待数据...</Text>
            )}
          </Card>

          {/* Angle diffs */}
          <Card size="small" title="关节角度差异" style={{ marginBottom: 12 }}>
            {diffs.length > 0 ? (
              diffs.map((d: AngleDiff) => (
                <div key={d.joint} style={{ marginBottom: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 2 }}>
                    <Space size={4}>
                      {STATUS_ICONS[d.status]}
                      <span>{d.joint}</span>
                    </Space>
                    <span>
                      {d.user !== null ? `${d.user}°` : "-"} /
                      <Text type="secondary"> 标准 {d.standard_optimal}°</Text>
                    </span>
                  </div>
                  <Progress
                    percent={d.user !== null ? Math.min(100, (d.user / d.standard_optimal) * 100) : 0}
                    strokeColor={STATUS_COLORS[d.status] || "#d9d9d9"}
                    size="small"
                    format={() => STATUS_LABELS[d.status]}
                  />
                </div>
              ))
            ) : (
              <Empty description="等待分析数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>

          {/* Feedback */}
          <Card size="small" title={
            <Space>
              <span>实时反馈</span>
              {feedbacks.length > 0 && <Tag color="error">{feedbacks.length}</Tag>}
            </Space>
          }>
            {feedbacks.length > 0 ? (
              feedbacks.map((fb: LearningFeedback, i) => (
                <div key={i} style={{
                  padding: "8px 12px", marginBottom: 6, borderRadius: 6,
                  background: fb.severity === "bad" ? "rgba(245,34,45,0.1)" :
                    fb.severity === "warning" ? "rgba(250,140,22,0.1)" : "rgba(82,196,26,0.1)",
                  border: `1px solid ${fb.severity === "bad" ? "rgba(245,34,45,0.2)" :
                    fb.severity === "warning" ? "rgba(250,140,22,0.2)" : "rgba(82,196,26,0.2)"}`,
                  fontSize: 13,
                }}>
                  <WarningOutlined style={{
                    color: fb.severity === "bad" ? "#f5222d" :
                      fb.severity === "warning" ? "#fa8c16" : "#52c41a",
                    marginRight: 6,
                  }} />
                  {fb.message}
                </div>
              ))
            ) : (
              <div style={{ padding: 12, textAlign: "center", color: "#52c41a" }}>
                <CheckCircleOutlined style={{ fontSize: 24, marginBottom: 8 }} />
                <div>动作标准，继续保持！</div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Bottom controls */}
      <div style={{ textAlign: "center", padding: "12px 0 4px" }}>
        <Space size="large">
          <Button type="primary" danger size="large" icon={<StopOutlined />}
            onClick={endSession} loading={!isSessionActive}>
            结束训练
          </Button>
        </Space>
      </div>
    </div>
  );
}
