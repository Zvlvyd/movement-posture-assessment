import { useState } from "react";
import { Layout, Menu, Avatar, Dropdown, Typography } from "antd";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  HomeOutlined, ExperimentOutlined, PlayCircleOutlined, ThunderboltOutlined,
  BookOutlined, CheckCircleOutlined, UserOutlined,
  TeamOutlined, SettingOutlined, LogoutOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined
} from "@ant-design/icons";
import { useAuthStore } from "../store/auth";

const { Sider, Content, Footer } = Layout;
const { Text } = Typography;

interface MenuItem {
  key: string;
  icon: React.ReactNode;
  label: string;
}

const CORE_MENU: MenuItem[] = [
  { key: "/home",          icon: <HomeOutlined />,          label: "首页" },
  { key: "/assessment",   icon: <PlayCircleOutlined />,    label: "体态评估" },
  { key: "/fms",           icon: <ExperimentOutlined />,    label: "FMS 筛查" },
  { key: "/prescription",  icon: <ThunderboltOutlined />,  label: "AI 处方" },
  { key: "/training",      icon: <PlayCircleOutlined />,    label: "计划训练" },
  { key: "/learning",      icon: <BookOutlined />,          label: "标准学习" },
  { key: "/checkin",       icon: <CheckCircleOutlined />,   label: "每日打卡" },
];

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);

  const selectedKey = "/" + location.pathname.split("/")[1];

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const userMenuItems: any[] = [
    { key: "/profile", icon: <UserOutlined />,  label: "个人中心" },
    ...(user?.role === "coach" || user?.role === "admin"
      ? [{ key: "/coach", icon: <TeamOutlined />, label: "教练管理" }]
      : []),
    ...(user?.role === "admin"
      ? [{ key: "/admin", icon: <SettingOutlined />, label: "系统管理" }]
      : []),
    { type: "divider" },
    { key: "logout", icon: <LogoutOutlined />, label: "退出登录" },
  ];

  const onUserMenuClick = ({ key }: { key: string }) => {
    if (key === "logout") { handleLogout(); }
    else { navigate(key); }
  };

  return (
    <Layout hasSider style={{ minHeight: "100vh" }}>
      {/* Sidebar */}
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        breakpoint="lg"
        collapsedWidth="64"
        width={220}
        trigger={null}
        style={{
          background: "var(--color-pure-white)",
          
          boxShadow: "var(--shadow-sider)",
          borderRight: "1px solid var(--color-hairline)",
          display: "flex",
          flexDirection: "column",
          height: "100vh",
          position: "sticky",
          top: 0,
          left: 0,
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
          {/* Logo Area */}
          <div
            style={{
              padding: collapsed ? "24px 0" : "28px 20px 20px",
              textAlign: collapsed ? "center" : "left",
              borderBottom: "1px solid var(--color-hairline)",
            }}
          >
            {collapsed ? (
              <ThunderboltOutlined style={{
                fontSize: 24,
                background: "linear-gradient(135deg, var(--color-cyan), var(--color-violet))",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }} />
            ) : (
              <div>
                <Text style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: 800,
                  fontSize: 18,
                  letterSpacing: "-0.02em",
                  background: "linear-gradient(135deg, var(--color-cyan), var(--color-magenta))",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  lineHeight: 1.3,
                  display: "block",
                }}>
                  运动姿态
                </Text>
                <Text style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: 600,
                  fontSize: 14,
                  color: "var(--color-text-secondary)",
                  lineHeight: 1.3,
                  display: "block",
                }}>
                  评估与纠错
                </Text>
              </div>
            )}
          </div>

          {/* Navigation Menu */}
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            onClick={({ key }) => navigate(key)}
            items={CORE_MENU as any}
            style={{
              flex: 1,
              padding: "12px 8px",
              borderInlineEnd: "none",
              background: "transparent",
              fontFamily: "var(--font-body)",
              fontSize: 14,
              fontWeight: 500,
            }}
          />

          {/* Collapse Toggle */}
          <div
            onClick={() => setCollapsed(!collapsed)}
            style={{
              padding: "14px",
              textAlign: "center",
              cursor: "pointer",
              color: "var(--color-text-muted)",
              borderTop: "1px solid var(--color-hairline)",
              transition: "color 250ms var(--ease-smooth)",
            }}
            onMouseEnter={e => (e.currentTarget.style.color = "var(--color-primary)")}
            onMouseLeave={e => (e.currentTarget.style.color = "var(--color-text-muted)")}
          >
            {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          </div>

          {/* User Area */}
          <Dropdown
            menu={{ items: userMenuItems, onClick: onUserMenuClick }}
            trigger={["click"]}
            placement="topRight"
          >
            <div
              style={{
                padding: collapsed ? "16px 0" : "16px 20px",
                borderTop: "1px solid var(--color-hairline)",
                display: "flex",
                alignItems: "center",
                gap: 10,
                cursor: "pointer",
                transition: "background 250ms var(--ease-smooth)",
                justifyContent: collapsed ? "center" : "flex-start",
              }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--color-neutral)")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >
              <Avatar
                size={collapsed ? 32 : 36}
                icon={<UserOutlined />}
                style={{
                  background: "var(--color-primary)",
                  flexShrink: 0,
                }}
              />
              {!collapsed && (
                <Text
                  style={{
                    fontFamily: "var(--font-body)",
                    color: "var(--color-text-primary)",
                    fontSize: 14,
                    fontWeight: 500,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {user?.username || "用户"}
                </Text>
              )}
            </div>
          </Dropdown>
        </div>
      </Sider>

      {/* Main Content */}
      <Layout style={{ background: "transparent" }}>
        <Content style={{ padding: 24, minHeight: "calc(100vh - 48px)" }}>
          <Outlet />
        </Content>
        <Footer
          style={{
            textAlign: "center",
            padding: "12px 24px",
            color: "var(--color-text-muted)",
            fontFamily: "var(--font-body)",
            fontSize: 12,
            background: "transparent",
          }}
        >
          运动姿态评估与纠错系统 &copy;2026
        </Footer>
      </Layout>
    </Layout>
  );
}
