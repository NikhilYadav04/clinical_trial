const STEPS = [
  { label: 'Profile'  },
  { label: 'Search'   },
  { label: 'Evaluate' },
  { label: 'Rank'     },
  { label: 'Reports'  },
]

function Spinner() {
  return (
    <svg className="animate-spin w-2.5 h-2.5" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
      <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
    </svg>
  )
}

export default function Stepper({ activeStep = 0, completedSteps = new Set() }) {
  return (
    <div className="bg-white border border-[#e8e4de] px-6 py-4">
      <div className="flex items-center">
        {STEPS.map((s, i) => {
          const done    = completedSteps.has(i)
          const active  = i === activeStep && !done
          const pending = !done && !active

          return (
            <div key={s.label} className="flex items-center flex-1 min-w-0">
              <div className="flex flex-col items-center gap-1.5 flex-shrink-0">
                {/* Dot */}
                <div className={`flex items-center justify-center transition-all
                  ${done   ? 'w-5 h-5 bg-[#1a6b3c] text-white'       : ''}
                  ${active ? 'w-5 h-5 bg-[#1a4f7a] text-white'       : ''}
                  ${pending? 'w-4 h-4 border border-[#dedad4] bg-white' : ''}`}
                >
                  {done   && <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/></svg>}
                  {active && <Spinner />}
                </div>
                {/* Label */}
                <span className={`text-[10px] font-semibold uppercase tracking-wider whitespace-nowrap
                  ${done    ? 'text-[#1a6b3c]' : ''}
                  ${active  ? 'text-[#1a4f7a]' : ''}
                  ${pending ? 'text-[#c0bbb4]' : ''}`}>
                  {s.label}
                </span>
              </div>
              {/* Connector */}
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-px mx-3 mb-5 ${done ? 'bg-[#1a6b3c]' : 'bg-[#e8e4de]'}`} />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
