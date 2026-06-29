import { useState } from 'react';
import { Card, Typography, Button, Spin, message } from 'antd';
import { RobotOutlined, ReloadOutlined } from '@ant-design/icons';
import { assessmentApi } from '../services/api';

/**
 * 简易 Markdown 渲染器 —— 支持标题、列表、加粗、段落。
 * 避免引入额外依赖。
 */
function renderMarkdown(md: string) {
  const lines = md.split('\n');
  const elements: React.ReactNode[] = [];
  let listItems: React.ReactNode[] = [];

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(<ul key={elements.length} style={{ paddingLeft: 20, margin: '4px 0' }}>{listItems}</ul>);
      listItems = [];
    }
  };

  for (const line of lines) {
    // 标题
    const hMatch = line.match(/^### (.+)/);
    if (hMatch) {
      flushList();
      elements.push(
        <Typography.Title key={elements.length} level={5} style={{ margin: '16px 0 4px' }}>
          {hMatch[1]}
        </Typography.Title>
      );
      continue;
    }
    const h2Match = line.match(/^## (.+)/);
    if (h2Match) {
      flushList();
      elements.push(
        <Typography.Title key={elements.length} level={4} style={{ margin: '18px 0 4px' }}>
          {h2Match[1]}
        </Typography.Title>
      );
      continue;
    }
    // 无序列表
    const liMatch = line.match(/^-\s+(.+)/);
    if (liMatch) {
      listItems.push(<li key={listItems.length}>{inlineBold(liMatch[1])}</li>);
      continue;
    }
    // 有序列表
    const oliMatch = line.match(/^\d+\.\s+(.+)/);
    if (oliMatch) {
      listItems.push(<li key={listItems.length}>{inlineBold(oliMatch[1])}</li>);
      continue;
    }
    // 空行 — 结束列表
    if (line.trim() === '') {
      flushList();
      continue;
    }
    // 普通段落
    flushList();
    elements.push(
      <Typography.Paragraph key={elements.length} style={{ margin: '4px 0' }}>
        {inlineBold(line)}
      </Typography.Paragraph>
    );
  }
  flushList();
  return elements;
}

/** 处理行内的 **加粗** */
function inlineBold(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) {
      return <strong key={i}>{p.slice(2, -2)}</strong>;
    }
    return p;
  });
}

// ── Component ─────────────────────────────────────────────

interface Props {
  assessmentId: number;
}

export default function AiReportSection({ assessmentId }: Props) {
  const [report, setReport] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const generate = async (forceRegenerate: boolean) => {
    setLoading(true);
    try {
      const data = await assessmentApi.generateReport(assessmentId, forceRegenerate);
      setReport(data.report);
      if (data.cached) message.info('已加载缓存的 AI 报告');
      else message.success('AI 报告生成成功');
    } catch (e: any) {
      message.error(e.response?.data?.detail || 'AI 报告生成失败，请确保已配置 DEEPSEEK_API_KEY');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      title={<><RobotOutlined /> AI 智能分析报告</>}
      size="small"
      style={{ marginBottom: 16 }}
      extra={
        report && !loading ? (
          <Button size="small" icon={<ReloadOutlined />} onClick={() => generate(true)}>
            重新生成
          </Button>
        ) : null
      }
    >
      {report ? (
        <div style={{ lineHeight: 1.8, fontSize: 14 }}>
          {renderMarkdown(report)}
        </div>
      ) : loading ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <Spin />
          <Typography.Text type="secondary" style={{ display: 'block', marginTop: 12 }}>
            DeepSeek AI 正在分析体态数据，请耐心等待（约 10-30 秒）...
          </Typography.Text>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <Typography.Text type="secondary">
            点击下方按钮，使用 DeepSeek AI 基于本次体态评估数据生成专业分析报告
          </Typography.Text>
          <br /><br />
          <Button
            type="primary"
            icon={<RobotOutlined />}
            onClick={() => generate(false)}
            size="large"
          >
            生成 AI 报告
          </Button>
        </div>
      )}
    </Card>
  );
}
