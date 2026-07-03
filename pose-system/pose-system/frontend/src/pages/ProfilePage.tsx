import { useEffect, useState } from "react";
import {
  Card, Descriptions, Tabs, Table, Tag, Statistic, Row, Col,
  Button, Form, Input, Select, InputNumber, DatePicker, message, Modal, Space
} from "antd";
import { EditOutlined, LockOutlined, SaveOutlined, CloseOutlined, TeamOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import { recordsApi, fmsApi, userApi } from "../services/api";
import type { TrainingRecord, FMSRecord, TrainingStats } from "../types";
import dayjs from "dayjs";

export default function ProfilePage() {
  const { user, setUser } = useAuthStore();
  const navigate = useNavigate();
  const [stats, setStats] = useState<TrainingStats | null>(null);
  const [records, setRecords] = useState<TrainingRecord[]>([]);
  const [fmsRecords, setFmsRecords] = useState<FMSRecord[]>([]);
  const [cycleConfig, setCycleConfig] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [editingProfile, setEditingProfile] = useState(false);
  const [pwdModal, setPwdModal] = useState(false);

  // Profile edit form
  const [profileForm] = Form.useForm();
  // Cycle config form
  const [cycleForm] = Form.useForm();
  // Password change form
  const [pwdForm] = Form.useForm();

  const fetchAll = async () => {
    try {
      const [statsRes, recsRes, fmsRes, cycleRes] = await Promise.all([
        recordsApi.stats(),
        recordsApi.history(90),
        fmsApi.getRecords(),
        userApi.getCycleConfig(),
      ]);
      setStats(statsRes);
      setRecords(recsRes);
      setFmsRecords(fmsRes);
      setCycleConfig(cycleRes);
      cycleForm.setFieldsValue({
        cycle_length: cycleRes.cycle_length,
        last_period_date: cycleRes.last_period_date ? dayjs(cycleRes.last_period_date) : null,
      });
    } catch { /* ignore */ }
  };
  useEffect(() => { fetchAll(); }, []);

  const saveProfile = async () => {
    const vals = profileForm.getFieldsValue();
    try {
      const updated = await userApi.updateProfile(vals);
      setUser(updated);
      message.success("个人信息已更新");
      setEditingProfile(false);
    } catch { message.error("更新失败"); }
  };

  const saveCycleConfig = async () => {
    const vals = cycleForm.getFieldsValue();
    setLoading(true);
    try {
      const payload: any = { cycle_length: vals.cycle_length || 28 };
      if (vals.last_period_date) payload.last_period_date = vals.last_period_date.format("YYYY-MM-DD");
      await userApi.updateCycleConfig(payload);
      message.success("月经周期已更新");
    } catch { message.error("更新失败"); }
    finally { setLoading(false); }
  };

  const changePassword = async () => {
    try {
      const vals = await pwdForm.validateFields();
      await userApi.changePassword(vals);
      message.success("密码已修改");
      setPwdModal(false);
      pwdForm.resetFields();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "修改失败，请检查旧密码");
    }
  };

  const columns = [
    { title: "时间", dataIndex: "start_time", render: (v: string) => new Date(v).toLocaleString() },
    { title: "模式", dataIndex: "mode", render: (v: string) => <Tag>{v === "basic" ? "基础" : "进阶"}</Tag> },
    { title: "评分", dataIndex: "total_score", render: (v: number) => v ? `${v}分` : "-" },
  ];

  const fmsColumns = [
    { title: "日期", dataIndex: "test_date", render: (v: string) => new Date(v).toLocaleDateString() },
    { title: "综合评分", dataIndex: "overall_score" },
    { title: "风险", dataIndex: "risk_level", render: (v: string) => <Tag color={v === "high" ? "red" : v === "medium" ? "orange" : "green"}>{v}</Tag> },
  ];

  return (
    <div style={{ maxWidth: 960, margin: "0 auto" }}>
      {/* ── Profile Card ── */}
      <Card>
        {editingProfile ? (
          <Form form={profileForm} layout="inline" initialValues={{
            phone: user?.phone, gender: user?.gender
          }}>
            <Form.Item label="手机" name="phone">
              <Input placeholder="请输入手机号" />
            </Form.Item>
            <Form.Item label="性别" name="gender">
              <Select style={{ width: 100 }}>
                <Select.Option value="male">男</Select.Option>
                <Select.Option value="female">女</Select.Option>
              </Select>
            </Form.Item>
            <Space>
              <Button type="primary" icon={<SaveOutlined />} onClick={saveProfile}>保存</Button>
              <Button icon={<CloseOutlined />} onClick={() => setEditingProfile(false)}>取消</Button>
            </Space>
          </Form>
        ) : (
          <Descriptions title="个人信息" extra={
            <Space>
              {user?.role === "trainee" && (
                <Button icon={<TeamOutlined />} size="small" onClick={() => navigate('/my-classes')}>我的班级</Button>
              )}
              <Button icon={<EditOutlined />} size="small" onClick={() => {
                profileForm.setFieldsValue({ phone: user?.phone, gender: user?.gender });
                setEditingProfile(true);
              }}>编辑</Button>
              <Button icon={<LockOutlined />} size="small" onClick={() => setPwdModal(true)}>修改密码</Button>
            </Space>
          }>
            <Descriptions.Item label="用户名">{user?.username}</Descriptions.Item>
            <Descriptions.Item label="角色">{user?.role === "trainee" ? "训练者" : user?.role === "coach" ? "教练" : "管理员"}</Descriptions.Item>
            <Descriptions.Item label="手机">{user?.phone || "-"}</Descriptions.Item>
            <Descriptions.Item label="性别">{user?.gender === "male" ? "男" : user?.gender === "female" ? "女" : "-"}</Descriptions.Item>
            <Descriptions.Item label="注册时间">{user?.created_at ? new Date(user.created_at).toLocaleDateString() : "-"}</Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      {/* ── Cycle Config Card (female users) ── */}
      {user?.gender === "female" && (
        <Card title="月经周期设置" style={{ marginTop: 16 }} size="small">
          <Form form={cycleForm} layout="inline" initialValues={{
            cycle_length: 28,
          }}>
            <Form.Item label="周期天数" name="cycle_length">
              <InputNumber min={21} max={40} style={{ width: 80 }} />
            </Form.Item>
            <Form.Item label="末次月经" name="last_period_date">
              <DatePicker />
            </Form.Item>
            <Form.Item>
              <Button type="primary" loading={loading} onClick={saveCycleConfig}>保存</Button>
            </Form.Item>
          </Form>
          {cycleConfig && cycleConfig.intensity_coefficient && (
            <div style={{ marginTop: 8, fontSize: 12, color: "#888" }}>
              当前周期强度系数: {cycleConfig.intensity_coefficient}
              {cycleConfig.last_period_date && ` | 末次月经: ${cycleConfig.last_period_date.substring(0, 10)}`}
            </div>
          )}
        </Card>
      )}

      {/* ── Tabs ── */}
      <Tabs defaultActiveKey="stats" style={{ marginTop: 16 }} items={[
        {
          key: "stats", label: "训练统计", children: (
            <Row gutter={16}>
              <Col span={6}><Card><Statistic title="连续打卡" value={stats?.current_streak || 0} suffix="天" /></Card></Col>
              <Col span={6}><Card><Statistic title="近7天" value={stats?.total_sessions_7d || 0} suffix="次" /></Card></Col>
              <Col span={6}><Card><Statistic title="近30天" value={stats?.total_sessions_30d || 0} suffix="次" /></Card></Col>
              <Col span={6}><Card><Statistic title="平均评分" value={stats?.average_score || 0} suffix="分" precision={1} /></Card></Col>
            </Row>
          )
        },
        {
          key: "records", label: "训练记录", children: (
            <Table dataSource={records} columns={columns} rowKey="id" size="small" />
          )
        },
        {
          key: "fms", label: "FMS档案", children: (
            <Table dataSource={fmsRecords} columns={fmsColumns} rowKey="id" size="small" />
          )
        },
      ]} />

      {/* ── Password Modal ── */}
      <Modal title="修改密码" open={pwdModal} onOk={changePassword} onCancel={() => { setPwdModal(false); pwdForm.resetFields(); }}>
        <Form form={pwdForm} layout="vertical">
          <Form.Item label="旧密码" name="old_password" rules={[{ required: true, message: "请输入旧密码" }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item label="新密码" name="new_password" rules={[{ required: true, min: 6, message: "密码至少6位" }]}>
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
