import { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { Card, Typography, Tag, Button, Spin, Collapse, Alert, Divider, Space, Descriptions } from 'antd';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { ExclamationCircleOutlined, CheckCircleOutlined, BulbOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { assessmentApi } from '../services/api';

const RISK_COLORS: Record<string, string> = { high: '#ff4d4f', medium: '#faad14', low: '#52c41a' };
const RISK_LABELS: Record<string, string> = { high: '高风险', medium: '中等', low: '良好' };

export default function AssessmentReportPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const stateData = (location.state as any)?.result;

  const [record, setRecord] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (stateData) {
      setRecord({
        id: stateData.record_id,
        overall_score: stateData.overall_score,
        risk_level: stateData.risk_level,
        dimensions: stateData.dimensions,
        chart_data: stateData.chart_data,
        posture_problems: stateData.posture_problems,
        asymmetry_findings: stateData.asymmetry_findings,
        muscle_analysis: stateData.muscle_analysis,
        suggestions: stateData.suggestions,
        summary: stateData.summary,
      });
    } else if (id) {
      setLoading(true);
      assessmentApi.getRecord(Number(id))
        .then(setRecord)
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [id, stateData]);

  if (loading) return <div style={{ textAlign: 'center', padding: 48 }}><Spin size="large" /></div>;
  if (!record) return <div style={{ textAlign: 'center', padding: 48 }}>未找到评估记录</div>;

  const riskColor = RISK_COLORS[record.risk_level] || '#999';

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      {/* Header */}
      <Card style={{ marginBottom: 16, textAlign: 'center', borderLeft: `4px solid ${riskColor}`}}>
        <Typography.Title level={3} style={{ marginBottom: 4 }}>
          <ExclamationCircleOutlined style={{ color: riskColor, marginRight: 8 }} />
          体态评估报告
        </Typography.Title>
        <Space size="large">
          <div>
            <Typography.Text type="secondary">综合评分</Typography.Text>
            <br />
            <Typography.Text style={{ fontSize: 36, fontWeight: 'bold', color: riskColor }}>
              {record.overall_score?.toFixed(1)}
            </Typography.Text>
            <Typography.Text type="secondary"> / 100</Typography.Text>
          </div>
          <Tag color={riskColor} style={{ fontSize: 16, padding: '4px 16px' }}>
            {RISK_LABELS[record.risk_level] || record.risk_level}
          </Tag>
        </Space>
      </Card>

      {/* Radar Chart */}
      {record.chart_data && (
        <Card title="5维度能力图" size="small" style={{ marginBottom: 16 }}>
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={record.dimensions?.map((d: any, i: number) => ({
              dimension: d.label, score: d.score, full: 100,
            }))}>
              <PolarGrid />
              <PolarAngleAxis dataKey="dimension" />
              <PolarRadiusAxis angle={30} domain={[0, 100]} />
              <Radar dataKey="score" stroke={riskColor} fill={riskColor} fillOpacity={0.3} />
              <Radar dataKey="full" stroke="#ddd" fill="#f5f5f5" fillOpacity={0.1} />
            </RadarChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Posture Problems */}
      {record.posture_problems?.length > 0 && (
        <Card title="体态问题" size="small" style={{ marginBottom: 16 }}>
          {record.posture_problems.map((p: any, i: number) => (
            <Card key={i} size="small" style={{ marginBottom: 8 }}
              title={<Space><Tag color={p.severity === 'severe' ? 'red' : p.severity === 'moderate' ? 'orange' : 'blue'}>{p.severity}</Tag> {p.name}</Space>}>
              {p.tight?.length > 0 && (
                <div style={{ marginBottom: 6 }}>
                  <Typography.Text type="secondary">紧张肌肉: </Typography.Text>
                  {p.tight.map((m: string, j: number) => <Tag key={j} color="volcano">{m}</Tag>)}
                </div>
              )}
              {p.weak?.length > 0 && (
                <div style={{ marginBottom: 6 }}>
                  <Typography.Text type="secondary">薄弱肌肉: </Typography.Text>
                  {p.weak.map((m: string, j: number) => <Tag key={j} color="cyan">{m}</Tag>)}
                </div>
              )}
              {p.cause && <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 4 }}>原因: {p.cause}</Typography.Paragraph>}
              {p.exercises && (
                <Collapse ghost size="small" items={[
                  ...(p.exercises.stretch?.length > 0 ? [{
                    key: 'stretch', label: 拉伸训练 (项),
                    children: p.exercises.stretch.map((e: any, j: number) => (
                      <div key={j} style={{ marginBottom: 8 }}>
                        <Typography.Text strong>{e.name || e}</Typography.Text>
                        {e.sets && <Tag style={{ marginLeft: 8 }}>{e.sets}</Tag>}
                      </div>
                    ))
                  }] : []),
                  ...(p.exercises.strength?.length > 0 ? [{
                    key: 'strength', label: 强化训练 (项),
                    children: p.exercises.strength.map((e: any, j: number) => (
                      <div key={j} style={{ marginBottom: 8 }}>
                        <Typography.Text strong>{e.name || e}</Typography.Text>
                        {e.sets && <Tag style={{ marginLeft: 8 }}>{e.sets}</Tag>}
                      </div>
                    ))
                  }] : []),
                ]} />
              )}
            </Card>
          ))}
        </Card>
      )}

      {/* Asymmetry */}
      {record.asymmetry_findings?.length > 0 && (
        <Card title="关节不对称" size="small" style={{ marginBottom: 16 }}>
          {record.asymmetry_findings.map((f: any, i: number) => (
            <div key={i} style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Tag color={f.severity === 'severe' ? 'red' : f.severity === 'moderate' ? 'orange' : 'gold'}>
                {f.severity}
              </Tag>
              <Typography.Text>{f.joint}</Typography.Text>
              <Typography.Text type="secondary">差异 {f.diff_pct}%</Typography.Text>
              {f.side_limited && <Tag>{f.side_limited === 'left' ? '左侧受限' : '右侧受限'}</Tag>}
            </div>
          ))}
        </Card>
      )}

      {/* Muscle Analysis */}
      {record.muscle_analysis && (
        <Card title="肌肉分析" size="small" style={{ marginBottom: 16 }}>
          <Descriptions column={2} size="small">
            <Descriptions.Item label="紧张肌肉">{record.muscle_analysis.tight_count || 0} 块</Descriptions.Item>
            <Descriptions.Item label="薄弱肌肉">{record.muscle_analysis.weak_count || 0} 块</Descriptions.Item>
          </Descriptions>
          <Divider style={{ margin: '8px 0' }} />
          {record.muscle_analysis.tight_muscles?.map((m: any, i: number) => (
            <Tag key={`t${i}`} color="volcano" style={{ margin: 2 }}>
              {m.name} ({m.en})
            </Tag>
          ))}
          {record.muscle_analysis.weak_muscles?.map((m: any, i: number) => (
            <Tag key={`w${i}`} color="cyan" style={{ margin: 2 }}>
              {m.name} ({m.en})
            </Tag>
          ))}
        </Card>
      )}

      {/* Suggestions */}
      {record.suggestions?.length > 0 && (
        <Card title={<Space><BulbOutlined /> 训练建议</Space>} size="small" style={{ marginBottom: 16 }}>
          {record.suggestions.map((s: string, i: number) => (
            <Alert key={i} message={s} type="info" style={{ marginBottom: 4 }} showIcon={false} />
          ))}
        </Card>
      )}

      {/* Summary */}
      {record.summary && (
        <Alert message="评估总结" description={record.summary} type="warning" showIcon style={{ marginBottom: 16 }} />
      )}

      <div style={{ textAlign: 'center', marginTop: 16 }}>
        <Space>
          <Button type="primary" onClick={() => navigate('/assessment')}>重新评估</Button>
          <Button onClick={() => navigate('/')}>返回首页</Button>
        </Space>
      </div>
    </div>
  );
}
