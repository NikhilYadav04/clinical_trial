import { useState, useEffect } from 'react'

const TOUR_KEY = 'trialmatch_tour_v1'

const STEPS = [
  {
    title: 'Welcome to TrialMatch',
    body:  'A LangGraph multi-agent pipeline that matches patients to clinical trials across 400,000+ studies. Let\'s take a quick tour.',
    position: 'center',
  },
  {
    title: 'Patient Intake Form',
    body:  'Fill in the patient\'s diagnosis, demographics, biomarkers, prior treatments, and location. Use "Load Example" to see sample data.',
    position: 'center',
  },
  {
    title: 'Saved Patient Records',
    body:  'Save frequently-used patient profiles and reload them instantly — no need to re-enter data for follow-up searches.',
    position: 'center',
  },
  {
    title: 'Real-Time Pipeline Streaming',
    body:  'After submitting, watch each of the 7 agents work in real time: Profile → Search → Evaluation → Ranking → Report generation.',
    position: 'center',
  },
  {
    title: 'Match Results & Scoring',
    body:  'Trials are ranked by a composite score: eligibility 60%, quality 20%, logistics 10%, biomarker 10%. Click any card to see full details.',
    position: 'center',
  },
  {
    title: 'Bookmarks & Comparison',
    body:  'Save trials with the Save button. In the Saved view, select 2–3 trials and click Compare for a side-by-side breakdown.',
    position: 'center',
  },
  {
    title: 'Analytics Dashboard',
    body:  'The Analytics tab shows your search history trends, match quality distribution, and most-searched diagnoses.',
    position: 'center',
  },
  {
    title: 'Export Results',
    body:  'Export any result set as a PDF report or CSV spreadsheet for sharing with colleagues or importing into other tools.',
    position: 'center',
  },
]

export default function OnboardingTour({ user }) {
  const [step,   setStep]   = useState(0)
  const [active, setActive] = useState(false)

  useEffect(() => {
    if (!user) return
    const key = `${TOUR_KEY}_${user.user_id || user.email}`
    if (!localStorage.getItem(key)) {
      setActive(true)
    }
  }, [user])

  function finish() {
    const key = `${TOUR_KEY}_${user?.user_id || user?.email}`
    localStorage.setItem(key, '1')
    setActive(false)
  }

  function next() {
    if (step < STEPS.length - 1) setStep(s => s + 1)
    else finish()
  }

  function prev() {
    if (step > 0) setStep(s => s - 1)
  }

  if (!active) return null

  const current = STEPS[step]
  const isLast  = step === STEPS.length - 1

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.6)' }}
      role="dialog"
      aria-modal="true"
      aria-label={`Onboarding tour step ${step + 1} of ${STEPS.length}`}
    >
      <div
        className="bg-white w-full max-w-sm mx-4"
        style={{ border: '1px solid #dedad4', borderTop: '3px solid #1a4f7a' }}
      >
        {/* Progress bar */}
        <div className="h-0.5 bg-[#f0ece6]">
          <div
            className="h-0.5 transition-all duration-300"
            style={{ width: `${((step + 1) / STEPS.length) * 100}%`, background: '#1a4f7a' }}
          />
        </div>

        <div className="px-6 py-5">
          {/* Step indicator */}
          <div className="flex items-center justify-between mb-4">
            <span className="font-mono text-[10px] text-[#9b9b9b] uppercase tracking-widest">
              {step + 1} / {STEPS.length}
            </span>
            <button
              onClick={finish}
              aria-label="Skip tour"
              className="text-[10px] text-[#c0bbb4] hover:text-[#6b6b6b] transition-colors"
            >
              Skip tour
            </button>
          </div>

          {/* Content */}
          <h3 className="font-serif text-lg text-[#1a1a1a] mb-2 leading-snug">{current.title}</h3>
          <div className="w-5 h-px bg-[#1a4f7a] mb-3" />
          <p className="text-sm text-[#6b6b6b] leading-relaxed">{current.body}</p>

          {/* Dot nav */}
          <div className="flex justify-center gap-1.5 my-5" role="tablist" aria-label="Tour steps">
            {STEPS.map((_, i) => (
              <button
                key={i}
                onClick={() => setStep(i)}
                role="tab"
                aria-selected={i === step}
                aria-label={`Go to step ${i + 1}`}
                className="w-1.5 h-1.5 transition-all"
                style={{
                  background:   i === step ? '#1a4f7a' : '#dedad4',
                  width:        i === step ? 20 : 6,
                  borderRadius: i === step ? 3 : '50%',
                }}
              />
            ))}
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            {step > 0 && (
              <button
                onClick={prev}
                className="flex-1 py-2 text-xs font-medium text-[#6b6b6b] border border-[#dedad4] hover:border-[#c5c0b8] hover:text-[#1a1a1a] transition-colors"
                style={{ borderRadius: 0 }}
              >
                ← Back
              </button>
            )}
            <button
              onClick={next}
              className="flex-1 py-2 text-xs font-semibold text-white transition-colors"
              style={{ background: '#1a4f7a', borderRadius: 0 }}
            >
              {isLast ? 'Get started →' : 'Next →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
