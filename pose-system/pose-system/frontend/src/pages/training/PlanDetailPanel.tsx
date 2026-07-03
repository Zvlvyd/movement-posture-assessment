import { Card, Button, Typography, Row, Col, Tag, Space, Progress } from "antd";
import { ArrowLeftOutlined, PlayCircleOutlined, CheckCircleOutlined, TrophyOutlined } from "@ant-design/icons";
import type { PlanV2, PlanItemV2 } from "../../types";

const { Title, Text } = Typography;

interface ItemProgressInfo {
  sets_done: number;
  total_sets: number;
  latest_reps: number;
  latest_score: number;
}

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
  completedItems: Set<number>;
  itemProgress: Map<number, ItemProgressInfo>;
  onBack: () => void;
  onStartExercise: (item: PlanItemV2) => void;
}

export default function PlanDetailPanel({ plan, completedItems, itemProgress, onBack, onStartExercise }: Props) {
  const phaseGroups = getPhaseExercises(plan);
  const phases = Object.keys(phaseGroups).filter(p => phaseGroups[p].length > 0);
  const total = (plan.items || []).length;
  const done = completedItems.size;

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
              const isDone = completedItems.has(item.id);
              const prog = itemProgress.get(item.id);
              const setsDone = prog ? Math.min(prog.sets_done, item.sets) : 0;
              const currentSet = Math.min(setsDone + 1, item.sets);
              const isCurrentSet = setsDone < item.sets;
              // 只有当前组未达标时才显示部分进度（latest_reps < target_reps）
              const partialReps = isCurrentSet && prog && prog.latest_reps > 0 && prog.latest_reps < item.reps
                ? prog.latest_reps : 0;

              return (
                <Row key={item.id} align="top"
                  style={{
                    padding: "12px 16px", marginBottom: 8, borderRadius: "var(--radius-md)",
                    background: isDone ? "rgba(0, 240, 255, 0.05)" : "var(--color-bg-hover)",
                    border: `1px solid ${isDone ? "rgba(0, 240, 255, 0.15)" : "rgba(255,255,255,0.04)"}`,
                  }}
                >
                  <Col flex="40px" style={{ paddingTop: 2 }}>
                    {isDone ? <CheckCircleOutlined style={{ color: "#52c41a", fontSize: 22 }} /> :
                      <Text style={{ color: "var(--color-text-muted)", fontSize: 18, fontWeight: 600 }}>{idx + 1}</Text>}
                  </Col>
                  <Col flex="auto">
                    <Text strong style={{ color: "var(--color-text-primary)" }}>{item.action_name}</Text>
                    <div style={{ marginTop: 4 }}>
                      {/* 每组进度块 */}
                      <div style={{ display: "flex", gap: 4, marginBottom: 4, flexWrap: "wrap" }}>
                        {Array.from({ length: item.sets }, (_, i) => {
                          const setNum = i + 1;
                          const setDone = setNum <= setsDone;
                          const isCur = setNum === currentSet && isCurrentSet;
                          return (
                            <div key={i} style={{
                              width: 28, height: 28, borderRadius: 6,
                              display: "flex", alignItems: "center", justifyContent: "center",
                              fontSize: 11, fontWeight: 700,
                              background: setDone ? "#52c41a" : isCur ? "var(--color-accent)" : "rgba(255,255,255,0.08)",
                              color: setDone || isCur ? "#fff" : "var(--color-text-muted)",
                              transition: "all 0.3s",
                            }}>
                              {setDone ? "✓" : setNum}
                            </div>
                          );
                        })}
                      </div>
                      <Space size={4} wrap>
                        <Tag>{item.sets} 组 x {item.reps} 次</Tag>
                        {isCurrentSet && partialReps > 0 && (
                          <Tag color="var(--color-accent)">第{currentSet}组已完成 {partialReps}/{item.reps} 次</Tag>
                        )}
                        {prog && prog.latest_score > 0 && (
                          <Tag icon={<TrophyOutlined />} color="gold">{prog.latest_score}分</Tag>
                        )}
                        {item.is_substitution && <Tag color="warning">替代</Tag>}
                      </Space>
                    </div>
                  </Col>
                  <Col style={{ paddingTop: 4 }}>
                    <Button type="primary" size="middle"
                      icon={isDone ? <CheckCircleOutlined /> : <PlayCircleOutlined />}
                      onClick={() => onStartExercise(item)}
                      style={isDone ? { background: "rgba(0,240,255,0.2)" } : {}}
                    >
                      {isDone ? "再练一组" : setsDone > 0 ? `第${currentSet}组` : "开始训练"}
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
