import { useState, useEffect, useCallback } from 'react';
import { Table, Input, Button, message, Card, Space, Select, Tag } from 'antd';
import { SearchOutlined, ExportOutlined, ReloadOutlined } from '@ant-design/icons';
import type { SystemLogEntry } from '../../types';
import { adminApi } from '../../services/api';

export default function LogsTab() {
  const [logs, setLogs] = useState<SystemLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionFilter, setActionFilter] = useState('');
  const [userIdFilter, setUserIdFilter] = useState<number | undefined>();
  const [limit, setLimit] = useState(100);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { limit };
      if (actionFilter) params.action = actionFilter;
      if (userIdFilter) params.user_id = userIdFilter;
      const data = await adminApi.logs(params);
      setLogs(Array.isArray(data) ? data : []);
    } catch {
      message.error('获取日志失败');
    } finally {
      setLoading(false);
    }
  }, [limit, actionFilter, userIdFilter]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const handleExport = async () => {
    try {
      const blob = await adminApi.exportLogs(limit);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'logs_export.csv';
      a.click();
      URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch {
      message.error('导出失败');
    }
  };

  const columns = [
    {
      title: 'ID', dataIndex: 'id', width: 60,
    },
    {
      title: '用户ID', dataIndex: 'user_id', width: 80,
      render: (v: number | null) => v ?? '-',
    },
    {
      title: '操作', dataIndex: 'action', width: 200, ellipsis: true,
      render: (v: string) => {
        const isError = v.toLowerCase().includes('error') || v.toLowerCase().includes('fail');
        return isError ? <Tag color="red">{v}</Tag> : v;
      },
    },
    {
      title: '详情', dataIndex: 'detail', ellipsis: true,
      render: (v: string) => v || '-',
    },
    {
      title: 'IP', dataIndex: 'ip_address', width: 130,
      render: (v: string) => v || '-',
    },
    {
      title: '时间', dataIndex: 'created_at', width: 160,
      render: (v: string) => v?.slice(0, 19) || '-',
    },
  ];

  return (
    <div>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input
            placeholder="搜索操作名称"
            prefix={<SearchOutlined />}
            allowClear
            style={{ width: 200 }}
            value={actionFilter}
            onChange={e => setActionFilter(e.target.value)}
          />
          <Input
            placeholder="按用户ID过滤"
            allowClear
            type="number"
            style={{ width: 150 }}
            value={userIdFilter || ''}
            onChange={e => {
              const v = e.target.value;
              setUserIdFilter(v ? Number(v) : undefined);
            }}
          />
          <Select
            value={limit}
            style={{ width: 110 }}
            onChange={setLimit}
            options={[
              { value: 50, label: '最近50条' },
              { value: 100, label: '最近100条' },
              { value: 200, label: '最近200条' },
              { value: 500, label: '最近500条' },
            ]}
          />
          <Button icon={<ExportOutlined />} onClick={handleExport}>导出</Button>
          <Button icon={<ReloadOutlined />} onClick={fetchLogs}>刷新</Button>
        </Space>
      </Card>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={logs}
        loading={loading}
        size="middle"
        pagination={{ pageSize: 50, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
        scroll={{ x: 900 }}
      />
    </div>
  );
}
