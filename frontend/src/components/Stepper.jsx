const STEPS = [
  { icon: '🧠', label: 'Profile' },
  { icon: '🔍', label: 'Search' },
  { icon: '⚖️', label: 'Evaluate' },
  { icon: '🏆', label: 'Rank' },
  { icon: '📋', label: 'Reports' },
]

export default function Stepper({ logs }) {
  const active = Math.min(Math.floor(logs.length / 2), STEPS.length - 1)

  return (
    <div className="flex items-center justify-center gap-0 bg-white rounded-2xl border border-slate-100 shadow-sm px-6 py-4 mb-4">
      {STEPS.map((s, i) => (
        <div key={s.label} className="flex items-center">
          <div className="flex flex-col items-center gap-1">
            <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold
              ${i < active ? 'bg-emerald-500 text-white' :
                i === active ? 'bg-slate-800 text-white ring-4 ring-slate-200' :
                'bg-slate-100 text-slate-400'}`}>
              {i < active ? '✓' : s.icon}
            </div>
            <span className={`text-[10px] font-semibold whitespace-nowrap
              ${i < active ? 'text-emerald-600' : i === active ? 'text-slate-700' : 'text-slate-300'}`}>
              {s.label}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`w-10 h-0.5 mb-4 mx-1 ${i < active ? 'bg-emerald-400' : 'bg-slate-100'}`} />
          )}
        </div>
      ))}
    </div>
  )
}
