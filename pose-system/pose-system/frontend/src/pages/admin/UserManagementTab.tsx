import { useState, useEffect, useCallback } from 'react';
import {
  Table, Button, Select, Switch, Input, Space, Tag, Popconfirm,
  message, Row, Col, Modal, Descriptions, Card, Typography,
} from 'antd';
import {
  SearchOutlined, DeleteOutlined, UndoOutlined, ExportOutlined,
  ReloadOutlined, EyeOutlined, UserAddOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { AdminUser, UserRole, AdminUserDetail } from '../../types';
import { adminApi } from '../../services/api';

const { Text } = Typography;

const ROLE_OPTIONS: { value: UserRole; label: string; color: string }[] = [
  { value: 'admin', label: '管理员', color: 'red' },
  { value: 'coach', label: '教练', color: 'gold' },
  { value: 'trainee', label: '学员', color: 'blue' },
];

const BATCH_OPS = [
  { value: 'activate', label: '批量激活' },
  { value: 'deactivate', label: '批量停用' },
  { value: 'make_coach', label: '批量设为教练' },
  { value: 'make_trainee', label: '批量设为学员' },
];

export default function UserManagementTab() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Filters
  const [filterRole, setFilterRole] = useState<string | undefined>();
  const [filterStatus, setFilterStatus] = useState<boolean | undefined>();
  const [searchText, setSearchText] = useState('');
  const [includeDeleted, setIncludeDeleted] = useState(false);

  // Selection
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  // Detail modal
  const [detailUser, setDetailUser] = useState<AdminUserDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.users({
        role: filterRole,
        is_active: filterStatus,
        search: searchText || undefined,
        page,
        page_size: pageSize,
        include_deleted: includeDeleted,
      });
      setUsers(res.items);
      setTotal(res.total);
    } catch {
      message.error('获取用户列表失败');
    } finally {
      setLoading(false);
    }
  }, [filterRole, filterStatus, searchText, page, pageSize, includeDeleted]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const handleRoleChange = async (userId: number, role: string) => {
    try {
      await adminApi.changeRole(userId, role);
      message.success('角色已更新');
      fetchUsers();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '更新失败');
    }
  };

  const handleStatusToggle = async (userId: number, checked: boolean) => {
    try {
      await adminApi.toggleStatus(userId, checked);
      message.success(checked ? '用户已激活' : '用户已停用');
      fetchUsers();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '操作失败');
    }
  };

  const handleDelete = async (userId: number) => {
    try {
      await adminApi.deleteUser(userId);
      message.success('用户已删除');
      fetchUsers();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败');
    }
  };

  const handleRestore = async (userId: number) => {
    try {
      await adminApi.restoreUser(userId);
      message.success('用户已恢复');
      fetchUsers();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '恢复失败');
    }
  };

  const handleViewDetail = async (userId: number) => {
    try {
      const detail = await adminApi.userDetail(userId);
      setDetailUser(detail);
      setDetailOpen(true);
    } catch {
      message.error('获取用户详情失败');
    }
  };

  const handleBatchOp = async (operation: string) => {
    if (selectedIds.length === 0) {
      message.warning('请先选择用户');
      return;
    }
    try {
      await adminApi.batchOperation({ user_ids: selectedIds, operation });
      message.success('批量操作完成');
      setSelectedIds([]);
      fetchUsers();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '批量操作失败');
    }
  };

  const handleExport = async () => {
    try {
      const blob = await adminApi.exportUsers();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'users_export.csv';
      a.click();
      URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch {
      message.error('导出失败');
    }
  };

  const columns: ColumnsType<AdminUser> = [
    {
      title: 'ID', dataIndex: 'id', width: 60, sorter: (a, b) => a.id - b.id,
    },
    {
      title: '用户名', dataIndex: 'username', width: 120,
      render: (text: string, record: AdminUser) => (
        <Space>
          {text}
          {record.deleted_at && <Tag color="red">已删除</Tag>}
        </Space>
      ),
    },
    {
      title: '角色', dataIndex: 'role', width: 110,
      render: (role: string, record: AdminUser) => {
        if (record.deleted_at) {
          const opt = ROLE_OPTIONS.find(o => o.value === role);
          return <Tag color={opt?.color}>{opt?.label || role}</Tag>;
        }
        return (
          <Select
            size="small"
            value={role}
            style={{ width: 90 }}
            onChange={(val) => handleRoleChange(record.id, val)}
            options={ROLE_OPTIONS.map(o => ({ value: o.value, label: o.label }))}
          />
        );
      },
    },
    {
      title: '手机', dataIndex: 'phone', width: 120, ellipsis: true,
      render: (v: string) => v || '-',
    },
    {
      title: '性别', dataIndex: 'gender', width: 60,
      render: (v: string) => v || '-',
    },
    {
      title: '状态', dataIndex: 'is_active', width: 70,
      render: (active: boolean, record: AdminUser) => (
        <Switch
          checked={active}
          disabled={!!record.deleted_at}
          size="small"
          onChange={(checked) => handleStatusToggle(record.id, checked)}
        />
      ),
    },
    {
      title: '注册时间', dataIndex: 'created_at', width: 140,
      render: (v: string) => v?.slice(0, 10) || '-',
    },
    {
      title: '最后登录', dataIndex: 'last_login_at', width: 140, ellipsis: true,
      render: (v: string) => v?.slice(0, 16) || '-',
    },
    {
      title: '操作', key: 'actions', width: 160, fixed: 'right',
      render: (_: any, record: AdminUser) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record.id)}>
            详情
          </Button>
          {record.deleted_at ? (
            <Popconfirm title="确认恢复此用户？" onConfirm={() => handleRestore(record.id)}>
              <Button type="link" size="small" icon={<UndoOutlined />}>恢复</Button>
            </Popconfirm>
          ) : (
            <Popconfirm title="确认删除此用户？删除后可恢复" onConfirm={() => handleDelete(record.id)}>
              <Button type="link" danger size="small" icon={<DeleteOutlined />}>删除</Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* Toolbar */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col>
            <Input
              placeholder="搜索用户名/手机"
              prefix={<SearchOutlined />}
              allowClear
              style={{ width: 200 }}
              value={searchText}
              onChange={e => { setSearchText(e.target.value); setPage(1); }}
            />
          </Col>
          <Col>
            <Select
              placeholder="角色筛选"
              allowClear
              style={{ width: 120 }}
              value={filterRole}
              onChange={v => { setFilterRole(v); setPage(1); }}
              options={ROLE_OPTIONS.map(o => ({ value: o.value, label: o.label }))}
            />
          </Col>
          <Col>
            <Select
              placeholder="状态筛选"
              allowClear
              style={{ width: 110 }}
              value={filterStatus}
              onChange={v => { setFilterStatus(v); setPage(1); }}
              options={[
                { value: true, label: '活跃' },
                { value: false, label: '停用' },
              ]}
            />
          </Col>
          <Col>
            <Button
              type={includeDeleted ? 'primary' : 'default'}
              size="small"
              onClick={() => { setIncludeDeleted(!includeDeleted); setPage(1); }}
            >
              显示已删除
            </Button>
          </Col>
          <Col flex="auto" />
          <Col>
            <Space>
              {selectedIds.length > 0 && (
                <Select
                  placeholder="批量操作"
                  style={{ width: 130 }}
                  onChange={handleBatchOp}
                  options={BATCH_OPS}
                />
              )}
              <Button icon={<ExportOutlined />} size="small" onClick={handleExport}>导出</Button>
              <Button icon={<ReloadOutlined />} size="small" onClick={fetchUsers}>刷新</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Table */}
      <Table
        rowKey="id"
        columns={columns}
        dataSource={users}
        loading={loading}
        size="middle"
        rowSelection={{
          selectedRowKeys: selectedIds,
          onChange: (keys) => setSelectedIds(keys as number[]),
          getCheckboxProps: (record) => ({ disabled: !!record.deleted_at }),
        }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 个用户`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps); },
        }}
        scroll={{ x: 1000 }}
      />

      {/* User Detail Modal */}
      <Modal
        title="用户详情"
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={<Button onClick={() => setDetailOpen(false)}>关闭</Button>}
        width={600}
      >
        {detailUser && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="ID">{detailUser.id}</Descriptions.Item>
            <Descriptions.Item label="用户名">{detailUser.username}</Descriptions.Item>
            <Descriptions.Item label="角色">
              <Tag color={ROLE_OPTIONS.find(o => o.value === detailUser.role)?.color}>
                {ROLE_OPTIONS.find(o => o.value === detailUser.role)?.label || detailUser.role}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              {detailUser.is_active ? <Tag color="green">活跃</Tag> : <Tag color="red">停用</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="手机">{detailUser.phone || '-'}</Descriptions.Item>
            <Descriptions.Item label="性别">{detailUser.gender || '-'}</Descriptions.Item>
            <Descriptions.Item label="注册时间">{detailUser.created_at?.slice(0, 16) || '-'}</Descriptions.Item>
            <Descriptions.Item label="最后登录">{detailUser.last_login_at?.slice(0, 16) || '-'}</Descriptions.Item>
            <Descriptions.Item label="FMS 记录" span={2}>{detailUser.stats.fms_records}</Descriptions.Item>
            <Descriptions.Item label="体态评估">{detailUser.stats.assessments}</Descriptions.Item>
            <Descriptions.Item label="训练计划">{detailUser.stats.prescriptions}</Descriptions.Item>
            <Descriptions.Item label="打卡次数">{detailUser.stats.checkins}</Descriptions.Item>
            <Descriptions.Item label="连续打卡">{detailUser.stats.streak_days} 天</Descriptions.Item>
            <Descriptions.Item label="所在班级" span={2}>
              {detailUser.stats.classes.length > 0
                ? detailUser.stats.classes.map(c => <Tag key={c.id}>{c.name}</Tag>)
                : '无'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
}
