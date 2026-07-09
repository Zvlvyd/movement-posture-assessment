export const riskColor: Record<string, string> = {
  low: '#10b981',
  medium: '#f59e0b',
  high: '#ef4444',
  severe: '#dc2626',
  normal: '#10b981',
  mild: '#f59e0b',
  moderate: '#f97316',
}

export function getRiskColor(level: string | null | undefined): string {
  if (!level) return '#64748b'
  return riskColor[level.toLowerCase()] || '#64748b'
}

export function getRiskLabel(level: string | null | undefined): string {
  if (!level) return '-'
  const map: Record<string, string> = {
    low: '低风险', medium: '中风险', high: '高风险',
    severe: '严重', normal: '正常', mild: '轻度', moderate: '中度',
  }
  return map[level.toLowerCase()] || level
}
