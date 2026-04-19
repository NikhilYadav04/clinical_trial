import { useMemo } from 'react'

function StatCard({ label, value, sub, color = '#1a4f7a' }) {
  return (
    <div className="bg-white border border-[#e8e4de] p-4" style={{ borderTop: `2px solid ${color}` }}>
      <div className="font-mono text-2xl font-bold leading-none" style={{ color }}>{value}</div>
      <div className="text-[10px] font-semibold uppercase tracking-widest text-[#9b9b9b] mt-1">{label}</div>
      {sub && <div className="text-[11px] text-[#c0bbb4] mt-1">{sub}</div>}
    </div>
  )
}

function MiniBar({ value, max, color }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div className="flex-1 h-1.5 bg-[#f0ece6]">
      <div className="h-1.5 transition-all" style={{ width: `${pct}%`, background: color }} />
    </div>
  )
}

function ScoreSparkline({ entries }) {
  if (!entries.length) return null
  const scores = entries.map(e => e.top_score || 0)
  const max    = Math.max(...scores, 1)
  const W = 200, H = 48
  const pts = scores.map((s, i) => {
    const x = scores.length === 1 ? W / 2 : (i / (scores.length - 1)) * W
    const y = H - (s / max) * (H - 6) - 3
    return `${x},${y}`
  }).join(' ')

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: H }}>
      <polyline
        points={pts}
        fill="none"
        stroke="#1a4f7a"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {scores.map((s, i) => {
        const x = scores.length === 1 ? W / 2 : (i / (scores.length - 1)) * W
        const y = H - (s / max) * (H - 6) - 3
        return <circle key={i} cx={x} cy={y} r="2.5" fill="#1a4f7a" />
      })}
    </svg>
  )
}

export default function DashboardPage({ history }) {
  const stats = useMemo(() => {
    if (!history.length) return null
    const scores      = history.map(h => h.top_score).filter(Boolean)
    const avgScore    = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null
    const totalTrials = history.reduce((a, h) => a + (h.ranked_count || 0), 0)

    // Diagnosis frequency
    const diagCount = {}
    history.forEach(h => {
      const d = h.diagnosis || 'Unknown'
      diagCount[d] = (diagCount[d] || 0) + 1
    })
    const topDiagnoses = Object.entries(diagCount)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)

    // Score distribution
    const tiers = { Strong: 0, Moderate: 0, Weak: 0, Low: 0 }
    scores.forEach(s => {
      if (s >= 70) tiers.Strong++
      else if (s >= 50) tiers.Moderate++
      else if (s >= 30) tiers.Weak++
      else tiers.Low++
    })

    // Recent 10 for sparkline
    const recent = [...history].reverse().slice(0, 10)

    return { avgScore, totalTrials, topDiagnoses, tiers, recent }
  }, [history])

  if (!history.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-12 py-24">
        <svg className="w-10 h-10 text-[#dedad4] mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round"
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
        </svg>
        <p className="text-sm text-[#9b9b9b]">No data yet.</p>
        <p className="text-[11px] text-[#c0bbb4] mt-1">Run a search to see analytics here.</p>
      </div>
    )
  }

  const TIER_COLORS = {
    Strong: '#1a6b3c', Moderate: '#1a4f7a', Weak: '#7d4e00', Low: '#8b1a1a',
  }
  const maxDiag = stats.topDiagnoses[0]?.[1] || 1

  return (
    <div className="p-8 space-y-6" role="main" aria-label="Analytics Dashboard">

      {/* Header */}
      <div>
        <h2 className="font-serif text-xl text-[#1a1a1a] mb-0.5">Analytics</h2>
        <div className="w-6 h-px bg-[#1a4f7a]" />
        <p className="text-[11px] text-[#9b9b9b] mt-2">Based on {history.length} search{history.length !== 1 ? 'es' : ''}</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard
          label="Total Searches"
          value={history.length}
          sub="all time"
          color="#1a4f7a"
        />
        <StatCard
          label="Avg Top Score"
          value={stats.avgScore !== null ? `${stats.avgScore}/100` : '—'}
          sub="across all runs"
          color={stats.avgScore >= 70 ? '#1a6b3c' : stats.avgScore >= 50 ? '#1a4f7a' : '#7d4e00'}
        />
        <StatCard
          label="Trials Matched"
          value={stats.totalTrials}
          sub="total across searches"
          color="#5b2d8e"
        />
      </div>

      {/* Score trend sparkline */}
      <div className="bg-white border border-[#e8e4de] p-4" style={{ borderTop: '2px solid #1a4f7a' }}>
        <div className="text-[10px] font-semibold uppercase tracking-widest text-[#9b9b9b] mb-3">
          Top Score Trend · Last {stats.recent.length} searches
        </div>
        <ScoreSparkline entries={stats.recent} />
        <div className="flex justify-between text-[10px] text-[#c0bbb4] mt-1">
          <span>Oldest</span>
          <span>Most Recent</span>
        </div>
      </div>

      {/* Score tier distribution */}
      <div className="bg-white border border-[#e8e4de] p-4">
        <div className="text-[10px] font-semibold uppercase tracking-widest text-[#9b9b9b] mb-3">
          Match Quality Distribution
        </div>
        <div className="space-y-2.5">
          {Object.entries(stats.tiers).map(([tier, count]) => (
            <div key={tier} className="flex items-center gap-3">
              <span className="text-[11px] font-medium w-16 flex-shrink-0" style={{ color: TIER_COLORS[tier] }}>
                {tier}
              </span>
              <MiniBar value={count} max={Math.max(...Object.values(stats.tiers), 1)} color={TIER_COLORS[tier]} />
              <span className="font-mono text-[11px] text-[#6b6b6b] w-4 text-right">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Top diagnoses */}
      <div className="bg-white border border-[#e8e4de] p-4">
        <div className="text-[10px] font-semibold uppercase tracking-widest text-[#9b9b9b] mb-3">
          Most Searched Diagnoses
        </div>
        <div className="space-y-2">
          {stats.topDiagnoses.map(([diag, count]) => (
            <div key={diag} className="flex items-center gap-3">
              <span className="text-[11px] text-[#4a4a4a] flex-1 truncate">{diag}</span>
              <MiniBar value={count} max={maxDiag} color="#1a4f7a" />
              <span className="font-mono text-[11px] text-[#9b9b9b] w-4 text-right">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Recent searches table */}
      <div className="bg-white border border-[#e8e4de]">
        <div className="px-4 py-3 border-b border-[#e8e4de]">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-[#9b9b9b]">Recent Searches</div>
        </div>
        <div className="divide-y divide-[#f0ece6]">
          {[...history].slice(0, 8).map((h, i) => {
            const score = h.top_score
            const color = score >= 70 ? '#1a6b3c' : score >= 50 ? '#1a4f7a' : score >= 30 ? '#7d4e00' : '#8b1a1a'
            const date  = h.created_at
              ? new Date(h.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
              : ''
            return (
              <div key={i} className="flex items-center gap-3 px-4 py-2.5 text-[11px]">
                <span className="text-[#c0bbb4] font-mono w-4">{i + 1}</span>
                <span className="flex-1 text-[#4a4a4a] truncate">{h.diagnosis}</span>
                {h.location && <span className="text-[#9b9b9b] truncate max-w-[100px]">{h.location}</span>}
                <span className="font-mono font-semibold" style={{ color }}>
                  {score ? `${Math.round(score)}` : '—'}
                </span>
                <span className="text-[#c0bbb4]">{date}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
