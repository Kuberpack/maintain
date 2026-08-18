import { useEffect, useState } from 'react'
import { getHealth } from './lib/api'

type ConnectionState = 'checking' | 'connected' | 'error'

function App() {
  const [connection, setConnection] = useState<ConnectionState>('checking')

  useEffect(() => {
    getHealth()
      .then(() => setConnection('connected'))
      .catch(() => setConnection('error'))
  }, [])

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-2xl font-semibold text-slate-900">
        Machine Maintenance &amp; Cleaning Tracker
      </h1>
      <p className="text-slate-600">Kuberpack — Sonipat plant</p>
      <div
        className="rounded-full px-4 py-1 text-sm font-medium"
        data-state={connection}
        style={{
          backgroundColor:
            connection === 'connected' ? '#dcfce7' : connection === 'error' ? '#fee2e2' : '#f1f5f9',
          color: connection === 'connected' ? '#166534' : connection === 'error' ? '#991b1b' : '#475569',
        }}
      >
        {connection === 'checking' && 'Checking backend connection…'}
        {connection === 'connected' && 'Backend connected'}
        {connection === 'error' && 'Backend unreachable'}
      </div>
    </div>
  )
}

export default App
