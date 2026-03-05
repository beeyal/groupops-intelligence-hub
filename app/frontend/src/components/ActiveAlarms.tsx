import { useApi } from '../hooks/useApi'
import { Bell } from 'lucide-react'

interface AlarmAsset {
  asset_id: string
  asset_type: string
  zone: string
  latest_temp_c: number
  latest_voltage_kv: number
  latest_load_pct: number
  fault_count_30d: number
  health_score: number
}

function healthBadge(score: number) {
  if (score >= 70) return <span className="health-badge health-green">{score}</span>
  if (score >= 40) return <span className="health-badge health-amber">{score}</span>
  return <span className="health-badge health-red">{score}</span>
}

export default function ActiveAlarms() {
  const { data, loading, error } = useApi<AlarmAsset[]>('/active-alarms')

  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3><Bell size={14} style={{ marginRight: 8, verticalAlign: 'middle' }} />Active Alarms</h3>
        </div>
        <div className="loading-container">
          <div className="spinner" />
          Loading alarms...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <div className="card-header">
          <h3><Bell size={14} style={{ marginRight: 8, verticalAlign: 'middle' }} />Active Alarms</h3>
        </div>
        <div className="error-container">Failed to load: {error}</div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-header">
        <h3><Bell size={14} style={{ marginRight: 8, verticalAlign: 'middle' }} />Active Alarms</h3>
        <span className="count-badge">{data?.length ?? 0}</span>
      </div>
      <div className="card-body">
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Asset ID</th>
                <th>Type</th>
                <th>Zone</th>
                <th>Temp C</th>
                <th>Voltage kV</th>
                <th>Load %</th>
                <th>Faults (30d)</th>
                <th>Health</th>
              </tr>
            </thead>
            <tbody>
              {data?.map((row) => (
                <tr
                  key={row.asset_id}
                  className={row.health_score < 40 ? 'row-critical' : ''}
                >
                  <td style={{ fontWeight: 500 }}>{row.asset_id}</td>
                  <td>{row.asset_type}</td>
                  <td>{row.zone}</td>
                  <td>{row.latest_temp_c?.toFixed(1)}</td>
                  <td>{row.latest_voltage_kv?.toFixed(1)}</td>
                  <td>{row.latest_load_pct?.toFixed(1)}</td>
                  <td style={{ fontWeight: 600, color: row.fault_count_30d >= 3 ? '#ef4444' : 'inherit' }}>
                    {row.fault_count_30d}
                  </td>
                  <td>{healthBadge(row.health_score)}</td>
                </tr>
              ))}
              {(!data || data.length === 0) && (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', color: '#6B7280', padding: 24 }}>
                    No active alarms
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
