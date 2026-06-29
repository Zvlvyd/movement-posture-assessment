import { useEffect, useState } from 'react';
import { Card, Table, Tabs, Descriptions, Switch, Select, message } from 'antd';
import { adminApi } from '../services/api';

export default function AdminPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [config, setConfig] = useState<any>({});
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    adminApi.users().then(setUsers).catch(() => {});
    adminApi.config().then(setConfig).catch(() => {});
    adminApi.logs().then(setLogs).catch(() => {});
  }, []);

  const toggleStatus = async (userId: number, active: boolean) => {
    try {
      await adminApi.toggleStatus(userId, active);
      message.success('状态已更新');
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, is_active: active } : u));
    } catch {
      message.error('状态更新失败');
    }
  };

  const changeRole = async (userId: number, role: string) => {
    try {
      await adminApi.changeRole(userId, role);
      message.success('角色已更新');
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, role } : u));
    } catch {
      message.error('角色更新失败');
    }
  };

  const userColumns = [
    { title: 'ID', dataIndex: 'id' },
    { title: '用户名', dataIndex: 'username' },
    { title: '角色', dataIndex: 'role', render: (v: string, r: any) => (
      <Select size="small" value={v} onChange={val => changeRole(r.id, val)} style={{ width: 100 }}
        options={[{ value: 'trainee', label: '学员' }, { value: 'coach', label: '教练' }, { value: 'admin', label: '管理员' }]} />
    )},
    { title: '状态', dataIndex: 'is_active', render: (v: boolean, r: any) => (
      <Switch checked={v} onChange={val => toggleStatus(r.id, val)} size="small" />
    )},
    { title: '注册时间', dataIndex: 'created_at', render: (v: string) => v?.slice(0, 10) },
  ];

  const logColumns = [
    { title: 'ID', dataIndex: 'id' },
    { title: '用户', dataIndex: 'user_id' },
    { title: '操作', dataIndex: 'action' },
    { title: 'IP', dataIndex: 'ip_address' },
    { title: '时间', dataIndex: 'created_at', render: (v: string) => v?.slice(0, 19) },
  ];

  return (
    <Tabs defaultActiveKey="users" items={[
      {
        key: 'users', label: '用户管理', children: (
          <Card><Table dataSource={users} columns={userColumns} rowKey="id" size="small" /></Card>
        )
      },
      {
        key: 'config', label: '系统配置', children: (
          <Card>
            <Descriptions column={1}>
              <Descriptions.Item label="当前模型">{config.model_path}</Descriptions.Item>
              <Descriptions.Item label="高精度模型">{config.high_precision_model_path}</Descriptions.Item>
              <Descriptions.Item label="运行设备">{config.device}</Descriptions.Item>
            </Descriptions>
          </Card>
        )
      },
      {
        key: 'logs', label: '操作日志', children: (
          <Card><Table dataSource={logs} columns={logColumns} rowKey="id" size="small" /></Card>
        )
      },
    ]} />
  );
}
