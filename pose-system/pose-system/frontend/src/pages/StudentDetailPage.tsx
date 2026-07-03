import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card, Row, Col, Statistic, Descriptions, Tag, Table,
  Spin, Empty, Tabs, Space, Button, Typography, Popconfirm, message, Progress
} from "antd";
import {
  ArrowLeftOutlined, TrophyOutlined, ExperimentOutlined,
  HistoryOutlined, CheckCircleOutlined,
  UserOutlined, CalendarOutlined, ThunderboltOutlined, DeleteOutlined,
  ClockCircleOutlined, BarChartOutlined
} from "@ant-design/icons";
import { coachApi } from "../services/api";
import type { PlanV2 } from '../types';
import ScoreBar from "../components/ScoreBar";
import { riskColor } from "../utils/riskColor";

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
interface StudentProfile {
  id: number; username: string; phone: string;
  gender: string; created_at: string;
  fms: FMSRecord | null;
  fms_history: FMSRecord[];
  assessment: AssessmentRecord | null;
  assessment_history: AssessmentRecord[];
  checkin: { streak_days: number; total_checkins: number };
  badges: { id: number; badge_type: string; name: string; description: string; earned_at: string }[];
}
interface TrainingRecord {
  id: number; plan_id: number; plan_name: string;
  action_name: string; best_score: number;
  rep_count: number; hold_time_seconds: number;
  duration_seconds: number; created_at: string;
}
interface PlanProgress {
  plan_id: number; plan_name: string;
  total_items: number; completed_sessions: number;
  latest_score: number | null; created_at: string;
}
interface TrainingStats {
  student_id: number;
  all_time: { total: number; avg_score: number; total_duration_minutes: number };
  week: { total: number; avg_score: number; total_duration_minutes: number };
  active_plans: PlanProgress[];
}

// ── Helpers ────────────────────────────────────────────────
function scoreColor(s: number) {
  if (s >= 85) return "#52c41a";
  if (s >= 60) return "#faad14";
  return "#f5222d";
}

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
      {[0.25, 0.5, 0.75, 1].map(scale => (
        <polygon key={scale} points={dims.map((_, i) => {
          const a = (Math.PI * 2 * i) / dims.length - Math.PI / 2;
          return `${cx + r * scale * Math.cos(a)},${cy + r * scale * Math.sin(a)}`;
        }).join(" ")} fill="none" stroke="#e8e8e8" strokeWidth="1" />
      ))}
      {dims.map((_, i) => {
        const a = (Math.PI * 2 * i) / dims.length - Math.PI / 2;
        return <line key={i} x1={cx} y1={cy} x2={cx + r * Math.cos(a)} y2={cy + r * Math.sin(a)} stroke="#e8e8e8" strokeWidth="1" />;
      })}
      <polygon points={polyPoints} fill="rgba(24,144,255,0.25)" stroke="#1890ff" strokeWidth="2" />
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
  const [v2Plans, setV2Plans] = useState<PlanV2[]>([]);
  const [plansLoading, setPlansLoading] = useState(false);
  const [trainingStats, setTrainingStats] = useState<TrainingStats | null>(null);
  const [trainingRecords, setTrainingRecords] = useState<TrainingRecord[]>([]);
  const [trainingLoading, setTrainingLoading] = useState(false);

  const loadTrainingData = async (sid: number) => {
    setTrainingLoading(true);
    try {
      const [stats, records] = await Promise.all([
        coachApi.trainingStats(sid),
        coachApi.trainingRecords(sid, 30),
      ]);
      setTrainingStats(stats);
      setTrainingRecords(records?.records || []);
    } catch { /* ignore */ }
    finally { setTrainingLoading(false); }
  };

  useEffect(() => {
    if (!studentId) return;
    const sid = Number(studentId);
    setLoading(true);
    Promise.all([
      coachApi.studentProfile(sid).then(setProfile).catch(() => setProfile(null)),
      coachApi.studentPlans(sid).then((data: any) => setV2Plans(Array.isArray(data) ? data : [])).catch(() => setV2Plans([])),
    ]).finally(() => setLoading(false));
    loadTrainingData(sid);
  }, [studentId]);

  const handleDeletePlan = async (planId: number) => {
    if (!studentId) return;
    try {
      await coachApi.deleteStudentPlan(Number(studentId), planId);
      message.success('训练计划已删除');
      setV2Plans(prev => prev.filter(p => p.id !== planId));
    } catch { message.error('删除失败'); }
  };

  if (loading) return <Spin size="large" style={{ display: "block", margin: "80px auto" }} />;
  if (!profile) return <Empty description="学员未找到" style={{ marginTop: 80 }} />;

  const { fms, assessment, checkin, badges, fms_history, assessment_history } = profile;

  // ── Render: 训练记录 tab ──
  const renderTrainingTab = () => (
    <div>
      {trainingStats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic title="本周训练" value={trainingStats.week.total} suffix="次"
                prefix={<HistoryOutlined />} valueStyle={{ color: "#1890ff" }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="本周均分" value={trainingStats.week.avg_score} suffix="分"
                prefix={<TrophyOutlined />} valueStyle={{ color: scoreColor(trainingStats.week.avg_score) }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="本周时长" value={trainingStats.week.total_duration_minutes} suffix="分钟"
                prefix={<ClockCircleOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="累计训练" value={trainingStats.all_time.total} suffix="次"
                prefix={<BarChartOutlined />} />
            </Card>
          </Col>
        </Row>
      )}

      {/* Active plan progress */}
      {trainingStats && trainingStats.active_plans.length > 0 && (
        <Card title={<span><ThunderboltOutlined /> 激活计划进度</span>} size="small" style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            {trainingStats.active_plans.map(p => (
              <Col span={12} key={p.plan_id}>
                <Card size="small" hoverable onClick={() => {
                  const plan = v2Plans.find(vp => vp.id === p.plan_id);
                  if (plan) setV2Plans([plan]); // Not used, but kept for logic
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <Space direction="vertical" size={2}>
                      <Typography.Text strong>{p.plan_name}</Typography.Text>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        已完成 {p.completed_sessions} 组训练
                      </Typography.Text>
                      {p.latest_score != null && (
                        <Tag color={scoreColor(p.latest_score)}>最近得分 {p.latest_score}</Tag>
                      )}
                    </Space>
                    <Progress type="circle" width={60}
                      percent={p.total_items > 0 ? Math.round(p.completed_sessions / Math.max(p.total_items, 1) * 100) : 0}
                      format={() => `${p.completed_sessions}`} />
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {/* Training records table */}
      <Card title={<span><HistoryOutlined /> 最近训练记录</span>} size="small" loading={trainingLoading}>
        {trainingRecords.length === 0 ? (
          <Empty description="暂无训练记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Table dataSource={trainingRecords} rowKey="id" size="small"
            pagination={{ pageSize: 15, showSizeChanger: true, showTotal: t => `共 ${t} 条` }}
            columns={[
              { title: "时间", dataIndex: "created_at", width: 140, render: (v: string) => v?.slice(0, 16) },
              { title: "所属计划", dataIndex: "plan_name", width: 120, ellipsis: true,
                render: (v: string) => <Tag color="blue">{v}</Tag> },
              { title: "动作", dataIndex: "action_name", width: 120,
                render: (v: string) => <Typography.Text strong>{v}</Typography.Text> },
              { title: "得分", dataIndex: "best_score", width: 80, align: "center" as const,
                render: (v: number) => (
                  <Tag color={scoreColor(v)} style={{ fontWeight: 700, fontSize: 13 }}>
                    {v?.toFixed(0) ?? "-"}
                  </Tag>
                )},
              { title: "次数/时长", width: 120,
                render: (_: any, r: TrainingRecord) => (
                  <Space size={4}>
                    {r.rep_count > 0 && <Tag>{r.rep_count} 次</Tag>}
                    {r.hold_time_seconds > 0 && <Tag>{r.hold_time_seconds.toFixed(0)}s</Tag>}
                    <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                      {r.duration_seconds > 0 ? `${(r.duration_seconds / 60).toFixed(1)}min` : ""}
                    </Typography.Text>
                  </Space>
                )},
            ]}
          />
        )}
      </Card>
    </div>
  );

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
      <Tabs defaultActiveKey={fms || assessment ? "body" : "training"} items={[
        // ── 身体状况 ──
        {
          key: "body",
          label: <span><ExperimentOutlined /> 身体状况</span>,
          children: (
            <Row gutter={16}>
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

        // ── 训练计划 V2 ──
        {
          key: "plans_v2",
          label: <span><ThunderboltOutlined /> 训练计划 ({v2Plans.length})</span>,
          children: v2Plans.length === 0 ? (
            <Empty description="暂无训练计划" />
          ) : (
            <Row gutter={[16, 16]}>
              {v2Plans.map(plan => {
                // 计算总体进度
                const totalCompletions = (plan.items || []).reduce((sum, item: any) => sum + (item.completions || 0), 0);
                const totalSets = (plan.items || []).reduce((sum, item: any) => sum + (item.sets || 0), 0);
                return (
                <Col span={24} key={plan.id}>
                  <Card size="small" title={
                    <Space>
                      <span>{plan.plan_name}</span>
                      <Tag color={plan.status === 'active' ? 'blue' : plan.status === 'completed' ? 'green' : 'default'}>
                        {plan.status === 'active' ? '进行中' : plan.status === 'completed' ? '已完成' : '草稿'}
                      </Tag>
                      <Tag color={plan.generation_method === 'deepseek' ? 'purple' : 'blue'}>
                        {plan.generation_method === 'deepseek' ? 'AI生成' : '本地引擎'}
                      </Tag>
                      {plan.item_count > 0 && (
                        <Tag>{plan.item_count} 个动作</Tag>
                      )}
                    </Space>
                  } extra={
                    <Space>
                      {totalSets > 0 && (
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          训练进度 {totalCompletions}/{totalSets} 组
                        </Typography.Text>
                      )}
                      <span style={{ color: '#888', fontSize: 12 }}>{plan.created_at?.slice(0, 10)}</span>
                      <Popconfirm
                        title="确认删除此训练计划？"
                        onConfirm={() => handleDeletePlan(plan.id)}
                        okText="删除"
                        cancelText="取消"
                      >
                        <Button type="link" danger size="small" icon={<DeleteOutlined />}>删除</Button>
                      </Popconfirm>
                    </Space>
                  }>
                    {plan.overall_strategy && (
                      <Typography.Paragraph ellipsis={{ rows: 2 }} type="secondary" style={{ marginBottom: 12 }}>
                        {plan.overall_strategy}
                      </Typography.Paragraph>
                    )}
                    {/* 总体进度条 */}
                    {totalSets > 0 && (
                      <div style={{ marginBottom: 12 }}>
                        <Progress
                          percent={Math.round(totalCompletions / Math.max(totalSets, 1) * 100)}
                          size="small"
                          format={() => `${totalCompletions}/${totalSets} 组已完成`}
                        />
                      </div>
                    )}
                    <Table
                      dataSource={plan.items || []}
                      rowKey="id"
                      size="small"
                      pagination={false}
                      columns={[
                        { title: '#', dataIndex: 'order_index', width: 40 },
                        { title: '动作', dataIndex: 'action_name', ellipsis: true,
                          render: (v: string) => <Typography.Text strong>{v}</Typography.Text> },
                        { title: '阶段', dataIndex: 'phase', width: 70, render: (v: string) => {
                          const m: Record<string, string> = { warmup: '热身', activation: '激活', main: '主体', cooldown: '冷身' };
                          return <Tag color="default">{m[v] || v}</Tag>;
                        }},
                        { title: '组数', dataIndex: 'sets', width: 50, align: 'center' as const },
                        { title: '次数', dataIndex: 'reps', width: 50, align: 'center' as const },
                        { title: '时长(s)', dataIndex: 'duration_seconds', width: 70, align: 'center' as const,
                          render: (v: number) => v > 0 ? `${v}s` : '-' },
                        { title: '难度', dataIndex: 'difficulty', width: 50, align: 'center' as const },
                        { title: '强度', dataIndex: 'intensity', width: 60, render: (v: string) => {
                          const colors: Record<string, string> = { LOW: 'green', MEDIUM: 'orange', HIGH: 'red' };
                          return <Tag color={colors[v] || 'default'}>{v}</Tag>;
                        }},
                        { title: '完成', dataIndex: 'completions', width: 60, align: 'center' as const,
                          render: (v: number, r: any) => (
                            <Typography.Text style={{ color: v > 0 ? '#52c41a' : '#d9d9d9' }}>
                              {v || 0}/{r.sets || 0}
                            </Typography.Text>
                          )},
                        { title: '最新得分', dataIndex: 'latest_score', width: 80, align: 'center' as const,
                          render: (v: number | null) => v != null ? (
                            <Tag color={scoreColor(v)} style={{ fontWeight: 700 }}>{v.toFixed(0)}</Tag>
                          ) : <Typography.Text type="secondary">-</Typography.Text> },
                        { title: '备注', dataIndex: 'notes', ellipsis: true, width: 100,
                          render: (v: string) => v ? <Typography.Text type="secondary" style={{ fontSize: 12 }}>{v}</Typography.Text> : '-' },
                      ]}
                    />
                  </Card>
                </Col>
              )})}
            </Row>
          ),
        },

        // ── 训练记录（新）──
        {
          key: "training",
          label: <span><HistoryOutlined /> 训练记录 ({trainingRecords.length})</span>,
          children: renderTrainingTab(),
        },
      ]} />
    </div>
  );
}
