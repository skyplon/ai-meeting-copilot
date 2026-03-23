import React, { useState } from 'react'

const PRIORITY_META = {
  high:   { color: 'var(--coral)',  bg: 'var(--coral-light)',  label: 'HIGH' },
  medium: { color: 'var(--amber)',  bg: 'var(--amber-light)',  label: 'MED' },
  low:    { color: 'var(--green)',  bg: 'var(--green-light)',  label: 'LOW' },
}

const TOOL_META = {
  jira:     { color: '#0052CC', bg: '#DEEBFF', label: 'Jira' },
  asana:    { color: '#F06A6A', bg: '#FFF3F3', label: 'Asana' },
  linear:   { color: '#5E6AD2', bg: '#EBEFFE', label: 'Linear' },
  notion:   { color: '#374151', bg: '#F3F4F6', label: 'Notion' },
  calendar: { color: 'var(--green)', bg: 'var(--green-light)', label: 'Calendar' },
  unrouted: { color: 'var(--gray-500)', bg: 'var(--gray-100)', label: '—' },
}

const MOOD_META = {
  productive: { icon: '✅', label: 'Productive', color: 'var(--green)' },
  aligned:    { icon: '🤝', label: 'Aligned',    color: 'var(--teal)' },
  tense:      { icon: '⚡', label: 'Tense',       color: 'var(--coral)' },
  unclear:    { icon: '❓', label: 'Unclear',     color: 'var(--amber)' },
}

export default function ResultsView({ result, onReset }) {
  const [activeTab, setActiveTab] = useState('summary')
  const [copied, setCopied] = useState(false)

  const { summary, action_items = [], routed_tasks = [],
          follow_up_event, recurring_issues = [], transcript = [],
          meeting_id, errors = [] } = result

  const mood = summary?.mood ? MOOD_META[summary.mood] || MOOD_META.productive : MOOD_META.productive

  const copySlack = async () => {
    try {
      const res = await fetch(`/api/meetings/${meeting_id}/slack`)
      const { markdown } = await res.json()
      await navigator.clipboard.writeText(markdown)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const TABS = [
    { id: 'summary',    label: `Summary`,                  count: null },
    { id: 'actions',    label: `Action items`,             count: routed_tasks.length },
    { id: 'transcript', label: `Transcript`,               count: transcript.length },
    { id: 'email',      label: `Email draft`,              count: null },
  ]

  return (
    <div>
      {/* ── Top bar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 20, flexWrap: 'wrap', gap: 10,
      }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--navy)', marginBottom: 3 }}>
            {result.meeting_title || 'Meeting Results'}
          </h2>
          <span style={{ fontSize: 13, color: 'var(--gray-500)' }}>
            ID: <code style={{ fontFamily: 'monospace', fontSize: 12 }}>{meeting_id?.slice(0, 8)}…</code>
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={copySlack} style={outlineBtn}>
            {copied ? '✓ Copied' : '📋 Copy Slack brief'}
          </button>
          <button onClick={onReset} style={outlineBtn}>
            ← New meeting
          </button>
        </div>
      </div>

      {/* ── Stat cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 20 }}>
        {[
          { label: 'Action items', value: action_items.length, icon: '✅', color: 'var(--blue)', bg: 'var(--blue-light)' },
          { label: 'Decisions made', value: summary?.decisions?.length ?? 0, icon: '🎯', color: 'var(--teal)', bg: 'var(--teal-light)' },
          { label: 'Open blockers', value: summary?.blockers?.length ?? 0, icon: '⚠', color: 'var(--coral)', bg: 'var(--coral-light)' },
          { label: 'Meeting mood', value: mood.label, icon: mood.icon, color: mood.color, bg: 'var(--gray-50)' },
        ].map(card => (
          <div key={card.label} style={{
            background: '#fff', borderRadius: 'var(--radius)', border: '1px solid var(--gray-200)',
            padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12,
          }}>
            <div style={{
              width: 38, height: 38, borderRadius: 8, background: card.bg,
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0,
            }}>{card.icon}</div>
            <div>
              <div style={{ fontSize: 20, fontWeight: 700, color: card.color, lineHeight: 1 }}>{card.value}</div>
              <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 2 }}>{card.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Recurring issues banner ── */}
      {recurring_issues.length > 0 && (
        <div style={{
          background: 'var(--amber-light)', border: '1px solid #FCD34D',
          borderLeft: '4px solid var(--amber)', borderRadius: 'var(--radius)',
          padding: '12px 16px', marginBottom: 20,
        }}>
          <p style={{ fontWeight: 600, color: 'var(--amber)', fontSize: 14, marginBottom: 6 }}>
            ⚠ {recurring_issues.length} recurring issue{recurring_issues.length > 1 ? 's' : ''} detected
          </p>
          {recurring_issues.map((r, i) => (
            <p key={i} style={{ fontSize: 13, color: 'var(--gray-700)', marginTop: 4 }}>• {r}</p>
          ))}
        </div>
      )}

      {/* ── Follow-up event banner ── */}
      {follow_up_event && (
        <div style={{
          background: 'var(--blue-light)', border: '1px solid #93C5FD',
          borderLeft: '4px solid var(--blue)', borderRadius: 'var(--radius)',
          padding: '12px 16px', marginBottom: 20, display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', flexWrap: 'wrap', gap: 10,
        }}>
          <div>
            <p style={{ fontWeight: 600, color: 'var(--blue)', fontSize: 14, marginBottom: 3 }}>
              📅 Follow-up meeting scheduled
            </p>
            <p style={{ fontSize: 13, color: 'var(--slate)' }}>
              <strong>{follow_up_event.title}</strong>
              {follow_up_event.start_datetime && (
                <span style={{ marginLeft: 8, color: 'var(--gray-500)' }}>
                  {follow_up_event.start_datetime.slice(0, 16).replace('T', ' at ')}
                </span>
              )}
            </p>
          </div>
          {follow_up_event.event_url && (
            <a href={follow_up_event.event_url} target="_blank" rel="noopener noreferrer"
              style={{
                background: 'var(--blue)', color: '#fff', padding: '8px 16px',
                borderRadius: 'var(--radius)', fontSize: 13, fontWeight: 500, textDecoration: 'none',
              }}>
              Add to calendar ↗
            </a>
          )}
        </div>
      )}

      {/* ── Errors ── */}
      {errors.length > 0 && (
        <div style={{
          background: 'var(--coral-light)', borderLeft: '4px solid var(--coral)',
          borderRadius: 'var(--radius)', padding: '12px 16px', marginBottom: 20,
        }}>
          <p style={{ fontWeight: 600, color: 'var(--coral)', marginBottom: 6, fontSize: 14 }}>
            {errors.length} agent error{errors.length > 1 ? 's' : ''} (non-fatal)
          </p>
          {errors.map((e, i) => (
            <p key={i} style={{ fontSize: 12, color: 'var(--gray-700)', fontFamily: 'monospace', marginTop: 4 }}>{e}</p>
          ))}
        </div>
      )}

      {/* ── Tabs ── */}
      <div style={{
        background: '#fff', borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--gray-200)', overflow: 'hidden',
      }}>
        <div style={{
          display: 'flex', borderBottom: '1px solid var(--gray-200)',
          background: 'var(--gray-50)', padding: '0 4px',
        }}>
          {TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
              padding: '13px 18px', border: 'none', background: 'none', cursor: 'pointer',
              fontSize: 14, fontWeight: activeTab === tab.id ? 600 : 400,
              color: activeTab === tab.id ? 'var(--navy)' : 'var(--gray-500)',
              borderBottom: activeTab === tab.id ? '2px solid var(--navy)' : '2px solid transparent',
              marginBottom: -1, transition: 'color .15s',
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              {tab.label}
              {tab.count !== null && (
                <span style={{
                  background: activeTab === tab.id ? 'var(--navy)' : 'var(--gray-200)',
                  color: activeTab === tab.id ? '#fff' : 'var(--gray-500)',
                  fontSize: 11, padding: '1px 6px', borderRadius: 99, fontWeight: 600,
                }}>{tab.count}</span>
              )}
            </button>
          ))}
        </div>

        <div style={{ padding: 24 }}>
          {activeTab === 'summary'    && <SummaryTab summary={summary} />}
          {activeTab === 'actions'    && <ActionsTab tasks={routed_tasks} />}
          {activeTab === 'transcript' && <TranscriptTab turns={transcript} />}
          {activeTab === 'email'      && <EmailTab meetingId={meeting_id} />}
        </div>
      </div>
    </div>
  )
}

// ── Tab: Summary ──────────────────────────────────────────────────────────────
function SummaryTab({ summary }) {
  if (!summary) return <p style={{ color: 'var(--gray-500)' }}>Summary not available.</p>
  return (
    <div>
      <div style={{
        background: 'var(--gray-50)', borderLeft: '4px solid var(--navy)',
        borderRadius: '0 var(--radius) var(--radius) 0', padding: '14px 18px', marginBottom: 24,
      }}>
        <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 6 }}>Meeting goal</p>
        <p style={{ fontSize: 16, color: 'var(--navy)', fontWeight: 500 }}>{summary.goal}</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <Section title="Decisions made" icon="🎯" items={summary.decisions} emptyMsg="No firm decisions recorded" />
        <Section title="Open blockers" icon="⚠" items={summary.blockers} emptyMsg="No blockers — great meeting!" accentColor="var(--coral)" />
      </div>

      {summary.key_quotes?.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--slate)', marginBottom: 12 }}>Key quotes</p>
          {summary.key_quotes.map((q, i) => (
            <div key={i} style={{
              padding: '12px 16px', background: 'var(--gray-50)', borderRadius: 'var(--radius)',
              borderLeft: '3px solid var(--blue)', marginBottom: 8,
            }}>
              <p style={{ fontSize: 14, fontStyle: 'italic', color: 'var(--gray-700)', marginBottom: 4 }}>"{q.quote}"</p>
              <p style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 500 }}>— {q.speaker}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Section({ title, icon, items = [], emptyMsg, accentColor = 'var(--teal)' }) {
  return (
    <div>
      <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--slate)', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
        <span>{icon}</span> {title}
      </p>
      {items.length === 0 ? (
        <p style={{ fontSize: 13, color: 'var(--gray-500)', fontStyle: 'italic' }}>{emptyMsg}</p>
      ) : items.map((item, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'flex-start', gap: 8, padding: '7px 0',
          borderBottom: i < items.length - 1 ? '1px solid var(--gray-200)' : 'none',
        }}>
          <span style={{ color: accentColor, marginTop: 2, fontSize: 12 }}>•</span>
          <span style={{ fontSize: 14, color: 'var(--gray-700)', lineHeight: 1.5 }}>{item}</span>
        </div>
      ))}
    </div>
  )
}

// ── Tab: Actions ──────────────────────────────────────────────────────────────
function ActionsTab({ tasks = [] }) {
  if (tasks.length === 0) return <p style={{ color: 'var(--gray-500)' }}>No action items extracted.</p>
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <p style={{ fontSize: 13, color: 'var(--gray-500)' }}>
          {tasks.length} tasks routed to external tools automatically
        </p>
        <div style={{ display: 'flex', gap: 8, fontSize: 12, color: 'var(--gray-500)' }}>
          {['jira','asana','linear','notion','calendar'].map(tool => {
            const n = tasks.filter(t => t.tool === tool).length
            if (!n) return null
            const meta = TOOL_META[tool]
            return (
              <span key={tool} style={{
                background: meta.bg, color: meta.color, padding: '3px 8px', borderRadius: 99, fontWeight: 500
              }}>{meta.label} {n}</span>
            )
          })}
        </div>
      </div>

      {tasks.map((task, i) => {
        const ai = task.action_item
        const pm = PRIORITY_META[ai?.priority] || PRIORITY_META.medium
        const tm = TOOL_META[task.tool] || TOOL_META.unrouted
        return (
          <div key={i} style={{
            display: 'flex', alignItems: 'flex-start', gap: 14, padding: '14px 0',
            borderBottom: i < tasks.length - 1 ? '1px solid var(--gray-200)' : 'none',
          }}>
            {/* Priority dot */}
            <div style={{
              width: 8, height: 8, borderRadius: '50%', background: pm.color,
              marginTop: 6, flexShrink: 0,
            }} />
            {/* Content */}
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
                <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--navy)' }}>{ai?.title}</span>
                <span style={{
                  background: pm.bg, color: pm.color, fontSize: 10, fontWeight: 700,
                  padding: '2px 6px', borderRadius: 4,
                }}>{pm.label}</span>
              </div>
              <div style={{ display: 'flex', gap: 12, fontSize: 12, color: 'var(--gray-500)', flexWrap: 'wrap' }}>
                {ai?.owner_name && <span>👤 {ai.owner_name}{ai.owner_email ? ` (${ai.owner_email})` : ''}</span>}
                {ai?.due_date   && <span>📅 {ai.due_date}</span>}
                {ai?.source_quote && (
                  <span style={{ fontStyle: 'italic', color: 'var(--gray-500)' }}>
                    "{ai.source_quote.slice(0, 80)}{ai.source_quote.length > 80 ? '…' : ''}"
                  </span>
                )}
              </div>
            </div>
            {/* Tool badge + link */}
            <div style={{ flexShrink: 0, textAlign: 'right' }}>
              {task.url ? (
                <a href={task.url} target="_blank" rel="noopener noreferrer" style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  background: tm.bg, color: tm.color, padding: '5px 10px',
                  borderRadius: 6, fontSize: 12, fontWeight: 600, textDecoration: 'none',
                }}>
                  {tm.label} ↗
                </a>
              ) : (
                <span style={{
                  background: tm.bg, color: tm.color, padding: '5px 10px',
                  borderRadius: 6, fontSize: 12, fontWeight: 600,
                }}>{tm.label}</span>
              )}
              {task.external_id && (
                <p style={{ fontSize: 11, color: 'var(--gray-500)', marginTop: 3 }}>#{task.external_id?.slice(0, 10)}</p>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Tab: Transcript ───────────────────────────────────────────────────────────
const SPEAKER_COLORS = ['var(--blue)', 'var(--teal)', 'var(--purple)', 'var(--amber)', 'var(--coral)']

function TranscriptTab({ turns = [] }) {
  const speakers = [...new Set(turns.map(t => t.speaker))]
  const colorMap = Object.fromEntries(speakers.map((s, i) => [s, SPEAKER_COLORS[i % SPEAKER_COLORS.length]]))

  if (turns.length === 0) return <p style={{ color: 'var(--gray-500)' }}>Transcript not available.</p>

  return (
    <div>
      {/* Speaker legend */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {speakers.map(s => (
          <span key={s} style={{
            fontSize: 12, padding: '3px 10px', borderRadius: 99, fontWeight: 500,
            background: 'var(--gray-100)', color: colorMap[s], border: `1px solid ${colorMap[s]}`,
          }}>{s}</span>
        ))}
      </div>

      <div style={{ maxHeight: 420, overflowY: 'auto', paddingRight: 4 }}>
        {turns.map((turn, i) => {
          const min = Math.floor(turn.start_ms / 60000)
          const sec = Math.floor((turn.start_ms % 60000) / 1000)
          return (
            <div key={i} style={{
              display: 'flex', gap: 12, padding: '8px 0',
              borderBottom: i < turns.length - 1 ? '1px solid var(--gray-200)' : 'none',
            }}>
              <span style={{ fontSize: 11, color: 'var(--gray-500)', fontFamily: 'monospace', minWidth: 38, paddingTop: 2 }}>
                {String(min).padStart(2,'0')}:{String(sec).padStart(2,'0')}
              </span>
              <span style={{ fontSize: 12, fontWeight: 600, color: colorMap[turn.speaker], minWidth: 90, paddingTop: 2 }}>
                {turn.speaker}
              </span>
              <span style={{ fontSize: 14, color: 'var(--gray-700)', lineHeight: 1.5, flex: 1 }}>
                {turn.text}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Tab: Email draft ──────────────────────────────────────────────────────────
function EmailTab({ meetingId }) {
  const [html, setHtml] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/meetings/${meetingId}/email`)
      const { html: emailHtml } = await res.json()
      setHtml(emailHtml)
    } catch {
      setHtml('<p>Could not load email draft.</p>')
    }
    setLoading(false)
  }

  if (!html) return (
    <div style={{ textAlign: 'center', padding: '32px 0' }}>
      <p style={{ color: 'var(--gray-500)', marginBottom: 16 }}>
        HTML email draft ready — formatted summary with action item table, 
        decisions, blockers, and follow-up calendar link.
      </p>
      <button onClick={load} disabled={loading} style={{
        background: 'var(--navy)', color: '#fff', border: 'none',
        borderRadius: 'var(--radius)', padding: '10px 24px', fontSize: 14, fontWeight: 500,
        cursor: 'pointer',
      }}>
        {loading ? 'Loading…' : 'Preview email draft'}
      </button>
    </div>
  )

  return (
    <div>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16,
      }}>
        <p style={{ fontSize: 13, color: 'var(--gray-500)' }}>
          HTML email — ready to paste into Gmail or send via Gmail MCP
        </p>
        <button onClick={() => {
          navigator.clipboard.writeText(html)
        }} style={outlineBtn}>Copy HTML</button>
      </div>
      <div style={{
        border: '1px solid var(--gray-200)', borderRadius: 'var(--radius)',
        overflow: 'auto', maxHeight: 500, background: '#fff',
      }}>
        <iframe
          srcDoc={html}
          style={{ width: '100%', minHeight: 500, border: 'none', display: 'block' }}
          title="Email preview"
          sandbox="allow-same-origin"
        />
      </div>
    </div>
  )
}

// ── Shared button style ────────────────────────────────────────────────────────
const outlineBtn = {
  background: 'none', border: '1px solid var(--gray-200)', color: 'var(--slate)',
  borderRadius: 'var(--radius)', padding: '7px 14px', fontSize: 13, fontWeight: 500,
  cursor: 'pointer',
}
