/**
 * AI 训练计划
 *
 * 基于体态评估与FMS筛查结果，智能生成个性化训练计划
 */
import React, { useState, useEffect, useCallback } from "react";
import {
  Card, Tabs, Table, Tag, Button, Select, InputNumber, Input,
  Space, Spin, Empty, message, Modal,
  Descriptions, Steps, Typography, Divider,
} from "antd";
import {
  ThunderboltOutlined, BookOutlined, ReloadOutlined,
  AimOutlined, BarChartOutlined, PlusOutlined, DeleteOutlined,
} from "@ant-design/icons";
import { prescriptionV2Api, assessmentApi, fmsApi, planEditApi } from "../services/api";
import type {
  PlanV2, PlanItemV2, ActionLibItem, ActionLibResponse,
  AssessmentRecord, FMSRecord,
} from "../types";

const { Text, Title, Paragraph } = Typography;

// ---------- Constants ----------

const PHASE_TAG_COLORS: Record<string, string> = {
  warmup: "blue", main: "red", cooldown: "green",
};
const INTENSITY_TAG_COLORS: Record<string, string> = {
  LOW: "green", MEDIUM: "orange", HIGH: "red",
};

// ---------- Component ----------

const PrescriptionPage: React.FC = () => {
  // --- State ---
  const [activeTab, setActiveTab] = useState("prescription");

  // Action library
  const [actionLib, setActionLib] = useState<ActionLibResponse | null>(null);
  const [libLoading, setLibLoading] = useState(false);
  const [libSearch, setLibSearch] = useState("");

  // Records from DB
  const [assessments, setAssessments] = useState<AssessmentRecord[]>([]);
  const [fmsRecords, setFmsRecords] = useState<FMSRecord[]>([]);
  const [recordsLoading, setRecordsLoading] = useState(false);

  // Generation
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<number | null>(null);
  const [selectedFMSId, setSelectedFMSId] = useState<number | null>(null);
  const [userLevel, setUserLevel] = useState(1);
  const [generating, setGenerating] = useState(false);
  const [plan, setPlan] = useState<PlanV2 | null>(null);
  const [genMethod, setGenMethod] = useState("");
  const [plans, setPlans] = useState<PlanV2[]>([]);

  // --- Data Loading ---
  const loadRecords = useCallback(async () => {
    setRecordsLoading(true);
    try {
      const [aList, fList] = await Promise.all([
        assessmentApi.getRecords(),
        fmsApi.getRecords(),
      ]);
      setAssessments(aList || []);
      setFmsRecords(fList || []);
    } catch { /* ignore */ }
    finally { setRecordsLoading(false); }
  }, []);

  const loadPlans = useCallback(async () => {
    try {
      const r = await prescriptionV2Api.list();
      if (r.plans) setPlans(r.plans);
    } catch { /* ignore */ }
  }, []);

  const loadActionLib = useCallback(async () => {
    setLibLoading(true);
    try {
      const r = await prescriptionV2Api.getActions();
      setActionLib(r);
    } catch { message.error("加载动作库失败"); }
    finally { setLibLoading(false); }
  }, []);

  useEffect(() => { loadRecords(); loadPlans(); }, [loadRecords, loadPlans]);

  // --- Handlers ---
  const handleGenerate = async () => {
    if (!selectedAssessmentId && !selectedFMSId) {
      message.warning("请至少选择一项评估或筛查记录");
      return;
    }
    setGenerating(true);
    try {
      const r = await prescriptionV2Api.generate({
        assessment_record_id: selectedAssessmentId || 0,
        fms_record_id: selectedFMSId || 0,
        user_level: userLevel,
      });
      setPlan(r.plan || null);
      setGenMethod(r.generation_method || "");
      message.success("训练计划生成成功");
      loadPlans();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "生成失败");
    } finally { setGenerating(false); }
  };

  const handleDelete = (planId: number) => {
    Modal.confirm({
      title: "确认删除",
      content: "删除后不可恢复，确定要删除此训练计划吗？",
      okText: "确认删除",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        try {
          await prescriptionV2Api.delete(planId);
          message.success("计划已删除");
          if (plan?.id === planId) setPlan(null);
          loadPlans();
        } catch (e: any) {
          message.error(e?.response?.data?.detail || "删除失败");
        }
      },
    });
  };

  const handleActivate = async (planId: number) => {
    try { await prescriptionV2Api.activate(planId); message.success("计划已激活"); loadPlans(); }
    catch { message.error("激活失败"); }
  };

  // ── Edit Plan ──
  const [editModal, setEditModal] = useState(false);
  const [editingPlan, setEditingPlan] = useState<PlanV2 | null>(null);
  const [editItems, setEditItems] = useState<any[]>([]);
  const [editName, setEditName] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [editing, setEditing] = useState(false);

  const handleEdit = (plan: PlanV2) => {
    setEditingPlan(plan);
    setEditName(plan.plan_name);
    setEditNotes("");
    setEditItems((plan.items || []).map(item => ({
      action_name: item.action_name,
      action_id: item.action_id,
      phase: item.phase,
      sets: item.sets,
      reps: item.reps,
      duration_seconds: item.duration_seconds,
      order_index: item.order_index,
      difficulty: item.difficulty,
      intensity: item.intensity,
      notes: item.notes || '',
    })));
    setEditModal(true);
  };

  const updateEditItem = (idx: number, field: string, value: any) => {
    setEditItems(prev => prev.map((item, i) =>
      i === idx ? { ...item, [field]: value } : item
    ));
  };

  const addEditItem = (actionId: string) => {
    const libAction = actionLib?.actions?.find(a => a.id === actionId);
    if (!libAction) return;
    const newItem = {
      action_name: libAction.name,
      action_id: libAction.id,
      phase: libAction.phases?.[0] || 'main',
      sets: libAction.default_sets || 3,
      reps: libAction.default_reps || 10,
      duration_seconds: libAction.default_duration_seconds || 0,
      order_index: editItems.length + 1,
      difficulty: libAction.difficulty || 1,
      intensity: libAction.intensity || 'MEDIUM',
      notes: '',
    };
    setEditItems(prev => [...prev, newItem]);
    setAddActionId(undefined);
  };

  const removeEditItem = (idx: number) => {
    setEditItems(prev => prev.filter((_, i) => i !== idx));
  };

  const [addActionId, setAddActionId] = useState<string | undefined>(undefined);

  const saveEdit = async () => {
    if (!editingPlan) return;
    setEditing(true);
    try {
      const res = await planEditApi.edit(editingPlan.id, {
        plan_name: editName,
        items: editItems,
        student_notes: editNotes || undefined,
      });
      if (res.status === 'pending') {
        message.success(res.message || '已提交教练审批');
      } else {
        message.success(res.message || '计划已更新');
      }
      setEditModal(false);
      loadPlans();
      if (plan?.id === editingPlan.id) setPlan(null);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "保存失败");
    } finally { setEditing(false); }
  };

  // ---------- Tab: Action Library ----------
  const renderActionLibTab = () => (
    <Card title="标准动作库" size="small"
      extra={<Button size="small" icon={<ReloadOutlined />} onClick={loadActionLib} loading={libLoading}>加载</Button>}
    >
      {!actionLib ? (
        <Empty description="点击「加载」获取标准动作列表" />
      ) : (
        <>
          <Space style={{ marginBottom: 12 }}>
            <Text>搜索：</Text>
            <Select showSearch size="small" style={{ width: 240 }} placeholder="输入动作名称"
              value={libSearch || undefined} onChange={setLibSearch} allowClear
              filterOption={(input, option) => (option?.label as string)?.toLowerCase().includes(input.toLowerCase())}
              options={actionLib.actions.map(a => ({ label: `${a.name} (${a.category})`, value: a.id }))}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              共 {actionLib.total} 个动作，{actionLib.families?.length || 0} 个家族
            </Text>
          </Space>
          <Table size="small" pagination={{ pageSize: 10 }}
            dataSource={libSearch ? actionLib.actions.filter(a => a.id === libSearch) : actionLib.actions}
            rowKey="id"
            columns={[
              { title: "名称", dataIndex: "name", width: 160 },
              { title: "家族", dataIndex: "family_name", width: 100 },
              { title: "类别", dataIndex: "category", width: 80, render: (v: string) => <Tag>{v}</Tag> },
              { title: "难度", dataIndex: "difficulty", width: 60, render: (v: number) => "⭐".repeat(v) },
              { title: "强度", dataIndex: "intensity", width: 70, render: (v: string) => <Tag color={INTENSITY_TAG_COLORS[v] || "default"}>{v}</Tag> },
              { title: "阶段", dataIndex: "phases", width: 160, render: (v: string[]) => v?.map(p => <Tag key={p} color={PHASE_TAG_COLORS[p] || "default"}>{p}</Tag>) },
              { title: "目标部位", dataIndex: "target_body_parts", render: (v: string[]) => v?.join(", "), width: 140 },
            ]}
          />
        </>
      )}
    </Card>
  );

  // ---------- Tab: Prescription Generation ----------
  const renderPrescriptionTab = () => (
    <div>
      {/* Record Selection */}
      <Card size="small" title="选择评估与筛查记录" style={{ marginBottom: 16 }}>
        <Spin spinning={recordsLoading}>
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <Space wrap>
              <Space>
                <AimOutlined style={{ color: "var(--color-cyan)" }} />
                <Text strong>体态评估记录：</Text>
                <Select
                  size="small" style={{ minWidth: 220 }} placeholder="选择评估记录"
                  value={selectedAssessmentId}
                  onChange={setSelectedAssessmentId}
                  allowClear
                  loading={recordsLoading}
                  options={assessments.map(a => ({
                    label: `#${a.id} | ${a.test_date?.slice(0, 10)} | 总分${a.overall_score} | ${a.risk_level === "low" ? "低风险" : a.risk_level === "medium" ? "中风险" : "高风险"}`,
                    value: a.id,
                  }))}
                  notFoundContent="暂无评估记录 — 请先进行体态评估"
                />
              </Space>
            </Space>

            <Space wrap>
              <Space>
                <BarChartOutlined style={{ color: "var(--color-cyan)" }} />
                <Text strong>FMS 筛查记录：</Text>
                <Select
                  size="small" style={{ minWidth: 220 }} placeholder="选择FMS记录"
                  value={selectedFMSId}
                  onChange={setSelectedFMSId}
                  allowClear
                  loading={recordsLoading}
                  options={fmsRecords.map(f => ({
                    label: `#${f.id} | ${f.test_date?.slice(0, 10)} | 总分${f.overall_score} | ${f.risk_level === "low" ? "低风险" : f.risk_level === "medium" ? "中风险" : "高风险"}`,
                    value: f.id,
                  }))}
                  notFoundContent="暂无FMS记录 — 请先进行FMS筛查"
                />
              </Space>
            </Space>
          </Space>
        </Spin>
      </Card>

      {/* Generation Config */}
      <Card size="small" title="生成配置" style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
          <Space>
            <Text>训练者类型：</Text>
            <Select value={userLevel} onChange={setUserLevel} size="small" style={{ width: 140 }}
              options={[
                { label: "心血来潮", value: 1 },
                { label: "偶尔进行", value: 2 },
                { label: "渐入佳境", value: 3 },
                { label: "健身发烧友", value: 4 },
                { label: "肌肉掌控者", value: 5 },
              ]}
            />
          </Space>
          <Button type="primary" icon={<ThunderboltOutlined />} loading={generating} onClick={handleGenerate} size="large">
            生成 AI 训练计划
          </Button>
        </Space>
      </Card>

      {/* Generated Plan */}
      {plan && (
        <Card size="small" title={
          <Space>
            <Text strong style={{ color: "var(--color-text-primary)" }}>{plan.plan_name}</Text>
            <Tag color={genMethod === "deepseek" ? "purple" : "blue"}>
              {genMethod === "deepseek" ? "DeepSeek AI" : "本地引擎"}
            </Tag>
            <Tag color={plan.status === "active" ? "green" : "default"}>{plan.status}</Tag>
          </Space>
        } style={{ marginBottom: 16 }}>
          {plan.overall_strategy && <Paragraph type="secondary" style={{ fontSize: 13 }}>{plan.overall_strategy}</Paragraph>}
          <Steps size="small" style={{ marginTop: 12, marginBottom: 16 }} current={0}
            items={[{ title: "热身", status: "finish" }, { title: "主训练", status: "process" }, { title: "冷身", status: "wait" }]}
          />
          {["warmup", "main", "cooldown"].map(phase => {
            const items = plan.items.filter(i => i.phase === phase);
            if (items.length === 0) return null;
            return (
              <Card key={phase} size="small" style={{ marginBottom: 8 }}
                title={<Tag color={PHASE_TAG_COLORS[phase]}>{phase === "warmup" ? "热身" : phase === "main" ? "主训练" : "冷身"}</Tag>}
              >
                {items.map(item => (
                  <div key={item.id} style={{ marginBottom: 8 }}>
                    <Space>
                      <Text strong>{item.order_index}. {item.action_name}</Text>
                      <Tag>{item.sets} 组 x {item.reps} 次</Tag>
                      <Tag color={INTENSITY_TAG_COLORS[item.intensity] || "default"}>{item.intensity}</Tag>
                      {item.is_substitution && <Tag color="warning">替代</Tag>}
                    </Space>
                    <div><Text type="secondary" style={{ fontSize: 12 }}>{item.duration_seconds}s | 难度: {"⭐".repeat(item.difficulty)}</Text></div>
                    {item.notes && <Text type="secondary" style={{ fontSize: 12 }}>备注: {item.notes}</Text>}
                  </div>
                ))}
              </Card>
            );
          })}
          <Descriptions size="small" bordered column={4} style={{ marginTop: 16 }}>
            <Descriptions.Item label="动作总数">{plan.items.length}</Descriptions.Item>
            <Descriptions.Item label="总组数">{plan.items.reduce((s, i) => s + i.sets, 0)}</Descriptions.Item>
            <Descriptions.Item label="总次数">{plan.items.reduce((s, i) => s + i.sets * i.reps, 0)}</Descriptions.Item>
            <Descriptions.Item label="总时长">{(plan.items.reduce((s, i) => s + i.sets * i.duration_seconds, 0) / 60).toFixed(1)} 分钟</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* History */}
      <Card size="small" title="历史计划" extra={<Button size="small" onClick={loadPlans}>刷新</Button>}>
        {plans.length === 0 ? (
          <Empty description="暂无计划" />
        ) : (
          <Table size="small" pagination={{ pageSize: 8 }} dataSource={plans} rowKey="id"
            columns={[
              { title: "ID", dataIndex: "id", width: 50 },
              { title: "名称", dataIndex: "plan_name", width: 180 },
              { title: "方式", dataIndex: "generation_method", width: 80, render: (v: string) => <Tag color={v === "deepseek" ? "purple" : "blue"}>{v}</Tag> },
              { title: "状态", dataIndex: "status", width: 70, render: (v: string) => <Tag color={v === "active" ? "green" : "default"}>{v === "active" ? "激活" : v}</Tag> },
              { title: "动作", render: (_: any, r: PlanV2) => r.items?.length || 0, width: 60 },
              { title: "创建时间", dataIndex: "created_at", render: (v: string) => v?.slice(0, 16), width: 150 },
              { title: "操作", width: 170, render: (_: any, r: PlanV2) => (
                <Space size={0}>
                  <Button size="small" type="link" onClick={() => setPlan(r)}>查看</Button>
                  {r.status !== "active" && <Button size="small" type="link" onClick={() => handleActivate(r.id)}>激活</Button>}
                  <Button size="small" type="link" onClick={() => handleEdit(r)}>编辑</Button>
                  <Button size="small" type="link" danger onClick={() => handleDelete(r.id)}>删除</Button>
                </Space>
              )},
            ]}
          />
        )}
      </Card>
    </div>
  );

  // ---------- Render ----------
  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: "0 auto" }}>
      <div style={{ marginBottom: 16 }}>
        <Space>
          <ThunderboltOutlined style={{ fontSize: 24, color: "var(--color-primary)" }} />
          <Title level={3} style={{ margin: 0, color: "var(--color-text-primary)" }}>AI 训练计划生成</Title>
        </Space>
        <Paragraph type="secondary" style={{ marginTop: 4 }}>
          基于体态评估与FMS筛查结果，智能生成个性化训练计划
        </Paragraph>
      </div>

      <Tabs activeKey={activeTab} onChange={setActiveTab} size="large" items={[
        {
          key: "prescription",
          label: <span><ThunderboltOutlined /> 训练计划生成</span>,
          children: renderPrescriptionTab(),
        },
        {
          key: "actions",
          label: <span><BookOutlined /> 动作库 ({actionLib?.total || 0})</span>,
          children: renderActionLibTab(),
        },
      ]} />

      {/* ── Edit Plan Modal ── */}
      <Modal
        title="修改训练计划"
        open={editModal}
        onCancel={() => setEditModal(false)}
        width={900}
        footer={[
          <Button key="cancel" onClick={() => setEditModal(false)}>取消</Button>,
          <Button key="save" type="primary" loading={editing} onClick={saveEdit}>
            保存修改
          </Button>,
        ]}
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <Text strong>计划名称</Text>
            <Input value={editName} onChange={e => setEditName(e.target.value)}
              placeholder="计划名称" style={{ marginTop: 4 }} />
          </div>

          <div>
            <Text strong>修改原因（如有班级，将提交教练审批）</Text>
            <Input.TextArea value={editNotes} onChange={e => setEditNotes(e.target.value)}
              placeholder="说明为什么要修改计划..." rows={2} style={{ marginTop: 4 }} />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <Text strong>计划动作</Text>
              <Select
                value={addActionId}
                onChange={addEditItem}
                size="small"
                showSearch
                placeholder="+ 添加动作"
                style={{ width: 220 }}
                filterOption={(input, option) =>
                  (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                }
                options={
                  actionLib?.actions
                    ?.filter(a => !editItems.some(item => item.action_id === a.id))
                    ?.map(a => ({ label: `${a.name} (${a.family_name || a.category || ''})`, value: a.id }))
                  || []
                }
                notFoundContent={actionLib ? "无更多动作可添加" : "请先在动作库加载"}
                popupMatchSelectWidth={false}
              />
            </div>
            <Table dataSource={editItems} rowKey={(r: any, i: number) => `${r.action_name}-${i}`}
              size="small" pagination={false}
              columns={[
                { title: '动作', dataIndex: 'action_name', width: 130 },
                { title: '阶段', dataIndex: 'phase', width: 60, render: (v: string) => <Tag>{v}</Tag> },
                { title: '组数', dataIndex: 'sets', width: 75,
                  render: (v: number, _: any, i: number) => (
                    <InputNumber size="small" min={1} max={10} value={v} style={{ width: 50 }}
                      onChange={val => updateEditItem(i, 'sets', val)} />
                  )},
                { title: '次数', dataIndex: 'reps', width: 75,
                  render: (v: number, _: any, i: number) => (
                    <InputNumber size="small" min={1} max={50} value={v} style={{ width: 50 }}
                      onChange={val => updateEditItem(i, 'reps', val)} />
                  )},
                { title: '时长(s)', dataIndex: 'duration_seconds', width: 80,
                  render: (v: number, _: any, i: number) => (
                    <InputNumber size="small" min={0} max={600} value={v} style={{ width: 60 }}
                      onChange={val => updateEditItem(i, 'duration_seconds', val)} />
                  )},
                { title: '难度', dataIndex: 'difficulty', width: 70,
                  render: (v: number, _: any, i: number) => (
                    <InputNumber size="small" min={1} max={5} value={v} style={{ width: 50 }}
                      onChange={val => updateEditItem(i, 'difficulty', val)} />
                  )},
                { title: '强度', dataIndex: 'intensity', width: 85,
                  render: (v: string, _: any, i: number) => (
                    <Select size="small" value={v} style={{ width: 70 }}
                      onChange={val => updateEditItem(i, 'intensity', val)}>
                      <Select.Option value="LOW">LOW</Select.Option>
                      <Select.Option value="MEDIUM">MEDIUM</Select.Option>
                      <Select.Option value="HIGH">HIGH</Select.Option>
                    </Select>
                  )},
                { title: '', width: 40,
                  render: (_: any, __: any, i: number) => (
                    <Button type="text" danger size="small" icon={<DeleteOutlined />}
                      onClick={() => removeEditItem(i)} />
                  )},
              ]}
            />
          </div>
        </Space>
      </Modal>
    </div>
  );
};

export default PrescriptionPage;
