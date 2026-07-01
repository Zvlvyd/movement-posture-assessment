/**
 * ScoreBar — 迷你评分条组件
 * 用于教练端和学员详情页中展示 FMS 各项评分
 */
interface Props {
  label: string;
  value: number;
  max?: number;
}

export default function ScoreBar({ label, value, max = 100 }: Props) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100);
  const color = pct >= 80 ? '#52c41a' : pct >= 60 ? '#1890ff' : pct >= 40 ? '#faad14' : '#f5222d';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, width: 48 }}>
      <span style={{ fontSize: 11, color: '#888', width: 22, textAlign: 'right' }}>{label}</span>
      <div style={{ flex: 1, height: 6, background: '#f0f0f0', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3, transition: 'width 0.3s' }} />
      </div>
    </div>
  );
}
