import { Card, Button, Row, Col, Statistic, Typography, Space, Divider } from "antd";
import { TrophyOutlined, ArrowLeftOutlined, RightOutlined, OrderedListOutlined } from "@ant-design/icons";
import type { LearningComplete, PlanV2 } from "../../types";

const { Title, Text } = Typography;

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
  return (
    <div style={{ maxWidth: 700, margin: "0 auto", padding: 24 }}>
      <Card>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <TrophyOutlined style={{ fontSize: 48, color: "var(--color-cyan)" }} />
          <Title level={3} style={{ color: "var(--color-text-primary)" }}>训练完成！</Title>
        </div>

        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Statistic title="总分" value={result.total_score} suffix="分"
              valueStyle={{ color: result.total_score >= 70 ? "#52c41a" : "#faad14", fontSize: 32 }} />
          </Col>
          <Col span={8}>
            <Statistic title="最佳得分" value={result.best_score} suffix="分" />
          </Col>
          <Col span={8}>
            <Statistic title="训练帧数" value={result.frame_count} />
          </Col>
        </Row>

        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={12}>
            <Statistic title="训练时长" value={(result.duration / 60).toFixed(1)} suffix="分钟" />
          </Col>
          <Col span={12}>
            <Statistic title="反馈次数"
              value={Object.values(result.feedback_counts || {}).reduce((a: number, b: number) => a + b, 0)} />
          </Col>
        </Row>

        {result.summary?.length > 0 && (
          <Card size="small" title="总结建议" style={{ marginBottom: 16 }}>
            {result.summary.map((s: string, i: number) => (
              <div key={i} style={{ marginBottom: 6 }}><Text>• {s}</Text></div>
            ))}
          </Card>
        )}

        <div style={{ textAlign: "center" }}>
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
