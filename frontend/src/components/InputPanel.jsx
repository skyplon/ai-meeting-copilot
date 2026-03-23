import React, { useState, useRef } from 'react'

const DEMO_TRANSCRIPT = `Alice Chen: Okay everyone, let's get started. The goal today is to align on the Q2 roadmap and unblock the API integration work.

Bob Martinez: Before we jump in — the authentication bug is still causing failures in production. We've had three customer complaints since yesterday. I think this needs to be our top priority today.

Alice Chen: Agreed, that's critical. Bob, can you own the fix and get it deployed by Thursday?

Bob Martinez: Yes, I'll handle it. I'll need Carlos to review the PR though — I estimate about two days of work.

Carlos Ruiz: Sure, I can do a review by Wednesday afternoon. Just tag me in the PR.

Alice Chen: Great. Now on the Q2 roadmap — we've decided to push the analytics dashboard to Q3 and focus on the mobile app rewrite instead. That was confirmed with leadership last week.

Bob Martinez: Makes sense. Who's leading the mobile rewrite?

Alice Chen: That'll be Carlos. Carlos, can you put together a technical spec by end of next week?

Carlos Ruiz: I can do that. I'll also need design mockups from the design team before I finalize the spec.

Alice Chen: Right — I'll reach out to Sarah on the design team today and ask her to prioritize mobile mockups. Target is to have mockups ready by Friday.

Bob Martinez: One thing I want to flag — we still don't have a decision on which third-party payment provider to use. That's been blocking the checkout flow work for two weeks now.

Alice Chen: That's a real blocker. I need to schedule a decision meeting with the CFO and product team to resolve this. Let me set that up for this week.

Carlos Ruiz: Also, the staging environment has been down intermittently. I've raised it twice before and it's still not resolved. DevOps needs to investigate.

Alice Chen: Okay, let's make sure that gets escalated. Bob, can you file a P1 ticket for the staging environment issue and ping the DevOps lead?

Bob Martinez: Will do. I'll file it right after this meeting.

Alice Chen: Alright, let's wrap up. We have the auth bug fix, the mobile spec, design mockups, the payment provider decision meeting, and the staging environment ticket. Does everyone know what they're doing?

Carlos Ruiz: Yep, clear on my end.

Bob Martinez: Same here.

Alice Chen: Great. Let's sync again on Friday to check in on the auth bug and the payment provider situation.`

export default function InputPanel({ onSubmit }) {
  const [mode, setMode] = useState('text')       // 'text' | 'audio'
  const [transcript, setTranscript] = useState('')
  const [title, setTitle] = useState('')
  const [attendees, setAttendees] = useState('')
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const fileRef = useRef(null)

  const valid = mode === 'text' ? transcript.trim().length > 20 : !!file

  const handleSubmit = async () => {
    if (!valid || loading) return
    setLoading(true)
    await onSubmit({
      transcript: mode === 'text' ? transcript : null,
      title: title || 'Untitled Meeting',
      attendees,
      file: mode === 'audio' ? file : null,
    })
    setLoading(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  return (
    <div>
      {/* Hero */}
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          width: 56, height: 56, borderRadius: 14, background: 'var(--navy)',
          fontSize: 24, marginBottom: 16,
        }}>✦</div>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: 'var(--navy)', marginBottom: 8 }}>
          AI Meeting Co-pilot
        </h1>
        <p style={{ color: 'var(--gray-500)', fontSize: 15, maxWidth: 500, margin: '0 auto' }}>
          Paste a transcript or upload audio — get a full summary, action items
          routed to Jira/Asana, and a follow-up scheduled automatically.
        </p>
      </div>

      {/* Agent pipeline badge row */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginBottom: 32, flexWrap: 'wrap' }}>
        {[
          { label: 'Transcription', color: 'var(--blue)', bg: 'var(--blue-light)' },
          { label: 'Summarize', color: 'var(--teal)', bg: 'var(--teal-light)' },
          { label: 'Extract actions', color: 'var(--purple)', bg: 'var(--purple-light)' },
          { label: 'Route tasks', color: 'var(--amber)', bg: 'var(--amber-light)' },
          { label: 'Schedule follow-up', color: 'var(--coral)', bg: 'var(--coral-light)' },
          { label: 'Distribute', color: 'var(--green)', bg: 'var(--green-light)' },
        ].map((s, i) => (
          <React.Fragment key={s.label}>
            {i > 0 && <span style={{ color: 'var(--gray-500)', fontSize: 12, alignSelf: 'center' }}>→</span>}
            <span style={{
              background: s.bg, color: s.color, fontSize: 12, fontWeight: 500,
              padding: '4px 10px', borderRadius: 99,
            }}>{s.label}</span>
          </React.Fragment>
        ))}
      </div>

      {/* Card */}
      <div style={{
        background: '#fff', borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--gray-200)', padding: 28,
      }}>
        {/* Mode toggle */}
        <div style={{
          display: 'flex', background: 'var(--gray-100)', borderRadius: 'var(--radius)',
          padding: 3, marginBottom: 24, width: 'fit-content',
        }}>
          {['text', 'audio'].map(m => (
            <button key={m} onClick={() => setMode(m)} style={{
              padding: '7px 20px', borderRadius: 6, border: 'none', fontSize: 13, fontWeight: 500,
              background: mode === m ? '#fff' : 'transparent',
              color: mode === m ? 'var(--navy)' : 'var(--gray-500)',
              boxShadow: mode === m ? '0 1px 3px rgba(0,0,0,.1)' : 'none',
              transition: 'all .15s',
            }}>
              {m === 'text' ? '📝 Paste transcript' : '🎙 Upload audio'}
            </button>
          ))}
        </div>

        {/* Meeting title + attendees row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
          <div>
            <label style={labelStyle}>Meeting title</label>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="e.g. Sprint Planning — Week 14"
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Attendees <span style={{ color: 'var(--gray-500)', fontWeight: 400 }}>(comma-separated emails, optional)</span></label>
            <input
              value={attendees}
              onChange={e => setAttendees(e.target.value)}
              placeholder="alice@co.com, bob@co.com"
              style={inputStyle}
            />
          </div>
        </div>

        {/* Input area */}
        {mode === 'text' ? (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <label style={labelStyle}>Transcript</label>
              <button onClick={() => setTranscript(DEMO_TRANSCRIPT)} style={{
                background: 'none', border: '1px solid var(--blue)', color: 'var(--blue)',
                fontSize: 12, padding: '4px 10px', borderRadius: 6, fontWeight: 500,
              }}>
                Load demo transcript
              </button>
            </div>
            <textarea
              value={transcript}
              onChange={e => setTranscript(e.target.value)}
              placeholder={`Paste your meeting transcript here.\n\nFormats supported:\n  Alice: We need to ship by Friday.\n  Bob: Agreed, I'll handle the fix.\n\nOr plain text without speaker labels.`}
              style={{
                ...inputStyle, minHeight: 280, resize: 'vertical',
                fontFamily: 'monospace', fontSize: 13, lineHeight: 1.6,
              }}
            />
            {transcript && (
              <p style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 6 }}>
                {transcript.split('\n').filter(Boolean).length} lines · {transcript.length.toLocaleString()} chars
              </p>
            )}
          </div>
        ) : (
          <div>
            <label style={{ ...labelStyle, marginBottom: 8, display: 'block' }}>Audio file</label>
            <div
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileRef.current?.click()}
              style={{
                border: `2px dashed ${dragging ? 'var(--blue)' : 'var(--gray-200)'}`,
                borderRadius: 'var(--radius-lg)', padding: '40px 24px', textAlign: 'center',
                cursor: 'pointer', background: dragging ? 'var(--blue-light)' : 'var(--gray-50)',
                transition: 'all .15s',
              }}
            >
              {file ? (
                <div>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>🎙</div>
                  <p style={{ fontWeight: 600, color: 'var(--navy)' }}>{file.name}</p>
                  <p style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 4 }}>
                    {(file.size / 1024 / 1024).toFixed(1)} MB · Click to change
                  </p>
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: 36, marginBottom: 12 }}>🎙</div>
                  <p style={{ fontWeight: 500, color: 'var(--navy)', marginBottom: 4 }}>
                    Drop audio file here or click to browse
                  </p>
                  <p style={{ fontSize: 13, color: 'var(--gray-500)' }}>
                    MP3, MP4, WAV, M4A, OGG · Max 25 MB
                  </p>
                </div>
              )}
              <input
                ref={fileRef}
                type="file"
                accept=".mp3,.mp4,.wav,.m4a,.ogg,.webm"
                style={{ display: 'none' }}
                onChange={e => setFile(e.target.files[0])}
              />
            </div>
          </div>
        )}

        {/* Submit */}
        <div style={{ marginTop: 20, display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={handleSubmit}
            disabled={!valid || loading}
            style={{
              background: valid ? 'var(--navy)' : 'var(--gray-200)',
              color: valid ? '#fff' : 'var(--gray-500)',
              border: 'none', borderRadius: 'var(--radius)', padding: '11px 28px',
              fontSize: 15, fontWeight: 600, transition: 'all .15s',
              cursor: valid ? 'pointer' : 'default',
            }}
          >
            {loading ? 'Processing…' : '✦  Run Co-pilot'}
          </button>
          <span style={{ fontSize: 13, color: 'var(--gray-500)' }}>
            Takes 15–60 seconds depending on transcript length
          </span>
        </div>
      </div>
    </div>
  )
}

const labelStyle = {
  display: 'block', fontSize: 13, fontWeight: 500,
  color: 'var(--slate)', marginBottom: 6,
}
const inputStyle = {
  width: '100%', padding: '9px 12px', borderRadius: 'var(--radius)',
  border: '1px solid var(--gray-200)', fontSize: 14, color: 'var(--gray-700)',
  outline: 'none', background: '#fff',
}
