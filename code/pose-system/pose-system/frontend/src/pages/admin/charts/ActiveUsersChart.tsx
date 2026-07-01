import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface Props {
  dauTrend: Array<{ date: string; count: number }>;
  dau: number;
  wau: number;
  mau: number;
}

/**
 * 日活/周活/月活柱状图 + KPI 指标
 */
export default function ActiveUsersChart({ dauTrend, dau, wau, mau }: Props) {
  const chartData = dauTrend.map(d => ({
    ...d,
    date: d.date.slice(5), // "MM-DD"
  }));

  return (
    <div>
      <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
        <div style={{ textAlign: 'center', flex: 1 }}>
          <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--color-primary)' }}>{dau}</div>
          <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>DAU（今日）</div>
        </div>
        <div style={{ textAlign: 'center', flex: 1 }}>
          <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--color-success, #52c41a)' }}>{wau}</div>
          <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>WAU（近7天）</div>
        </div>
        <div style={{ textAlign: 'center', flex: 1 }}>
          <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--color-warning, #faad14)' }}>{mau}</div>
          <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>MAU（近30天）</div>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-hairline, #e8e8e8)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: 'var(--color-text-muted, #999)' }}
            interval="preserveStartEnd"
          />
          <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={32} />
          <Tooltip
            contentStyle={{
              borderRadius: 8,
              border: '1px solid var(--color-hairline, #e8e8e8)',
            }}
          />
          <Legend />
          <Bar dataKey="count" fill="var(--color-primary, #1677ff)" name="活跃用户" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
