import { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { Card, Typography, Tag, Button, Spin, Descriptions, List, message, Collapse, Alert, Divider, Space, Progress } from 'antd';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { ExclamationCircleOutlined, CheckCircleOutlined, BulbOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { fmsApi, prescriptionApi } from '../services/api';
import type { FMSRecord } from '../types';

export default function FMSReportPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [record, setRecord] = useState<FMSRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [genLoading, setGenLoading] = useState(false);

  const location = useLocation();
  const stateData = (location.state as any)?.fmsResult;
  const [postureReport, setPostureReport] = useState<any>(null);

  useEffect(() => {
    // 优先使用路由 state 传入的数据，否则从 API 加载
    if (stateData) {
      // Extract posture report from state
    if (stateData?.posture_report) setPostureReport(stateData.posture_report);
    
    setRecord({
        id: stateData.record_id || 0,
        overall_score: stateData.overall_score,
        risk_level: stateData.risk_level,
        test_date: new Date().toISOString(),
        radar_data: {
          dimensions: stateData.scores?.map((s: any) => ({ key: s.dimension, label: s.label || s.dimension, score: s.score })) || [],
          chart_data: { labels: stateData.scores?.map((s: any) => s.label || s.dimension) || [], values: stateData.scores?.map((s: any) => s.score) || [] },
          suggestions: stateData.radar_data?.suggestions || [],
        },
        problem_tags: stateData.problem_tags || [],
      } as any);
    } else if (id && id !== '0') {
      fmsApi.getRecord(Number(id)).then(setRecord).catch(() => message.error('加载失败'));
    }
  }, [id, stateData]);

  const generateRx = async () => {
    if (!record) return;
    setGenLoading(true);
    try {
      await prescriptionApi.generate(record.id);
      message.success('处方已生成！');
      navigate('/training');
    } catch (e: any) {
      message.error(e.response?.data?.detail || '生成失败');
    } finally { setGenLoading(false); }
  };

  if (!record) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  const riskColor = record.risk_level === 'high' ? 'red' : record.risk_level === 'medium' ? 'orange' : 'green';
  const radarData = record.radar_data?.chart_data?.labels?.map((label: string, i: number) => ({
    subject: label, score: record.radar_data.chart_data.values[i], fullMark: 100,
  })) || [];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Card title="FMS 筛查报告">
        <Descriptions column={3}>
          <Descriptions.Item label="综合评分"><Typography.Title level={3}>{record.overall_score}</Typography.Title></Descriptions.Item>
          <Descriptions.Item label="风险等级"><Tag color={riskColor}>{record.risk_level === 'high' ? '高风险' : record.risk_level === 'medium' ? '中等' : '低风险'}</Tag></Descriptions.Item>
          <Descriptions.Item label="测试日期">{new Date(record.test_date).toLocaleDateString()}</Descriptions.Item>
        </Descriptions>
      </Card>

      {radarData.length > 0 && (
        <Card title="能力雷达图" style={{ marginTop: 16 }}>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid /><PolarAngleAxis dataKey="subject" /><PolarRadiusAxis angle={30} domain={[0, 100]} />
              <Radar name="评分" dataKey="score" stroke="#1677ff" fill="#1677ff" fillOpacity={0.3} />
            </RadarChart>
          </ResponsiveContainer>
        </Card>
      )}

      <Card title="各维度评分" style={{ marginTop: 16 }}>
        {record.radar_data?.dimensions?.map((d: any) => (
          <Descriptions key={d.key} column={1} size="small" style={{ marginBottom: 8 }}>
            <Descriptions.Item label={d.label}>{d.score} / 100</Descriptions.Item>
          </Descriptions>
        ))}
      </Card>

      {record.problem_tags && record.problem_tags.length > 0 && (
        <Card title="发现的问题" style={{ marginTop: 16 }}>
          {record.problem_tags.map((t: any, i: number) => (
            <Tag color="orange" key={i}>{t.name}: {t.description}</Tag>
          ))}
        </Card>
      )}

      {/* 各维度评分详情（带进度条和颜色标识） */}
      <Card title="各维度评分详情" style={{ marginTop: 16 }}>
        {record.radar_data?.dimensions?.map((d: any) => {
          const scoreColor = d.score >= 80 ? '#52c41a' : d.score >= 60 ? '#faad14' : d.score >= 40 ? '#fa8c16' : '#ff4d4f';
          const scoreLabel = d.score >= 80 ? '优秀' : d.score >= 60 ? '良好' : d.score >= 40 ? '待改善' : '较差';
          return (
            <div key={d.key || d.dimension} style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <Typography.Text strong>{d.label}</Typography.Text>
                <Space>
                  <Tag color={scoreColor}>{scoreLabel}</Tag>
                  <Typography.Text style={{ color: scoreColor, fontWeight: 'bold' }}>{d.score} / 100</Typography.Text>
                </Space>
              </div>
              <Progress
                percent={d.score}
                strokeColor={scoreColor}
                showInfo={false}
                size="small"
              />
            </div>
          );
        })}
      </Card>

      {/* 个性化训练建议 */}
      {record.radar_data?.suggestions && record.radar_data.suggestions.length > 0 && (
        <Card
          title={<Space><BulbOutlined />个性化训练建议</Space>}
          style={{ marginTop: 16 }}
        >
          <List
            dataSource={record.radar_data.suggestions}
            renderItem={(s: string, i: number) => (
              <List.Item>
                <List.Item.Meta
                  avatar={
                    <div style={{
                      width: 28, height: 28, borderRadius: '50%',
                      background: '#1677ff', color: '#fff',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontWeight: 'bold', fontSize: 14,
                    }}>
                      {i + 1}
                    </div>
                  }
                  description={s}
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* 风险预警 */}
      {record.risk_level === 'high' && (
        <Alert
          message="高风险预警"
          description="您的综合评分较低，存在较高的运动损伤风险。建议在专业教练指导下进行训练，避免高强度或高难度动作。请优先关注评分最低的维度进行针对性改善。"
          type="error"
          showIcon
          icon={<ExclamationCircleOutlined />}
          style={{ marginTop: 16 }}
        />
      )}
      {record.risk_level === 'medium' && (
        <Alert
          message="中等风险提示"
          description="您的部分运动能力有待提升，建议针对评分较低的维度进行专项训练，逐步改善身体弱链。"
          type="warning"
          showIcon
          icon={<ExclamationCircleOutlined />}
          style={{ marginTop: 16 }}
        />
      )}
      {record.risk_level === 'low' && (
        <Alert
          message="低风险"
          description="您的运动能力整体良好，继续保持规律训练。建议定期复测以跟踪进步情况。"
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
          style={{ marginTop: 16 }}
        />
      )}

      {/* Posture Analysis Section */}
      {postureReport && postureReport.problems && postureReport.problems.length > 0 && (
        <>
          <Divider orientation="left" style={{ marginTop: 24 }}>
            <Space><ThunderboltOutlined />体态肌骨分析</Space>
          </Divider>
          
          {postureReport.summary && (
            <Alert message="分析总结" description={postureReport.summary} type="info" showIcon style={{ marginBottom: 16 }} />
          )}
          
          <Collapse accordion>
            {postureReport.problems.map((p: any, i: number) => {
              const sevColor = p.severity === 'severe' ? 'red' : p.severity === 'moderate' ? 'orange' : p.severity === 'mild' ? 'gold' : 'green';
              const sevLabel = p.severity === 'severe' ? '严重' : p.severity === 'moderate' ? '中度' : p.severity === 'mild' ? '轻度' : '正常';
              return (
                <Collapse.Panel
                  key={i}
                  header={
                    <Space>
                      <Tag color={sevColor}>{sevLabel}</Tag>
                      <span>{p.name}</span>
                      {p.value !== undefined && <Typography.Text type="secondary">({p.value}{p.unit})</Typography.Text>}
                    </Space>
                  }
                >
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="测量值">{p.value}{p.unit}（正常: {p.normal_range}）</Descriptions.Item>
                    <Descriptions.Item label="成因">{p.cause || '无'}</Descriptions.Item>
                  </Descriptions>
                  
                  {p.note && <Alert message={p.note} type="warning" showIcon style={{ marginTop: 8, marginBottom: 8 }} />}
                  
                  {p.tight_muscles && p.tight_muscles.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <Typography.Text strong>紧张肌群：</Typography.Text>
                      {p.tight_muscles.map((m: any) => (
                        <Tag key={m.name} color="volcano" style={{ margin: 2 }}>{m.name}</Tag>
                      ))}
                    </div>
                  )}
                  
                  {p.weak_muscles && p.weak_muscles.length > 0 && (
                    <div style={{ marginTop: 4 }}>
                      <Typography.Text strong>薄弱肌群：</Typography.Text>
                      {p.weak_muscles.map((m: any) => (
                        <Tag key={m.name} color="blue" style={{ margin: 2 }}>{m.name}</Tag>
                      ))}
                    </div>
                  )}
                  
                  {p.exercises && (p.exercises.stretch?.length > 0 || p.exercises.strength?.length > 0) && (
                    <div style={{ marginTop: 12 }}>
                      <Typography.Text strong><ThunderboltOutlined /> 康复训练建议</Typography.Text>
                      
                      {p.exercises.stretch?.map((ex: any, j: number) => (
                        <Card key={`stretch-${j}`} size="small" style={{ marginTop: 8 }}>
                          <Typography.Text strong type="success">拉伸：{ex.name}</Typography.Text>
                          <List size="small" dataSource={ex.steps} renderItem={(step: string, k: number) => (
                            <List.Item>{k+1}. {step}</List.Item>
                          )} />
                          <Typography.Text type="secondary">组数：{ex.sets}</Typography.Text>
                        </Card>
                      ))}
                      
                      {p.exercises.strength?.map((ex: any, j: number) => (
                        <Card key={`strength-${j}`} size="small" style={{ marginTop: 8 }}>
                          <Typography.Text strong type="warning">力量：{ex.name}</Typography.Text>
                          <List size="small" dataSource={ex.steps} renderItem={(step: string, k: number) => (
                            <List.Item>{k+1}. {step}</List.Item>
                          )} />
                          <Typography.Text type="secondary">组数：{ex.sets}</Typography.Text>
                        </Card>
                      ))}
                    </div>
                  )}
                </Collapse.Panel>
              );
            })}
          </Collapse>
        </>
      )}
      
      <Button type="primary" size="large" block loading={genLoading} onClick={generateRx} style={{ marginTop: 24 }}>
        基于此结果生成训练处方
      </Button>
    </div>
  );
}
