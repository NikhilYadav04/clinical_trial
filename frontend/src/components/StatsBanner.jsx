export default function StatsBanner({ candidates, evaluated, ranked, topScore }) {
  const items = [
    { label: 'Searched', value: candidates },
    { label: 'Evaluated', value: evaluated },
    { label: 'Matched', value: ranked },
    { label: 'Top Score', value: topScore !== null ? `${topScore}/100` : 'N/A' },
  ]

  return (
    <div className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-2xl px-6 py-4 flex justify-around text-white">
      {items.map((item, i) => (
        <div key={item.label} className="flex items-center gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold">{item.value}</div>
            <div className="text-[11px] text-slate-400 uppercase tracking-wide mt-0.5">{item.label}</div>
          </div>
          {i < items.length - 1 && <div className="text-slate-600 text-lg">›</div>}
        </div>
      ))}
    </div>
  )
}
