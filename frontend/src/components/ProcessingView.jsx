import React, { useState, useEffect } from 'react'

const STAGES = [
  {
    id: 'transcription',
    label: 'Transcribing',
    sub: 'Whisper large-v3 · speaker diarization',
    icon: '🎙',
    color: 'var(--blue)',
    bg: 'var(--blue-light)',
    ms: 2400,
  },
  {
    id: 'summarizing',
    label: 'Summarizing',
    sub: 'claude-3-5-haiku · structured output via Instructor',
    icon: '📋',
    color: 'var(--teal)',
    bg: 'var(--teal-light)',
    ms: 3200,
  },
  {
    id: 'extracting',
    label: 'Extracting action items',
    sub: 'Claude tool use · agentic extraction loop',
    icon: '✅',
    color: 'var(--purple)',
    bg: 'var(--purple-light)',
    ms: 3800,
  },
  {
    id: 'routing',
    label: 'Routing tasks',
    sub: 'claude-haiku classifier · Jira / Asana / Linear routing',
    icon: '🔀',
    color: 'var(--amber)',
    bg: 'var(--amber-light)',
    ms: 2800,
  },
  {
    id: 'scheduling',
    label: 'Scheduling follow-up',
    sub: 'Google Calendar MCP · finding shared availability',
    icon: '📅',
    color: 'var(--coral)',
    bg: 'var(--coral-light)',
    ms: 2000,
  },
  {
    id: 'distributing',
    label: 'Distributing summary',
    sub: 'Gmail MCP · Slack brief · HTML email',
    icon: '📤',
    color: 'var(--green)',
    bg: 'var(--green-light)',
    ms: 1600,
  },
]

export default function ProcessingView() {
  const [activeIdx, setActiveIdx] = useState(0)
  const [completed, setCompleted] = useState([])
  const [dots, setDots] = useState('.')

  useEffect(() => {
    let idx = 0
    const advance = () => {
      if (idx >= STAGES.length) return
      const stage = STAGES[idx]
      const timer = setTimeout(() => {
        setCompleted(prev => [...prev, stage.id])
        idx++
        setActiveIdx(idx)
        advance()
      }, stage.ms)
      return timer
    }
    const t = advance()
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    const t = setInterval(() => setDots(d => d.length >= 3 ? '.' : d + '.'), 500)
    return () => clearInterval(t)
  }, [])

  const currentStage = STAGES[Math.min(activeIdx, STAGES.length - 1)]

  return (
    <div style={{ maxWidth: 560, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <div style={{
          width: 56, height: 56, borderRadius: '50%', margin: '0 auto 16px',
          background: currentStage.bg, display: 'flex', alignItems: 'center',
          justifyContent: 'center', fontSize: 24,
          animation: 'pulse 1.5s ease-in-out infinite',
        }}>
          {currentStage.icon}
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 600, color: 'var(--navy)', marginBottom: 6 }}>
          {activeIdx < STAGES.length ? `${currentStage.label}${dots}` : 'Finalizing results…'}
        </h2>
        <p style={{ fontSize: 13, color: 'var(--gray-500)' }}>
          {activeIdx < STAGES.length ? currentStage.sub : 'Wrapping up the agent graph'}
        </p>
      </div>

      {/* Stage list */}
      <div style={{
        background: '#fff', borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--gray-200)', overflow: 'hidden',
      }}>
        {STAGES.map((stage, i) => {
          const isDone = completed.includes(stage.id)
          const isActive = i === activeIdx && !isDone
          const isPending = i > activeIdx

          return (
            <div key={stage.id} style={{
              display: 'flex', alignItems: 'center', gap: 14, padding: '14px 20px',
              borderBottom: i < STAGES.length - 1 ? '1px solid var(--gray-200)' : 'none',
              background: isActive ? stage.bg : '#fff',
              transition: 'background .3s',
              opacity: isPending ? 0.45 : 1,
            }}>
              {/* Icon / status */}
              <div style={{
                width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
                background: isDone ? 'var(--green-light)' : isActive ? stage.bg : 'var(--gray-100)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 16, border: isActive ? `2px solid ${stage.color}` : '2px solid transparent',
                transition: 'all .3s',
              }}>
                {isDone ? '✓' : stage.icon}
              </div>

              {/* Label */}
              <div style={{ flex: 1 }}>
                <div style={{
                  fontSize: 14, fontWeight: 500,
                  color: isDone ? 'var(--green)' : isActive ? stage.color : 'var(--gray-700)',
                }}>
                  {stage.label}
                </div>
                <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 2 }}>
                  {stage.sub}
                </div>
              </div>

              {/* Status badge */}
              <div style={{
                fontSize: 11, fontWeight: 600, padding: '3px 8px', borderRadius: 99,
                background: isDone ? 'var(--green-light)' : isActive ? stage.bg : 'transparent',
                color: isDone ? 'var(--green)' : isActive ? stage.color : 'var(--gray-500)',
                border: isPending ? '1px solid var(--gray-200)' : 'none',
              }}>
                {isDone ? 'Done' : isActive ? 'Running' : 'Pending'}
              </div>
            </div>
          )
        })}
      </div>

      {/* LangGraph callout */}
      <div style={{
        marginTop: 20, padding: '12px 16px', borderRadius: 'var(--radius)',
        background: 'var(--gray-50)', border: '1px solid var(--gray-200)',
        fontSize: 12, color: 'var(--gray-500)', textAlign: 'center',
      }}>
        Orchestrated by <strong style={{ color: 'var(--navy)' }}>LangGraph</strong> · 
        7-node stateful graph · Router + Memory running in parallel
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.08); }
        }
      `}</style>
    </div>
  )
}
