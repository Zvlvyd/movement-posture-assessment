import { useState, useEffect, useCallback } from 'react';
import { Table, Input, Button, message, Space, Card, Popconfirm, Typography } from 'antd';
import { SaveOutlined, ReloadOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons';
import type { SystemConfigMap } from '../../types';
import { adminApi } from '../../services/api';

const { Text } = Typography;

/**
 * 系统配置管理 Tab
 * 可编辑表格，支持保存和重置
 */
export default function ConfigTab() {
  const [config, setConfig] = useState<SystemConfigMap>({});
  const [loading, setLoading] = useState(false);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchConfig = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.config();
      setConfig(data);
    } catch {
      message.error('获取系统配置失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchConfig(); }, [fetchConfig]);

  const handleEdit = (key: string) => {
    setEditingKey(key);
    setEditingValue(config[key]?.value || '');
  };

  const handleCancel = () => {
    setEditingKey(null);
    setEditingValue('');
  };

  const handleSave = async (key: string) => {
    setSaving(true);
    try {
      await adminApi.updateConfig({ [key]: editingValue });
      message.success(`配置 ${key} 已更新`);
      setEditingKey(null);
      fetchConfig();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    {
      title: '配置项',
      dataIndex: 'key',
      width: 260,
      render: (key: string) => <Text code>{key}</Text>,
    },
    {
      title: '值',
      dataIndex: 'value',
      render: (_: any, record: { key: string; value: string; description: string }) => {
        if (editingKey === record.key) {
          return (
            <Input
              value={editingValue}
              onChange={e => setEditingValue(e.target.value)}
              style={{ width: 300 }}
              onPressEnter={() => handleSave(record.key)}
            />
          );
        }
        return <Text>{record.value || <Text type="secondary">（空）</Text>}</Text>;
      },
    },
    {
      title: '说明',
      dataIndex: 'description',
      ellipsis: true,
      render: (v: string) => v || '-',
    },
    {
      title: '最后更新',
      dataIndex: 'updated_at',
      width: 160,
      render: (v: string) => v?.slice(0, 16) || '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: { key: string; value: string }) => {
        if (editingKey === record.key) {
          return (
            <Space size="small">
              <Button
                type="link"
                size="small"
                icon={<CheckOutlined />}
                loading={saving}
                onClick={() => handleSave(record.key)}
              />
              <Button
                type="link"
                size="small"
                icon={<CloseOutlined />}
                onClick={handleCancel}
              />
            </Space>
          );
        }
        return (
          <Button type="link" size="small" onClick={() => handleEdit(record.key)}>
            编辑
          </Button>
        );
      },
    },
  ];

  const dataSource = Object.entries(config).map(([key, info]) => ({
    key,
    value: info.value,
    description: info.description || '',
    updated_at: info.updated_at,
  }));

  return (
    <Card
      size="small"
      title="系统配置"
      extra={
        <Button icon={<ReloadOutlined />} size="small" onClick={fetchConfig}>刷新</Button>
      }
    >
      <Table
        columns={columns}
        dataSource={dataSource}
        loading={loading}
        size="middle"
        pagination={false}
        locale={{ emptyText: '暂无配置' }}
      />
    </Card>
  );
}
