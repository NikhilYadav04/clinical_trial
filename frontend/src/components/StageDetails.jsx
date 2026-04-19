import { useState } from 'react'

// Per-stage color identity
const STAGE_COLORS = [
  { accent: '#1a4f7a', bg: '#f3f7fc', border: '#c5d6e8', label_color: '#1a4f7a' }, // Profile — blue
  { accent: '#0f6b5e', bg: '#f3faf8', border: '#9fd3cb', label_color: '#0f6b5e' }, // Search  — teal
  { accent: '#7d4e00', bg: '#fdf8f0', border: '#e8d5a0', label_color: '#7d4e00' }, // Eval    — amber
  { accent: '#1a6b3c', bg: '#f4fbf6', border: '#b8dfc5', label_color: '#1a6b3c' }, // Rank    — green
  { accent: '#5b2d8e', bg: '#f7f3fc', border: '#d0bde8', label_color: '#5b2d8e' }, // Reports — violet
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function Chevron({ open, color }) {
  return (
    <svg className={`w-3 h-3 transition-transform flex-shrink-0 ${open ? 'rotate-180' : ''}`}
         style={{ color }}
         fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7"/>
    </svg>
  )
}

function Row({ label, value }) {
  if (!value && value !== 0) return null
  const vals = Array.isArray(value) ? value : [value]
  if (vals.length === 0 || (vals.length === 1 && !vals[0])) return null
  return (
    <tr className="border-b border-[#f0ece6] last:border-0">
      <td className="py-1.5 pr-4 text-[10px] font-semibold text-[#9b9b9b] uppercase tracking-widest whitespace-nowrap align-top w-32">
        {label}
      </td>
      <td className="py-1.5 text-xs text-[#1a1a1a]">
        {vals.map((v, i) => (
          <span key={i} className={i < vals.length - 1 ? 'block' : ''}>{v || '—'}</span>
        ))}
      </td>
    </tr>
  )
}

function parseSearchLog(logs) {
  const data = {}
  for (const line of logs) {
    if (!line.includes('[Trial Search Agent]')) continue
    const found    = line.match(/Found (\d+) RECRUITING/)
    const filtered = line.match(/Phase filter applied: (\d+) -> (\d+)/)
    const final    = line.match(/Final candidate list: (\d+)/)
    const location = line.match(/Location: (.+?), Radius/)
    const query    = line.match(/Searching for: '(.+?)'/)
    if (found)    data.found    = found[1]
    if (filtered) { data.before = filtered[1]; data.after = filtered[2] }
    if (final)    data.final    = final[1]
    if (location) data.location = location[1]
    if (query)    data.query    = query[1]
  }
  return data
}

function parseEvalLog(logs) {
  const trials = []
  for (const line of logs) {
    const m = line.match(/\[Evaluator\] (NCT\w+) scored ([\d.]+)\/100/)
    if (m) trials.push({ nct_id: m[1], score: parseFloat(m[2]) })
  }
  return trials
}

// ── Stage Cards ───────────────────────────────────────────────────────────────

function StageCard({ number, label, done, colors, children }) {
  const [open, setOpen] = useState(false)
  const idx = number - 1
  const c = colors || STAGE_COLORS[idx] || STAGE_COLORS[0]

  return (
    <div className="overflow-hidden" style={{ border: `1px solid ${c.border}` }}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-4 py-3 transition-colors text-left"
        style={{ background: open ? c.bg : 'white' }}
        onMouseEnter={e => e.currentTarget.style.background = c.bg}
        onMouseLeave={e => { if (!open) e.currentTarget.style.background = 'white' }}
      >
        {/* Stage indicator */}
        <div className="w-4 h-4 flex items-center justify-center flex-shrink-0"
             style={{
               background: done ? c.accent : 'transparent',
               border: done ? 'none' : `1px solid ${c.border}`,
             }}>
          {done
            ? <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24"
                   stroke="currentColor" strokeWidth={3}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
            : <span className="text-[9px] font-mono font-bold" style={{ color: c.accent }}>{number}</span>
          }
        </div>
        <span className="text-[10px] font-semibold uppercase tracking-widest flex-1"
              style={{ color: c.label_color }}>{label}</span>
        <Chevron open={open} color={c.accent} />
      </button>

      {open && (
        <div className="border-t px-4 py-3" style={{ background: c.bg, borderColor: c.border }}>
          {children}
        </div>
      )}
    </div>
  )
}

// ── Stage 1 — Profile ─────────────────────────────────────────────────────────

function ProfileStage({ profile }) {
  if (!profile) return <p className="text-xs text-[#9b9b9b] italic">Profile not available.</p>
  const c = STAGE_COLORS[0]
  return (
    <div className="space-y-3">
      <table className="w-full">
        <tbody>
          <Row label="Diagnosis"  value={profile.diagnosis} />
          <Row label="Stage"      value={profile.stage} />
          <Row label="Age / Sex"  value={[profile.age && `${profile.age} yo`, profile.sex].filter(Boolean).join(' · ')} />
          <Row label="ECOG"       value={profile.ecog_score !== null && profile.ecog_score !== undefined ? `${profile.ecog_score}` : null} />
          <Row label="Location"   value={profile.location} />
          <Row label="Max Travel" value={profile.max_travel_miles ? `${profile.max_travel_miles} miles` : null} />
        </tbody>
      </table>

      {profile.biomarkers?.length > 0 && (
        <div>
          <div className="data-label mb-1.5">Biomarkers</div>
          <div className="flex flex-wrap gap-1">
            {profile.biomarkers.map(b => (
              <span key={b} className="px-2 py-0.5 border text-[11px] font-medium"
                    style={{ background: '#eef3f8', color: '#1a4f7a', borderColor: '#c5d6e8' }}>{b}</span>
            ))}
          </div>
        </div>
      )}

      {profile.prior_treatments?.length > 0 && (
        <div>
          <div className="data-label mb-1.5">Prior Treatments</div>
          <div className="flex flex-wrap gap-1">
            {profile.prior_treatments.map(t => (
              <span key={t} className="px-2 py-0.5 border text-[11px] font-medium"
                    style={{ background: '#fdf6e8', color: '#7d4e00', borderColor: '#e8d5a0' }}>{t}</span>
            ))}
          </div>
        </div>
      )}

      {profile.comorbidities?.length > 0 && (
        <div>
          <div className="data-label mb-1.5">Comorbidities</div>
          <div className="flex flex-wrap gap-1">
            {profile.comorbidities.map(c => (
              <span key={c} className="px-2 py-0.5 border text-[11px] font-medium"
                    style={{ background: '#f5f4f0', color: '#4a4a4a', borderColor: '#dedad4' }}>{c}</span>
            ))}
          </div>
        </div>
      )}

      {profile.lab_values && Object.keys(profile.lab_values).length > 0 && (
        <div>
          <div className="data-label mb-1.5">Lab Values</div>
          <table className="w-full">
            <tbody>
              {Object.entries(profile.lab_values).map(([k, v]) => (
                <Row key={k} label={k} value={String(v)} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {profile.missing_info?.length > 0 && (
        <div className="px-3 py-2" style={{ border: '1px solid #e8d5a0', background: '#fdf6e8' }}>
          <div className="data-label mb-1" style={{ color: '#7d4e00' }}>Confirm with physician</div>
          {profile.missing_info.map((m, i) => (
            <p key={i} className="text-xs" style={{ color: '#7d4e00' }}>• {m}</p>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Stage 2 — Search ──────────────────────────────────────────────────────────

function SearchStage({ logs }) {
  const d = parseSearchLog(logs)
  if (!d.found) return <p className="text-xs text-[#9b9b9b] italic">No search data in logs.</p>
  return (
    <table className="w-full">
      <tbody>
        {d.query    && <Row label="Query"        value={`"${d.query}"`} />}
        {d.location && <Row label="Location"     value={d.location} />}
        {d.found    && <Row label="Recruiting"   value={`${d.found} trials found`} />}
        {d.before   && <Row label="Phase filter" value={`${d.before} → ${d.after} trials`} />}
        {d.final    && <Row label="Final list"   value={`${d.final} candidates`} />}
      </tbody>
    </table>
  )
}

// ── Stage 3 — Evaluate ────────────────────────────────────────────────────────

function EvalStage({ logs }) {
  const scored = parseEvalLog(logs)
  const dist = { high: 0, mid: 0, low: 0, fail: 0 }
  for (const t of scored) {
    if (t.score >= 70) dist.high++
    else if (t.score >= 50) dist.mid++
    else if (t.score >= 30) dist.low++
    else dist.fail++
  }

  return (
    <div className="space-y-3">
      {scored.length > 0 && (
        <div className="grid grid-cols-4 gap-1.5">
          {[
            { label: '≥70 Strong',   val: dist.high, color: '#1a6b3c', bg: '#eef6f0', border: '#b8dfc5' },
            { label: '50–69 Mod',    val: dist.mid,  color: '#1a4f7a', bg: '#eef3f8', border: '#c5d6e8' },
            { label: '30–49 Weak',   val: dist.low,  color: '#7d4e00', bg: '#fdf6e8', border: '#e8d5a0' },
            { label: '<30 Excluded', val: dist.fail,  color: '#8b1a1a', bg: '#fff5f5', border: '#c97b7b' },
          ].map(d => (
            <div key={d.label} className="p-2 text-center"
                 style={{ background: d.bg, border: `1px solid ${d.border}` }}>
              <div className="font-mono text-lg font-bold" style={{ color: d.color }}>{d.val}</div>
              <div className="text-[10px] leading-tight mt-0.5" style={{ color: d.color, opacity: 0.7 }}>{d.label}</div>
            </div>
          ))}
        </div>
      )}

      {scored.length > 0 && (
        <div>
          <div className="data-label mb-1.5">All Evaluated Trials</div>
          <div className="overflow-hidden" style={{ border: '1px solid #e8d5a0' }}>
            <table className="w-full text-xs">
              <thead>
                <tr style={{ background: '#fdf6e8', borderBottom: '1px solid #e8d5a0' }}>
                  <th className="text-left px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest"
                      style={{ color: '#7d4e00' }}>NCT ID</th>
                  <th className="text-right px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest"
                      style={{ color: '#7d4e00' }}>Score</th>
                </tr>
              </thead>
              <tbody>
                {scored.sort((a, b) => b.score - a.score).map(t => {
                  const c = t.score >= 70 ? '#1a6b3c' : t.score >= 50 ? '#1a4f7a' : t.score >= 30 ? '#7d4e00' : '#8b1a1a'
                  return (
                    <tr key={t.nct_id} className="border-b border-[#f0ece6] last:border-0 hover:bg-[#f9f8f5]">
                      <td className="px-3 py-1.5 font-mono text-[#4a4a4a]">{t.nct_id}</td>
                      <td className="px-3 py-1.5 text-right font-mono font-semibold" style={{ color: c }}>{t.score}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Stage 4 — Rank ────────────────────────────────────────────────────────────

function RankStage({ ranked }) {
  if (!ranked?.length) return <p className="text-xs text-[#9b9b9b] italic">No matches above threshold.</p>
  const scores = ranked.map(t => t.final_score || 0)
  const avg    = (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)

  return (
    <div className="space-y-3">
      <table className="w-full">
        <tbody>
          <Row label="Passed (≥30)" value={`${ranked.length} trials`} />
          <Row label="Top score"    value={`${scores[0]} / 100`} />
          <Row label="Avg score"    value={`${avg} / 100`} />
        </tbody>
      </table>

      <div>
        <div className="data-label mb-1.5">Ranked Order</div>
        <div className="space-y-2">
          {ranked.slice(0, 5).map((t, i) => {
            const score = t.final_score || 0
            const color = score >= 70 ? '#1a6b3c' : score >= 50 ? '#1a4f7a' : '#7d4e00'
            return (
              <div key={t.nct_id} className="flex items-center gap-2 text-xs">
                <span className="font-mono text-[#9b9b9b] w-4 text-right">#{i + 1}</span>
                <div className="flex-1 h-px bg-[#e8e4de] relative">
                  <div className="absolute top-0 left-0 h-px" style={{ width: `${score}%`, background: color }} />
                </div>
                <span className="font-mono font-semibold text-[#1a1a1a] w-8 text-right">{score}</span>
                <span className="font-mono text-[#9b9b9b] text-[10px] w-24">{t.nct_id}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ── Stage 5 — Reports ─────────────────────────────────────────────────────────

function ReportsStage({ ranked }) {
  const withReports = (ranked || []).filter(t => t.patient_summary || t.physician_brief)
  if (!withReports.length) return <p className="text-xs text-[#9b9b9b] italic">No reports generated.</p>
  return (
    <div className="space-y-2">
      {withReports.map((t, i) => (
        <div key={t.nct_id} className="flex items-start gap-2 text-xs">
          <span className="font-mono text-[#9b9b9b]">#{i + 1}</span>
          <div>
            <span className="font-mono" style={{ color: '#1a4f7a' }}>{t.nct_id}</span>
            <span className="text-[#9b9b9b] mx-2">·</span>
            <span className="text-[#4a4a4a]">{t.title?.slice(0, 60)}…</span>
            <div className="flex gap-1 mt-1">
              {t.patient_summary && (
                <span className="px-1.5 py-0.5 border text-[10px] font-medium"
                      style={{ background: '#eef3f8', color: '#1a4f7a', borderColor: '#c5d6e8' }}>
                  Patient summary
                </span>
              )}
              {t.physician_brief && (
                <span className="px-1.5 py-0.5 border text-[10px] font-medium"
                      style={{ background: '#f3eef8', color: '#5b2d8e', borderColor: '#d0bde8' }}>
                  Physician brief
                </span>
              )}
              {t.outreach_email && (
                <span className="px-1.5 py-0.5 border text-[10px] font-medium"
                      style={{ background: '#f5f4f0', color: '#4a4a4a', borderColor: '#dedad4' }}>
                  Outreach email
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Root ──────────────────────────────────────────────────────────────────────

export default function StageDetails({ logs, result }) {
  const profile = result?.patient_profile
  const ranked  = result?.ranked_trials || []

  const stages = [
    { label: 'Patient Profile',   done: !!profile,                          content: <ProfileStage profile={profile} /> },
    { label: 'Trial Search',      done: !!result,                           content: <SearchStage logs={logs} /> },
    { label: 'Evaluation',        done: !!result,                           content: <EvalStage logs={logs} /> },
    { label: 'Ranking',           done: ranked.length > 0,                  content: <RankStage ranked={ranked} /> },
    { label: 'Report Generation', done: ranked.some(t => t.patient_summary), content: <ReportsStage ranked={ranked} /> },
  ]

  return (
    <div>
      {/* Section label with colored left strip */}
      <div className="flex items-center gap-3 mb-2">
        <div className="w-0.5 h-4 bg-[#9b9b9b]" />
        <div className="data-label">Pipeline Stage Output</div>
      </div>
      <div className="space-y-1.5">
        {stages.map((s, i) => (
          <StageCard key={s.label} number={i + 1} label={s.label} done={s.done}>
            {s.content}
          </StageCard>
        ))}
      </div>
    </div>
  )
}
