import { useState, useRef, useEffect, useCallback } from 'react'
import {
  startMatch, streamMatch,
  getBookmarks, addBookmark, removeBookmark,
  getFeedback, submitFeedback, deleteFeedback,
  getSavedPatients, savePatient, deletePatient,
  getHistory, saveHistory, deleteHistory,
  getNotes, saveNote,
  exportPdf, exportCsv,
  getMe, logout, getToken, clearToken, setUnauthorizedHandler,
} from './api'
import AuthPage from './components/AuthPage'
import PatientForm    from './components/PatientForm'
import Stepper        from './components/Stepper'
import StatsBanner    from './components/StatsBanner'
import ProfileCard    from './components/ProfileCard'
import TrialCard      from './components/TrialCard'
import StageDetails   from './components/StageDetails'
import BookmarksPage  from './components/BookmarksPage'
import HistoryPage    from './components/HistoryPage'
import DashboardPage  from './components/DashboardPage'
import TrialDetailModal from './components/TrialDetailModal'
import OnboardingTour   from './components/OnboardingTour'

// ── Stage detection ───────────────────────────────────────────────────────────
const STAGE_MARKERS = [
  { marker: '[Patient Profile Agent]', stage: 0 },
  { marker: '[Trial Search Agent]',    stage: 1 },
  { marker: '[Evaluation Node]',       stage: 2 },
  { marker: '[Evaluator]',             stage: 2 },
  { marker: '[Eligibility',            stage: 2 },
  { marker: '[Ranking Node]',          stage: 3 },
  { marker: '[Report Node]',           stage: 4 },
]
function detectStage(line) {
  for (const { marker, stage } of STAGE_MARKERS) {
    if (line.includes(marker)) return stage
  }
  return null
}

// ── Scrollable sidebar ────────────────────────────────────────────────────────
function ScrollableSidebar({ children }) {
  const ref = useRef(null)
  const [canScroll, setCanScroll] = useState(false)
  const [atBottom,  setAtBottom]  = useState(false)

  const check = useCallback(() => {
    const el = ref.current
    if (!el) return
    setCanScroll(el.scrollHeight > el.clientHeight)
    setAtBottom(el.scrollHeight - el.scrollTop <= el.clientHeight + 4)
  }, [])

  useEffect(() => {
    const el = ref.current
    if (!el) return
    check()
    el.addEventListener('scroll', check)
    const ro = new ResizeObserver(check)
    ro.observe(el)
    return () => { el.removeEventListener('scroll', check); ro.disconnect() }
  }, [check])

  return (
    <div className="relative flex-1 overflow-hidden">
      <div ref={ref} className="h-full overflow-y-auto px-5 py-5">{children}</div>
      {canScroll && !atBottom && (
        <button
          onClick={() => ref.current?.scrollBy({ top: 200, behavior: 'smooth' })}
          className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-1.5
                     bg-white border border-[#dedad4] shadow-sm px-3 py-1.5
                     text-[11px] text-[#6b6b6b] hover:text-[#1a1a1a] hover:border-[#c5c0b8] transition-colors"
          style={{ borderRadius: 0 }}
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7"/>
          </svg>
          scroll down
        </button>
      )}
    </div>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────
function EmptyState() {
  return (
    <div className="flex flex-col justify-center h-full px-12 py-16 max-w-lg">
      <h2 className="font-serif text-2xl text-[#1a1a1a] mb-2 leading-tight">
        Clinical Trial<br/>Matching
      </h2>
      <div className="w-8 h-px bg-[#1a4f7a] mb-4" />
      <p className="text-sm text-[#6b6b6b] leading-relaxed mb-8">
        Complete the patient intake form and submit. The pipeline searches 400,000+ trials,
        evaluates eligibility criterion by criterion, and returns a ranked shortlist.
      </p>
      <div className="border-t border-[#e8e4de]">
        {[
          { n: '01', label: 'Patient Profile Extraction',   desc: 'LLM parses clinical notes into a structured profile.' },
          { n: '02', label: 'Trial Discovery',               desc: 'ClinicalTrials.gov queried for recruiting matches.' },
          { n: '03', label: 'Eligibility Evaluation',        desc: 'Each criterion assessed. Hard exclusions applied.' },
          { n: '04', label: 'Scoring & Ranking',             desc: 'Eligibility 60% · Quality 20% · Logistics 10% · Biomarker 10%' },
          { n: '05', label: 'Report Generation',             desc: 'Patient summary and physician brief for top matches.' },
        ].map(s => (
          <div key={s.n} className="flex gap-4 py-3 border-b border-[#e8e4de]">
            <span className="font-mono text-[11px] text-[#c0bbb4] mt-0.5 w-5 flex-shrink-0">{s.n}</span>
            <div>
              <div className="text-xs font-semibold text-[#1a1a1a] mb-0.5">{s.label}</div>
              <div className="text-[11px] text-[#9b9b9b] leading-relaxed">{s.desc}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Running panel ─────────────────────────────────────────────────────────────
function RunningPanel({ logs, activeStep, completedSteps }) {
  const logRef = useRef(null)
  useEffect(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight }, [logs])

  return (
    <div className="p-8 space-y-5">
      <div>
        <h2 className="font-serif text-xl text-[#1a1a1a] mb-0.5">Pipeline Running</h2>
        <div className="w-6 h-px bg-[#1a4f7a]" />
      </div>
      <Stepper activeStep={activeStep} completedSteps={completedSteps} />
      <div className="border border-[#3a3a3a] overflow-hidden">
        <div className="bg-[#1a1a1a] px-4 py-2 flex items-center gap-2.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-mono text-[10px] text-[#6b6b6b] uppercase tracking-widest">Agent Output</span>
          <span className="ml-auto font-mono text-[10px] text-[#4a4a4a]">{logs.length} lines</span>
        </div>
        <div ref={logRef} className="bg-[#0d1117] px-4 py-4 max-h-[520px] overflow-y-auto space-y-0.5"
             role="log" aria-live="polite" aria-label="Agent pipeline output">
          {logs.length === 0
            ? <p className="font-mono text-xs text-[#4a4a4a] italic">Initialising pipeline…</p>
            : logs.map((line, i) => {
                const isAgent = line.startsWith('[') && (line.includes('Agent]') || line.includes('Node]'))
                return (
                  <div key={i} className={`font-mono text-[11px] leading-5 ${isAgent ? 'text-[#7dd3a8] mt-2 first:mt-0' : 'text-[#6b7280]'}`}>
                    {!isAgent && <span className="text-[#333] mr-2 select-none">›</span>}
                    {line}
                  </div>
                )
              })
          }
        </div>
      </div>
    </div>
  )
}

// ── Results panel ─────────────────────────────────────────────────────────────
function ResultsPanel({ result, logs, onReset, bookmarkedIds, onBookmarkToggle,
                        feedbackMap, onFeedback, notesMap, onNote,
                        onExportPdf, pdfLoading, onExportCsv, onTrialDetail }) {
  const ranked = result?.ranked_trials || []

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-serif text-xl text-[#1a1a1a] mb-0.5">Match Results</h2>
          <div className="w-6 h-px bg-[#1a4f7a]" />
        </div>
        <div className="flex items-center gap-2 mt-1">
          <button onClick={onExportCsv}
                  aria-label="Export results as CSV"
                  className="flex items-center gap-1.5 text-xs text-[#6b6b6b] hover:text-[#1a1a1a] font-medium
                             border border-[#dedad4] hover:border-[#c5c0b8] px-3 py-1.5 transition-colors"
                  style={{ borderRadius: 0 }}>
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6M3 21h18M3 10l9-7 9 7"/>
            </svg>
            CSV
          </button>
          <button onClick={onExportPdf} disabled={pdfLoading}
                  aria-label="Export results as PDF"
                  className="flex items-center gap-1.5 text-xs text-[#6b6b6b] hover:text-[#1a1a1a] font-medium
                             border border-[#dedad4] hover:border-[#c5c0b8] px-3 py-1.5 transition-colors disabled:opacity-40"
                  style={{ borderRadius: 0 }}>
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            {pdfLoading ? 'Generating…' : 'PDF'}
          </button>
          <button onClick={onReset} className="btn-ghost">← New search</button>
        </div>
      </div>

      {/* Patient & summary zone */}
      <div className="space-y-3 p-4" style={{
        background: '#f3f7fc', border: '1px solid #c5d6e8', borderLeft: '3px solid #1a4f7a',
      }}>
        <div className="text-[10px] font-semibold uppercase tracking-[0.15em]" style={{ color: '#1a4f7a' }}>
          Patient &amp; Pipeline Summary
        </div>
        <StatsBanner
          candidates={result.candidates_count}
          evaluated={result.evaluated_count}
          ranked={ranked.length}
          topScore={ranked[0]?.final_score ?? null}
        />
        {result.patient_profile && <ProfileCard profile={result.patient_profile} />}
      </div>

      {/* Matches zone */}
      {ranked.length === 0 ? (
        <div className="alert-amber">
          No trials scored above the 30-point threshold. Try broadening the diagnosis or removing location constraints.
        </div>
      ) : (
        <div>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-0.5 h-4 bg-[#1a6b3c]" />
            <div className="text-[10px] font-semibold uppercase tracking-[0.15em] text-[#1a6b3c]">
              Top {Math.min(ranked.length, 5)} Matches
            </div>
            <div className="flex-1 h-px bg-[#d5edde]" />
          </div>
          {ranked.slice(0, 5).map((trial, i) => (
            <TrialCard
              key={trial.nct_id}
              trial={trial}
              rank={i + 1}
              isBookmarked={bookmarkedIds.has(trial.nct_id)}
              onBookmarkToggle={onBookmarkToggle}
              feedback={feedbackMap[trial.nct_id] || null}
              onFeedback={verdict => onFeedback(trial.nct_id, verdict)}
              note={notesMap[trial.nct_id] || ''}
              onNote={text => onNote(trial.nct_id, text)}
              onDetail={() => onTrialDetail(trial)}
            />
          ))}
          {ranked.length > 5 && (
            <p className="text-center text-xs text-[#9b9b9b] mt-2">
              +{ranked.length - 5} additional matches above threshold
            </p>
          )}
        </div>
      )}

      <div className="h-px bg-[#e8e4de]" />
      <StageDetails logs={logs} result={result} />
    </div>
  )
}

// ── Nav button ────────────────────────────────────────────────────────────────
function NavBtn({ active, onClick, icon, label, badge }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1.5 border transition-colors
        ${active
          ? 'border-[#1a4f7a] text-[#1a4f7a] bg-[#eef3f8]'
          : 'border-[#dedad4] text-[#9b9b9b] hover:text-[#1a1a1a] hover:border-[#c5c0b8]'}`}
      style={{ borderRadius: 0 }}
    >
      {icon}
      {label}
      {badge > 0 && (
        <span className="font-mono text-[10px] bg-[#1a4f7a] text-white px-1 py-0.5 leading-none">{badge}</span>
      )}
    </button>
  )
}

// ── Root ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [user,           setUser]           = useState(null)
  const [authLoading,    setAuthLoading]    = useState(true)

  const [phase,          setPhase]          = useState('form')
  const [logs,           setLogs]           = useState([])
  const [result,         setResult]         = useState(null)
  const [errMsg,         setErrMsg]         = useState('')
  const [activeStep,     setActiveStep]     = useState(0)
  const [completedSteps, setCompletedSteps] = useState(new Set())
  const [view,           setView]           = useState('main')

  const [bookmarks,      setBookmarks]      = useState([])
  const [feedbackMap,    setFeedbackMap]    = useState({})
  const [notesMap,       setNotesMap]       = useState({})
  const [savedPatients,  setSavedPatients]  = useState([])
  const [history,        setHistory]        = useState([])
  const [pdfLoading,     setPdfLoading]     = useState(false)
  const [detailTrial,    setDetailTrial]    = useState(null)

  const esRef = useRef(null)

  // ── On mount: validate token ──
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null)
      resetUserData()
    })
    if (!getToken()) { setAuthLoading(false); return }
    getMe()
      .then(u => { setUser(u); loadUserData() })
      .catch(() => { clearToken() })
      .finally(() => setAuthLoading(false))
  }, [])

  function resetUserData() {
    setBookmarks([]); setFeedbackMap({}); setNotesMap({})
    setSavedPatients([]); setHistory([])
  }

  function loadUserData() {
    getBookmarks().then(setBookmarks).catch(() => {})
    getFeedback().then(items => {
      const map = {}
      items.forEach(f => { map[f.nct_id] = f.verdict })
      setFeedbackMap(map)
    }).catch(() => {})
    getSavedPatients().then(setSavedPatients).catch(() => {})
    getHistory().then(setHistory).catch(() => {})
    getNotes().then(items => {
      const map = {}
      items.forEach(n => { map[n.nct_id] = n.note })
      setNotesMap(map)
    }).catch(() => {})
  }

  function handleAuth(newUser) {
    setUser(newUser)
    loadUserData()
  }

  function handleLogout() {
    esRef.current?.close()
    logout()
    setUser(null)
    resetUserData()
    setPhase('form')
    setView('main')
    setResult(null)
    setLogs([])
  }

  // ── Auth gate ──
  if (authLoading) {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: '#f7f6f2' }}>
        <div className="flex flex-col items-center gap-3">
          <div className="w-5 h-5 border-2 border-[#1a4f7a]/30 border-t-[#1a4f7a] rounded-full animate-spin" />
          <span className="font-mono text-[11px] text-[#9b9b9b]">Loading…</span>
        </div>
      </div>
    )
  }

  if (!user) return <AuthPage onAuth={handleAuth} />

  const bookmarkedIds = new Set(bookmarks.map(b => b.nct_id))

  // ── Bookmark handlers ──
  async function handleBookmarkToggle(trial, shouldAdd) {
    if (shouldAdd) {
      const bm = {
        nct_id: trial.nct_id, title: trial.title,
        score: trial.final_score || 0, phase: trial.phase,
        sponsor: trial.sponsor, url: trial.url,
        patient_context: result?.patient_profile
          ? { diagnosis: result.patient_profile.diagnosis, location: result.patient_profile.location }
          : null,
        trial_data: trial,
      }
      await addBookmark(bm)
      setBookmarks(prev => [...prev, { ...bm, bookmarked_at: new Date().toISOString() }])
    } else {
      await removeBookmark(trial.nct_id)
      setBookmarks(prev => prev.filter(b => b.nct_id !== trial.nct_id))
    }
  }

  // ── Feedback handlers ──
  async function handleFeedback(nctId, verdict) {
    if (verdict === null) {
      await deleteFeedback(nctId)
      setFeedbackMap(prev => { const n = { ...prev }; delete n[nctId]; return n })
    } else {
      await submitFeedback({ nct_id: nctId, verdict })
      setFeedbackMap(prev => ({ ...prev, [nctId]: verdict }))
    }
  }

  // ── Notes handler ──
  async function handleNote(nctId, text) {
    await saveNote({ nct_id: nctId, note: text })
    setNotesMap(prev => ({ ...prev, [nctId]: text }))
  }

  // ── Patient record handlers ──
  async function handleSavePatient(label, formData) {
    const patient = await savePatient({ label, form_data: formData })
    setSavedPatients(prev => [...prev, patient])
  }

  // ── History handlers ──
  function handleLoadHistory(entry) {
    setResult(entry.result)
    setLogs(entry.result.log || [])
    setCompletedSteps(new Set([0, 1, 2, 3, 4]))
    setPhase('results')
    setView('main')
  }

  // ── PDF export ──
  async function handleExportPdf() {
    if (!result) return
    setPdfLoading(true)
    try { await exportPdf(result) } catch (e) { console.error(e) } finally { setPdfLoading(false) }
  }

  // ── CSV export ──
  async function handleExportCsv() {
    if (!result) return
    try { await exportCsv(result) } catch (e) { console.error(e) }
  }

  // ── Submit ──
  async function handleSubmit(form) {
    setPhase('running')
    setView('main')
    setLogs([])
    setResult(null)
    setActiveStep(0)
    setCompletedSteps(new Set())
    try {
      const jobId = await startMatch(form)
      esRef.current = streamMatch(jobId, {
        onLog(line) {
          setLogs(prev => [...prev, line])
          const stage = detectStage(line)
          if (stage !== null) {
            setActiveStep(stage)
            setCompletedSteps(prev => {
              const next = new Set(prev)
              for (let i = 0; i < stage; i++) next.add(i)
              return next
            })
          }
        },
        onDone(data) {
          setLogs(prev => [...prev, '✓ Pipeline complete'])
          setCompletedSteps(new Set([0, 1, 2, 3, 4]))
          setResult(data)
          setPhase('results')
          // Auto-save to history
          const p = data.patient_profile
          saveHistory({
            diagnosis:    p?.diagnosis || 'Unknown',
            location:     p?.location  || null,
            ranked_count: data.ranked_trials?.length || 0,
            top_score:    data.ranked_trials?.[0]?.final_score || null,
            result:       data,
          }).then(entry => setHistory(prev => [entry, ...prev])).catch(() => {})
        },
        onError(msg) { setErrMsg(msg); setPhase('error') },
      })
    } catch (e) {
      setErrMsg(e.message)
      setPhase('error')
    }
  }

  function handleReset() {
    esRef.current?.close()
    setPhase('form')
    setView('main')
    setLogs([])
    setResult(null)
    setActiveStep(0)
    setCompletedSteps(new Set())
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#f7f6f2' }}>
      {/* Skip nav for keyboard accessibility */}
      <a href="#main-content"
         className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-3 focus:py-1.5 focus:bg-white focus:border focus:border-[#1a4f7a] focus:text-xs">
        Skip to main content
      </a>

      {/* ── Left sidebar ── */}
      <div className="w-[460px] flex-shrink-0 flex flex-col border-r border-[#e0ddd8] bg-white overflow-hidden"
           role="complementary" aria-label="Patient form and navigation">

        {/* Header */}
        <div className="flex-shrink-0 border-b border-[#e8e4de]">
          {/* Title row */}
          <div className="px-5 pt-4 pb-2 flex items-center justify-between">
            <div>
              <div className="flex items-baseline gap-2">
                <span className="font-serif text-lg font-bold text-[#1a1a1a] leading-none">TrialMatch</span>
                <span className="text-[10px] font-semibold text-[#9b9b9b] uppercase tracking-widest">Beta</span>
              </div>
              <p className="text-[11px] text-[#9b9b9b] mt-0.5">
                Signed in as <span className="text-[#1a4f7a] font-medium">{user.name}</span>
              </p>
            </div>
            <button
              onClick={handleLogout}
              aria-label="Sign out of TrialMatch"
              className="text-[10px] text-[#c0bbb4] hover:text-[#8b1a1a] transition-colors px-2 py-1 border border-transparent hover:border-[#c97b7b] flex-shrink-0"
              style={{ borderRadius: 0 }}
            >
              Sign out
            </button>
          </div>

          {/* Scrollable tab strip */}
          <nav
            className="flex overflow-x-auto border-t border-[#f0ece6]"
            style={{ scrollbarWidth: 'none' }}
            aria-label="Main navigation"
          >
            {[
              {
                key: 'main', label: 'Search',
                icon: <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>,
              },
              {
                key: 'bookmarks', label: 'Saved', badge: bookmarks.length,
                icon: <svg className="w-3.5 h-3.5" fill={view === 'bookmarks' ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/></svg>,
              },
              {
                key: 'history', label: 'History', badge: history.length,
                icon: <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>,
              },
              {
                key: 'dashboard', label: 'Analytics',
                icon: <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>,
              },
            ].map(({ key, label, icon, badge }) => {
              const active = view === key || (key === 'main' && view === 'main')
              return (
                <button
                  key={key}
                  onClick={() => setView(v => key === 'main' ? 'main' : (v === key ? 'main' : key))}
                  aria-current={active ? 'page' : undefined}
                  className="flex items-center gap-1.5 px-4 py-2.5 text-[11px] font-medium whitespace-nowrap flex-shrink-0 border-b-2 transition-colors"
                  style={{
                    borderBottomColor: active ? '#1a4f7a' : 'transparent',
                    color:             active ? '#1a4f7a' : '#9b9b9b',
                    background:        active ? '#f3f7fc' : 'transparent',
                  }}
                >
                  {icon}
                  {label}
                  {badge > 0 && (
                    <span className="font-mono text-[9px] bg-[#1a4f7a] text-white px-1 py-0.5 leading-none">{badge}</span>
                  )}
                </button>
              )
            })}
          </nav>
        </div>

        {/* Scrollable form */}
        <ScrollableSidebar>
          <PatientForm
            onSubmit={handleSubmit}
            loading={phase === 'running'}
            savedPatients={savedPatients}
            onSavePatient={handleSavePatient}
            onDeletePatient={async id => {
              await deletePatient(id)
              setSavedPatients(prev => prev.filter(p => p.patient_id !== id))
            }}
          />
        </ScrollableSidebar>
      </div>

      {/* ── Right panel ── */}
      <div id="main-content" className="flex-1 overflow-y-auto relative" style={{ background: '#f7f6f2' }}>
        {view === 'bookmarks' && (
          <BookmarksPage
            bookmarks={bookmarks}
            notesMap={notesMap}
            onRemove={nctId => setBookmarks(prev => prev.filter(b => b.nct_id !== nctId))}
            onDetail={setDetailTrial}
          />
        )}
        {view === 'history' && (
          <HistoryPage
            history={history}
            onLoad={handleLoadHistory}
            onRemove={historyId => setHistory(prev => prev.filter(h => h.history_id !== historyId))}
          />
        )}
        {view === 'dashboard' && (
          <DashboardPage history={history} />
        )}
        {view === 'main' && phase === 'form'    && <EmptyState />}
        {view === 'main' && phase === 'running' && (
          <RunningPanel logs={logs} activeStep={activeStep} completedSteps={completedSteps} />
        )}
        {view === 'main' && phase === 'results' && (
          <ResultsPanel
            result={result} logs={logs} onReset={handleReset}
            bookmarkedIds={bookmarkedIds}  onBookmarkToggle={handleBookmarkToggle}
            feedbackMap={feedbackMap}      onFeedback={handleFeedback}
            notesMap={notesMap}            onNote={handleNote}
            onExportPdf={handleExportPdf}  pdfLoading={pdfLoading}
            onExportCsv={handleExportCsv}  onTrialDetail={setDetailTrial}
          />
        )}
        {view === 'main' && phase === 'error' && (
          <div className="p-8">
            <div className="alert-red mb-4"><strong>Error:</strong> {errMsg}</div>
            <button onClick={handleReset} className="btn-primary max-w-xs">← Try again</button>
          </div>
        )}
      </div>

      {/* ── Trial Detail Modal ── */}
      {detailTrial && (
        <TrialDetailModal trial={detailTrial} onClose={() => setDetailTrial(null)} />
      )}

      {/* ── Onboarding Tour ── */}
      <OnboardingTour user={user} />
    </div>
  )
}
