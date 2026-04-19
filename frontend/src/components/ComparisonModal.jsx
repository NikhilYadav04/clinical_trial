import { useEffect, useRef } from 'react'

function scoreTier(score) {
  if (score >= 70) return { accent: '#1a6b3c', label: 'Strong' }
  if (score >= 50) return { accent: '#1a4f7a', label: 'Moderate' }
  if (score >= 30) return { accent: '#7d4e00', label: 'Weak' }
  return { accent: '#8b1a1a', label: 'Low' }
}

function ScoreCell({ value, color }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-[#f0ece6]">
        <div className="h-1.5" style={{ width: `${Math.min(value || 0, 100)}%`, background: color }} />
      </div>
      <span className="font-mono text-[11px] text-[#4a4a4a] w-6 text-right">{Math.round(value || 0)}</span>
    </div>
  )
}

const ROWS = [
  { key: 'score',      label: 'Final Score',    render: (t) => {
    const tier = scoreTier(t.final_score || t.score || 0)
    const s = t.final_score || t.score || 0
    return <span className="font-mono font-bold text-base" style={{ color: tier.accent }}>{Math.round(s)} <span className="text-xs font-normal text-[#9b9b9b]">/ 100 · {tier.label}</span></span>
  }},
  { key: 'elig',       label: 'Eligibility',    render: (t) => <ScoreCell value={(t.trial_data?.eligibility_score || t.eligibility_score) || 0} color="#1a4f7a" /> },
  { key: 'logi',       label: 'Logistics',      render: (t) => <ScoreCell value={(t.trial_data?.logistics_score   || t.logistics_score)   || 0} color="#1a6b3c" /> },
  { key: 'qual',       label: 'Quality',        render: (t) => <ScoreCell value={(t.trial_data?.quality_score     || t.quality_score)     || 0} color="#5b2d8e" /> },
  { key: 'phase',      label: 'Phase',          render: (t) => <span className="text-xs text-[#4a4a4a]">{(t.phase || 'N/A').replace('PHASE','Ph ').replace('EARLY_','Early ').replace('_',' ')}</span> },
  { key: 'sponsor',    label: 'Sponsor',        render: (t) => <span className="text-xs text-[#4a4a4a]">{(t.sponsor || '—').slice(0, 50)}</span> },
  { key: 'dist',       label: 'Distance',       render: (t) => {
    const miles = t.trial_data?.nearest_site_miles ?? t.nearest_site_miles
    return <span className="text-xs" style={{ color: miles != null ? '#1a6b3c' : '#9b9b9b' }}>{miles != null ? `${miles} mi` : 'Unknown'}</span>
  }},
  { key: 'criteria',   label: 'Criteria',       render: (t) => {
    const bd = t.trial_data?.eligibility_breakdown || t.eligibility_breakdown || []
    const nP = bd.filter(v => v.verdict === 'PASS').length
    const nF = bd.filter(v => v.verdict === 'FAIL').length
    const nU = bd.filter(v => v.verdict === 'UNCERTAIN').length
    if (!bd.length) return <span className="text-xs text-[#9b9b9b]">—</span>
    return (
      <div className="flex gap-2 text-[11px]">
        <span className="text-[#1a6b3c]">{nP}✓</span>
        <span className="text-[#7d4e00]">{nU}?</span>
        <span className="text-[#8b1a1a]">{nF}✗</span>
      </div>
    )
  }},
  { key: 'hardstops',  label: 'Hard Stops',     render: (t) => {
    const bd = t.trial_data?.eligibility_breakdown || t.eligibility_breakdown || []
    const hs = bd.filter(v => v.verdict === 'FAIL' && v.is_hard_stop)
    return <span className="text-xs" style={{ color: hs.length ? '#8b1a1a' : '#1a6b3c' }}>{hs.length ? `${hs.length} disqualifier${hs.length>1?'s':''}` : 'None'}</span>
  }},
  { key: 'nct',        label: 'NCT ID',         render: (t) => (
    <a href={t.url} target="_blank" rel="noreferrer"
       className="font-mono text-xs text-[#1a4f7a] hover:underline">{t.nct_id} ↗</a>
  )},
]

export default function ComparisonModal({ trials, onClose }) {
  const ref = useRef(null)

  useEffect(() => {
    ref.current?.focus()
    function onKey(e) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.5)' }}
      role="dialog"
      aria-modal="true"
      aria-label="Trial comparison"
    >
      <div
        ref={ref}
        tabIndex={-1}
        className="bg-white w-full max-w-5xl max-h-[90vh] flex flex-col outline-none"
        style={{ border: '1px solid #dedad4', borderTop: '3px solid #1a4f7a' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#e8e4de] flex-shrink-0">
          <div>
            <h2 className="font-serif text-lg text-[#1a1a1a]">Trial Comparison</h2>
            <p className="text-[11px] text-[#9b9b9b]">Side-by-side comparison of {trials.length} saved trials</p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close comparison"
            className="text-[#9b9b9b] hover:text-[#1a1a1a] transition-colors p-1"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Table */}
        <div className="overflow-auto flex-1">
          <table className="w-full border-collapse" style={{ tableLayout: 'fixed' }}>
            <thead>
              <tr className="border-b border-[#e8e4de]" style={{ background: '#f9f8f5' }}>
                <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-[#9b9b9b]"
                    style={{ width: 110 }}>Field</th>
                {trials.map(t => (
                  <th key={t.nct_id} className="text-left px-4 py-3">
                    <div className="text-xs font-semibold text-[#1a1a1a] leading-snug line-clamp-2">
                      {t.title}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row, ri) => (
                <tr key={row.key} style={{ background: ri % 2 === 0 ? 'white' : '#f9f8f5' }}
                    className="border-b border-[#f0ece6]">
                  <td className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-[#9b9b9b] align-top">
                    {row.label}
                  </td>
                  {trials.map(t => (
                    <td key={t.nct_id} className="px-4 py-3 align-top">
                      {row.render(t)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
