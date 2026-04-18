import { useState } from 'react'

function ScoreBar({ label, value, color }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-slate-400 w-16 flex-shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(value, 100)}%`, background: color }} />
      </div>
      <span className="text-[10px] text-slate-500 w-5 text-right">{Math.round(value)}</span>
    </div>
  )
}

function scoreColor(score) {
  if (score >= 70) return 'from-emerald-500 to-emerald-400'
  if (score >= 50) return 'from-amber-500 to-amber-400'
  return 'from-red-500 to-red-400'
}

export default function TrialCard({ trial, rank }) {
  const [open, setOpen] = useState(false)
  const score    = trial.final_score || 0
  const breakdown = trial.eligibility_breakdown || []
  const nPass    = breakdown.filter(v => v.verdict === 'PASS').length
  const nFail    = breakdown.filter(v => v.verdict === 'FAIL').length
  const nUncert  = breakdown.filter(v => v.verdict === 'UNCERTAIN').length
  const phase    = (trial.phase || 'N/A').replace('PHASE', 'Phase ').replace('_', ' ')

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm mb-3 overflow-hidden">
      <div className="flex items-start gap-4 p-4">
        {/* Score ring */}
        <div className={`w-16 h-16 rounded-full bg-gradient-to-br ${scoreColor(score)} flex flex-col items-center justify-center text-white flex-shrink-0`}>
          <span className="text-lg font-bold leading-none">{Math.round(score)}</span>
          <span className="text-[9px] opacity-80">/100</span>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Match #{rank}</div>
          <div className="text-sm font-semibold text-slate-900 mt-0.5 mb-2 leading-snug">{trial.title}</div>
          <div className="flex flex-wrap gap-1.5 mb-2">
            <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-blue-50 text-blue-700">{phase}</span>
            {trial.sponsor && <span className="px-2 py-0.5 rounded-md text-[11px] bg-slate-100 text-slate-600">{trial.sponsor.slice(0, 30)}</span>}
            {trial.nearest_site_miles !== null && trial.nearest_site_miles !== undefined
              ? <span className="px-2 py-0.5 rounded-md text-[11px] bg-emerald-50 text-emerald-700">📍 {trial.nearest_site_miles} mi</span>
              : <span className="px-2 py-0.5 rounded-md text-[11px] bg-slate-100 text-slate-400">📍 dist unknown</span>
            }
            <a href={trial.url} target="_blank" rel="noreferrer"
               className="px-2 py-0.5 rounded-md text-[11px] font-semibold text-slate-500 hover:text-slate-800 border border-slate-200">
              {trial.nct_id} ↗
            </a>
          </div>
          <div className="space-y-1">
            <ScoreBar label="Eligibility" value={trial.eligibility_score || 0} color="#3b82f6" />
            <ScoreBar label="Logistics"   value={trial.logistics_score || 0}   color="#10b981" />
            <ScoreBar label="Quality"     value={trial.quality_score || 0}     color="#8b5cf6" />
          </div>
        </div>
      </div>

      {/* Eligibility summary bar */}
      <div className="flex items-center gap-3 px-4 py-2.5 bg-slate-50 border-t border-slate-100 text-xs">
        <span className="text-slate-400 font-medium">Eligibility:</span>
        <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-semibold">✓ {nPass} met</span>
        <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-semibold">⚠ {nUncert} uncertain</span>
        <span className="px-2 py-0.5 rounded-full bg-red-50 text-red-700 font-semibold">{nFail > 0 ? '🔴' : '🟢'} {nFail} disqualifiers</span>
        <button onClick={() => setOpen(o => !o)} className="ml-auto text-slate-400 hover:text-slate-600 font-medium">
          {open ? 'Hide ▲' : 'Details ▼'}
        </button>
      </div>

      {/* Expanded details */}
      {open && (
        <div className="p-4 border-t border-slate-100 space-y-4">
          {/* Hard fails */}
          {breakdown.filter(v => v.verdict === 'FAIL' && v.is_hard_stop).length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-xs text-red-800">
              <strong>Hard disqualifiers:</strong>
              {breakdown.filter(v => v.verdict === 'FAIL' && v.is_hard_stop).map((v, i) => (
                <div key={i} className="mt-1">• <strong>{v.criterion_text}</strong> — {v.reason}</div>
              ))}
            </div>
          )}

          {/* All criteria pills */}
          {breakdown.length > 0 && (
            <div>
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mb-2">All Criteria</div>
              <div className="flex flex-wrap gap-1">
                {breakdown.slice(0, 20).map((v, i) => {
                  const cls = v.verdict === 'PASS' ? 'bg-emerald-50 text-emerald-700 border-emerald-100'
                            : v.verdict === 'FAIL' ? 'bg-red-50 text-red-700 border-red-100'
                            : 'bg-amber-50 text-amber-700 border-amber-100'
                  const icon = v.verdict === 'PASS' ? '✓' : v.verdict === 'FAIL' ? '✗' : '⚠'
                  return (
                    <span key={i} className={`px-2 py-0.5 rounded-full text-[11px] font-medium border ${cls}`}>
                      {icon} {v.criterion_text?.slice(0, 50)}
                    </span>
                  )
                })}
              </div>
            </div>
          )}

          {/* Summary */}
          {trial.brief_summary && (
            <div>
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mb-1">Trial Summary</div>
              <p className="text-xs text-slate-600 leading-relaxed">{trial.brief_summary.slice(0, 500)}{trial.brief_summary.length > 500 ? '...' : ''}</p>
            </div>
          )}

          {/* Reports */}
          {(trial.patient_summary || trial.physician_brief || trial.outreach_email) && (
            <div className="space-y-3">
              {trial.patient_summary && (
                <div>
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mb-1">Patient Summary</div>
                  <div className="bg-slate-50 rounded-xl p-3 text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">{trial.patient_summary}</div>
                </div>
              )}
              {trial.physician_brief && (
                <div>
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mb-1">Physician Brief</div>
                  <div className="bg-slate-50 rounded-xl p-3 text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">{trial.physician_brief}</div>
                </div>
              )}
              {trial.outreach_email && (
                <div>
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mb-1">Outreach Email</div>
                  <div className="bg-slate-900 rounded-xl p-3 text-xs text-slate-300 font-mono leading-relaxed whitespace-pre-wrap">{trial.outreach_email}</div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
