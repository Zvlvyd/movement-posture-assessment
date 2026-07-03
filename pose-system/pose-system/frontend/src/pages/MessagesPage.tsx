import { useEffect, useState, useCallback } from "react";
import {
  Card, List, Input, Button, Space, Tag, Typography, Badge,
  Spin, Empty, message, Divider, Avatar
} from "antd";
import {
  SendOutlined, UserOutlined, MessageOutlined,
  TeamOutlined, BellOutlined, ReloadOutlined
} from "@ant-design/icons";
import { messageApi } from "../services/api";
import { useAuthStore } from "../store/auth";
import type { Conversation, MessageItem } from "../types";

const { Text, Paragraph, Title } = Typography;

export default function MessagesPage() {
  const user = useAuthStore(s => s.user);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPartner, setSelectedPartner] = useState<number | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [msgLoading, setMsgLoading] = useState(false);
  const [newMsg, setNewMsg] = useState("");
  const [sending, setSending] = useState(false);
  const [unreadTotal, setUnreadTotal] = useState(0);

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    try {
      const [convRes, unreadRes] = await Promise.all([
        messageApi.conversations(),
        messageApi.unreadCount(),
      ]);
      setConversations(convRes.conversations || []);
      setUnreadTotal(unreadRes.unread_count || 0);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchConversations(); }, [fetchConversations]);

  // Poll unread count every 30 seconds
  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        const res = await messageApi.unreadCount();
        setUnreadTotal(res.unread_count || 0);
      } catch { /* ignore */ }
    }, 30000);
    return () => clearInterval(timer);
  }, []);

  const selectConversation = async (partnerId: number) => {
    setSelectedPartner(partnerId);
    setMsgLoading(true);
    try {
      const res = await messageApi.getWith(partnerId);
      setMessages(res.messages || []);
      // Refresh conversations to clear unread
      fetchConversations();
    } catch { /* ignore */ }
    finally { setMsgLoading(false); }
  };

  const sendMessage = async () => {
    if (!newMsg.trim() || !selectedPartner) return;
    setSending(true);
    try {
      await messageApi.send(selectedPartner, newMsg.trim());
      setNewMsg("");
      // Refresh messages
      const res = await messageApi.getWith(selectedPartner);
      setMessages(res.messages || []);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "发送失败");
    } finally { setSending(false); }
  };

  const selectedConv = conversations.find(c => c.partner_id === selectedPartner);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "80px auto" }} />;

  return (
    <div style={{ maxWidth: 960, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          <MessageOutlined style={{ marginRight: 8 }} />
          消息中心
          {unreadTotal > 0 && (
            <Badge count={unreadTotal} style={{ marginLeft: 8 }} />
          )}
        </Title>
        <Button icon={<ReloadOutlined />} onClick={fetchConversations}>刷新</Button>
      </div>

      <div style={{ display: "flex", gap: 16 }}>
        {/* Conversation List */}
        <Card
          style={{ width: 320, flexShrink: 0 }}
          bodyStyle={{ padding: 0, maxHeight: "calc(100vh - 200px)", overflow: "auto" }}
        >
          {conversations.length === 0 ? (
            <Empty description="暂无消息" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ padding: 40 }} />
          ) : (
            <List
              dataSource={conversations}
              renderItem={conv => (
                <div
                  onClick={() => selectConversation(conv.partner_id)}
                  style={{
                    padding: "12px 16px",
                    cursor: "pointer",
                    background: selectedPartner === conv.partner_id ? "#e6f4ff" : "transparent",
                    borderBottom: "1px solid #f0f0f0",
                    transition: "background 0.2s",
                  }}
                  onMouseEnter={e => { if (selectedPartner !== conv.partner_id) e.currentTarget.style.background = "#fafafa"; }}
                  onMouseLeave={e => { if (selectedPartner !== conv.partner_id) e.currentTarget.style.background = "transparent"; }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <Avatar icon={conv.partner_role === 'coach' ? <TeamOutlined /> : <UserOutlined />}
                            style={{ background: conv.partner_role === 'coach' ? '#1890ff' : '#52c41a', flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <Text strong style={{ fontSize: 14 }}>
                          {conv.partner_name}
                          <Tag style={{ marginLeft: 6, fontSize: 10 }}>
                            {conv.partner_role === 'coach' ? '教练' : '学员'}
                          </Tag>
                        </Text>
                        {conv.unread_count > 0 && <Badge count={conv.unread_count} size="small" />}
                      </div>
                      <Paragraph ellipsis type="secondary" style={{ fontSize: 12, margin: 0, marginTop: 2 }}>
                        {conv.last_message}
                      </Paragraph>
                      <Text type="secondary" style={{ fontSize: 11 }}>{conv.last_time?.slice(0, 16)}</Text>
                    </div>
                  </div>
                </div>
              )}
            />
          )}
        </Card>

        {/* Message Detail */}
        <Card
          style={{ flex: 1 }}
          title={
            selectedConv ? (
              <Space>
                <Avatar icon={selectedConv.partner_role === 'coach' ? <TeamOutlined /> : <UserOutlined />}
                        size="small" />
                <Text strong>{selectedConv.partner_name}</Text>
                <Tag>{selectedConv.partner_role === 'coach' ? '教练' : '学员'}</Tag>
              </Space>
            ) : (
              <Text type="secondary"><BellOutlined /> 选择一个对话查看消息</Text>
            )
          }
          bodyStyle={{ padding: 0, display: "flex", flexDirection: "column", height: "calc(100vh - 280px)" }}
        >
          {!selectedPartner ? (
            <div style={{ flex: 1, display: "flex", justifyContent: "center", alignItems: "center" }}>
              <Empty description="选择左侧对话查看消息" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            </div>
          ) : msgLoading ? (
            <Spin style={{ flex: 1, display: "flex", justifyContent: "center", alignItems: "center" }} />
          ) : (
            <>
              <div style={{ flex: 1, overflow: "auto", padding: 16 }}>
                {messages.length === 0 ? (
                  <Empty description="暂无消息，发送第一条消息吧" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                ) : (
                  messages.map(m => {
                    const isMe = m.sender_id === user?.id;
                    return (
                      <div key={m.id} style={{
                        display: "flex", justifyContent: isMe ? "flex-end" : "flex-start",
                        marginBottom: 12,
                      }}>
                        <div style={{
                          maxWidth: "70%",
                          padding: "10px 14px",
                          borderRadius: 12,
                          background: isMe ? "#1890ff" : "#f0f0f0",
                          color: isMe ? "#fff" : "#333",
                          borderTopRightRadius: isMe ? 4 : 12,
                          borderTopLeftRadius: isMe ? 12 : 4,
                        }}>
                          <Text style={{ color: "inherit", fontSize: 14, whiteSpace: "pre-wrap" }}>
                            {m.content}
                          </Text>
                          <div style={{ marginTop: 4 }}>
                            <Text style={{ color: isMe ? "rgba(255,255,255,0.7)" : "#999", fontSize: 11 }}>
                              {m.created_at?.slice(0, 16)}
                            </Text>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
              <Divider style={{ margin: 0 }} />
              <div style={{ padding: "12px 16px", display: "flex", gap: 8 }}>
                <Input.TextArea
                  value={newMsg}
                  onChange={e => setNewMsg(e.target.value)}
                  onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                  placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
                  autoSize={{ minRows: 1, maxRows: 4 }}
                  style={{ flex: 1 }}
                />
                <Button type="primary" icon={<SendOutlined />} loading={sending}
                        onClick={sendMessage} disabled={!newMsg.trim()}>
                  发送
                </Button>
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
