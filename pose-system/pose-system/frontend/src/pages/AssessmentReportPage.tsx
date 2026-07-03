import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card, Typography, Tag, Button, Spin, Empty,
  Space, Collapse,
} from "antd";
import { ExclamationCircleOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { assessmentApi } from "../services/api";

const { Title, Text, Paragraph } = Typography;

const RISK_COLORS: Record<string, string> = { high: "#ff4d4f", medium: "#faad14", low: "#52c41a" };
const RISK_LABELS: Record<string, string> = { high: "高风险", medium: "中等", low: "低风险" };

export default function AssessmentReportPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [record, setRecord] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) { setError("缺少记录ID"); setLoading(false); return; }
    assessmentApi.getRecord(Number(id))
      .then(r => { setRecord(r); setLoading(false); })
      .catch(() => { setError("加载失败"); setLoading(false); });
  }, [id]);

  if (loading) return <div style={{ textAlign: "center", padding: 48 }}><Spin size="large" /></div>;
  if (error || !record) return (
    <div style={{ textAlign: "center", padding: 48 }}>
      <Empty description={error || "未找到评估记录"} />
      <Button style={{ marginTop: 16 }} onClick={() => navigate("/assessment")}>返回评估</Button>
    </div>
  );

  const riskColor = RISK_COLORS[record.risk_level] || "#999";

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: "0 auto" }}>
      {/* Header */}
      <Card style={{ marginBottom: 16, textAlign: "center", borderLeft: `4px solid ${riskColor}` }}>
        <Title level={3} style={{ marginBottom: 4 }}>
          <ExclamationCircleOutlined style={{ color: riskColor, marginRight: 8 }} />
          体态评估报告
        </Title>
        <Space size="large">
          <div>
            <Text type="secondary">综合评分</Text>
            <br />
            <Text style={{ fontSize: 36, fontWeight: "bold", color: riskColor }}>
              {record.overall_score?.toFixed?.(1) ?? record.overall_score ?? "-"}
            </Text>
            <Text type="secondary"> / 100</Text>
          </div>
          <Tag color={riskColor} style={{ fontSize: 16, padding: "4px 16px" }}>
            {RISK_LABELS[record.risk_level] || record.risk_level}
          </Tag>
        </Space>
        {record.test_date && (
          <div style={{ marginTop: 8 }}>
            <Text type="secondary">评估日期: {record.test_date?.slice(0, 10)}</Text>
          </div>
        )}
      </Card>

      {/* Posture Problems */}
      {record.posture_problems?.length > 0 ? (
        <Card title="体态问题" size="small" style={{ marginBottom: 16 }}>
          {record.posture_problems.map((p: any, i: number) => (
            <Card key={i} size="small" style={{ marginBottom: 8 }}
              title={<Space>
                <Tag color={p.severity === "severe" ? "red" : p.severity === "moderate" ? "orange" : "blue"}>
                  {p.severity === "severe" ? "重度" : p.severity === "moderate" ? "中度" : "轻度"}
                </Tag>
                {p.name}
              </Space>}>
              {p.tight?.length > 0 && (
                <div style={{ marginBottom: 6 }}>
                  <Text type="secondary">紧张肌群: </Text>
                  {p.tight.map((m: string, j: number) => <Tag key={j} color="volcano">{m}</Tag>)}
                </div>
              )}
              {p.weak?.length > 0 && (
                <div style={{ marginBottom: 6 }}>
                  <Text type="secondary">薄弱肌群: </Text>
                  {p.weak.map((m: string, j: number) => <Tag key={j} color="cyan">{m}</Tag>)}
                </div>
              )}
              {p.cause && <Paragraph type="secondary" style={{ fontSize: 12 }}>原因: {p.cause}</Paragraph>}
              {p.exercises && (
                <Collapse ghost size="small" items={[
                  ...(p.exercises.stretch?.length > 0 ? [{
                    key: "stretch", label: "拉伸训练",
                    children: p.exercises.stretch.map((e: any, j: number) => (
                      <div key={j} style={{ marginBottom: 8 }}><Text strong>{e.name || e}</Text>{e.sets && <Tag style={{ marginLeft: 8 }}>{e.sets}</Tag>}</div>
                    ))
                  }] : []),
                  ...(p.exercises.strength?.length > 0 ? [{
                    key: "strength", label: "强化训练",
                    children: p.exercises.strength.map((e: any, j: number) => (
                      <div key={j} style={{ marginBottom: 8 }}><Text strong>{e.name || e}</Text>{e.sets && <Tag style={{ marginLeft: 8 }}>{e.sets}</Tag>}</div>
                    ))
                  }] : []),
                ]} />
              )}
            </Card>
          ))}
        </Card>
      ) : (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Empty description="暂未检测到体态问题，或数据尚未分析完成" />
        </Card>
      )}

      {/* No problems at all */}
      {(!record.posture_problems || record.posture_problems.length === 0) && record.risk_level === "low" && (
        <Card size="small" style={{ marginBottom: 16, textAlign: "center" }}>
          <Text style={{ color: "#52c41a", fontSize: 16 }}>✓ 未发现明显体态问题，继续保持！</Text>
        </Card>
      )}

      {/* Actions */}
      <div style={{ textAlign: "center", marginTop: 24 }}>
        <Space direction="vertical" style={{ width: "100%", maxWidth: 400 }}>
          <Button type="primary" size="large" block icon={<ThunderboltOutlined />}
            onClick={() => navigate("/prescription")}>
            生成 AI 训练处方
          </Button>
          <Space>
            <Button onClick={() => navigate("/assessment")}>返回评估</Button>
            <Button onClick={() => navigate("/home")}>返回首页</Button>
          </Space>
        </Space>
      </div>
    </div>
  );
}
