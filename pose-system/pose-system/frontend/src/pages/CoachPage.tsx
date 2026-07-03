import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card, Table, Button, Modal, Input, Tag, Space, message,
  Statistic, Row, Col, Descriptions, Empty, Spin,
  Form, Select, Popconfirm, Tabs, Typography
} from "antd";
import {
  PlusOutlined, TeamOutlined, BarChartOutlined,
  UserOutlined, TrophyOutlined, ArrowUpOutlined, ArrowDownOutlined,
  DeleteOutlined, EditOutlined, ReloadOutlined, IdcardOutlined,
  CopyOutlined, SyncOutlined
} from "@ant-design/icons";
import { coachApi } from "../services/api";
import ScoreBar from "../components/ScoreBar";
import { riskColor } from "../utils/riskColor";

const { Text } = Typography;

// ── Types ────────────────────────────────────────────────────────────────
interface ClassInfo {
  id: number; name: string; description?: string;
  student_count: number; created_at: string;
  invite_code?: string;
}
interface StudentProgress {
  id: number; username: string; phone: string;
  fms_scores: Record<string, number> | null;
  sessions_7d: number; sessions_30d: number;
  streak_days: number; risk_level: string | null;
}
interface StudentBrief {
  id: number; username: string; phone?: string;
  class_id?: number; class?: string;
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

  // Tab state
  const [activeTab, setActiveTab] = useState("classes");

  // Class management states
  const [summary, setSummary] = useState<CoachSummary | null>(null);
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [selectedClassId, setSelectedClassId] = useState<number | null>(null);
  const [classStats, setClassStats] = useState<ClassStats | null>(null);
  const [trendData, setTrendData] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  // Student management states
  const [allStudents, setAllStudents] = useState<StudentBrief[]>([]);
  const [studentsLoading, setStudentsLoading] = useState(false);

  // Modal states
  const [createModal, setCreateModal] = useState(false);
  const [addModal, setAddModal] = useState(false);
  const [className, setClassName] = useState("");
  const [addForm] = Form.useForm();
  const [traineeOptions, setTraineeOptions] = useState<{ value: number; label: string }[]>([]);
  const [traineeSearching, setTraineeSearching] = useState(false);
  const [editClassModal, setEditClassModal] = useState(false);
  const [editClassName, setEditClassName] = useState('');
  const [editClassDesc, setEditClassDesc] = useState('');
  const [editClassId, setEditClassId] = useState<number | null>(null);

  // ── Data loading ───────────────────────────────────────────────────────

  const loadAllStudents = useCallback(async () => {
    setStudentsLoading(true);
    try {
      const data = await coachApi.students();
      setAllStudents(Array.isArray(data) ? data : []);
    } catch { /* ignore */ }
    finally { setStudentsLoading(false); }
  }, []);

  const refreshAllData = useCallback(async () => {
    setLoading(true);
    try {
      await Promise.all([
        coachApi.summary().then(setSummary),
        coachApi.classes().then(setClasses),
        coachApi.students().then(d => setAllStudents(Array.isArray(d) ? d : [])),
      ]);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, []);

  // Initial load
  useEffect(() => { refreshAllData(); }, []);

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

  // ── Class operations ───────────────────────────────────────────────────

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
      await refreshAllData();
    } catch { message.error("创建失败"); }
  };

  const handleEditClass = (c: ClassInfo) => {
    setEditClassId(c.id);
    setEditClassName(c.name);
    setEditClassDesc(c.description || '');
    setEditClassModal(true);
  };

  const handleSaveClass = async () => {
    if (!editClassId) return;
    try {
      await coachApi.updateClass(editClassId, { name: editClassName, description: editClassDesc });
      message.success('班级已更新');
      setEditClassModal(false);
      coachApi.classes().then(setClasses);
      if (selectedClassId === editClassId) loadClassDetail(editClassId);
    } catch { message.error('更新失败'); }
  };

  const handleDeleteClass = async (classId: number) => {
    try {
      await coachApi.deleteClass(classId);
      message.success('班级已删除');
      setSelectedClassId(null);
      setClassStats(null);
      await refreshAllData();
    } catch (e: any) { message.error(e?.response?.data?.detail || '删除失败'); }
  };

  const handleCopyCode = (code: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    navigator.clipboard.writeText(code).then(
      () => message.success(`邀请码 ${code} 已复制`),
      () => message.error('复制失败')
    );
  };

  const handleRegenerateCode = async (classId: number, e?: React.MouseEvent) => {
    e?.stopPropagation();
    try {
      const res = await coachApi.regenerateCode(classId);
      message.success(`邀请码已更新为 ${res.invite_code}`);
      await loadClasses();
      if (selectedClassId === classId) loadClassDetail(classId);
    } catch (e: any) { message.error(e?.response?.data?.detail || '刷新邀请码失败'); }
  };

  // ── Student operations ─────────────────────────────────────────────────

  const addStudent = async () => {
    try {
      const values = await addForm.validateFields();
      const classId: number = values.classId;
      const studentId: number = values.studentId;
      await coachApi.addStudent(classId, studentId);
      message.success("学员已添加");
      setAddModal(false);
      addForm.resetFields();
      // Refresh data
      await refreshAllData();
      if (selectedClassId === classId) loadClassDetail(classId);
    } catch (e: any) {
      if (e.errorFields) return;
      message.error(e.response?.data?.detail || "添加失败");
    }
  };

  const handleRemoveStudent = async (studentId: number, classId?: number) => {
    const cid = classId || selectedClassId;
    if (!cid) { message.warning("请先选择班级"); return; }
    try {
      await coachApi.removeStudent(cid, studentId);
      message.success('学员已移除');
      if (selectedClassId === cid) loadClassDetail(cid);
      await loadAllStudents();
    } catch { message.error('移除失败'); }
  };

  // ── Render: 班级管理 tab ────────────────────────────────────────────────

  const renderClassManagement = () => {
    if (loading) return <Spin size="large" style={{ display: "block", margin: "80px auto" }} />;

    if (selectedClassId && classStats) {
      // ── Class Detail View ──
      const s = classStats.summary;
      return (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Button type="link" onClick={() => { setSelectedClassId(null); setClassStats(null); }}
                    style={{ padding: 0 }}>← 返回班级列表</Button>
            <Space>
              <Button icon={<EditOutlined />} size="small" onClick={() => {
                const c = classes.find(cl => cl.id === selectedClassId);
                if (c) handleEditClass(c);
              }}>编辑班级</Button>
              <Popconfirm
                title="确认删除此班级？班级中如有学员需先移除"
                onConfirm={() => selectedClassId && handleDeleteClass(selectedClassId)}
              >
                <Button icon={<DeleteOutlined />} danger size="small">删除班级</Button>
              </Popconfirm>
            </Space>
          </div>

          {/* ── Invite Code Banner ── */}
          {(() => {
            const currentClass = classes.find(cl => cl.id === selectedClassId);
            if (currentClass?.invite_code) {
              return (
                <Card size="small" style={{ marginBottom: 16, background: "#f0f5ff" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <Text strong>班级邀请码</Text>
                    <Tag color="blue" style={{
                      fontFamily: "monospace", fontSize: 18, letterSpacing: 3,
                      padding: "4px 16px", cursor: "pointer",
                    }} onClick={() => handleCopyCode(currentClass.invite_code!)}>
                      {currentClass.invite_code}
                    </Tag>
                    <Button size="small" icon={<CopyOutlined />}
                            onClick={() => handleCopyCode(currentClass.invite_code!)}>
                      复制
                    </Button>
                    <Popconfirm title="确认刷新邀请码？旧邀请码将失效"
                                onConfirm={() => handleRegenerateCode(selectedClassId)}>
                      <Button size="small" icon={<SyncOutlined />}>刷新</Button>
                    </Popconfirm>
                    <Text type="secondary" style={{ fontSize: 12, marginLeft: "auto" }}>
                      将邀请码分享给学员即可加入班级
                    </Text>
                  </div>
                </Card>
              );
            }
            return null;
          })()}

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

          <Card title="班级学员" size="small" loading={detailLoading} extra={
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
                { title: "操作", key: "actions", width: 70,
                  render: (_: any, r: StudentProgress) => (
                    <Popconfirm
                      title="确认从班级移除此学员？"
                      onConfirm={() => handleRemoveStudent(r.id)}
                    >
                      <Button type="link" danger size="small" icon={<DeleteOutlined />}>移除</Button>
                    </Popconfirm>
                  ),
                },
              ]}
            />
          </Card>
        </div>
      );
    }

    // ── Class List View ──
    return (
      <div>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}><Card><Statistic title="班级数" value={summary?.class_count || 0} prefix={<TeamOutlined />} /></Card></Col>
          <Col span={6}><Card><Statistic title="学员总数" value={summary?.total_students || 0} prefix={<UserOutlined />} /></Card></Col>
          <Col span={6}><Card><Statistic title="7日训练" value={summary?.sessions_7d || 0} suffix="次" prefix={<BarChartOutlined />} /></Card></Col>
          <Col span={6}><Card><Statistic title="30日训练" value={summary?.sessions_30d || 0} suffix="次" /></Card></Col>
        </Row>

        <Card title="班级管理" extra={
          <Button icon={<PlusOutlined />} onClick={() => setCreateModal(true)}>新建班级</Button>
        }>
          {classes.length === 0 ? (
            <Empty description="暂无班级，点击新建班级开始" />
          ) : (
            <Row gutter={[16, 16]}>
              {classes.map(c => (
                <Col span={8} key={c.id}>
                  <Card hoverable onClick={() => loadClassDetail(c.id)}
                        title={<span><TeamOutlined /> {c.name}</span>}
                        extra={
                          <Space>
                            <Tag color="blue">{c.student_count}人</Tag>
                            <Button size="small" type="text" icon={<EditOutlined />}
                                    onClick={(e) => { e.stopPropagation(); handleEditClass(c); }} />
                            <Popconfirm title="确认删除此班级？" onConfirm={(e) => { e?.stopPropagation(); handleDeleteClass(c.id); }}
                                        onCancel={(e) => e?.stopPropagation()}>
                              <Button size="small" type="text" danger icon={<DeleteOutlined />}
                                      onClick={(e) => e.stopPropagation()} />
                            </Popconfirm>
                          </Space>
                        }>
                    <p style={{ color: "#888", fontSize: 13, minHeight: 20, marginBottom: 8 }}>
                      {c.description || "暂无描述"}
                    </p>
                    <div style={{
                      display: "flex", alignItems: "center", gap: 8, marginBottom: 12,
                      padding: "8px 12px", background: "#f6f8fa", borderRadius: 8,
                    }} onClick={(e) => e.stopPropagation()}>
                      <Text type="secondary" style={{ fontSize: 12, flexShrink: 0 }}>邀请码</Text>
                      <Tag color="blue" style={{
                        fontFamily: "monospace", fontSize: 14, letterSpacing: 2,
                        margin: 0, flex: 1, textAlign: "center", cursor: "pointer",
                      }} onClick={(e) => { e.stopPropagation(); handleCopyCode(c.invite_code || ""); }}>
                        {c.invite_code || "---"}
                      </Tag>
                      <Button size="small" type="text" icon={<CopyOutlined />}
                              onClick={(e) => handleCopyCode(c.invite_code || "", e)}
                              title="复制邀请码" />
                      <Popconfirm title="确认刷新邀请码？旧邀请码将失效"
                                  onConfirm={(e) => { handleRegenerateCode(c.id, e as any); }}
                                  onCancel={(e) => e?.stopPropagation()}>
                        <Button size="small" type="text" icon={<SyncOutlined />}
                                onClick={(e) => e.stopPropagation()}
                                title="刷新邀请码" />
                      </Popconfirm>
                    </div>
                    <Button type="primary" size="small" ghost style={{ color: "#000" }}
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
    );
  };

  // ── Render: 学员管理 tab ────────────────────────────────────────────────

  const renderStudentManagement = () => {
    return (
      <Card
        title={<span><IdcardOutlined /> 全部学员 <Tag style={{ marginLeft: 8 }}>{allStudents.length}人</Tag></span>}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadAllStudents} loading={studentsLoading}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddModal(true)}>添加学员</Button>
          </Space>
        }
      >
        {allStudents.length === 0 && !studentsLoading ? (
          <Empty
            description={
              <div>
                <Text type="secondary">暂无学员</Text>
                <br />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  请先创建班级，然后在班级中或通过"添加学员"按钮添加学员
                </Text>
              </div>
            }
            style={{ padding: "40px 0" }}
          >
            <Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModal(true)}>新建班级</Button>
              <Button icon={<PlusOutlined />} onClick={() => setAddModal(true)}>添加学员</Button>
            </Space>
          </Empty>
        ) : (
          <Table
            dataSource={allStudents}
            rowKey={(r) => `${r.id}-${r.class_id || ''}`}
            size="small"
            loading={studentsLoading}
            pagination={allStudents.length > 20 ? { pageSize: 20, showSizeChanger: true, showTotal: t => `共 ${t} 人` } : false}
            columns={[
              { title: "ID", dataIndex: "id", width: 50 },
              {
                title: "用户名", dataIndex: "username", width: 100,
                render: (v: string, r: StudentBrief) => (
                  <a onClick={() => navigate(`/coach/student/${r.id}`)} style={{ color: "#1890ff", cursor: "pointer", fontWeight: 500 }}>
                    {v}
                  </a>
                ),
              },
              { title: "手机号", dataIndex: "phone", width: 120, render: (v: string) => v || '-' },
              {
                title: "所属班级", dataIndex: "class", width: 120,
                render: (v: string) => v ? <Tag color="blue">{v}</Tag> : <Tag color="default">未分班</Tag>
              },
              {
                title: "操作", key: "actions", width: 130,
                render: (_: any, r: StudentBrief) => (
                  <Space size="small">
                    <Button type="link" size="small"
                            onClick={() => navigate(`/coach/student/${r.id}`)}>
                      查看详情
                    </Button>
                    {r.class_id && (
                      <Popconfirm
                        title={`确认将 ${r.username} 从班级中移除？`}
                        onConfirm={() => handleRemoveStudent(r.id, r.class_id!)}
                      >
                        <Button type="link" danger size="small" icon={<DeleteOutlined />}>移除</Button>
                      </Popconfirm>
                    )}
                  </Space>
                ),
              },
            ]}
          />
        )}
      </Card>
    );
  };

  // ── Render ──
  return (
    <div>
      <Tabs
        activeKey={activeTab}
        onChange={key => {
          setActiveTab(key);
          if (key === "classes") {
            // Reset to list view when switching to classes tab
            setSelectedClassId(null);
            setClassStats(null);
          }
          if (key === "students") {
            loadAllStudents();
          }
        }}
        items={[
          {
            key: "classes",
            label: <span><TeamOutlined /> 班级管理</span>,
            children: renderClassManagement(),
          },
          {
            key: "students",
            label: <span><IdcardOutlined /> 学员管理 ({allStudents.length})</span>,
            children: renderStudentManagement(),
          },
        ]}
        style={{ marginTop: -8 }}
      />

      {/* ── Modals ── */}
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
          <Form.Item name="classId" label="选择班级" rules={[{ required: true, message: "请选择班级" }]}>
            <Select
              placeholder="选择要添加到的班级"
              showSearch
              optionFilterProp="label"
              options={classes.map(c => ({ value: c.id, label: `${c.name}（${c.student_count}人）` }))}
              notFoundContent={
                <div style={{ padding: 8, textAlign: 'center' }}>
                  <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>暂无班级</Text>
                  <Button size="small" type="link" onClick={() => { setAddModal(false); setCreateModal(true); }}>
                    去创建班级
                  </Button>
                </div>
              }
            />
          </Form.Item>
          <Form.Item name="studentId" label="搜索学员" rules={[{ required: true, message: "请选择学员" }]}>
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

      <Modal
        title="编辑班级"
        open={editClassModal}
        onOk={handleSaveClass}
        onCancel={() => setEditClassModal(false)}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input
            placeholder="班级名称"
            value={editClassName}
            onChange={e => setEditClassName(e.target.value)}
          />
          <Input.TextArea
            placeholder="班级描述（可选）"
            value={editClassDesc}
            onChange={e => setEditClassDesc(e.target.value)}
            rows={3}
          />
        </Space>
      </Modal>
    </div>
  );
}
