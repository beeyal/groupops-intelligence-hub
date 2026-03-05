import { useApi } from '../hooks/useApi'
import { AlertTriangle } from 'lucide-react'

interface GapAsset {
  asset_id: string
  asset_type: string
  zone: string
  fault_count_30d: number
  health_score: number
  latest_temp_c: number
  latest_voltage_kv: number
  alarm_active: boolean
}

function healthBadge(score: number) {
  if (score >= 70) return <span className="health-badge health-green">{score}</span>
  if (score >= 40) return <span className="health-badge health-amber">{score}</span>
  return <span className="health-badge health-red">{score}</span>
}

export default function FaultWoGap() {
  const { data, loading, error } = useApi<GapAsset[]>('/fault-wo-gap')

  if (loading) {
    return (
      <div className="card gap-alert">
        <div className="card-header">
          <h3><AlertTriangle size={14} style={{ marginRight: 8, verticalAlign: 'middle', color: '#f59e0b' }} />Fault vs WO Gap</h3>
        </div>
        <div className="loading-container">
          <div className="spinner" />
          Analyzing gap assets...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card gap-alert">
        <div className="card-header">
          <h3><AlertTriangle size={14} style={{ marginRight: 8, verticalAlign: 'middle', color: '#f59e0b' }} />Fault vs WO Gap</h3>
        </div>
        <div className="error-container">Failed to load: {error}</div>
      </div>
    )
  }

  const count = data?.length ?? 0

  return (
    <div className="card gap-alert">
      {/* Alert banner */}
      <div className="gap-banner">
        <AlertTriangle size={18} />
        {count} assets have 3+ faults with no open work order -- review required
      </div>

      <div className="card-body">
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Asset ID</th>
                <th>Type</th>
                <th>Zone</th>
                <th>Faults (30d)</th>
                <th>Health</th>
                <th>Temp C</th>
                <th>Voltage kV</th>
                <th>Alarm</th>
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
                  <td style={{ fontWeight: 700, color: '#ef4444' }}>{row.fault_count_30d}</td>
                  <td>{healthBadge(row.health_score)}</td>
                  <td>{row.latest_temp_c?.toFixed(1)}</td>
                  <td>{row.latest_voltage_kv?.toFixed(1)}</td>
                  <td>
                    {row.alarm_active ? (
                      <span style={{ color: '#ef4444', fontWeight: 600 }}>ACTIVE</span>
                    ) : (
                      <span style={{ color: '#6B7280' }}>--</span>
                    )}
                  </td>
                </tr>
              ))}
              {(!data || data.length === 0) && (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', color: '#22c55e', padding: 24 }}>
                    All assets with faults have open work orders
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
