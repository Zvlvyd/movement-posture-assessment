import { useEffect, useState, useCallback } from "react";
import {
  Card, Button, Modal, Input, Empty, Spin, message, Popconfirm, Descriptions, Tag, Space, Typography
} from "antd";
import {
  PlusOutlined, TeamOutlined, UserOutlined, CopyOutlined,
  LogoutOutlined, ReloadOutlined, LockOutlined
} from "@ant-design/icons";
import { studentClassApi } from "../services/api";
import type { MyClassInfo } from "../types";
import { useNavigate } from "react-router-dom";

const { Title, Text, Paragraph } = Typography;

export default function MyClassesPage() {
  const [classes, setClasses] = useState<MyClassInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [joinModalOpen, setJoinModalOpen] = useState(false);
  const [inviteCode, setInviteCode] = useState("");
  const [joining, setJoining] = useState(false);
  const navigate = useNavigate();

  const fetchClasses = useCallback(async () => {
    setLoading(true);
    try {
      const res = await studentClassApi.myClasses();
      setClasses(res.classes || []);
    } catch {
      // Ignore fetch errors
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchClasses(); }, [fetchClasses]);

  const handleJoin = async () => {
    const code = inviteCode.trim().toUpperCase();
    if (code.length !== 8) {
      message.warning("请输入8位邀请码");
      return;
    }
    setJoining(true);
    try {
      const res = await studentClassApi.join(code);
      message.success(res.message || "加入成功！");
      setJoinModalOpen(false);
      setInviteCode("");
      fetchClasses();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "加入失败，请检查邀请码是否正确");
    } finally {
      setJoining(false);
    }
  };

  const handleLeave = async (classId: number) => {
    try {
      const res = await studentClassApi.leaveClass(classId);
      message.success(res.message || "已退出班级");
      fetchClasses();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "退出失败");
    }
  };

  const copyInviteCode = (code: string) => {
    navigator.clipboard.writeText(code).then(
      () => message.success("邀请码已复制"),
      () => message.error("复制失败")
    );
  };

  // ── Loading ──
  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: 300 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  // ── Empty State ──
  if (classes.length === 0) {
    return (
      <div style={{ maxWidth: 600, margin: "0 auto", paddingTop: 48 }}>
        <Card>
          <Empty
            description={
              <div>
                <Paragraph type="secondary" style={{ fontSize: 16, marginBottom: 8 }}>
                  加入班级，获取更专业指导
                </Paragraph>
                <Paragraph type="secondary" style={{ fontSize: 13 }}>
                  输入教练分享的邀请码，即可加入班级并接受教练的专业指导
                </Paragraph>
              </div>
            }
          >
            <Button type="primary" icon={<PlusOutlined />} size="large" onClick={() => setJoinModalOpen(true)}>
              加入班级
            </Button>
          </Empty>
        </Card>

        <Modal
          title="加入班级"
          open={joinModalOpen}
          onOk={handleJoin}
          onCancel={() => { setJoinModalOpen(false); setInviteCode(""); }}
          confirmLoading={joining}
          okText="加入"
          cancelText="取消"
          destroyOnClose
        >
          <div style={{ padding: "16px 0" }}>
            <Paragraph type="secondary" style={{ marginBottom: 12 }}>
              请输入教练分享的8位班级邀请码
            </Paragraph>
            <Input
              size="large"
              placeholder="输入邀请码，如 A3B7K9M2"
              maxLength={8}
              value={inviteCode}
              onChange={e => setInviteCode(e.target.value.toUpperCase())}
              onPressEnter={handleJoin}
              prefix={<LockOutlined />}
              style={{ fontFamily: "monospace", letterSpacing: 4, fontSize: 18, textAlign: "center" }}
              autoFocus
            />
          </div>
        </Modal>
      </div>
    );
  }

  // ── Has Classes ──
  return (
    <div style={{ maxWidth: 800, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>我的班级</Title>
          <Text type="secondary">共 {classes.length} 个班级</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setJoinModalOpen(true)}>
          加入班级
        </Button>
      </div>

      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        {classes.map(cls => (
          <Card
            key={cls.class_id}
            hoverable
            actions={[
              <Button
                key="copy"
                type="link"
                icon={<CopyOutlined />}
                onClick={() => copyInviteCode(cls.invite_code || "")}
              >
                复制邀请码
              </Button>,
              <Popconfirm
                key="leave"
                title="确认退出班级？"
                description={`退出后将无法查看「${cls.class_name}」的训练数据`}
                onConfirm={() => handleLeave(cls.class_id)}
                okText="确认退出"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button type="link" danger icon={<LogoutOutlined />}>退出班级</Button>
              </Popconfirm>,
            ]}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
              <div style={{ flex: 1, minWidth: 200 }}>
                <Title level={4} style={{ margin: 0, marginBottom: 8 }}>
                  <TeamOutlined style={{ marginRight: 8 }} />
                  {cls.class_name}
                </Title>
                {cls.description && (
                  <Paragraph type="secondary" style={{ marginBottom: 12 }}>{cls.description}</Paragraph>
                )}
                <Descriptions column={1} size="small" colon={false}>
                  <Descriptions.Item label={<><UserOutlined /> 教练</>}>
                    {cls.coach.username}{cls.coach.phone ? ` (${cls.coach.phone})` : ""}
                  </Descriptions.Item>
                </Descriptions>
              </div>

              <div style={{ textAlign: "right", minWidth: 120 }}>
                <div style={{ marginBottom: 8 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>邀请码</Text>
                  <br />
                  <Tag
                    color="blue"
                    style={{ fontFamily: "monospace", fontSize: 16, letterSpacing: 3, padding: "4px 12px", cursor: "pointer" }}
                    onClick={() => copyInviteCode(cls.invite_code || "")}
                  >
                    {cls.invite_code || "---"}
                  </Tag>
                </div>
                <Text type="secondary">
                  <TeamOutlined /> {cls.student_count} 名学员
                </Text>
                <br />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  创建于 {new Date(cls.created_at).toLocaleDateString()}
                </Text>
              </div>
            </div>
          </Card>
        ))}
      </Space>

      {/* ── Join Modal ── */}
      <Modal
        title="加入班级"
        open={joinModalOpen}
        onOk={handleJoin}
        onCancel={() => { setJoinModalOpen(false); setInviteCode(""); }}
        confirmLoading={joining}
        okText="加入"
        cancelText="取消"
        destroyOnClose
      >
        <div style={{ padding: "16px 0" }}>
          <Paragraph type="secondary" style={{ marginBottom: 12 }}>
            请输入教练分享的8位班级邀请码
          </Paragraph>
          <Input
            size="large"
            placeholder="输入邀请码，如 A3B7K9M2"
            maxLength={8}
            value={inviteCode}
            onChange={e => setInviteCode(e.target.value.toUpperCase())}
            onPressEnter={handleJoin}
            prefix={<LockOutlined />}
            style={{ fontFamily: "monospace", letterSpacing: 4, fontSize: 18, textAlign: "center" }}
            autoFocus
          />
        </div>
      </Modal>
    </div>
  );
}
