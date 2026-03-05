import { useState, useEffect } from 'react'
import './App.css'
import HealthScorecard from './components/HealthScorecard'
import ActiveAlarms from './components/ActiveAlarms'
import MaintenanceQueue from './components/MaintenanceQueue'
import FaultWoGap from './components/FaultWoGap'
import ChatPanel from './components/ChatPanel'

function App() {
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 60000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="app-layout">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <h1>GroupOps Intelligence Hub</h1>
          <span className="brand">Ausnet</span>
        </div>
        <div className="header-right">
          <span className="header-timestamp">
            {now.toLocaleString('en-AU', {
              weekday: 'short',
              day: 'numeric',
              month: 'short',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
          <div className="status-dot" title="Live" />
        </div>
      </header>

      {/* Main content */}
      <main className="app-main">
        {/* Left: Dashboard panels */}
        <div className="panels-container">
          <HealthScorecard />
          <ActiveAlarms />
          <MaintenanceQueue />
          <FaultWoGap />
        </div>

        {/* Right: AI Chat */}
        <ChatPanel />
      </main>
    </div>
  )
}

export default App
