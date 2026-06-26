import { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { Card, Typography, Tag, Button, Spin, Descriptions, List, message, Divider, Space, Progress, Row, Col, Statistic, Steps } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, WarningOutlined, ArrowLeftOutlined, TrophyOutlined, ClockCircleOutlined, OrderedListOutlined, AimOutlined } from '@ant-design/icons';
import { trainingApi } from '../services/api';
import type { TrainingRecord, Prescription } from '../types';

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

export default function PrescriptionTrainingReportPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const stateData = (location.state as any)?.trainingResult;
  const extraData = (location.state as any)?.extraData || {};

  const [record, setRecord] = useState<TrainingRecord | null>(null);
  const [loading, setLoading] = useState(true);

  // 从 state 中获取处方训练数据
  const {
    actionResults = [],
    rxDetail = null,
    totalDuration = 0,
    startTime = '',
    endTime = '',
  } = extraData;

  useEffect(() => {
    if (stateData) {
      setRecord(stateData as TrainingRecord);
      setLoading(false);
    } else if (id && id !== '0') {
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
        <Button type="primary" onClick={() => navigate('/prescription-training')}>返回处方训练</Button>
      </Card>
    );
  }

  const score = record.total_score ?? 0;
  const quality = score >= 90 ? 'excellent' : score >= 75 ? 'good' : score >= 60 ? 'fair' : 'needs_improvement';
  const qualityConfig = QUALITY_CONFIG[quality] || { color: '#999', label: '未知' };

  // 计算训练时长
  const duration = totalDuration > 0 ? totalDuration : (record.end_time && record.start_time
    ? Math.round((new Date(record.end_time).getTime() - new Date(record.start_time).getTime()) / 1000)
    : 0);
  const durationStr = duration >= 60
    ? `${Math.floor(duration / 60)}分${duration % 60}秒`
    : `${duration}秒`;

  // 计算总完成次数
  const totalCount = actionResults.reduce((sum: number, r: any) => sum + (r.count || 0), 0);

  // 计算各动作的平均分
  const scoredActions = actionResults.filter((r: any) => r.score !== null);
  const avgScore = scoredActions.length > 0
    ? Math.round(scoredActions.reduce((sum: number, r: any) => sum + r.score, 0) / scoredActions.length)
    : score;

  // 处方进度
  const totalActions = rxDetail?.items?.length || actionResults.length;
  const completedActions = actionResults.filter((r: any) => r.score !== null).length;
  const progressPercent = totalActions > 0 ? Math.round((completedActions / totalActions) * 100) : 0;

  // 收集所有错误
  const allErrors: string[] = [];
  actionResults.forEach((r: any) => {
    if (r.errors && r.errors.length > 0) {
      r.errors.forEach((err: string) => {
        if (!allErrors.includes(err)) allErrors.push(err);
      });
    }
  });

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Button 
        icon={<ArrowLeftOutlined />} 
        style={{ marginBottom: 16 }}
        onClick={() => navigate('/prescription-training')}
      >
        返回处方训练
      </Button>

      <Card>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={3}>
            <TrophyOutlined style={{ color: qualityConfig.color, marginRight: 8 }} />
            处方训练报告
          </Title>
          {rxDetail && (
            <Space>
              <Tag color="blue" style={{ fontSize: 14, padding: '2px 12px' }}>处方 #{rxDetail.id}</Tag>
              <Tag color="orange" style={{ fontSize: 14, padding: '2px 12px' }}>阶段 {rxDetail.phase}</Tag>
              <Tag color="cyan" style={{ fontSize: 14, padding: '2px 12px' }}>
                难度: {'★'.repeat(rxDetail.difficulty)}{'☆'.repeat(5 - rxDetail.difficulty)}
              </Tag>
            </Space>
          )}
          <Tag color={record.mode === 'advanced' ? 'purple' : 'green'} style={{ fontSize: 14, padding: '2px 12px', marginLeft: 8 }}>
            {record.mode === 'advanced' ? '进阶模式' : '基础模式'}
          </Tag>
        </div>

        {/* 评分概览 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card style={{ textAlign: 'center', background: '#fafafa' }}>
              <Statistic
                title="综合评分"
                value={avgScore}
                suffix="/ 100"
                valueStyle={{ color: qualityConfig.color, fontSize: 28, fontWeight: 'bold' }}
              />
              <Tag color={qualityConfig.color} style={{ marginTop: 4, fontSize: 12, padding: '2px 8px' }}>
                {qualityConfig.label}
              </Tag>
            </Card>
          </Col>
          <Col span={6}>
            <Card style={{ textAlign: 'center', background: '#fafafa' }}>
              <Statistic
                title="训练时长"
                value={durationStr}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ fontSize: 20 }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card style={{ textAlign: 'center', background: '#fafafa' }}>
              <Statistic
                title="完成动作"
                value={`${completedActions}/${totalActions}`}
                prefix={<OrderedListOutlined />}
                valueStyle={{ fontSize: 20 }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card style={{ textAlign: 'center', background: '#fafafa' }}>
              <Statistic
                title="总完成次数"
                value={totalCount}
                suffix="次"
                valueStyle={{ fontSize: 20 }}
              />
            </Card>
          </Col>
        </Row>

        {/* 处方执行进度 */}
        <div style={{ marginBottom: 24 }}>
          <Text strong><AimOutlined style={{ marginRight: 4 }} />处方执行进度</Text>
          <Progress 
            percent={progressPercent} 
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
            format={() => `${completedActions}/${totalActions} 个动作`}
            style={{ marginTop: 8 }}
          />
        </div>

        {/* 各动作完成情况 */}
        {actionResults.length > 0 && (
          <div style={{ marginBottom: 24 }}>
            <Title level={5}>各动作完成情况</Title>
            <Steps
              direction="vertical"
              size="small"
              current={completedActions - 1}
              items={actionResults.map((item: any, idx: number) => {
                const itemScore = item.score;
                const isCompleted = itemScore !== null;
                const itemQuality = itemScore >= 90 ? 'excellent' : itemScore >= 75 ? 'good' : itemScore >= 60 ? 'fair' : 'needs_improvement';
                const itemQualityColor = QUALITY_CONFIG[itemQuality]?.color || '#999';
                
                return {
                  title: (
                    <Space>
                      <Text strong>{ACTION_NAME_MAP[item.action_name] || item.action_name}</Text>
                      {isCompleted ? (
                        <Tag color={itemQualityColor} style={{ fontSize: 12 }}>
                          {itemScore}分
                        </Tag>
                      ) : (
                        <Tag color="default">未完成</Tag>
                      )}
                      {item.count > 0 && (
                        <Tag color="orange" style={{ fontSize: 12 }}>完成 {item.count} 次</Tag>
                      )}
                      {item.errors && item.errors.length > 0 && (
                        <Tag color="red" style={{ fontSize: 12 }}>{item.errors.length}个错误</Tag>
                      )}
                    </Space>
                  ),
                  description: isCompleted && item.errors && item.errors.length > 0 ? (
                    <div style={{ marginTop: 4 }}>
                      {item.errors.slice(0, 3).map((err: string, i: number) => (
                        <Tag key={i} color="red" style={{ fontSize: 11, marginBottom: 2, whiteSpace: 'normal', height: 'auto', lineHeight: '16px', padding: '1px 6px' }}>
                          {err}
                        </Tag>
                      ))}
                      {item.errors.length > 3 && (
                        <Text type="secondary" style={{ fontSize: 11 }}>...还有 {item.errors.length - 3} 个问题</Text>
                      )}
                    </div>
                  ) : isCompleted ? (
                    <Text type="secondary" style={{ fontSize: 12, color: '#52c41a' }}>
                      <CheckCircleOutlined /> 完成良好
                    </Text>
                  ) : (
                    <Text type="secondary" style={{ fontSize: 12 }}>未开始</Text>
                  ),
                  status: isCompleted ? 'finish' as const : 'wait' as const,
                };
              })}
            />
          </div>
        )}

        {/* 训练信息 */}
        <Descriptions title="训练信息" bordered column={2} size="small" style={{ marginBottom: 24 }}>
          <Descriptions.Item label="训练模式">
            <Tag color={record.mode === 'advanced' ? 'purple' : 'green'}>
              {record.mode === 'advanced' ? '进阶模式' : '基础模式'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="处方编号">
            <Tag color="blue">#{rxDetail?.id || record.prescription_id}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="开始时间">
            {startTime || (record.start_time ? new Date(record.start_time).toLocaleString('zh-CN') : '-')}
          </Descriptions.Item>
          <Descriptions.Item label="结束时间">
            {endTime || (record.end_time ? new Date(record.end_time).toLocaleString('zh-CN') : '-')}
          </Descriptions.Item>
          <Descriptions.Item label="训练时长">{durationStr}</Descriptions.Item>
          <Descriptions.Item label="完成动作数">{completedActions}/{totalActions}</Descriptions.Item>
        </Descriptions>

        {/* 错误记录汇总 */}
        {allErrors.length > 0 && (
          <>
            <Divider />
            <Title level={5}>
              <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />
              训练中检测到的问题汇总
            </Title>
            <List
              size="small"
              dataSource={allErrors}
              renderItem={(err: string, idx: number) => (
                <List.Item style={{ padding: '4px 0' }}>
                  <Tag color="red" style={{ whiteSpace: 'normal', height: 'auto', lineHeight: '20px', padding: '2px 10px', fontSize: 13 }}>
                    {err}
                  </Tag>
                </List.Item>
              )}
            />
          </>
        )}

        {/* 建议 */}
        {avgScore < 75 && (
          <>
            <Divider />
            <Card size="small" style={{ background: '#fff7e6', border: '1px solid #ffd591' }}>
              <Text strong style={{ color: '#fa8c16' }}>
                <WarningOutlined /> 改进建议：
              </Text>
              <div style={{ marginTop: 8 }}>
                {avgScore < 60 ? (
                  <Text>建议在标准学习页面先学习标准动作，掌握正确姿势后再进行训练。可以针对得分较低的动作重点练习。</Text>
                ) : (
                  <Text>整体动作尚可，但仍有改进空间。建议关注错误记录中的问题，针对性改进各动作的细节。</Text>
                )}
              </div>
            </Card>
          </>
        )}

        {/* 操作按钮 */}
        <Divider />
        <Space style={{ width: '100%', justifyContent: 'center' }}>
          <Button type="primary" size="large" onClick={() => navigate('/prescription-training')}>
            继续处方训练
          </Button>
          <Button size="large" onClick={() => navigate('/training')}>
            实时训练
          </Button>
          <Button size="large" onClick={() => navigate('/home')}>
            返回首页
          </Button>
        </Space>
      </Card>
    </div>
  );
}
