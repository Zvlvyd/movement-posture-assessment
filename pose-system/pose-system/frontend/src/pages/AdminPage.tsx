import { Tabs } from 'antd';
import { TeamOutlined, DashboardOutlined, SettingOutlined, FileTextOutlined } from '@ant-design/icons';
import UserManagementTab from './admin/UserManagementTab';
import DashboardTab from './admin/DashboardTab';
import ConfigTab from './admin/ConfigTab';
import LogsTab from './admin/LogsTab';

/**
 * 管理员端主页面
 * 4 个 Tab：用户管理 | 系统仪表板 | 系统配置 | 操作日志
 */
export default function AdminPage() {
  const items = [
    {
      key: 'users',
      label: <span><TeamOutlined /> 用户管理</span>,
      children: <UserManagementTab />,
    },
    {
      key: 'dashboard',
      label: <span><DashboardOutlined /> 系统仪表板</span>,
      children: <DashboardTab />,
    },
    {
      key: 'config',
      label: <span><SettingOutlined /> 系统配置</span>,
      children: <ConfigTab />,
    },
    {
      key: 'logs',
      label: <span><FileTextOutlined /> 操作日志</span>,
      children: <LogsTab />,
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 16, fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700 }}>
        系统管理
      </h2>
      <Tabs defaultActiveKey="users" items={items} size="large" />
    </div>
  );
}
