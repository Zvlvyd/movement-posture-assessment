import { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { Card, Typography, Tag, Button, Spin, Descriptions, List, message, Divider, Space, Progress, Row, Col, Statistic } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, WarningOutlined, ArrowLeftOutlined, TrophyOutlined, ClockCircleOutlined, NumberOutlined } from '@ant-design/icons';
import { trainingApi } from '../services/api';
import type { TrainingRecord } from '../types';

const { Title, Text } = Typography;

// 动作名称映射
const ACTION_NAME_MAP: Record<string, string> = {
  squat: '深蹲', lunge: '弓步蹲', pushup: '俯卧撑',
  plank: '平板支撑', shoulder_press: '肩部推举',
  jumping_jack: '开合跳', deadlift: '硬拉',
};

// 质量对应的颜色和文本
const QUALITY_CONFIG: Record<string, { color: string; label: string }> = {
  excellent: { color: '#52c41a', label: '优秀' },
  good: { color: '#1890ff', label: '良好' },
  fair: { color: '#faad14', label: '一般' },
  needs_improvement: { color: '#ff4d4f', label: '需改进' },
};

export default function TrainingReportPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const stateData = (location.state as any)?.trainingResult;

  const [record, setRecord] = useState<TrainingRecord | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (stateData) {
      setRecord(stateData as TrainingRecord);
      setLoading(false);
    } else if (id && id !== '0') {
      // 从 API 加载训练记录
      trainingApi.getRecords().then(records => {
        const found = records.find(r => r.id === Number(id));
        if (found) {
          setRecord(found);
        } else {
          message.error('未找到训练记录');
        }
      }).catch(() => message.error('加载训练记录失败'))
      .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [id, stateData]);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!record) {
    return (
      <Card style={{ maxWidth: 600, margin: '40px auto', textAlign: 'center' }}>
        <Title level={4}>未找到训练记录</Title>
        <Button type="primary" onClick={() => navigate('/training')}>返回训练</Button>
      </Card>
    );
  }

  const score = record.total_score ?? 0;
  const quality = score >= 90 ? 'excellent' : score >= 75 ? 'good' : score >= 60 ? 'fair' : 'needs_improvement';
  const qualityConfig = QUALITY_CONFIG[quality] || { color: '#999', label: '未知' };
  const duration = record.end_time && record.start_time
    ? Math.round((new Date(record.end_time).getTime() - new Date(record.start_time).getTime()) / 1000)
    : 0;
  const durationStr = duration >= 60
    ? `${Math.floor(duration / 60)}分${duration % 60}秒`
    : `${duration}秒`;

  // 从 state 中获取额外数据（如果有）
  const extraData = (location.state as any)?.extraData || {};
  const { count = 0, errorHistory = [], actionName = '' } = extraData;

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Button 
        icon={<ArrowLeftOutlined />} 
        style={{ marginBottom: 16 }}
        onClick={() => navigate('/training')}
      >
        返回训练
      </Button>

      <Card>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={3}>
            <TrophyOutlined style={{ color: qualityConfig.color, marginRight: 8 }} />
            训练报告
          </Title>
          {actionName && (
            <Tag color="blue" style={{ fontSize: 16, padding: '4px 16px' }}>
              {ACTION_NAME_MAP[actionName] || actionName}
            </Tag>
          )}
          <Tag color={record.mode === 'advanced' ? 'purple' : 'green'} style={{ fontSize: 14, padding: '2px 12px', marginLeft: 8 }}>
            {record.mode === 'advanced' ? '进阶模式' : '基础模式'}
          </Tag>
        </div>

        {/* 评分概览 */}
        <Row gutter={24} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Card style={{ textAlign: 'center', background: '#fafafa' }}>
              <Statistic
                title="综合评分"
                value={score}
                suffix="/ 100"
                valueStyle={{ color: qualityConfig.color, fontSize: 36, fontWeight: 'bold' }}
              />
              <Tag color={qualityConfig.color} style={{ marginTop: 8, fontSize: 14, padding: '2px 12px' }}>
                {qualityConfig.label}
              </Tag>
            </Card>
          </Col>
          <Col span={8}>
            <Card style={{ textAlign: 'center', background: '#fafafa' }}>
              <Statistic
                title="训练时长"
                value={durationStr}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ fontSize: 24 }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card style={{ textAlign: 'center', background: '#fafafa' }}>
              <Statistic
                title="完成次数"
                value={count}
                prefix={<NumberOutlined />}
                suffix="次"
                valueStyle={{ fontSize: 24 }}
              />
            </Card>
          </Col>
        </Row>

        {/* 进度条 */}
        <div style={{ marginBottom: 24 }}>
          <Text strong>评分详情</Text>
          <Progress 
            percent={score} 
            strokeColor={qualityConfig.color}
            format={(p) => `${p}分`}
            style={{ marginTop: 8 }}
          />
        </div>

        {/* 训练信息 */}
        <Descriptions title="训练信息" bordered column={2} size="small" style={{ marginBottom: 24 }}>
          <Descriptions.Item label="训练模式">
            <Tag color={record.mode === 'advanced' ? 'purple' : 'green'}>
              {record.mode === 'advanced' ? '进阶模式' : '基础模式'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="训练动作">
            <Tag color="blue">{ACTION_NAME_MAP[actionName] || actionName || '深蹲'}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="开始时间">
            {record.start_time ? new Date(record.start_time).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="结束时间">
            {record.end_time ? new Date(record.end_time).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="训练时长">{durationStr}</Descriptions.Item>
          <Descriptions.Item label="完成次数">{count} 次</Descriptions.Item>
        </Descriptions>

        {/* 错误记录 */}
        {errorHistory && errorHistory.length > 0 && (
          <>
            <Divider />
            <Title level={5}>
              <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />
              训练中检测到的问题
            </Title>
            <List
              size="small"
              dataSource={errorHistory}
              renderItem={(err: string, idx: number) => (
                <List.Item style={{ padding: '6px 0' }}>
                  <Tag color="red" style={{ whiteSpace: 'normal', height: 'auto', lineHeight: '20px', padding: '2px 10px', fontSize: 14 }}>
                    {err}
                  </Tag>
                </List.Item>
              )}
            />
          </>
        )}

        {/* 建议 */}
        {score < 75 && (
          <>
            <Divider />
            <Card size="small" style={{ background: '#fff7e6', border: '1px solid #ffd591' }}>
              <Text strong style={{ color: '#fa8c16' }}>
                <WarningOutlined /> 改进建议：
              </Text>
              <div style={{ marginTop: 8 }}>
                {score < 60 ? (
                  <Text>建议在标准学习页面先学习标准动作，掌握正确姿势后再进行训练。</Text>
                ) : (
                  <Text>整体动作尚可，但仍有改进空间。建议关注错误记录中的问题，针对性改进。</Text>
                )}
              </div>
            </Card>
          </>
        )}

        {/* 操作按钮 */}
        <Divider />
        <Space style={{ width: '100%', justifyContent: 'center' }}>
          <Button type="primary" size="large" onClick={() => navigate('/training')}>
            继续训练
          </Button>
          <Button size="large" onClick={() => navigate('/prescription-training')}>
            处方训练
          </Button>
          <Button size="large" onClick={() => navigate('/home')}>
            返回首页
          </Button>
        </Space>
      </Card>
    </div>
  );
}
