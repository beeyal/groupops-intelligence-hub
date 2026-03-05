import { useApi } from '../hooks/useApi'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Activity } from 'lucide-react'

interface ZoneHealth {
  zone: string
  healthy: number
  warning: number
  critical: number
}

// Custom tooltip for the chart
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload) return null
  const total = payload.reduce((sum: number, p: any) => sum + (p.value || 0), 0)
  return (
    <div
      style={{
        background: '#283044',
        border: '1px solid #374258',
        borderRadius: '6px',
        padding: '10px 14px',
        fontSize: '13px',
        color: '#E8ECF4',
        boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 6 }}>{label} Zone</div>
      {payload.map((p: any) => (
        <div key={p.name} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 2 }}>
          <span style={{ color: p.color }}>{p.name}</span>
          <span style={{ fontWeight: 600 }}>{p.value}</span>
        </div>
      ))}
      <div style={{ borderTop: '1px solid #374258', marginTop: 6, paddingTop: 6, fontWeight: 600 }}>
        Total: {total}
      </div>
    </div>
  )
}

export default function HealthScorecard() {
  const { data, loading, error } = useApi<ZoneHealth[]>('/health-summary')

  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3><Activity size={14} style={{ marginRight: 8, verticalAlign: 'middle' }} />Asset Health Scorecard</h3>
        </div>
        <div className="loading-container">
          <div className="spinner" />
          Loading health data...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <div className="card-header">
          <h3><Activity size={14} style={{ marginRight: 8, verticalAlign: 'middle' }} />Asset Health Scorecard</h3>
        </div>
        <div className="error-container">Failed to load: {error}</div>
      </div>
    )
  }

  const totalAssets = data?.reduce((sum, z) => sum + z.healthy + z.warning + z.critical, 0) ?? 0

  return (
    <div className="card">
      <div className="card-header">
        <h3><Activity size={14} style={{ marginRight: 8, verticalAlign: 'middle' }} />Asset Health Scorecard</h3>
        <span className="count-badge">{totalAssets} assets</span>
      </div>
      <div className="card-body with-padding">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data || []} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374258" />
            <XAxis dataKey="zone" tick={{ fill: '#9BA3B5', fontSize: 12 }} axisLine={{ stroke: '#374258' }} />
            <YAxis tick={{ fill: '#9BA3B5', fontSize: 12 }} axisLine={{ stroke: '#374258' }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 12, color: '#9BA3B5' }}
              iconType="circle"
              iconSize={8}
            />
            <Bar dataKey="healthy" name="Healthy" fill="#22c55e" stackId="stack" radius={[0, 0, 0, 0]} />
            <Bar dataKey="warning" name="Warning" fill="#f59e0b" stackId="stack" radius={[0, 0, 0, 0]} />
            <Bar dataKey="critical" name="Critical" fill="#ef4444" stackId="stack" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
