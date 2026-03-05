import { useApi } from '../hooks/useApi'
import { Wrench } from 'lucide-react'

interface WorkOrder {
  wo_number: string
  asset_id: string
  asset_type: string
  zone: string
  wo_type: string
  status: string
  created_date: string
  cost_aud: number
  health_score: number
}

function healthBadge(score: number) {
  if (score >= 70) return <span className="health-badge health-green">{score}</span>
  if (score >= 40) return <span className="health-badge health-amber">{score}</span>
  return <span className="health-badge health-red">{score}</span>
}

function statusBadge(status: string) {
  const cls = status === 'Open' ? 'status-open' : 'status-inprogress'
  return <span className={`status-badge ${cls}`}>{status}</span>
}

function formatCurrency(amount: number) {
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

function formatDate(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleDateString('en-AU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}

export default function MaintenanceQueue() {
  const { data, loading, error } = useApi<WorkOrder[]>('/maintenance-queue')

  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3><Wrench size={14} style={{ marginRight: 8, verticalAlign: 'middle' }} />Maintenance Queue</h3>
        </div>
        <div className="loading-container">
          <div className="spinner" />
          Loading work orders...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <div className="card-header">
          <h3><Wrench size={14} style={{ marginRight: 8, verticalAlign: 'middle' }} />Maintenance Queue</h3>
        </div>
        <div className="error-container">Failed to load: {error}</div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-header">
        <h3><Wrench size={14} style={{ marginRight: 8, verticalAlign: 'middle' }} />Maintenance Queue</h3>
        <span className="count-badge">{data?.length ?? 0} open</span>
      </div>
      <div className="card-body">
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>WO #</th>
                <th>Asset</th>
                <th>Zone</th>
                <th>WO Type</th>
                <th>Status</th>
                <th>Created</th>
                <th>Cost AUD</th>
                <th>Health</th>
              </tr>
            </thead>
            <tbody>
              {data?.map((row) => (
                <tr key={row.wo_number}>
                  <td style={{ fontWeight: 500, fontFamily: 'monospace', fontSize: 12 }}>{row.wo_number}</td>
                  <td>{row.asset_id}</td>
                  <td>{row.zone}</td>
                  <td>{row.wo_type}</td>
                  <td>{statusBadge(row.status)}</td>
                  <td>{formatDate(row.created_date)}</td>
                  <td style={{ fontFamily: 'monospace' }}>{formatCurrency(row.cost_aud)}</td>
                  <td>{healthBadge(row.health_score)}</td>
                </tr>
              ))}
              {(!data || data.length === 0) && (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', color: '#6B7280', padding: 24 }}>
                    No open work orders
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
