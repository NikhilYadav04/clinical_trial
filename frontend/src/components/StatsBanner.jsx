export default function StatsBanner({ candidates, evaluated, ranked, topScore }) {
  const items = [
    { label: 'Candidates',  value: candidates ?? '—' },
    { label: 'Evaluated',   value: evaluated  ?? '—' },
    { label: 'Matched',     value: ranked     ?? '—' },
    {
      label: 'Top Score',
      value: topScore !== null && topScore !== undefined ? topScore : '—',
      suffix: topScore !== null && topScore !== undefined ? '/100' : '',
      highlight: topScore !== null && topScore !== undefined,
    },
  ]

  return (
    <div className="overflow-hidden" style={{
      border: '1px solid #c5d6e8',
      borderTop: '2px solid #1a4f7a',
      background: '#f5f8fc',
    }}>
      <div className="flex divide-x" style={{ borderColor: '#d4e3f0' }}>
        {items.map(item => (
          <div key={item.label} className="flex-1 px-5 py-4 text-center">
            <div className="font-mono text-2xl font-semibold leading-none"
                 style={{ color: item.highlight ? '#1a6b3c' : '#1a1a1a' }}>
              {item.value}
              {item.suffix && (
                <span className="text-sm font-normal ml-0.5" style={{ color: '#9b9b9b' }}>
                  {item.suffix}
                </span>
              )}
            </div>
            <div className="text-[10px] uppercase tracking-widest mt-1.5" style={{ color: '#6b8fa8' }}>
              {item.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
