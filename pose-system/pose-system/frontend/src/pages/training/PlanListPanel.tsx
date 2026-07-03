import { Card, Col, Row, Space, Tag, Typography, Statistic, Spin, Empty, Button } from "antd";
import { OrderedListOutlined, ExperimentOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { PlanV2 } from "../../types";

const { Text, Title, Paragraph } = Typography;

interface Props {
  plans: PlanV2[];
  loading: boolean;
  onSelectPlan: (plan: PlanV2) => void;
}

export default function PlanListPanel({ plans, loading, onSelectPlan }: Props) {
  const navigate = useNavigate();

  const getTotalExercises = (plan: PlanV2) => (plan.items || []).length;

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Space>
          <OrderedListOutlined style={{ fontSize: 24, color: "var(--color-primary)" }} />
          <Title level={3} style={{ margin: 0, color: "var(--color-text-primary)" }}>计划训练</Title>
        </Space>
        <Paragraph type="secondary" style={{ marginTop: 4 }}>选择激活的训练计划，开始跟练</Paragraph>
      </div>

      <Spin spinning={loading}>
        {plans.length === 0 ? (
          <Card>
            <Empty description="暂无激活的训练计划">
              <Button type="primary" icon={<ExperimentOutlined />} onClick={() => navigate("/prescription")}>
                去生成处方
              </Button>
            </Empty>
          </Card>
        ) : (
          <Row gutter={[16, 16]}>
            {plans.map(plan => (
              <Col xs={24} sm={12} key={plan.id}>
                <Card hoverable onClick={() => onSelectPlan(plan)} style={{ cursor: "pointer" }}>
                  <Space direction="vertical" style={{ width: "100%" }}>
                    <Space>
                      <OrderedListOutlined style={{ color: "var(--color-cyan)" }} />
                      <Text strong style={{ fontSize: 16, color: "var(--color-text-primary)" }}>
                        {plan.plan_name}
                      </Text>
                      <Tag color={plan.generation_method === "deepseek" ? "purple" : "blue"}>
                        {plan.generation_method === "deepseek" ? "DeepSeek" : "本地"}
                      </Tag>
                    </Space>
                    <Row gutter={16}>
                      <Col span={8}><Statistic title="动作数" value={getTotalExercises(plan)} suffix="个" /></Col>
                      <Col span={8}>
                        <Statistic title="总时长" value={((plan.items || []).reduce((s, i) => s + i.sets * i.duration_seconds, 0) / 60).toFixed(0)} suffix="分钟" />
                      </Col>
                      <Col span={8}><Statistic title="创建" value={plan.created_at?.slice(0, 10) || "-"} /></Col>
                    </Row>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Spin>
    </div>
  );
}
