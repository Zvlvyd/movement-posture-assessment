import { Layout, Menu } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  HomeOutlined, ExperimentOutlined, PlayCircleOutlined,
  BookOutlined, CheckCircleOutlined, UserOutlined,
  TeamOutlined, SettingOutlined, LogoutOutlined,
  OrderedListOutlined
} from '@ant-design/icons';
import { useAuthStore } from '../store/auth';

const { Header, Content, Footer } = Layout;

const menuItems = [
  { key: '/home', icon: <HomeOutlined />, label: '首页', roles: ['trainee', 'coach', 'admin'] },
  { key: '/fms', icon: <ExperimentOutlined />, label: 'FMS筛查', roles: ['trainee'] },
  { key: '/training', icon: <PlayCircleOutlined />, label: '实时训练', roles: ['trainee'] },
  { key: '/prescription-training', icon: <OrderedListOutlined />, label: '处方训练', roles: ['trainee'] },
  { key: '/learning', icon: <BookOutlined />, label: '标准学习', roles: ['trainee'] },
  { key: '/checkin', icon: <CheckCircleOutlined />, label: '每日打卡', roles: ['trainee'] },
  { key: '/profile', icon: <UserOutlined />, label: '个人中心', roles: ['trainee', 'coach', 'admin'] },
  { key: '/coach', icon: <TeamOutlined />, label: '教练管理', roles: ['coach', 'admin'] },
  { key: '/admin', icon: <SettingOutlined />, label: '系统管理', roles: ['admin'] },
];

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();

  const visibleItems = menuItems.filter(item => item.roles.includes(user?.role || ''));
  const selectedKey = '/' + location.pathname.split('/')[1];

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <Layout className="layout">
      <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span className="logo" style={{ marginRight: 24 }}>运动姿态评估与纠错系统</span>
          <Menu theme="dark" mode="horizontal" selectedKeys={[selectedKey]} items={visibleItems} onClick={({ key }) => navigate(key)} style={{ minWidth: 400 }} />
        </div>
        <span style={{ color: 'white', cursor: 'pointer' }} onClick={handleLogout}>
          {user?.username} <LogoutOutlined style={{ marginLeft: 8 }} />
        </span>
      </Header>
      <Content className="site-content"><Outlet /></Content>
      <Footer style={{ textAlign: 'center' }}>运动姿态评估与纠错系统 ©2026</Footer>
    </Layout>
  );
}
