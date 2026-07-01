import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface Props {
  data: Array<{ date: string; count: number }>;
}

/**
 * 用户注册趋势折线图（最近30天）
 */
export default function RegistrationTrend({ data }: Props) {
  const chartData = data.map(d => ({
    ...d,
    date: d.date.slice(5), // "MM-DD"
  }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-hairline, #e8e8e8)" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: 'var(--color-text-muted, #999)' }}
          interval="preserveStartEnd"
        />
        <YAxis
          allowDecimals={false}
          tick={{ fontSize: 11, fill: 'var(--color-text-muted, #999)' }}
          width={32}
        />
        <Tooltip
          contentStyle={{
            borderRadius: 8,
            border: '1px solid var(--color-hairline, #e8e8e8)',
            fontFamily: 'var(--font-body)',
            fontSize: 13,
          }}
        />
        <Line
          type="monotone"
          dataKey="count"
          stroke="var(--color-primary, #1677ff)"
          strokeWidth={2}
          dot={{ r: 3 }}
          activeDot={{ r: 5 }}
          name="注册数"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
