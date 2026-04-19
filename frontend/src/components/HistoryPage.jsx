import { deleteHistory } from '../api'

function scoreTier(score) {
  if (!score) return { color: '#9b9b9b' }
  if (score >= 70) return { color: '#1a6b3c' }
  if (score >= 50) return { color: '#1a4f7a' }
  return { color: '#7d4e00' }
}

export default function HistoryPage({ history, onLoad, onRemove }) {
  if (!history.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-12 py-24">
        <svg className="w-10 h-10 text-[#dedad4] mb-4" fill="none" viewBox="0 0 24 24"
             stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round"
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <p className="text-sm text-[#9b9b9b]">No search history yet.</p>
        <p className="text-[11px] text-[#c0bbb4] mt-1">
          Every pipeline run is saved here automatically.
        </p>
      </div>
    )
  }

  async function handleRemove(e, historyId) {
    e.stopPropagation()
    await deleteHistory(historyId)
    onRemove(historyId)
  }

  return (
    <div className="p-8 space-y-4">
      <div>
        <h2 className="font-serif text-xl text-[#1a1a1a] mb-0.5">Search History</h2>
        <div className="w-6 h-px bg-[#1a4f7a]" />
      </div>
      <p className="text-[11px] text-[#9b9b9b]">{history.length} runs saved · click any row to restore results</p>

      <div className="space-y-1.5">
        {history.map(entry => {
          const tier = scoreTier(entry.top_score)
          const date = entry.created_at
            ? new Date(entry.created_at).toLocaleDateString('en-US', {
                month: 'short', day: 'numeric', year: 'numeric',
                hour: '2-digit', minute: '2-digit',
              })
            : ''

          return (
            <div
              key={entry.history_id}
              onClick={() => onLoad(entry)}
              className="bg-white border border-[#e8e4de] px-4 py-3 cursor-pointer
                         hover:border-[#c5d6e8] hover:bg-[#f8fafd] transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-[#1a1a1a] truncate">{entry.diagnosis}</div>
                  <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-0.5 text-[11px] text-[#9b9b9b]">
                    {entry.location && <span>{entry.location}</span>}
                    <span>{entry.ranked_count} match{entry.ranked_count !== 1 ? 'es' : ''}</span>
                    <span>{date}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3 flex-shrink-0">
                  {entry.top_score != null && (
                    <div className="text-center">
                      <div className="font-mono text-lg font-bold leading-none"
                           style={{ color: tier.color }}>
                        {Math.round(entry.top_score)}
                      </div>
                      <div className="font-mono text-[9px] text-[#9b9b9b]">top</div>
                    </div>
                  )}

                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-[#1a4f7a] font-medium">View →</span>
                    <button
                      onClick={e => handleRemove(e, entry.history_id)}
                      className="text-[10px] text-[#c0bbb4] hover:text-[#8b1a1a] transition-colors"
                      title="Remove from history"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
