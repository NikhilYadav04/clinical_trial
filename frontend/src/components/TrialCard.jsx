import { useState, useEffect } from 'react'
import { addBookmark, removeBookmark, submitFeedback, deleteFeedback } from '../api'

function ScoreBar({ label, value, color }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-[10px] text-[#9b9b9b] uppercase tracking-wider w-20 flex-shrink-0">{label}</span>
      <div className="flex-1 h-px bg-[#e8e4de] relative">
        <div className="absolute top-0 left-0 h-px" style={{ width: `${Math.min(value, 100)}%`, background: color }} />
      </div>
      <span className="font-mono text-[11px] text-[#4a4a4a] w-6 text-right">{Math.round(value)}</span>
    </div>
  )
}

function scoreTier(score) {
  if (score >= 70) return {
    accent: '#1a6b3c', label: 'Strong',
    cardBg: '#f4fbf6', critBg: '#e8f5ec', border: '#b8dfc5',
  }
  if (score >= 50) return {
    accent: '#1a4f7a', label: 'Moderate',
    cardBg: '#f3f7fc', critBg: '#e5eef6', border: '#c5d6e8',
  }
  if (score >= 30) return {
    accent: '#7d4e00', label: 'Weak',
    cardBg: '#fdf8f0', critBg: '#f5ecd8', border: '#e8d5a0',
  }
  return {
    accent: '#8b1a1a', label: 'Low',
    cardBg: '#fdf5f5', critBg: '#f5e0e0', border: '#c97b7b',
  }
}

// ── Bookmark button ───────────────────────────────────────────────────────────
function BookmarkBtn({ saved, onToggle, loading }) {
  return (
    <button
      onClick={e => { e.stopPropagation(); onToggle() }}
      disabled={loading}
      title={saved ? 'Remove bookmark' : 'Bookmark this trial'}
      className={`flex-shrink-0 flex items-center gap-1 px-2 py-1 border transition-colors text-[10px] font-medium
        ${loading ? 'opacity-40' : ''}
        ${saved
          ? 'border-[#1a4f7a] bg-[#eef3f8] text-[#1a4f7a]'
          : 'border-[#dedad4] bg-white text-[#9b9b9b] hover:border-[#1a4f7a] hover:text-[#1a4f7a]'}`}
      style={{ borderRadius: 0 }}
    >
      <svg className="w-3.5 h-3.5" fill={saved ? 'currentColor' : 'none'}
           viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round"
              d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/>
      </svg>
      {saved ? 'Saved' : 'Save'}
    </button>
  )
}

// ── Feedback thumbs ───────────────────────────────────────────────────────────
function FeedbackBar({ verdict, onFeedback }) {
  const [loading, setLoading] = useState(false)

  async function handle(v) {
    if (loading) return
    setLoading(true)
    try { await onFeedback(v === verdict ? null : v) }
    finally { setLoading(false) }
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-[#9b9b9b] uppercase tracking-wider">Feedback</span>
      <button onClick={() => handle('relevant')} disabled={loading}
              title="Mark as relevant"
              className={`p-1 transition-colors ${loading ? 'opacity-40' : 'hover:opacity-80'}
                ${verdict === 'relevant' ? 'text-[#1a6b3c]' : 'text-[#c0bbb4]'}`}>
        <svg className="w-4 h-4" fill={verdict === 'relevant' ? 'currentColor' : 'none'}
             viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round"
                d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"/>
        </svg>
      </button>
      <button onClick={() => handle('not_relevant')} disabled={loading}
              title="Mark as not relevant"
              className={`p-1 transition-colors ${loading ? 'opacity-40' : 'hover:opacity-80'}
                ${verdict === 'not_relevant' ? 'text-[#8b1a1a]' : 'text-[#c0bbb4]'}`}>
        <svg className="w-4 h-4" fill={verdict === 'not_relevant' ? 'currentColor' : 'none'}
             viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round"
                d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"/>
        </svg>
      </button>
      {verdict && (
        <span className={`text-[10px] font-medium ${verdict === 'relevant' ? 'text-[#1a6b3c]' : 'text-[#8b1a1a]'}`}>
          {verdict === 'relevant' ? 'Marked relevant' : 'Marked not relevant'}
        </span>
      )}
    </div>
  )
}

// ── Notes textarea ────────────────────────────────────────────────────────────
function NoteField({ note, onNote }) {
  const [local, setLocal] = useState(note || '')
  useEffect(() => { setLocal(note || '') }, [note])
  return (
    <div>
      <div className="data-label mb-1.5">Clinical Notes</div>
      <textarea
        className="w-full text-xs p-2 resize-none outline-none transition-colors"
        style={{ border: '1px solid #dedad4', background: 'white', borderRadius: 0, lineHeight: 1.6 }}
        rows={3}
        placeholder="Add a clinical note… e.g. PI confirmed slot available, patient declined — too far"
        value={local}
        onChange={e => setLocal(e.target.value)}
        onFocus={e => e.target.style.borderColor = '#1a4f7a'}
        onBlur={e => { e.target.style.borderColor = '#dedad4'; if (local !== (note || '')) onNote(local) }}
      />
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function TrialCard({ trial, rank, isBookmarked, onBookmarkToggle, feedback, onFeedback, note, onNote, onDetail }) {
  const [open, setOpen]           = useState(false)
  const [bmLoading, setBmLoading] = useState(false)

  const score     = trial.final_score || 0
  const breakdown = trial.eligibility_breakdown || []
  const nPass   = breakdown.filter(v => v.verdict === 'PASS').length
  const nFail   = breakdown.filter(v => v.verdict === 'FAIL').length
  const nUncert = breakdown.filter(v => v.verdict === 'UNCERTAIN').length
  const phase   = (trial.phase || 'N/A').replace('PHASE', 'Ph ').replace('EARLY_', 'Early ').replace('_', ' ')
  const tier    = scoreTier(score)

  async function handleBookmark() {
    setBmLoading(true)
    try { await onBookmarkToggle(trial, !isBookmarked) }
    finally { setBmLoading(false) }
  }

  return (
    <div className="mb-2 overflow-hidden" style={{ border: `1px solid ${tier.border}` }}
         role="article" aria-label={`Trial ${rank}: ${trial.title}, score ${Math.round(score)}`}>
      {/* Card body — tier-tinted bg */}
      <div className="flex" style={{ background: tier.cardBg }}>
        <div className="w-1 flex-shrink-0" style={{ background: tier.accent }} />
        <div className="flex-1 p-4">
          <div className="flex items-start gap-4">
            {/* Score column */}
            <div className="flex-shrink-0 text-center" style={{ minWidth: 44 }}>
              <div className="font-mono text-2xl font-bold leading-none" style={{ color: tier.accent }}>
                {Math.round(score)}
              </div>
              <div className="font-mono text-[9px] text-[#9b9b9b] mt-0.5">/100</div>
              <div className="text-[9px] uppercase tracking-wider mt-1" style={{ color: tier.accent }}>
                {tier.label}
              </div>
              <div className="text-[9px] text-[#9b9b9b] font-mono mt-0.5">#{rank}</div>
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2 mb-2">
                <button
                  onClick={() => onDetail && onDetail(trial)}
                  className="text-sm font-semibold text-[#1a1a1a] leading-snug text-left hover:text-[#1a4f7a] transition-colors"
                  aria-label={`View full details for ${trial.title}`}
                >
                  {trial.title}
                </button>
                <BookmarkBtn saved={isBookmarked} onToggle={handleBookmark} loading={bmLoading} />
              </div>

              <div className="flex flex-wrap gap-x-3 gap-y-0.5 mb-3 text-[11px] text-[#6b6b6b]">
                <span className="font-mono">{phase}</span>
                {trial.sponsor && <span>· {trial.sponsor.slice(0, 40)}</span>}
                {trial.nearest_site_miles !== null && trial.nearest_site_miles !== undefined
                  ? <span style={{ color: '#1a6b3c' }}>· {trial.nearest_site_miles} mi</span>
                  : <span>· dist unknown</span>
                }
                <a href={trial.url} target="_blank" rel="noreferrer"
                   className="font-mono hover:underline ml-auto" style={{ color: '#1a4f7a' }}>
                  {trial.nct_id} ↗
                </a>
              </div>

              <div className="space-y-2">
                <ScoreBar label="Eligibility" value={trial.eligibility_score || 0} color="#1a4f7a" />
                <ScoreBar label="Logistics"   value={trial.logistics_score   || 0} color="#1a6b3c" />
                <ScoreBar label="Quality"     value={trial.quality_score     || 0} color="#5b2d8e" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Criteria summary bar — slightly stronger bg */}
      <div className="flex items-center gap-3 px-4 py-2 border-t text-[11px]"
           style={{ background: tier.critBg, borderColor: tier.border }}>
        <span className="text-[10px] uppercase tracking-wider" style={{ color: tier.accent, opacity: 0.7 }}>Criteria</span>
        <span style={{ color: '#1a6b3c' }}>{nPass} passed</span>
        <span className="text-[#9b9b9b]">·</span>
        <span style={{ color: '#7d4e00' }}>{nUncert} uncertain</span>
        <span className="text-[#9b9b9b]">·</span>
        <span style={{ color: '#8b1a1a' }}>{nFail} failed</span>
        <button
          onClick={() => setOpen(o => !o)}
          aria-expanded={open}
          aria-label={open ? 'Hide trial details' : 'Show trial details'}
          className="ml-auto text-[11px] text-[#9b9b9b] hover:text-[#1a1a1a] transition-colors"
        >
          {open ? 'hide ▲' : 'details ▼'}
        </button>
      </div>

      {/* Expanded details */}
      {open && (
        <div className="px-4 py-4 border-t space-y-4"
             style={{ background: '#f9f8f5', borderColor: tier.border }}>

          {breakdown.filter(v => v.verdict === 'FAIL' && v.is_hard_stop).length > 0 && (
            <div className="p-3" style={{ border: '1px solid #c97b7b', background: '#fff5f5' }}>
              <div className="text-[10px] font-semibold uppercase tracking-widest mb-1.5"
                   style={{ color: '#8b1a1a' }}>Hard Disqualifiers</div>
              {breakdown.filter(v => v.verdict === 'FAIL' && v.is_hard_stop).map((v, i) => (
                <div key={i} className="text-xs mt-1 pl-2 border-l" style={{ color: '#8b1a1a', borderColor: '#c97b7b' }}>
                  <strong>{v.criterion_text}</strong> — {v.reason}
                </div>
              ))}
            </div>
          )}

          {breakdown.length > 0 && (
            <div>
              <div className="data-label mb-2">All Criteria</div>
              <div className="flex flex-wrap gap-1">
                {breakdown.slice(0, 20).map((v, i) => {
                  const cls = v.verdict === 'PASS'
                    ? 'bg-[#eef6f0] text-[#1a6b3c] border-[#b8dfc5]'
                    : v.verdict === 'FAIL'
                    ? 'bg-[#fff5f5] text-[#8b1a1a] border-[#c97b7b]'
                    : 'bg-[#fdf6e8] text-[#7d4e00] border-[#e8d5a0]'
                  const icon = v.verdict === 'PASS' ? '✓' : v.verdict === 'FAIL' ? '✗' : '?'
                  return (
                    <span key={i} className={`px-2 py-0.5 border text-[11px] font-medium ${cls}`}>
                      {icon} {v.criterion_text?.slice(0, 55)}
                    </span>
                  )
                })}
              </div>
            </div>
          )}

          {trial.brief_summary && (
            <div>
              <div className="data-label mb-1.5">Trial Summary</div>
              <p className="text-xs text-[#4a4a4a] leading-relaxed">
                {trial.brief_summary.slice(0, 500)}{trial.brief_summary.length > 500 ? '…' : ''}
              </p>
            </div>
          )}

          {(trial.patient_summary || trial.physician_brief || trial.outreach_email) && (
            <div className="space-y-3">
              {trial.patient_summary && (
                <div>
                  <div className="data-label mb-1.5">Patient Summary</div>
                  <div className="bg-white border border-[#e8e4de] p-3 text-xs text-[#4a4a4a] leading-relaxed whitespace-pre-wrap">
                    {trial.patient_summary}
                  </div>
                </div>
              )}
              {trial.physician_brief && (
                <div>
                  <div className="data-label mb-1.5">Physician Brief</div>
                  <div className="bg-white border border-[#e8e4de] p-3 text-xs text-[#4a4a4a] leading-relaxed whitespace-pre-wrap">
                    {trial.physician_brief}
                  </div>
                </div>
              )}
              {trial.outreach_email && (
                <div>
                  <div className="data-label mb-1.5">Outreach Email</div>
                  <div className="bg-[#0d1117] border border-[#333] p-3 text-xs text-[#9b9b9b] font-mono leading-relaxed whitespace-pre-wrap">
                    {trial.outreach_email}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="pt-2 border-t border-[#e8e4de] space-y-3">
            <FeedbackBar verdict={feedback} onFeedback={onFeedback} />
            <NoteField note={note} onNote={onNote} />
          </div>
        </div>
      )}
    </div>
  )
}
