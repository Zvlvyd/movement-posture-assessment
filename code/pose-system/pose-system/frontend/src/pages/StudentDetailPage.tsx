import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card, Row, Col, Statistic, Descriptions, Tag, Table,
  Spin, Empty, Tabs, Space, Button, Typography
} from "antd";
import {
  ArrowLeftOutlined, TrophyOutlined, ExperimentOutlined,
  MedicineBoxOutlined, HistoryOutlined, CheckCircleOutlined,
  UserOutlined, CalendarOutlined
} from "@ant-design/icons";
import { coachApi } from "../services/api";

// ── Types ──────────────────────────────────────────────────
interface FMSRecord {
  id: number; test_date: string;
  balance_score: number; flexibility_score: number;
  upper_limb_score: number; core_score: number;
  symmetry_score: number; overall_score: number;
  risk_level: string | null;
}
interface AssessmentRecord {
  id: number; test_date: string; assessment_type: string;
  balance_score: number; flexibility_score: number;
  upper_limb_score: number; core_score: number;
  symmetry_score: number; overall_score: number;
  risk_level: string | null;
  report_data: any; muscle_findings: any;
}
interface RxItem {
  id: number; action_name: string; phase: string;
  sets: number; reps: number; duration: number;
  order_index: number; difficulty: number;
}
interface Prescription {
  id: number; phase: number; status: string;
  difficulty: number; created_at: string;
  items: RxItem[];
}
interface StudentProfile {
  id: number; username: string; phone: string;
  gender: string; created_at: string;
  fms: FMSRecord | null;
  fms_history: FMSRecord[];
  assessment: AssessmentRecord | null;
  assessment_history: AssessmentRecord[];
  prescriptions: Prescription[];
  recent_trainings: { id: number; start_time: string; end_time: string | null; total_score: number; mode: string }[];
  checkin: { streak_days: number; total_checkins: number };
  badges: { id: number; badge_type: string; name: string; description: string; earned_at: string }[];
}

// ── Helpers ────────────────────────────────────────────────
const riskColor: Record<string, string> = { low: "green", medium: "orange", high: "red" };
const phaseLabel: Record<string, string> = {
  WARMUP: "热身", ACTIVATION: "激活", MAIN: "主训练", COOLDOWN: "冷身",
};
const statusLabel: Record<string, string> = {
  ACTIVE: "进行中", LOCKED: "已锁定", COMPLETED: "已完成",
};

const ScoreBar: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
    <span style={{ width: 50, fontSize: 12, color: "#888" }}>{label}</span>
    <div style={{ flex: 1, height: 8, background: "#f0f0f0", borderRadius: 4 }}>
      <div style={{
        width: `${Math.min(value || 0, 100)}%`, height: "100%", borderRadius: 4,
        background: (value || 0) >= 60 ? "#52c41a" : (value || 0) >= 40 ? "#faad14" : "#f5222d",
      }} />
    </div>
    <span style={{ width: 36, fontSize: 13, fontWeight: 600, textAlign: "right" }}>{value ?? "-"}</span>
  </div>
);

// ── Radar Chart (simple SVG) ───────────────────────────────
const MiniRadar: React.FC<{ scores: Record<string, number> }> = ({ scores }) => {
  const dims = ["balance_score", "flexibility_score", "upper_limb_score", "core_score", "symmetry_score"];
  const labels = ["平衡", "灵活", "上肢", "核心", "对称"];
  const cx = 110, cy = 110, r = 80;
  const points = dims.map((_, i) => {
    const angle = (Math.PI * 2 * i) / dims.length - Math.PI / 2;
    const val = Math.max((scores[dims[i]] || 0) / 100, 0.05);
    return { x: cx + r * val * Math.cos(angle), y: cy + r * val * Math.sin(angle), label: labels[i], score: scores[dims[i]] };
  });
  const polyPoints = points.map(p => `${p.x},${p.y}`).join(" ");

  return (
    <svg width="240" height="240" viewBox="0 0 220 220">
      {/* Grid circles */}
      {[0.25, 0.5, 0.75, 1].map(scale => (
        <polygon key={scale} points={dims.map((_, i) => {
          const a = (Math.PI * 2 * i) / dims.length - Math.PI / 2;
          return `${cx + r * scale * Math.cos(a)},${cy + r * scale * Math.sin(a)}`;
        }).join(" ")} fill="none" stroke="#e8e8e8" strokeWidth="1" />
      ))}
      {/* Axis lines */}
      {dims.map((_, i) => {
        const a = (Math.PI * 2 * i) / dims.length - Math.PI / 2;
        return <line key={i} x1={cx} y1={cy} x2={cx + r * Math.cos(a)} y2={cy + r * Math.sin(a)} stroke="#e8e8e8" strokeWidth="1" />;
      })}
      {/* Data polygon */}
      <polygon points={polyPoints} fill="rgba(24,144,255,0.25)" stroke="#1890ff" strokeWidth="2" />
      {/* Points + labels */}
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="4" fill="#1890ff" />
          <text x={p.x + (p.x > cx ? 8 : p.x < cx ? -8 : 0)} y={p.y + (p.y > cy ? 16 : p.y < cy ? -6 : -8)}
                fontSize="11" textAnchor={p.x > cx ? "start" : p.x < cx ? "end" : "middle"} fill="#333">
            {p.label}:{p.score ?? "-"}
          </text>
        </g>
      ))}
    </svg>
  );
};

// ── Main Component ─────────────────────────────────────────
export default function StudentDetailPage() {
  const { studentId } = useParams<{ studentId: string }>();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!studentId) return;
    setLoading(true);
    coachApi.studentProfile(Number(studentId))
      .then(setProfile)
      .catch(() => setProfile(null))
      .finally(() => setLoading(false));
  }, [studentId]);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "80px auto" }} />;
  if (!profile) return <Empty description="学员未找到" style={{ marginTop: 80 }} />;

  const { fms, assessment, prescriptions, recent_trainings, checkin, badges, fms_history, assessment_history } = profile;

  return (
    <div>
      {/* Header */}
      <Button type="link" onClick={() => navigate(-1)} style={{ padding: 0, marginBottom: 16 }}>
        <ArrowLeftOutlined /> 返回
      </Button>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="学员" value={profile.username} prefix={<UserOutlined />} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="性别" value={profile.gender === "female" ? "女" : profile.gender === "male" ? "男" : profile.gender} />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic title="手机" value={profile.phone} />
          </Card>
        </Col>
        <Col span={5}>
          <Card>
            <Statistic title="打卡天数" value={checkin.streak_days} suffix={`/ ${checkin.total_checkins}次`} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col span={5}>
          <Card>
            <Statistic title="注册时间" value={profile.created_at?.slice(0, 10)} prefix={<CalendarOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* Badges */}
      {badges.length > 0 && (
        <Card size="small" title={<span><TrophyOutlined /> 徽章成就</span>} style={{ marginBottom: 16 }}>
          <Space wrap>
            {badges.map(b => (
              <Tag key={b.id} color="gold" style={{ fontSize: 13, padding: "4px 10px" }}>
                🏅 {b.name}
              </Tag>
            ))}
          </Space>
        </Card>
      )}

      {/* Main Tabs */}
      <Tabs defaultActiveKey={fms || assessment ? "body" : "prescriptions"} items={[
        // ── 身体状况（FMS + 体态评估） ──
        {
          key: "body",
          label: <span><ExperimentOutlined /> 身体状况</span>,
          children: (
            <Row gutter={16}>
              {/* FMS 筛查 */}
              <Col span={12}>
                <Card title="FMS 功能性运动筛查" size="small" extra={
                  fms ? <Tag color={riskColor[fms.risk_level || ""] || "default"}>{fms.risk_level}</Tag> : null
                }>
                  {fms ? (
                    <>
                      <Row gutter={16}>
                        <Col span={12}>
                          <ScoreBar label="平衡" value={fms.balance_score} />
                          <ScoreBar label="灵活" value={fms.flexibility_score} />
                          <ScoreBar label="上肢" value={fms.upper_limb_score} />
                          <ScoreBar label="核心" value={fms.core_score} />
                          <ScoreBar label="对称" value={fms.symmetry_score} />
                          <Descriptions size="small" column={1} style={{ marginTop: 8 }}>
                            <Descriptions.Item label="综合评分">{fms.overall_score}</Descriptions.Item>
                            <Descriptions.Item label="测试日期">{fms.test_date?.slice(0, 10)}</Descriptions.Item>
                          </Descriptions>
                        </Col>
                        <Col span={12}>
                          <MiniRadar scores={{
                            balance_score: fms.balance_score,
                            flexibility_score: fms.flexibility_score,
                            upper_limb_score: fms.upper_limb_score,
                            core_score: fms.core_score,
                            symmetry_score: fms.symmetry_score,
                          }} />
                        </Col>
                      </Row>
                    </>
                  ) : <Empty description="暂无 FMS 数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
                </Card>
              </Col>

              {/* 体态评估 */}
              <Col span={12}>
                <Card title="体态评估" size="small" extra={
                  assessment ? <Tag color={riskColor[assessment.risk_level || ""] || "default"}>{assessment.risk_level}</Tag> : null
                }>
                  {assessment ? (
                    <>
                      <ScoreBar label="平衡" value={assessment.balance_score} />
                      <ScoreBar label="灵活" value={assessment.flexibility_score} />
                      <ScoreBar label="上肢" value={assessment.upper_limb_score} />
                      <ScoreBar label="核心" value={assessment.core_score} />
                      <ScoreBar label="对称" value={assessment.symmetry_score} />
                      <Descriptions size="small" column={1} style={{ marginTop: 8 }}>
                        <Descriptions.Item label="综合评分">{assessment.overall_score}</Descriptions.Item>
                        <Descriptions.Item label="评估类型">{assessment.assessment_type}</Descriptions.Item>
                        <Descriptions.Item label="评估日期">{assessment.test_date?.slice(0, 10)}</Descriptions.Item>
                      </Descriptions>
                      {assessment.muscle_findings && (
                        <div style={{ marginTop: 8 }}>
                          <Typography.Text strong>肌肉分析：</Typography.Text>
                          <pre style={{ fontSize: 11, maxHeight: 120, overflow: "auto", background: "#fafafa", padding: 8, borderRadius: 4 }}>
                            {typeof assessment.muscle_findings === "string"
                              ? assessment.muscle_findings
                              : JSON.stringify(assessment.muscle_findings, null, 2)}
                          </pre>
                        </div>
                      )}
                    </>
                  ) : <Empty description="暂无体态评估数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
                </Card>
              </Col>

              {/* FMS 历史 */}
              {fms_history.length > 1 && (
                <Col span={24} style={{ marginTop: 16 }}>
                  <Card title="FMS 历史记录" size="small">
                    <Table dataSource={fms_history} rowKey="id" size="small" pagination={false}
                      columns={[
                        { title: "日期", dataIndex: "test_date", render: (v: string) => v?.slice(0, 10), width: 100 },
                        { title: "平衡", dataIndex: "balance_score", width: 60, render: (v: number) => v?.toFixed(0) ?? "-" },
                        { title: "灵活", dataIndex: "flexibility_score", width: 60, render: (v: number) => v?.toFixed(0) ?? "-" },
                        { title: "上肢", dataIndex: "upper_limb_score", width: 60, render: (v: number) => v?.toFixed(0) ?? "-" },
                        { title: "核心", dataIndex: "core_score", width: 60, render: (v: number) => v?.toFixed(0) ?? "-" },
                        { title: "对称", dataIndex: "symmetry_score", width: 60, render: (v: number) => v?.toFixed(0) ?? "-" },
                        { title: "综合", dataIndex: "overall_score", width: 60, render: (v: number) => v?.toFixed(0) ?? "-" },
                        { title: "风险", dataIndex: "risk_level", width: 80, render: (v: string) => v ? <Tag color={riskColor[v] || "default"}>{v}</Tag> : "-" },
                      ]}
                    />
                  </Card>
                </Col>
              )}

              {/* 体态评估历史 */}
              {assessment_history.length > 1 && (
                <Col span={24} style={{ marginTop: 16 }}>
                  <Card title="体态评估历史记录" size="small">
                    <Table dataSource={assessment_history} rowKey="id" size="small" pagination={false}
                      columns={[
                        { title: "日期", dataIndex: "test_date", render: (v: string) => v?.slice(0, 10), width: 100 },
                        { title: "类型", dataIndex: "assessment_type", width: 70 },
                        { title: "综合", dataIndex: "overall_score", width: 60, render: (v: number) => v?.toFixed(0) ?? "-" },
                        { title: "风险", dataIndex: "risk_level", width: 80, render: (v: string) => v ? <Tag color={riskColor[v] || "default"}>{v}</Tag> : "-" },
                      ]}
                    />
                  </Card>
                </Col>
              )}
            </Row>
          ),
        },

        // ── 训练处方 ──
        {
          key: "prescriptions",
          label: <span><MedicineBoxOutlined /> 训练处方 ({prescriptions.length})</span>,
          children: prescriptions.length === 0 ? (
            <Empty description="暂无训练处方" />
          ) : (
            <Row gutter={[16, 16]}>
              {prescriptions.map(rx => (
                <Col span={24} key={rx.id}>
                  <Card size="small" title={
                    <Space>
                      <span>处方 #{rx.id}</span>
                      <Tag color={rx.status === "ACTIVE" ? "blue" : rx.status === "COMPLETED" ? "green" : "default"}>
                        {statusLabel[rx.status] || rx.status}
                      </Tag>
                      <Tag>阶段 {rx.phase}</Tag>
                      <Tag>难度 {rx.difficulty}</Tag>
                    </Space>
                  } extra={<span style={{ color: "#888", fontSize: 12 }}>{rx.created_at?.slice(0, 10)}</span>}>
                    <Table
                      dataSource={rx.items}
                      rowKey="id"
                      size="small"
                      pagination={false}
                      columns={[
                        { title: "#", dataIndex: "order_index", width: 40 },
                        { title: "动作名称", dataIndex: "action_name" },
                        { title: "阶段", dataIndex: "phase", width: 80, render: (v: string) => phaseLabel[v] || v },
                        { title: "组数", dataIndex: "sets", width: 60 },
                        { title: "次数", dataIndex: "reps", width: 60 },
                        { title: "时长(s)", dataIndex: "duration", width: 70 },
                        { title: "难度", dataIndex: "difficulty", width: 60 },
                      ]}
                    />
                  </Card>
                </Col>
              ))}
            </Row>
          ),
        },

        // ── 训练记录 ──
        {
          key: "trainings",
          label: <span><HistoryOutlined /> 训练记录 ({recent_trainings.length})</span>,
          children: recent_trainings.length === 0 ? (
            <Empty description="近期无训练记录" />
          ) : (
            <Table
              dataSource={recent_trainings}
              rowKey="id"
              size="small"
              pagination={{ pageSize: 20 }}
              columns={[
                { title: "时间", dataIndex: "start_time", width: 170, render: (v: string) => v?.slice(0, 19) },
                { title: "模式", dataIndex: "mode", width: 70, render: (v: string) => v === "ADVANCED" ? <Tag color="purple">进阶</Tag> : <Tag color="blue">基础</Tag> },
                { title: "得分", dataIndex: "total_score", width: 80, render: (v: number) => v != null ? v.toFixed(0) : "-" },
              ]}
            />
          ),
        },
      ]} />
    </div>
  );
}
