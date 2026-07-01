import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

const COLORS: Record<string, string> = {
  admin: '#f5222d',
  coach: '#faad14',
  trainee: '#1677ff',
};

const LABELS: Record<string, string> = {
  admin: '管理员',
  coach: '教练',
  trainee: '学员',
};

interface Props {
  data: Record<string, number>;
}

/**
 * 角色分布饼图
 */
export default function RoleDistribution({ data }: Props) {
  const chartData = Object.entries(data)
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({
      name: LABELS[key] || key,
      value,
      color: COLORS[key] || '#999',
    }));

  if (chartData.length === 0) {
    return <div style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: 60 }}>暂无数据</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          outerRadius={90}
          innerRadius={40}
          paddingAngle={3}
          dataKey="value"
          nameKey="name"
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
        >
          {chartData.map((entry, index) => (
            <Cell key={index} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            borderRadius: 8,
            border: '1px solid var(--color-hairline, #e8e8e8)',
          }}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
