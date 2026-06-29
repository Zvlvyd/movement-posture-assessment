import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card, Typography, Tag, Button, Spin, Empty,
  Space, Row, Col,
} from "antd";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer,
} from "recharts";
import { ExclamationCircleOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { fmsApi } from "../services/api";

const { Title, Text } = Typography;

const RISK_COLORS: Record<string, string> = { high: "#ff4d4f", medium: "#faad14", low: "#52c41a" };
const RISK_LABELS: Record<string, string> = { high: "高风险", medium: "中等", low: "低风险" };

const DIM_KEYS = [
  { key: "balance_score", label: "平衡能力" },
  { key: "flexibility_score", label: "柔韧性" },
  { key: "upper_limb_score", label: "上肢能力" },
  { key: "core_score", label: "核心稳定性" },
  { key: "symmetry_score", label: "对称性" },
];

export default function FMSReportPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [record, setRecord] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) { setError("缺少记录ID"); setLoading(false); return; }
    fmsApi.getRecord(Number(id))
      .then(r => { setRecord(r); setLoading(false); })
      .catch(() => { setError("加载失败"); setLoading(false); });
  }, [id]);

  if (loading) return <div style={{ textAlign: "center", padding: 48 }}><Spin size="large" /></div>;
  if (error || !record) return (
    <div style={{ textAlign: "center", padding: 48 }}>
      <Empty description={error || "未找到FMS筛查记录"} />
      <Button style={{ marginTop: 16 }} onClick={() => navigate("/fms")}>返回FMS筛查</Button>
    </div>
  );

  const riskColor = RISK_COLORS[record.risk_level] || "#999";
  const radarData = DIM_KEYS.map(d => ({
    dimension: d.label,
    score: record[d.key] ?? 0,
    full: 100,
  }));

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: "0 auto" }}>
      {/* Header */}
      <Card style={{ marginBottom: 16, textAlign: "center", borderLeft: `4px solid ${riskColor}` }}>
        <Title level={3} style={{ marginBottom: 4 }}>
          <ExclamationCircleOutlined style={{ color: riskColor, marginRight: 8 }} />
          FMS 筛查报告
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
            <Text type="secondary">筛查日期: {record.test_date?.slice(0, 10)}</Text>
          </div>
        )}
      </Card>

      {/* Dimension Scores */}
      <Card title="各维度评分" size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 12]}>
          {DIM_KEYS.map(d => (
            <Col span={Math.floor(24 / DIM_KEYS.length)} key={d.key} style={{ textAlign: "center" }}>
              <Text type="secondary" style={{ fontSize: 12 }}>{d.label}</Text>
              <br />
              <Text strong style={{
                fontSize: 20,
                color: record[d.key] >= 70 ? "#52c41a" : record[d.key] >= 50 ? "#faad14" : "#f5222d",
              }}>
                {record[d.key]?.toFixed?.(0) ?? record[d.key] ?? "-"}
              </Text>
            </Col>
          ))}
        </Row>
      </Card>

      {/* Radar Chart */}
      <Card title="雷达图" size="small" style={{ marginBottom: 16 }}>
        <ResponsiveContainer width="100%" height={260}>
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="dimension" />
            <PolarRadiusAxis angle={30} domain={[0, 100]} />
            <Radar dataKey="score" stroke={riskColor} fill={riskColor} fillOpacity={0.3} />
            <Radar dataKey="full" stroke="#ddd" fill="#f5f5f5" fillOpacity={0.1} />
          </RadarChart>
        </ResponsiveContainer>
      </Card>

      {/* Actions */}
      <div style={{ textAlign: "center", marginTop: 24 }}>
        <Space direction="vertical" style={{ width: "100%", maxWidth: 400 }}>
          <Button type="primary" size="large" block icon={<ThunderboltOutlined />}
            onClick={() => navigate("/prescription")}>
            生成 AI 训练处方
          </Button>
          <Space>
            <Button onClick={() => navigate("/fms")}>返回FMS筛查</Button>
            <Button onClick={() => navigate("/home")}>返回首页</Button>
          </Space>
        </Space>
      </div>
    </div>
  );
}
