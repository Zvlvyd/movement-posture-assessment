import { useEffect, useState, useCallback } from "react";
import {
  Card, Table, Button, Tag, Space, Typography, Modal, Input,
  Spin, Empty, message, Row, Col, Descriptions, Popconfirm, InputNumber, Select
} from "antd";
import {
  CheckOutlined, CloseOutlined, EditOutlined,
  ArrowLeftOutlined, ReloadOutlined, UserOutlined
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { coachApi } from "../../services/api";
import type { ChangeRequestItem } from "../../types";

const { Title, Text, Paragraph } = Typography;

const statusLabel: Record<string, { color: string; text: string }> = {
  pending: { color: "orange", text: "待审批" },
  approved: { color: "green", text: "已通过" },
  rejected: { color: "red", text: "已拒绝" },
  adjusted: { color: "blue", text: "已调整" },
};

export default function PlanReviewPage() {
  const navigate = useNavigate();
  const [requests, setRequests] = useState<ChangeRequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<ChangeRequestItem | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Approval states
  const [rejectModal, setRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [adjustItems, setAdjustItems] = useState<any[]>([]);
  const [adjustNotes, setAdjustNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    try {
      const res = await coachApi.listChangeRequests();
      setRequests(res.requests || []);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchRequests(); }, [fetchRequests]);

  const loadDetail = async (crId: number) => {
    setDetailLoading(true);
    try {
      const data = await coachApi.getChangeRequest(crId);
      setSelected(data);
      // Parse proposed items for adjust mode
      if (data.proposed_items) {
        try {
          setAdjustItems(JSON.parse(data.proposed_items));
        } catch { setAdjustItems([]); }
      }
    } catch { message.error("加载详情失败"); }
    finally { setDetailLoading(false); }
  };

  const handleApprove = async () => {
    if (!selected) return;
    setSubmitting(true);
    try {
      await coachApi.approveChangeRequest(selected.id);
      message.success("已通过审批");
      setSelected(null);
      fetchRequests();
    } catch (e: any) { message.error(e?.response?.data?.detail || "操作失败"); }
    finally { setSubmitting(false); }
  };

  const handleAdjust = async () => {
    if (!selected) return;
    setSubmitting(true);
    try {
      await coachApi.adjustChangeRequest(selected.id, adjustItems, adjustNotes);
      message.success("已调整并通过");
      setSelected(null);
      fetchRequests();
    } catch (e: any) { message.error(e?.response?.data?.detail || "操作失败"); }
    finally { setSubmitting(false); }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) { message.warning("请填写拒绝原因"); return; }
    setSubmitting(true);
    try {
      await coachApi.rejectChangeRequest(selected!.id, rejectReason.trim());
      message.success("已拒绝");
      setRejectModal(false);
      setRejectReason("");
      setSelected(null);
      fetchRequests();
    } catch (e: any) { message.error(e?.response?.data?.detail || "操作失败"); }
    finally { setSubmitting(false); }
  };

  const updateAdjustItem = (idx: number, field: string, value: any) => {
    setAdjustItems(prev => prev.map((item, i) =>
      i === idx ? { ...item, [field]: value } : item
    ));
  };

  const renderOriginalItems = () => {
    if (!selected?.original_snapshot) return <Empty description="无原始数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
    try {
      const items = JSON.parse(selected.original_snapshot);
      return (
        <Table dataSource={items} rowKey={(r: any, i: number) => `${r.action_name}-${i}`} size="small" pagination={false}
          columns={[
            { title: '动作', dataIndex: 'action_name' },
            { title: '阶段', dataIndex: 'phase', width: 60, render: (v: string) => <Tag>{v}</Tag> },
            { title: '组数', dataIndex: 'sets', width: 50, align: 'center' as const },
            { title: '次数', dataIndex: 'reps', width: 50, align: 'center' as const },
            { title: '时长(s)', dataIndex: 'duration_seconds', width: 70, align: 'center' as const },
            { title: '难度', dataIndex: 'difficulty', width: 50, align: 'center' as const },
          ]}
        />
      );
    } catch { return <Text type="secondary">无法解析数据</Text>; }
  };

  const renderProposedItems = () => {
    const items = adjustItems.length > 0 ? adjustItems :
      (selected?.proposed_items ? (() => { try { return JSON.parse(selected.proposed_items); } catch { return []; } })() : []);
    if (items.length === 0) return <Empty description="无计划项数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
    return (
      <Table dataSource={items} rowKey={(r: any, i: number) => `${r.action_name}-${i}`} size="small" pagination={false}
        columns={[
          { title: '动作', dataIndex: 'action_name' },
          { title: '阶段', dataIndex: 'phase', width: 60, render: (v: string) => <Tag>{v}</Tag> },
          { title: '组数', dataIndex: 'sets', width: 50, align: 'center' as const },
          { title: '次数', dataIndex: 'reps', width: 50, align: 'center' as const },
          { title: '时长(s)', dataIndex: 'duration_seconds', width: 70, align: 'center' as const },
          { title: '难度', dataIndex: 'difficulty', width: 50, align: 'center' as const },
        ]}
      />
    );
  };

  // ── Main View ──
  if (selected) {
    const st = statusLabel[selected.status] || { color: "default", text: selected.status };
    const isPending = selected.status === 'pending';

    return (
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <Button type="link" onClick={() => setSelected(null)} style={{ padding: 0, marginBottom: 12 }}>
          <ArrowLeftOutlined /> 返回列表
        </Button>

        <Card title={
          <Space>
            <UserOutlined />
            <span>{selected.student_name} — {selected.plan_name}</span>
            <Tag color={st.color}>{st.text}</Tag>
          </Space>
        } loading={detailLoading}>
          {/* Student Notes */}
          {selected.student_notes && (
            <Card size="small" style={{ marginBottom: 16, background: "#fffbe6" }}>
              <Text strong>学员留言：</Text>
              <Paragraph style={{ margin: 0, marginTop: 4 }}>{selected.student_notes}</Paragraph>
            </Card>
          )}

          <Row gutter={16}>
            <Col span={12}>
              <Card size="small" title="修改前">
                {renderOriginalItems()}
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" title={isPending ? "修改后（可调整）" : "修改后"}>
                {isPending ? (
                  <Table dataSource={adjustItems} rowKey={(r: any, i: number) => `${r.action_name}-${i}`}
                    size="small" pagination={false}
                    columns={[
                      { title: '动作', dataIndex: 'action_name' },
                      { title: '阶段', dataIndex: 'phase', width: 60, render: (v: string) => <Tag>{v}</Tag> },
                      { title: '组数', dataIndex: 'sets', width: 70,
                        render: (v: number, _: any, i: number) => (
                          <InputNumber size="small" min={1} max={10} value={v} style={{ width: 55 }}
                            onChange={val => updateAdjustItem(i, 'sets', val)} />
                        )},
                      { title: '次数', dataIndex: 'reps', width: 70,
                        render: (v: number, _: any, i: number) => (
                          <InputNumber size="small" min={1} max={50} value={v} style={{ width: 55 }}
                            onChange={val => updateAdjustItem(i, 'reps', val)} />
                        )},
                      { title: '时长(s)', dataIndex: 'duration_seconds', width: 80,
                        render: (v: number, _: any, i: number) => (
                          <InputNumber size="small" min={0} max={600} value={v} style={{ width: 65 }}
                            onChange={val => updateAdjustItem(i, 'duration_seconds', val)} />
                        )},
                    ]}
                  />
                ) : renderProposedItems()}
              </Card>
            </Col>
          </Row>

          {/* Coach Notes Input */}
          {isPending && (
            <Card size="small" title="教练留言（可选）" style={{ marginTop: 16 }}>
              <Input.TextArea
                value={adjustNotes}
                onChange={e => setAdjustNotes(e.target.value)}
                placeholder="给学员的反馈..."
                rows={2}
              />
            </Card>
          )}

          {/* Approval Actions */}
          {isPending && (
            <div style={{ marginTop: 16, display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <Popconfirm title="确认通过此修改请求？" onConfirm={handleApprove}>
                <Button type="primary" icon={<CheckOutlined />} loading={submitting}>通过</Button>
              </Popconfirm>
              <Button icon={<EditOutlined />} loading={submitting}
                onClick={handleAdjust}>调整后通过</Button>
              <Button danger icon={<CloseOutlined />} loading={submitting}
                onClick={() => setRejectModal(true)}>拒绝</Button>
            </div>
          )}

          {/* Rejected info */}
          {selected.status === 'rejected' && selected.coach_notes && (
            <Card size="small" style={{ marginTop: 16, background: "#fff2f0" }}>
              <Text strong type="danger">拒绝原因：</Text>
              <Paragraph style={{ margin: 0, marginTop: 4 }}>{selected.coach_notes}</Paragraph>
            </Card>
          )}

          {/* Adjusted info */}
          {selected.status === 'adjusted' && selected.coach_notes && (
            <Card size="small" style={{ marginTop: 16, background: "#e6f4ff" }}>
              <Text strong>教练留言：</Text>
              <Paragraph style={{ margin: 0, marginTop: 4 }}>{selected.coach_notes}</Paragraph>
            </Card>
          )}
        </Card>

        {/* Reject Modal */}
        <Modal title="拒绝修改请求" open={rejectModal} onOk={handleReject}
          onCancel={() => { setRejectModal(false); setRejectReason(""); }}
          confirmLoading={submitting} okText="确认拒绝" okButtonProps={{ danger: true }}>
          <Paragraph type="secondary" style={{ marginBottom: 8 }}>
            请填写拒绝原因，学员将收到通知
          </Paragraph>
          <Input.TextArea rows={3} value={rejectReason} onChange={e => setRejectReason(e.target.value)}
            placeholder="例如：当前训练强度已足够，建议保持原计划..." />
        </Modal>
      </div>
    );
  }

  // ── List View ──
  return (
    <div style={{ maxWidth: 1000, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>计划审批</Title>
        <Button icon={<ReloadOutlined />} onClick={fetchRequests}>刷新</Button>
      </div>

      {loading ? (
        <Spin size="large" style={{ display: "block", margin: "40px auto" }} />
      ) : requests.length === 0 ? (
        <Card><Empty description="暂无待审批的计划变更请求" /></Card>
      ) : (
        <Table dataSource={requests} rowKey="id" loading={loading}
          onRow={(record) => ({ onClick: () => loadDetail(record.id), style: { cursor: "pointer" } })}
          columns={[
            { title: '学员', dataIndex: 'student_name', width: 120,
              render: (v: string) => <Text strong><UserOutlined /> {v}</Text> },
            { title: '计划', dataIndex: 'plan_name', ellipsis: true },
            { title: '状态', dataIndex: 'status', width: 100,
              render: (v: string) => {
                const st = statusLabel[v] || { color: "default", text: v };
                return <Tag color={st.color}>{st.text}</Tag>;
              }},
            { title: '时间', dataIndex: 'created_at', width: 140,
              render: (v: string) => v?.slice(0, 16) },
            { title: '操作', width: 100, render: (_: any, r: ChangeRequestItem) => (
              <Button type="link" size="small" onClick={(e) => { e.stopPropagation(); loadDetail(r.id); }}>
                查看详情
              </Button>
            )},
          ]}
        />
      )}
    </div>
  );
}
