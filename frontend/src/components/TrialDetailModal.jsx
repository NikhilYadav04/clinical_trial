import { useEffect, useRef } from 'react'

function scoreTier(score) {
  if (score >= 70) return { accent: '#1a6b3c', label: 'Strong',   bg: '#f4fbf6' }
  if (score >= 50) return { accent: '#1a4f7a', label: 'Moderate', bg: '#f3f7fc' }
  if (score >= 30) return { accent: '#7d4e00', label: 'Weak',     bg: '#fdf8f0' }
  return               { accent: '#8b1a1a', label: 'Low',      bg: '#fdf5f5' }
}

function ScoreBar({ label, value, color }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-[10px] text-[#9b9b9b] uppercase tracking-wider w-20 flex-shrink-0">{label}</span>
      <div className="flex-1 h-1 bg-[#e8e4de] relative">
        <div className="absolute top-0 left-0 h-1"
             style={{ width: `${Math.min(value || 0, 100)}%`, background: color }} />
      </div>
      <span className="font-mono text-[11px] text-[#4a4a4a] w-6 text-right">{Math.round(value || 0)}</span>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-[0.15em] text-[#9b9b9b] mb-2">{title}</div>
      {children}
    </div>
  )
}

export default function TrialDetailModal({ trial, onClose }) {
  const ref = useRef(null)

  useEffect(() => {
    ref.current?.focus()
    function onKey(e) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const score     = trial.final_score || trial.score || 0
  const tier      = scoreTier(score)
  const phase     = (trial.phase || 'N/A').replace('PHASE','Ph ').replace('EARLY_','Early ').replace('_',' ')
  const breakdown = trial.eligibility_breakdown || []
  const nPass     = breakdown.filter(v => v.verdict === 'PASS').length
  const nFail     = breakdown.filter(v => v.verdict === 'FAIL').length
  const nUncert   = breakdown.filter(v => v.verdict === 'UNCERTAIN').length
  const hardStops = breakdown.filter(v => v.verdict === 'FAIL' && v.is_hard_stop)
  const locations = trial.locations || []

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.55)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
      role="dialog"
      aria-modal="true"
      aria-label={`Trial details: ${trial.title}`}
    >
      <div
        ref={ref}
        tabIndex={-1}
        className="bg-white w-full max-w-3xl max-h-[92vh] flex flex-col outline-none"
        style={{ border: '1px solid #dedad4', borderTop: `3px solid ${tier.accent}` }}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 px-6 py-4 border-b border-[#e8e4de] flex-shrink-0"
             style={{ background: tier.bg }}>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-1">
              <span className="font-mono text-2xl font-bold" style={{ color: tier.accent }}>{Math.round(score)}</span>
              <span className="font-mono text-[11px] text-[#9b9b9b]">/100</span>
              <span className="text-[10px] font-semibold uppercase tracking-widest px-1.5 py-0.5"
                    style={{ color: tier.accent, background: 'white', border: `1px solid ${tier.accent}` }}>
                {tier.label}
              </span>
              <span className="font-mono text-[11px] text-[#6b6b6b]">{phase}</span>
            </div>
            <h2 className="text-base font-semibold text-[#1a1a1a] leading-snug">{trial.title}</h2>
            {trial.sponsor && (
              <p className="text-[11px] text-[#9b9b9b] mt-0.5">{trial.sponsor}</p>
            )}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {trial.url && (
              <a href={trial.url} target="_blank" rel="noreferrer"
                 aria-label={`Open ${trial.nct_id} on ClinicalTrials.gov`}
                 className="font-mono text-xs text-[#1a4f7a] hover:underline border border-[#c5d6e8] px-2 py-1">
                {trial.nct_id} ↗
              </a>
            )}
            <button
              onClick={onClose}
              aria-label="Close trial details"
              className="text-[#9b9b9b] hover:text-[#1a1a1a] transition-colors p-1"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 px-6 py-5 space-y-5">

          {/* Score bars */}
          <Section title="Score Breakdown">
            <div className="space-y-2.5">
              <ScoreBar label="Eligibility" value={trial.eligibility_score} color="#1a4f7a" />
              <ScoreBar label="Logistics"   value={trial.logistics_score}   color="#1a6b3c" />
              <ScoreBar label="Quality"     value={trial.quality_score}     color="#5b2d8e" />
            </div>
          </Section>

          {/* Criteria summary */}
          {breakdown.length > 0 && (
            <Section title={`Eligibility Criteria · ${breakdown.length} total`}>
              <div className="flex gap-4 text-xs mb-3">
                <span style={{ color: '#1a6b3c' }}>{nPass} passed</span>
                <span style={{ color: '#7d4e00' }}>{nUncert} uncertain</span>
                <span style={{ color: '#8b1a1a' }}>{nFail} failed</span>
              </div>

              {hardStops.length > 0 && (
                <div className="p-3 mb-3" style={{ border: '1px solid #c97b7b', background: '#fff5f5' }}>
                  <div className="text-[10px] font-semibold uppercase tracking-widest mb-1.5" style={{ color: '#8b1a1a' }}>
                    Hard Disqualifiers
                  </div>
                  {hardStops.map((v, i) => (
                    <div key={i} className="text-xs mt-1 pl-2 border-l" style={{ color: '#8b1a1a', borderColor: '#c97b7b' }}>
                      <strong>{v.criterion_text}</strong> — {v.reason}
                    </div>
                  ))}
                </div>
              )}

              <div className="flex flex-wrap gap-1" role="list" aria-label="Eligibility criteria">
                {breakdown.map((v, i) => {
                  const cls = v.verdict === 'PASS'
                    ? 'bg-[#eef6f0] text-[#1a6b3c] border-[#b8dfc5]'
                    : v.verdict === 'FAIL'
                    ? 'bg-[#fff5f5] text-[#8b1a1a] border-[#c97b7b]'
                    : 'bg-[#fdf6e8] text-[#7d4e00] border-[#e8d5a0]'
                  const icon = v.verdict === 'PASS' ? '✓' : v.verdict === 'FAIL' ? '✗' : '?'
                  return (
                    <span key={i} role="listitem"
                          title={v.reason}
                          className={`px-2 py-0.5 border text-[11px] font-medium cursor-default ${cls}`}>
                      {icon} {v.criterion_text?.slice(0, 60)}
                    </span>
                  )
                })}
              </div>
            </Section>
          )}

          {/* Trial summary */}
          {trial.brief_summary && (
            <Section title="Trial Summary">
              <p className="text-xs text-[#4a4a4a] leading-relaxed">{trial.brief_summary}</p>
            </Section>
          )}

          {/* Locations */}
          {locations.length > 0 && (
            <Section title={`Trial Sites · ${locations.length} location${locations.length !== 1 ? 's' : ''}`}>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {locations.map((loc, i) => {
                  const locStr = typeof loc === 'string' ? loc : [loc.city, loc.state, loc.country].filter(Boolean).join(', ')
                  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(locStr)}`
                  return (
                    <div key={i} className="flex items-center gap-2 text-xs text-[#4a4a4a]">
                      <svg className="w-3 h-3 text-[#9b9b9b] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                      </svg>
                      <span>{locStr}</span>
                      <a href={mapsUrl} target="_blank" rel="noreferrer"
                         className="text-[#1a4f7a] hover:underline text-[10px]" aria-label={`Open ${locStr} in Google Maps`}>
                        map ↗
                      </a>
                    </div>
                  )
                })}
              </div>
              {trial.nearest_site_miles != null && (
                <div className="mt-2 text-[11px]" style={{ color: '#1a6b3c' }}>
                  Nearest site: {trial.nearest_site_miles} mi from patient location
                </div>
              )}
            </Section>
          )}

          {/* Patient summary */}
          {trial.patient_summary && (
            <Section title="Patient Summary">
              <div className="bg-[#f3f7fc] border border-[#c5d6e8] p-3 text-xs text-[#4a4a4a] leading-relaxed whitespace-pre-wrap">
                {trial.patient_summary}
              </div>
            </Section>
          )}

          {/* Physician brief */}
          {trial.physician_brief && (
            <Section title="Physician Brief">
              <div className="bg-[#f7f3fc] border border-[#d0bde8] p-3 text-xs text-[#4a4a4a] leading-relaxed whitespace-pre-wrap">
                {trial.physician_brief}
              </div>
            </Section>
          )}

          {/* Outreach email */}
          {trial.outreach_email && (
            <Section title="Outreach Email Draft">
              <div className="bg-[#0d1117] border border-[#333] p-3 text-xs text-[#9b9b9b] font-mono leading-relaxed whitespace-pre-wrap">
                {trial.outreach_email}
              </div>
            </Section>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#e8e4de] flex justify-end flex-shrink-0" style={{ background: '#f9f8f5' }}>
          <button
            onClick={onClose}
            className="text-xs text-[#6b6b6b] hover:text-[#1a1a1a] border border-[#dedad4] hover:border-[#c5c0b8] px-4 py-1.5 transition-colors"
            style={{ borderRadius: 0 }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
