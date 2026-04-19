import { useState, useEffect } from 'react'
import { removeBookmark, saveNote } from '../api'
import ComparisonModal from './ComparisonModal'

function scoreTier(score) {
  if (score >= 70) return { accent: '#1a6b3c', label: 'Strong'   }
  if (score >= 50) return { accent: '#1a4f7a', label: 'Moderate' }
  if (score >= 30) return { accent: '#7d4e00', label: 'Weak'     }
  return               { accent: '#8b1a1a', label: 'Low'      }
}

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

function NoteField({ nctId, note }) {
  const [local, setLocal] = useState(note || '')
  useEffect(() => { setLocal(note || '') }, [note])
  return (
    <div>
      <div className="data-label mb-1">Clinical Notes</div>
      <textarea
        className="w-full text-xs p-2 resize-none outline-none transition-colors"
        style={{ border: '1px solid #dedad4', background: 'white', borderRadius: 0, lineHeight: 1.6 }}
        rows={2}
        placeholder="Add a clinical note…"
        aria-label={`Clinical notes for trial ${nctId}`}
        value={local}
        onChange={e => setLocal(e.target.value)}
        onFocus={e => e.target.style.borderColor = '#1a4f7a'}
        onBlur={e => { e.target.style.borderColor = '#dedad4'; saveNote({ nct_id: nctId, note: local }).catch(() => {}) }}
      />
    </div>
  )
}

function BookmarkedTrial({ bm, onRemove, note, selected, onSelect, onDetail }) {
  const [open, setOpen] = useState(false)
  const trial  = bm.trial_data || {}
  const tier   = scoreTier(bm.score)
  const phase  = (bm.phase || 'N/A').replace('PHASE','Ph ').replace('EARLY_','Early ').replace('_',' ')
  const date   = bm.bookmarked_at
    ? new Date(bm.bookmarked_at).toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' })
    : ''

  const breakdown = trial.eligibility_breakdown || []
  const nPass   = breakdown.filter(v => v.verdict === 'PASS').length
  const nFail   = breakdown.filter(v => v.verdict === 'FAIL').length
  const nUncert = breakdown.filter(v => v.verdict === 'UNCERTAIN').length

  return (
    <div
      className="bg-white border overflow-hidden"
      style={{ borderColor: selected ? '#1a4f7a' : '#e8e4de', borderWidth: selected ? 2 : 1 }}
      role="article"
      aria-label={`Bookmarked trial: ${bm.title}`}
    >
      <div className="flex">
        {/* Checkbox column */}
        <div className="flex items-start pt-4 pl-3 pr-1 flex-shrink-0">
          <input
            type="checkbox"
            checked={selected}
            onChange={e => onSelect(bm.nct_id, e.target.checked)}
            aria-label={`Select ${bm.title} for comparison`}
            className="w-3.5 h-3.5 accent-[#1a4f7a]"
          />
        </div>
        <div className="w-0.5 flex-shrink-0 self-stretch" style={{ background: tier.accent }} />
        <div className="flex-1 p-4">
          <div className="flex items-start gap-4">
            {/* Score */}
            <div className="flex-shrink-0 text-center" style={{ minWidth: 44 }}>
              <div className="font-mono text-2xl font-bold leading-none" style={{ color: tier.accent }}>
                {Math.round(bm.score)}
              </div>
              <div className="font-mono text-[9px] text-[#9b9b9b] mt-0.5">/100</div>
              <div className="text-[9px] uppercase tracking-wider mt-1" style={{ color: tier.accent }}>
                {tier.label}
              </div>
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2 mb-1">
                <button
                  onClick={() => onDetail && onDetail(bm.trial_data ? { ...bm.trial_data, title: bm.title, nct_id: bm.nct_id, url: bm.url, phase: bm.phase, sponsor: bm.sponsor, final_score: bm.score } : bm)}
                  className="text-sm font-semibold text-[#1a1a1a] leading-snug text-left hover:text-[#1a4f7a] transition-colors"
                  aria-label={`View details for ${bm.title}`}
                >
                  {bm.title}
                </button>
                <button
                  onClick={() => onRemove(bm.nct_id)}
                  aria-label={`Remove bookmark for ${bm.title}`}
                  className="flex-shrink-0 text-[10px] text-[#c0bbb4] hover:text-[#8b1a1a] transition-colors whitespace-nowrap"
                >
                  remove
                </button>
              </div>

              <div className="flex flex-wrap gap-x-3 gap-y-0.5 mb-3 text-[11px] text-[#6b6b6b]">
                <span className="font-mono">{phase}</span>
                {bm.sponsor && <span>· {bm.sponsor.slice(0, 40)}</span>}
                {trial.nearest_site_miles !== null && trial.nearest_site_miles !== undefined
                  ? <span className="text-[#1a6b3c]">· {trial.nearest_site_miles} mi</span>
                  : null}
                {bm.url && (
                  <a href={bm.url} target="_blank" rel="noreferrer"
                     className="font-mono text-[#1a4f7a] hover:underline ml-auto">
                    {bm.nct_id} ↗
                  </a>
                )}
              </div>

              {(trial.eligibility_score || trial.logistics_score || trial.quality_score) && (
                <div className="space-y-2">
                  <ScoreBar label="Eligibility" value={trial.eligibility_score || 0} color="#1a4f7a" />
                  <ScoreBar label="Logistics"   value={trial.logistics_score   || 0} color="#1a6b3c" />
                  <ScoreBar label="Quality"     value={trial.quality_score     || 0} color="#5b2d8e" />
                </div>
              )}

              {bm.patient_context && (
                <div className="mt-2 pt-2 border-t border-[#f0ece6] text-[10px] text-[#9b9b9b]">
                  Searched for: <span className="text-[#6b6b6b]">{bm.patient_context.diagnosis}</span>
                  {bm.patient_context.location && <span> · {bm.patient_context.location}</span>}
                  {date && <span className="ml-2">· Saved {date}</span>}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Criteria bar + toggle */}
      {breakdown.length > 0 && (
        <div className="flex items-center gap-3 px-4 py-2 border-t border-[#e8e4de] bg-[#f9f8f5] text-[11px]">
          <span className="text-[#9b9b9b] uppercase tracking-wider text-[10px]">Criteria</span>
          <span className="text-[#1a6b3c]">{nPass} passed</span>
          <span className="text-[#9b9b9b]">·</span>
          <span className="text-[#7d4e00]">{nUncert} uncertain</span>
          <span className="text-[#9b9b9b]">·</span>
          <span className="text-[#8b1a1a]">{nFail} failed</span>
          <button
            onClick={() => setOpen(o => !o)}
            aria-expanded={open}
            aria-label={open ? 'Hide criteria details' : 'Show criteria details'}
            className="ml-auto text-[11px] text-[#9b9b9b] hover:text-[#1a1a1a] transition-colors"
          >
            {open ? 'hide ▲' : 'details ▼'}
          </button>
        </div>
      )}

      {/* Expanded details */}
      {open && (
        <div className="px-4 py-4 border-t border-[#e8e4de] space-y-4 bg-[#f9f8f5]">
          {breakdown.filter(v => v.verdict === 'FAIL' && v.is_hard_stop).length > 0 && (
            <div className="border border-[#c97b7b] bg-[#fff5f5] p-3">
              <div className="text-[10px] font-semibold text-[#8b1a1a] uppercase tracking-widest mb-1.5">
                Hard Disqualifiers
              </div>
              {breakdown.filter(v => v.verdict === 'FAIL' && v.is_hard_stop).map((v, i) => (
                <div key={i} className="text-xs text-[#8b1a1a] mt-1 pl-2 border-l border-[#c97b7b]">
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

          <div className="pt-2 border-t border-[#e8e4de]">
            <NoteField nctId={bm.nct_id} note={note} />
          </div>
        </div>
      )}
    </div>
  )
}

export default function BookmarksPage({ bookmarks, onRemove, notesMap = {}, onDetail }) {
  const [selected, setSelected] = useState(new Set())
  const [comparing, setComparing] = useState(false)

  function handleSelect(nctId, checked) {
    setSelected(prev => {
      const next = new Set(prev)
      if (checked) { if (next.size < 3) next.add(nctId) }
      else next.delete(nctId)
      return next
    })
  }

  async function handleRemove(nctId) {
    await removeBookmark(nctId)
    setSelected(prev => { const n = new Set(prev); n.delete(nctId); return n })
    onRemove(nctId)
  }

  const selectedTrials = bookmarks.filter(b => selected.has(b.nct_id))

  if (!bookmarks.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-12 py-24">
        <svg className="w-10 h-10 text-[#dedad4] mb-4" fill="none" viewBox="0 0 24 24"
             stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round"
                d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/>
        </svg>
        <p className="text-sm text-[#9b9b9b]">No bookmarks yet.</p>
        <p className="text-[11px] text-[#c0bbb4] mt-1">
          Click <strong>Save</strong> on any trial card to save it here.
        </p>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-serif text-xl text-[#1a1a1a] mb-0.5">Saved Trials</h2>
          <div className="w-6 h-px bg-[#1a4f7a]" />
          <p className="text-[11px] text-[#9b9b9b] mt-2">{bookmarks.length} saved · across all searches</p>
        </div>
        {selected.size >= 2 && (
          <button
            onClick={() => setComparing(true)}
            aria-label={`Compare ${selected.size} selected trials`}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white transition-colors"
            style={{ background: '#1a4f7a', borderRadius: 0 }}
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
            </svg>
            Compare {selected.size}
          </button>
        )}
      </div>

      {bookmarks.length >= 2 && (
        <p className="text-[11px] text-[#c0bbb4]">
          Select 2–3 trials to compare side-by-side.
        </p>
      )}

      <div className="space-y-2">
        {bookmarks.map(bm => (
          <BookmarkedTrial
            key={bm.nct_id}
            bm={bm}
            onRemove={handleRemove}
            note={notesMap[bm.nct_id]}
            selected={selected.has(bm.nct_id)}
            onSelect={handleSelect}
            onDetail={onDetail}
          />
        ))}
      </div>

      {comparing && (
        <ComparisonModal
          trials={selectedTrials}
          onClose={() => setComparing(false)}
        />
      )}
    </div>
  )
}
