import { Card, Button, Typography, Row, Col, Tag, Space, Progress } from "antd";
import { ArrowLeftOutlined, PlayCircleOutlined, CheckCircleOutlined } from "@ant-design/icons";
import type { PlanV2, PlanItemV2 } from "../../types";

const { Title, Text } = Typography;

const PHASE_LABELS: Record<string, string> = {
  warmup: "热身", main: "主训练", cooldown: "冷身",
};
const PHASE_COLORS: Record<string, string> = {
  warmup: "#3B82F6", main: "#FF006E", cooldown: "#00F0FF",
};

function getPhaseExercises(plan: PlanV2): Record<string, PlanItemV2[]> {
  const groups: Record<string, PlanItemV2[]> = { warmup: [], main: [], cooldown: [] };
  (plan.items || []).forEach(item => {
    const phase = item.phase || "main";
    if (!groups[phase]) groups[phase] = [];
    groups[phase].push(item);
  });
  return groups;
}

interface Props {
  plan: PlanV2;
  completedExercises: Set<string>;
  onBack: () => void;
  onStartExercise: (item: PlanItemV2) => void;
}

export default function PlanDetailPanel({ plan, completedExercises, onBack, onStartExercise }: Props) {
  const phaseGroups = getPhaseExercises(plan);
  const phases = Object.keys(phaseGroups).filter(p => phaseGroups[p].length > 0);
  const total = (plan.items || []).length;
  const done = completedExercises.size;

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto", padding: 24 }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={onBack}>返回</Button>
        <Title level={3} style={{ margin: 0, color: "var(--color-text-primary)" }}>{plan.plan_name}</Title>
        <Tag color="green">已激活</Tag>
      </Space>

      {plan.overall_strategy && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Text type="secondary">{plan.overall_strategy}</Text>
        </Card>
      )}

      <Progress
        percent={Math.round((done / Math.max(1, total)) * 100)}
        format={() => `${done}/${total}`}
        style={{ marginBottom: 24 }}
      />

      {phases.map(phase => {
        const exercises = phaseGroups[phase];
        return (
          <Card key={phase} size="small"
            title={<Tag color={PHASE_COLORS[phase]} style={{ fontSize: 14, padding: "2px 12px" }}>
              {PHASE_LABELS[phase] || phase} ({exercises.length} 个动作)
            </Tag>}
            style={{ marginBottom: 12 }}
          >
            {exercises.map((item, idx) => {
              const isDone = completedExercises.has(item.action_name);
              return (
                <Row key={item.id} align="middle"
                  style={{
                    padding: "12px 16px", marginBottom: 8, borderRadius: "var(--radius-md)",
                    background: isDone ? "rgba(0, 240, 255, 0.05)" : "var(--color-bg-hover)",
                    border: `1px solid ${isDone ? "rgba(0, 240, 255, 0.15)" : "rgba(255,255,255,0.04)"}`,
                  }}
                >
                  <Col flex="40px">
                    {isDone ? <CheckCircleOutlined style={{ color: "#52c41a", fontSize: 22 }} /> :
                      <Text style={{ color: "var(--color-text-muted)", fontSize: 18, fontWeight: 600 }}>{idx + 1}</Text>}
                  </Col>
                  <Col flex="auto">
                    <Text strong style={{ color: "var(--color-text-primary)" }}>{item.action_name}</Text>
                    <div>
                      <Space size={4}>
                        <Tag>{item.sets} 组 x {item.reps} 次</Tag>
                        {item.intensity && <Tag color={item.intensity === "HIGH" ? "red" : item.intensity === "MEDIUM" ? "orange" : "green"}>{item.intensity}</Tag>}
                        <Text type="secondary" style={{ fontSize: 12 }}>{item.duration_seconds}s</Text>
                        {item.is_substitution && <Tag color="warning">替代</Tag>}
                      </Space>
                    </div>
                  </Col>
                  <Col>
                    <Button type="primary" size="middle"
                      icon={isDone ? <CheckCircleOutlined /> : <PlayCircleOutlined />}
                      onClick={() => onStartExercise(item)}
                      style={isDone ? { background: "rgba(0,240,255,0.2)" } : {}}
                    >
                      {isDone ? "再练一次" : "开始训练"}
                    </Button>
                  </Col>
                </Row>
              );
            })}
          </Card>
        );
      })}
    </div>
  );
}
