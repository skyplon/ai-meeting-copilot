import React, { useState, useCallback } from 'react'
import InputPanel from './components/InputPanel.jsx'
import ProcessingView from './components/ProcessingView.jsx'
import ResultsView from './components/ResultsView.jsx'

const API = '/api'

export default function App() {
  const [view, setView] = useState('input')    // 'input' | 'processing' | 'results'
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleSubmit = useCallback(async ({ transcript, title, attendees, file }) => {
    setError(null)
    setView('processing')

    try {
      let res

      if (file) {
        // Audio upload path
        const form = new FormData()
        form.append('file', file)
        form.append('meeting_title', title)
        form.append('attendees', attendees)
        res = await fetch(`${API}/meetings/process-audio`, { method: 'POST', body: form })
      } else {
        // Text path
        res = await fetch(`${API}/meetings/process-text`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            transcript_text: transcript,
            meeting_title: title,
            attendees: attendees.split(',').map(e => e.trim()).filter(Boolean),
          }),
        })
      }

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Processing failed')
      }

      const data = await res.json()

      // If audio — poll until done
      if (file && data.status === 'queued') {
        const final = await pollUntilDone(data.meeting_id)
        setResult(final)
      } else {
        setResult(data)
      }

      setView('results')
    } catch (e) {
      setError(e.message)
      setView('input')
    }
  }, [])

  const pollUntilDone = async (meetingId) => {
    for (let i = 0; i < 60; i++) {
      await new Promise(r => setTimeout(r, 3000))
      const res = await fetch(`${API}/meetings/${meetingId}`)
      const data = await res.json()
      if (data.status === 'done') return data
      if (data.status === 'error') throw new Error('Graph processing failed')
    }
    throw new Error('Processing timed out after 3 minutes')
  }

  return (
    <div style={{ minHeight: '100vh' }}>
      {/* ── Header ── */}
      <header style={{
        background: 'var(--navy)', color: '#fff', padding: '0 32px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        height: 56, position: 'sticky', top: 0, zIndex: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 6, background: 'var(--blue)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14,
          }}>✦</div>
          <span style={{ fontWeight: 600, fontSize: 16 }}>AI Meeting Co-pilot</span>
          <span style={{ fontSize: 12, opacity: .5, marginLeft: 4 }}>MVP v1.0</span>
        </div>
        <div style={{ display: 'flex', gap: 16, fontSize: 13, opacity: .7 }}>
          <span>LangGraph</span>
          <span>·</span>
          <span>Claude API</span>
          <span>·</span>
          <span>Whisper</span>
        </div>
      </header>

      {/* ── Main ── */}
      <main style={{ maxWidth: 860, margin: '0 auto', padding: '32px 24px' }}>
        {error && (
          <div style={{
            background: 'var(--coral-light)', border: '1px solid #FCA5A5',
            borderRadius: 'var(--radius)', padding: '12px 16px', marginBottom: 20,
            color: 'var(--coral)', fontSize: 14, display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span>⚠</span> {error}
            <button onClick={() => setError(null)} style={{
              marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--coral)', fontSize: 16,
            }}>×</button>
          </div>
        )}

        {view === 'input'      && <InputPanel onSubmit={handleSubmit} />}
        {view === 'processing' && <ProcessingView />}
        {view === 'results'    && result && (
          <ResultsView result={result} onReset={() => { setResult(null); setView('input') }} />
        )}
      </main>
    </div>
  )
}
