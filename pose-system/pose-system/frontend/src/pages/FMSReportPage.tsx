import { useEffect, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import {
  Card, Typography, Tag, Button, Spin, Empty,
  Space, Row, Col, List, Collapse, Alert, Tooltip, Divider,
} from "antd";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer,
} from "recharts";
import {
  ExclamationCircleOutlined, ThunderboltOutlined, WarningOutlined,
  BulbOutlined, AimOutlined,
} from "@ant-design/icons";
import { fmsApi } from "../services/api";

const { Title, Text, Paragraph } = Typography;

const RISK_COLORS: Record<string, string> = { high: "#ff4d4f", medium: "#faad14", low: "#52c41a" };
const RISK_LABELS: Record<string, string> = { high: "高风险", medium: "中等", low: "低风险" };
const SEVERITY_COLORS: Record<string, string> = { "高": "#ff4d4f", "中": "#faad14", "低": "#fa8c16", "mild": "#1677ff", "moderate": "#fa8c16", "severe": "#ff4d4f" };

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
  const location = useLocation();

  // 优先使用 WebSocket 传来的丰富报告，其次用 REST API 基础数据
  const wsResult = (location.state as any)?.fmsResult;
  const [record, setRecord] = useState<any>(wsResult || null);
  const [loading, setLoading] = useState(!wsResult);
  const [error, setError] = useState("");

  useEffect(() => {
    if (wsResult) return; // 已有 WebSocket 数据，不用再请求
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
    score: record[d.key] ?? record.scores?.find((s: any) => s.dimension === d.key.replace("_score", ""))?.score ?? 0,
    full: 100,
  }));

  const scores = record.scores || DIM_KEYS.map(d => ({
    dimension: d.key.replace("_score", ""),
    label: d.label,
    score: record[d.key] ?? 0,
  }));
  const problemTags = record.problem_tags || [];
  const recommendations = record.recommendations || [];
  const postureProblems = record.posture_problems || [];
  const completedCount = record.completed_count ?? (record.scores?.length || 0);

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
            <Text type="secondary">功能性动作评分</Text>
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
        <div style={{ marginTop: 8 }}>
          <Text type="secondary">
            完成 {completedCount} 项测试
            {record.skipped_count > 0 && ` · 跳过 ${record.skipped_count} 项`}
            {record.test_date && ` · ${record.test_date?.slice(0, 10)}`}
          </Text>
        </div>
      </Card>

      {/* Radar Chart */}
      <Card title={<><AimOutlined /> 能力雷达图</>} size="small" style={{ marginBottom: 16 }}>
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="dimension" />
            <PolarRadiusAxis angle={30} domain={[0, 100]} />
            <Radar dataKey="score" stroke={riskColor} fill={riskColor} fillOpacity={0.3} />
            <Radar dataKey="full" stroke="#ddd" fill="#f5f5f5" fillOpacity={0.1} />
          </RadarChart>
        </ResponsiveContainer>
      </Card>

      {/* Dimension Scores with Details and Advice */}
      <Card title="各维度详细分析" size="small" style={{ marginBottom: 16 }}>
        {scores.map((s: any) => {
          const dimScore = typeof s.score === 'number' ? s.score : 0;
          const scoreColor = dimScore >= 70 ? "#52c41a" : dimScore >= 50 ? "#faad14" : "#f5222d";
          const isLow = dimScore < 50;
          const actions = s.recommended_actions || [];
          return (
            <div key={s.dimension} style={{ marginBottom: 12, padding: "8px 12px", background: isLow ? "#fff7e6" : "#fafafa", borderRadius: 8, border: isLow ? "1px solid #ffd591" : "none" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <Text strong>{s.label || s.dimension}</Text>
                <Tag color={scoreColor} style={{ fontSize: 14 }}>{dimScore.toFixed(0)} 分</Tag>
              </div>
              {s.detail && <Text type="secondary" style={{ fontSize: 12 }}>📊 测试指标：{s.detail}</Text>}
              {s.advice && (
                <div style={{ marginTop: 4 }}>
                  <Text style={{ fontSize: 12 }}>
                    💡 <strong>训练建议</strong>：{s.advice[1]}
                  </Text>
                </div>
              )}
              {/* 低分详细问题说明 */}
              {isLow && s.problem_detail && (
                <div style={{ marginTop: 6, padding: "6px 10px", background: "#fff2f0", borderRadius: 6 }}>
                  <Text style={{ fontSize: 12 }}>
                    ⚠️ <strong>问题分析</strong>：{s.problem_detail}
                  </Text>
                </div>
              )}
              {/* 推荐动作 */}
              {isLow && actions.length > 0 && (
                <div style={{ marginTop: 6 }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>🎯 推荐训练动作：</Text>
                  <div style={{ marginTop: 2 }}>
                    {actions.map((a: any, idx: number) => (
                      <Tag key={idx} color="blue" style={{ marginBottom: 2, fontSize: 11 }}>
                        {a.name}（难度{a.difficulty}/5）
                      </Tag>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </Card>

      {/* Problems Found */}
      {problemTags.length > 0 && (
        <Card title={<><WarningOutlined style={{ color: "#faad14" }} /> 发现的问题</>} size="small" style={{ marginBottom: 16 }}>
          <List
            size="small"
            dataSource={problemTags}
            renderItem={(tag: any) => {
              const actions = tag.recommended_actions || [];
              return (
              <List.Item>
                <List.Item.Meta
                  avatar={<Tag color={SEVERITY_COLORS[tag.severity] || "default"}>{tag.severity === "高" ? "严重" : tag.severity === "中" ? "中等" : tag.severity}</Tag>}
                  title={<Text strong>{tag.name || tag.dimension}</Text>}
                  description={
                    <>
                      {tag.description || tag.detail}
                      {tag.problem_detail && (
                        <div style={{ marginTop: 4, padding: "4px 8px", background: "#fff7e6", borderRadius: 4 }}>
                          <Text style={{ fontSize: 11 }}>⚠️ {tag.problem_detail}</Text>
                        </div>
                      )}
                      {actions.length > 0 && (
                        <div style={{ marginTop: 4 }}>
                          {actions.map((a: any, idx: number) => (
                            <Tag key={idx} color="blue" style={{ fontSize: 10, marginBottom: 2 }}>
                              🎯 {a.name}
                            </Tag>
                          ))}
                        </div>
                      )}
                    </>
                  }
                />
              </List.Item>
              );
            }}
          />
        </Card>
      )}

      {/* Posture Problems */}
      {postureProblems.length > 0 && (
        <Card title="体态异常" size="small" style={{ marginBottom: 16 }}>
          {postureProblems.map((p: any, idx: number) => (
            <Tag key={idx} color={SEVERITY_COLORS[p.severity] || "default"} style={{ marginBottom: 4 }}>
              {p.name}: {p.severity === "severe" ? "严重" : p.severity === "moderate" ? "中度" : "轻度"}
            </Tag>
          ))}
        </Card>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <Card title={<><BulbOutlined style={{ color: "#1677ff" }} /> 训练建议</>} size="small" style={{ marginBottom: 16 }}>
          <List
            size="small"
            dataSource={recommendations}
            renderItem={(rec: string, idx: number) => (
              <List.Item>
                <Text>📌 {rec}</Text>
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* Summary */}
      <Alert
        type={record.risk_level === "low" ? "success" : record.risk_level === "medium" ? "warning" : "error"}
        message={record.risk_level === "low" ? "整体状况良好" : record.risk_level === "medium" ? "建议针对性改善" : "需要重点关注"}
        description={
          record.risk_level === "low"
            ? "各项运动能力处于良好水平，建议继续保持规律训练，定期复查。"
            : record.risk_level === "medium"
            ? `功能性动作评分 ${record.overall_score} 分，建议根据上方问题标签和训练建议进行 4-6 周针对性训练后复查。`
            : `功能性动作评分偏低（${record.overall_score} 分），建议进行系统康复训练并在教练指导下逐步改善。`
        }
        style={{ marginBottom: 16 }}
        showIcon
      />

      {/* Actions */}
      <div style={{ textAlign: "center", marginTop: 24 }}>
        <Space direction="vertical" style={{ width: "100%", maxWidth: 400 }}>
          <Button type="primary" size="large" block icon={<ThunderboltOutlined />}
            onClick={() => navigate("/prescription")}>
            生成 AI 训练计划
          </Button>
          <Space>
            <Button onClick={() => navigate("/fms")}>重新筛查</Button>
            <Button onClick={() => navigate("/home")}>返回首页</Button>
          </Space>
        </Space>
      </div>
    </div>
  );
}
