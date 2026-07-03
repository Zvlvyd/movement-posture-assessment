import { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Spin, message, Table, Tag } from 'antd';
import {
  UserOutlined, TeamOutlined, SafetyOutlined, WarningOutlined,
  ExperimentOutlined, ThunderboltOutlined, CheckCircleOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import type { AdminDashboard, SystemConfigMap, StorageInfo } from '../../types';
import { adminApi } from '../../services/api';
import RegistrationTrend from './charts/RegistrationTrend';
import RoleDistribution from './charts/RoleDistribution';
import ActiveUsersChart from './charts/ActiveUsersChart';

export default function DashboardTab() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);

  useEffect(() => {
    setLoading(true);
    adminApi.dashboard()
      .then(setDashboard)
      .catch(() => message.error('获取仪表板数据失败'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" tip="加载中..." /></div>;
  }

  if (!dashboard) {
    return <div style={{ textAlign: 'center', padding: 80 }}>暂无数据</div>;
  }

  return (
    <div>
      {/* Top Stat Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="总用户数"
              value={dashboard.total_users}
              prefix={<UserOutlined />}
              valueStyle={{ color: 'var(--color-primary)' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="活跃用户"
              value={dashboard.active_users}
              prefix={<TeamOutlined />}
              valueStyle={{ color: 'var(--color-success, #52c41a)' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="教练数"
              value={dashboard.role_distribution.coach || 0}
              prefix={<SafetyOutlined />}
              valueStyle={{ color: 'var(--color-warning, #faad14)' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="管理员数"
              value={dashboard.role_distribution.admin || 0}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      {/* System Activity */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="FMS 筛查" value={dashboard.system_activity.fms_screens} prefix={<ExperimentOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="体态评估" value={dashboard.system_activity.assessments} prefix={<PlayCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="训练计划" value={dashboard.system_activity.prescriptions} prefix={<ThunderboltOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="打卡次数" value={dashboard.system_activity.checkins} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* Charts Row 1: Registration Trend + Role Distribution */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={14}>
          <Card title="注册趋势（近30天）" size="small">
            <RegistrationTrend data={dashboard.registration_trend} />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="角色分布" size="small">
            <RoleDistribution data={dashboard.role_distribution} />
          </Card>
        </Col>
      </Row>

      {/* Charts Row 2: Active Users + API Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={14}>
          <Card title="活跃用户" size="small">
            <ActiveUsersChart
              dauTrend={dashboard.dau_trend}
              dau={dashboard.dau}
              wau={dashboard.wau}
              mau={dashboard.mau}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="API 请求统计（近7天）" size="small">
            <Table
              dataSource={dashboard.api_stats.slice(0, 10)}
              rowKey="action"
              size="small"
              pagination={false}
              columns={[
                { title: '操作', dataIndex: 'action', ellipsis: true },
                { title: '次数', dataIndex: 'count', width: 80, align: 'right' },
              ]}
              style={{ maxHeight: 250, overflow: 'auto' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Error Rate */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic
              title="错误率（近7天）"
              value={dashboard.error_rate}
              suffix="%"
              valueStyle={{
                color: dashboard.error_rate > 5 ? '#f5222d' : dashboard.error_rate > 1 ? '#faad14' : '#52c41a',
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic title="DAU" value={dashboard.dau} />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic title="WAU" value={dashboard.wau} />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic title="MAU" value={dashboard.mau} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
