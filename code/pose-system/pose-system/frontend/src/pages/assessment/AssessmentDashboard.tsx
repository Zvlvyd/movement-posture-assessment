import { useEffect, useState } from "react";
import { Card, Table, Tag, Typography, Space, Statistic, Row, Col, Button, Empty, Spin } from "antd";
import { AimOutlined, HistoryOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { assessmentApi } from "../../services/api";
import type { AssessmentRecord } from "../../types";

const { Text, Title } = Typography;

const RISK_COLORS: Record<string, string> = { low: "green", medium: "orange", high: "red" };
const RISK_LABELS: Record<string, string> = { low: "低风险", medium: "中风险", high: "高风险" };

export default function AssessmentDashboard() {
  const navigate = useNavigate();
  const [records, setRecords] = useState<AssessmentRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    assessmentApi.getRecords().then(r => setRecords(r || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <Card><Spin /><Text type="secondary" style={{ marginLeft: 12 }}>加载评估记录...</Text></Card>;

  const latest = records[0];

  return (
    <Card
      title={<Space><HistoryOutlined style={{ color: "var(--color-cyan)" }} />历史评估记录</Space>}
      style={{ marginTop: 16 }}
    >
      {records.length === 0 ? (
        <Empty description="暂无评估记录" />
      ) : (
        <>
          {/* Summary Stats */}
          {latest && (
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}><Statistic title="总次数" value={records.length} suffix="次" /></Col>
              <Col span={6}>
                <Statistic title="最新得分" value={latest.overall_score} suffix="分"
                  valueStyle={{ color: latest.overall_score >= 70 ? "#52c41a" : "#faad14" }} />
              </Col>
              <Col span={6}>
                <Statistic title="风险等级" value={RISK_LABELS[latest.risk_level] || latest.risk_level}
                  valueStyle={{ color: `var(--ant-${RISK_COLORS[latest.risk_level] || "default"})` }} />
              </Col>
              <Col span={6}><Statistic title="最近日期" value={latest.test_date?.slice(0, 10) || "-"} /></Col>
            </Row>
          )}

          <Table
            size="small" pagination={{ pageSize: 5 }}
            dataSource={records} rowKey="id"
            columns={[
              { title: "ID", dataIndex: "id", width: 50 },
              { title: "日期", dataIndex: "test_date", render: (v: string) => v?.slice(0, 10), width: 100 },
              { title: "平衡", dataIndex: "balance_score", width: 60 },
              { title: "柔韧", dataIndex: "flexibility_score", width: 60 },
              { title: "上肢", dataIndex: "upper_limb_score", width: 60 },
              { title: "核心", dataIndex: "core_score", width: 60 },
              { title: "对称", dataIndex: "symmetry_score", width: 60 },
              { title: "总分", dataIndex: "overall_score", width: 60,
                render: (v: number) => <Text strong style={{ color: v >= 70 ? "#52c41a" : v >= 50 ? "#faad14" : "#f5222d" }}>{v}</Text> },
              { title: "风险", dataIndex: "risk_level", width: 80,
                render: (v: string) => <Tag color={RISK_COLORS[v] || "default"}>{RISK_LABELS[v] || v}</Tag> },
              { title: "操作", width: 80,
                render: (_: any, r: AssessmentRecord) => (
                  <Button size="small" type="link" onClick={() => navigate(`/assessment/report/${r.id}`)}>查看报告</Button>
                ),
              },
            ]}
          />
        </>
      )}
    </Card>
  );
}
