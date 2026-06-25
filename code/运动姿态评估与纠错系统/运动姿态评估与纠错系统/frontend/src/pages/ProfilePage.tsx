import { useEffect, useState } from 'react';
import { Card, Descriptions, Tabs, Table, Tag, Statistic, Row, Col } from 'antd';
import { useAuthStore } from '../store/auth';
import { recordsApi, fmsApi } from '../services/api';
import type { TrainingRecord, FMSRecord, TrainingStats } from '../types';

export default function ProfilePage() {
  const user = useAuthStore(s => s.user);
  const [stats, setStats] = useState<TrainingStats | null>(null);
  const [records, setRecords] = useState<TrainingRecord[]>([]);
  const [fmsRecords, setFmsRecords] = useState<FMSRecord[]>([]);

  useEffect(() => {
    recordsApi.stats().then(setStats);
    recordsApi.history(90).then(setRecords);
    fmsApi.getRecords().then(setFmsRecords);
  }, []);

  const columns = [
    { title: '时间', dataIndex: 'start_time', render: (v: string) => new Date(v).toLocaleString() },
    { title: '模式', dataIndex: 'mode', render: (v: string) => <Tag>{v === 'basic' ? '基础' : '进阶'}</Tag> },
    { title: '评分', dataIndex: 'total_score', render: (v: number) => v ? `${v}分` : '-' },
  ];

  const fmsColumns = [
    { title: '日期', dataIndex: 'test_date', render: (v: string) => new Date(v).toLocaleDateString() },
    { title: '综合评分', dataIndex: 'overall_score' },
    { title: '风险', dataIndex: 'risk_level', render: (v: string) => <Tag color={v === 'high' ? 'red' : 'green'}>{v}</Tag> },
  ];

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <Card>
        <Descriptions title="个人信息">
          <Descriptions.Item label="用户名">{user?.username}</Descriptions.Item>
          <Descriptions.Item label="角色">{user?.role === 'trainee' ? '训练者' : user?.role === 'coach' ? '教练' : '管理员'}</Descriptions.Item>
          <Descriptions.Item label="手机">{user?.phone || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Tabs defaultActiveKey="stats" style={{ marginTop: 16 }} items={[
        {
          key: 'stats', label: '训练统计', children: (
            <Row gutter={16}>
              <Col span={6}><Card><Statistic title="连续打卡" value={stats?.current_streak || 0} suffix="天" /></Card></Col>
              <Col span={6}><Card><Statistic title="近7天" value={stats?.total_sessions_7d || 0} suffix="次" /></Card></Col>
              <Col span={6}><Card><Statistic title="近30天" value={stats?.total_sessions_30d || 0} suffix="次" /></Card></Col>
              <Col span={6}><Card><Statistic title="平均评分" value={stats?.average_score || 0} suffix="分" precision={1} /></Card></Col>
            </Row>
          )
        },
        {
          key: 'records', label: '训练记录', children: (
            <Table dataSource={records} columns={columns} rowKey="id" size="small" />
          )
        },
        {
          key: 'fms', label: 'FMS档案', children: (
            <Table dataSource={fmsRecords} columns={fmsColumns} rowKey="id" size="small" />
          )
        },
      ]} />
    </div>
  );
}
