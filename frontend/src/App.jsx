import { useState } from 'react'
import { submitMatch } from './api'
import PatientForm from './components/PatientForm'
import Stepper     from './components/Stepper'
import StatsBanner from './components/StatsBanner'
import ProfileCard from './components/ProfileCard'
import TrialCard   from './components/TrialCard'

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-8 py-20">
      <div className="text-6xl mb-5">🔬</div>
      <h2 className="text-xl font-bold text-slate-800 mb-2">Ready to search</h2>
      <p className="text-sm text-slate-400 max-w-sm leading-relaxed">
        Fill in the patient details on the left and click <strong>Find Matching Trials</strong>.
        AI agents will search 400,000+ clinical trials and return a ranked shortlist.
      </p>
      <div className="mt-8 grid grid-cols-2 gap-3 w-full max-w-xs text-left">
        {[
          { icon: '🧠', label: 'Profile extraction', desc: 'Parses patient details' },
          { icon: '🔍', label: 'Trial search', desc: 'Queries ClinicalTrials.gov' },
          { icon: '⚖️', label: 'Eligibility check', desc: 'Criterion-by-criterion' },
          { icon: '📋', label: 'Report generation', desc: 'Patient & physician briefs' },
        ].map(s => (
          <div key={s.label} className="bg-white rounded-xl p-3 border border-slate-100 shadow-sm">
            <div className="text-xl mb-1">{s.icon}</div>
            <div className="text-xs font-semibold text-slate-700">{s.label}</div>
            <div className="text-[11px] text-slate-400">{s.desc}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function RunningPanel({ logs }) {
  return (
    <div className="p-6">
      <Stepper logs={logs} />
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Pipeline Running</span>
        </div>
        <div className="p-4 max-h-[420px] overflow-y-auto space-y-1.5">
          {logs.length === 0
            ? <p className="text-xs text-slate-400 italic">Initialising agents…</p>
            : logs.map((line, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className="text-slate-300 mt-0.5 flex-shrink-0">›</span>
                  <span className="text-slate-600">{line}</span>
                </div>
              ))
          }
        </div>
      </div>
    </div>
  )
}

function ResultsPanel({ result, logs, onReset }) {
  const ranked = result?.ranked_trials || []

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-900">Results</h2>
        <button onClick={onReset} className="btn-ghost">← New search</button>
      </div>

      <StatsBanner
        candidates={result.candidates_count}
        evaluated={result.evaluated_count}
        ranked={ranked.length}
        topScore={ranked[0]?.final_score ?? null}
      />

      {result.patient_profile && <ProfileCard profile={result.patient_profile} />}

      {ranked.length === 0 ? (
        <div className="alert-amber">
          No trials scored above the 30-point threshold. Try broadening the diagnosis or removing location constraints.
        </div>
      ) : (
        <div>
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
            Top {Math.min(ranked.length, 5)} Matches
          </p>
          {ranked.slice(0, 5).map((trial, i) => (
            <TrialCard key={trial.nct_id} trial={trial} rank={i + 1} />
          ))}
          {ranked.length > 5 && (
            <p className="text-center text-xs text-slate-400 mt-2">
              +{ranked.length - 5} more matches above threshold
            </p>
          )}
        </div>
      )}

      <details className="mt-2">
        <summary className="text-xs text-slate-400 cursor-pointer select-none hover:text-slate-600">
          Pipeline log ({logs.length} entries)
        </summary>
        <div className="mt-2 space-y-1 bg-slate-50 rounded-xl p-3">
          {logs.map((line, i) => (
            <p key={i} className="text-xs text-slate-500">
              <span className="text-slate-300 mr-1.5">›</span>{line}
            </p>
          ))}
        </div>
      </details>
    </div>
  )
}

export default function App() {
  const [phase,  setPhase]  = useState('form')
  const [logs,   setLogs]   = useState([])
  const [result, setResult] = useState(null)
  const [errMsg, setErrMsg] = useState('')

  async function handleSubmit(form) {
    setPhase('running')
    setLogs([])
    setResult(null)
    try {
      const data = await submitMatch(form)
      setLogs(data.log || [])
      setResult(data)
      setPhase('results')
    } catch (e) {
      setErrMsg(e.message)
      setPhase('error')
    }
  }

  function handleReset() {
    setPhase('form')
    setLogs([])
    setResult(null)
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">

      {/* Left column: form */}
      <div className="w-[460px] flex-shrink-0 flex flex-col border-r border-slate-200 bg-white overflow-hidden">
        <div className="bg-gradient-to-br from-slate-800 to-slate-700 px-6 pt-6 pb-5 flex-shrink-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">🔬</span>
            <h1 className="text-xl font-bold text-white tracking-tight">TrialMatch AI</h1>
          </div>
          <p className="text-slate-400 text-xs leading-relaxed">
            Clinical trial matching powered by LangGraph multi-agent AI.
            Fill in the patient's details to begin.
          </p>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-5">
          <PatientForm onSubmit={handleSubmit} loading={phase === 'running'} />
        </div>
      </div>

      {/* Right column: results */}
      <div className="flex-1 overflow-y-auto">
        {phase === 'form'    && <EmptyState />}
        {phase === 'running' && <RunningPanel logs={logs} />}
        {phase === 'results' && <ResultsPanel result={result} logs={logs} onReset={handleReset} />}
        {phase === 'error'   && (
          <div className="p-6">
            <div className="alert-red mb-4"><strong>Error:</strong> {errMsg}</div>
            <button onClick={handleReset} className="btn-primary max-w-xs">← Try again</button>
          </div>
        )}
      </div>
    </div>
  )
}
