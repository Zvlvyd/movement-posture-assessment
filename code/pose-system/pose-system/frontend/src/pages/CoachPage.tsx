import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card, Table, Button, Modal, Input, Tag, Space, message,
  Statistic, Row, Col, Descriptions, Empty, Spin,
  Form, Select
} from "antd";
import {
  PlusOutlined, TeamOutlined, BarChartOutlined,
  UserOutlined, TrophyOutlined, ArrowUpOutlined, ArrowDownOutlined
} from "@ant-design/icons";
import { coachApi } from "../services/api";

// ── Types ────────────────────────────────────────────────────────────────
interface ClassInfo {
  id: number; name: string; description?: string;
  student_count: number; created_at: string;
}
interface StudentProgress {
  id: number; username: string; phone: string;
  fms_scores: Record<string, number> | null;
  sessions_7d: number; sessions_30d: number;
  streak_days: number; risk_level: string | null;
}
interface ClassStats {
  class_id: number; class_name: string; student_count: number;
  summary: {
    avg_overall_score: number; active_7d_count: number;
    active_7d_rate: number; total_sessions_7d: number;
    total_sessions_30d: number; sessions_per_student_7d: number;
  };
  students: StudentProgress[];
}
interface TrendPoint {
  date: string; session_count: number; avg_score: number;
}
interface CoachSummary {
  class_count: number; total_students: number;
  sessions_7d: number; sessions_30d: number;
}

// ── Risk color helper ────────────────────────────────────────────────────
const riskColor: Record<string, string> = {
  low: "green", medium: "orange", high: "red",
};

// ── Score radar mini bar ────────────────────────────────────────────────
const ScoreBar: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div style={{ marginBottom: 2, fontSize: 12 }}>
    <span style={{ display: "inline-block", width: 60, color: "#888" }}>{label}</span>
    <div style={{ display: "inline-block", width: 80, height: 10, background: "#f0f0f0", borderRadius: 5, verticalAlign: "middle", marginRight: 4 }}>
      <div style={{ width: `${Math.min(value, 100)}%`, height: "100%", background: value >= 60 ? "#52c41a" : value >= 40 ? "#faad14" : "#f5222d", borderRadius: 5 }} />
    </div>
    <span style={{ fontWeight: 600 }}>{value}</span>
  </div>
);

// ── Trend mini chart ────────────────────────────────────────────────────
const MiniTrend: React.FC<{ data: TrendPoint[] }> = ({ data }) => {
  if (!data || data.length === 0) return <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  const maxCount = Math.max(...data.map(d => d.session_count), 1);
  const maxScore = Math.max(...data.map(d => d.avg_score), 1);
  const barWidth = Math.max(4, Math.min(12, 600 / data.length));
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 1, height: 100, padding: "8px 0" }}>
      {data.map((d, i) => (
        <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", width: barWidth }}>
          <div title={`${d.date} 分数:${d.avg_score}`}
               style={{ width: "100%", height: `${(d.avg_score / maxScore) * 50}px`,
                        background: d.avg_score >= 60 ? "#52c41a" : "#faad14", borderRadius: "2px 2px 0 0" }} />
          <div title={`${d.date} 次数:${d.session_count}`}
               style={{ width: "100%", height: `${(d.session_count / maxCount) * 40}px`,
                        background: "#1890ff", borderRadius: "0 0 2px 2px", opacity: 0.6 }} />
        </div>
      ))}
    </div>
  );
};

// ── Main Component ──────────────────────────────────────────────────────
export default function CoachPage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<CoachSummary | null>(null);
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [selectedClassId, setSelectedClassId] = useState<number | null>(null);
  const [classStats, setClassStats] = useState<ClassStats | null>(null);
  const [trendData, setTrendData] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  // Modal states
  const [createModal, setCreateModal] = useState(false);
  const [addModal, setAddModal] = useState(false);
  const [className, setClassName] = useState("");
  const [addForm] = Form.useForm();
  const [traineeOptions, setTraineeOptions] = useState<{ value: number; label: string }[]>([]);
  const [traineeSearching, setTraineeSearching] = useState(false);

  // Search available trainees by keyword
  const searchTrainees = async (keyword: string) => {
    if (!keyword) { setTraineeOptions([]); return; }
    setTraineeSearching(true);
    try {
      const data = await coachApi.availableTrainees(keyword);
      setTraineeOptions(data.map((t: any) => ({ value: t.id, label: `${t.username} (ID:${t.id})` })));
    } catch { setTraineeOptions([]); }
    finally { setTraineeSearching(false); }
  };

  // Load initial data
  useEffect(() => {
    setLoading(true);
    Promise.all([
      coachApi.summary().then(setSummary),
      coachApi.classes().then(setClasses),
    ]).finally(() => setLoading(false));
  }, []);

  // Load class detail
  const loadClassDetail = async (classId: number) => {
    setSelectedClassId(classId);
    setDetailLoading(true);
    try {
      const [statsRes, trendRes] = await Promise.all([
        coachApi.classStats(classId),
        coachApi.classTrend(classId, 14),
      ]);
      setClassStats(statsRes);
      setTrendData(trendRes.trend || []);
    } catch { message.error("加载班级详情失败"); }
    finally { setDetailLoading(false); }
  };

  const createClass = async () => {
    if (!className) { message.warning("请输入班级名称"); return; }
    try {
      await coachApi.createClass(className);
      message.success("班级创建成功");
      setCreateModal(false); setClassName("");
      const data = await coachApi.classes();
      setClasses(data);
    } catch { message.error("创建失败"); }
  };

  const addStudent = async () => {
    try {
      const values = await addForm.validateFields();
      const classId: number = values.classId;
      const studentId: number = values.studentId;
      await coachApi.addStudent(classId, studentId);
      message.success("学员已添加");
      setAddModal(false);
      addForm.resetFields();
      if (selectedClassId === classId) loadClassDetail(classId);
    } catch (e: any) {
      if (e.errorFields) return; // 表单校验失败，不弹错误
      message.error(e.response?.data?.detail || "添加失败");
    }
  };

  // ── Render ──
  return (
    <div>
      {loading ? (
        <Spin size="large" style={{ display: "block", margin: "80px auto" }} />
      ) : selectedClassId && classStats ? (
        /* ── Detail View ── */
        (() => {
          const s = classStats.summary;
          return (
            <div>
              <Button type="link" onClick={() => { setSelectedClassId(null); setClassStats(null); }}
                      style={{ marginBottom: 12, padding: 0 }}>← 返回班级列表</Button>

              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={6}><Card><Statistic title="班级" value={classStats.class_name} prefix={<TeamOutlined />} /></Card></Col>
                <Col span={6}><Card><Statistic title="学员数" value={classStats.student_count} prefix={<UserOutlined />} /></Card></Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="平均综合分" value={s.avg_overall_score} suffix="/100" prefix={<TrophyOutlined />} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="7日活跃率" value={s.active_7d_rate} suffix="%" prefix={s.active_7d_rate >= 50 ? <ArrowUpOutlined style={{color:"#52c41a"}} /> : <ArrowDownOutlined style={{color:"#f5222d"}} />} />
                  </Card>
                </Col>
              </Row>

              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={12}>
                  <Card title="训练趋势" size="small">
                    <MiniTrend data={trendData} />
                    <div style={{ fontSize: 12, color: "#888", textAlign: "center" }}>
                      <span style={{ color: "#1890ff" }}>■</span> 训练次数
                      <span style={{ color: "#52c41a", marginLeft: 12 }}>■</span> 平均分
                    </div>
                  </Card>
                </Col>
                <Col span={12}>
                  <Card title="本周概况" size="small">
                    <Descriptions column={2} size="small">
                      <Descriptions.Item label="7日总训练">{s.total_sessions_7d} 次</Descriptions.Item>
                      <Descriptions.Item label="30日总训练">{s.total_sessions_30d} 次</Descriptions.Item>
                      <Descriptions.Item label="人均周训练">{s.sessions_per_student_7d} 次</Descriptions.Item>
                      <Descriptions.Item label="本周训练学员">{s.active_7d_count}/{classStats.student_count} 人</Descriptions.Item>
                      <Descriptions.Item label="平均综合分">{s.avg_overall_score}</Descriptions.Item>
                      <Descriptions.Item label="完成率">{s.active_7d_rate}%</Descriptions.Item>
                    </Descriptions>
                  </Card>
                </Col>
              </Row>

              <Card title="学员进度" size="small" loading={detailLoading} extra={
                <Button size="small" icon={<PlusOutlined />} onClick={() => { addForm.setFieldsValue({ classId: selectedClassId }); setAddModal(true); }}>添加学员</Button>
              }>
                <Table dataSource={classStats.students} rowKey="id" size="small" pagination={false}
                  columns={[
                    { title: "ID", dataIndex: "id", width: 40 },
                    { title: "用户名", dataIndex: "username", width: 80,
                      render: (v: string, r: StudentProgress) => (
                        <a onClick={() => navigate(`/coach/student/${r.id}`)} style={{ color: "#1890ff", cursor: "pointer" }}>
                          {v}
                        </a>
                      ),
                    },
                    { title: "风险", dataIndex: "risk_level", width: 60,
                      render: (v: string) => v ? <Tag color={riskColor[v] || "default"}>{v}</Tag> : "-"
                    },
                    { title: "FMS评分", width: 260,
                      render: (_, r: StudentProgress) =>
                        r.fms_scores ? (
                          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                            <ScoreBar label="平衡" value={r.fms_scores.balance || 0} />
                            <ScoreBar label="灵活" value={r.fms_scores.flexibility || 0} />
                            <ScoreBar label="上肢" value={r.fms_scores.upper_limb || 0} />
                            <ScoreBar label="核心" value={r.fms_scores.core || 0} />
                            <ScoreBar label="对称" value={r.fms_scores.symmetry || 0} />
                          </div>
                        ) : <Tag color="default">未筛查</Tag>,
                    },
                    { title: "7日训练", dataIndex: "sessions_7d", width: 70,
                      render: (v: number) => <Tag color={v >= 3 ? "green" : v >= 1 ? "blue" : "default"}>{v}次</Tag>
                    },
                    { title: "打卡天数", dataIndex: "streak_days", width: 80,
                      render: (v: number) => <span>{v > 0 ? `🔥 ${v}天` : "-"}</span>
                    },
                  ]}
                />
              </Card>
            </div>
          );
        })()
      ) : (
        /* ── List View ── */
        <div>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}><Card><Statistic title="班级数" value={summary?.class_count || 0} prefix={<TeamOutlined />} /></Card></Col>
            <Col span={6}><Card><Statistic title="学员总数" value={summary?.total_students || 0} prefix={<UserOutlined />} /></Card></Col>
            <Col span={6}><Card><Statistic title="7日训练" value={summary?.sessions_7d || 0} suffix="次" prefix={<BarChartOutlined />} /></Card></Col>
            <Col span={6}><Card><Statistic title="30日训练" value={summary?.sessions_30d || 0} suffix="次" /></Card></Col>
          </Row>

          <Card title="班级管理" extra={
            <Space>
              <Button icon={<PlusOutlined />} onClick={() => setCreateModal(true)}>新建班级</Button>
              <Button onClick={() => { setAddModal(true); }}>添加学员</Button>
            </Space>
          }>
            {classes.length === 0 ? (
              <Empty description="暂无班级，点击新建班级开始" />
            ) : (
              <Row gutter={[16, 16]}>
                {classes.map(c => (
                  <Col span={8} key={c.id}>
                    <Card hoverable onClick={() => loadClassDetail(c.id)}
                          title={<span><TeamOutlined /> {c.name}</span>}
                          extra={<Tag color="blue">{c.student_count}人</Tag>}>
                      <p style={{ color: "#888", fontSize: 13, minHeight: 40 }}>
                        {c.description || "暂无描述"}
                      </p>
                      <Button type="primary" size="small" ghost
                              onClick={(e) => { e.stopPropagation(); loadClassDetail(c.id); }}>
                        查看统计
                      </Button>
                    </Card>
                  </Col>
                ))}
              </Row>
            )}
          </Card>
        </div>
      )}

      {/* Modals — 渲染在条件视图之外，列表页和详情页均可触发 */}
      <Modal title="新建班级" open={createModal} onOk={createClass} onCancel={() => setCreateModal(false)}>
        <Input placeholder="班级名称" value={className} onChange={e => setClassName(e.target.value)} />
      </Modal>

      <Modal
        title="添加学员"
        open={addModal}
        onOk={addStudent}
        onCancel={() => { setAddModal(false); addForm.resetFields(); }}
        destroyOnHidden
      >
        <Form form={addForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="classId" label="班级" rules={[{ required: true, message: "请选择班级" }]}>
            <Select
              placeholder="选择班级"
              showSearch
              optionFilterProp="label"
              options={classes.map(c => ({ value: c.id, label: `${c.name}（${c.student_count}人）` }))}
            />
          </Form.Item>
          <Form.Item name="studentId" label="学员" rules={[{ required: true, message: "请选择学员" }]}>
            <Select
              placeholder="输入用户名搜索学员"
              showSearch
              filterOption={false}
              onSearch={searchTrainees}
              loading={traineeSearching}
              options={traineeOptions}
              notFoundContent={traineeSearching ? '搜索中...' : '请输入关键词搜索'}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
