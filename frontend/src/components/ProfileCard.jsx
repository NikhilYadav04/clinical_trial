function Pill({ text, color }) {
  const colors = {
    blue:   'bg-blue-50 text-blue-700 border border-blue-100',
    orange: 'bg-orange-50 text-orange-700 border border-orange-100',
    gray:   'bg-slate-100 text-slate-600 border border-slate-200',
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-medium mr-1 mb-1 ${colors[color]}`}>
      {text}
    </span>
  )
}

export default function ProfileCard({ profile }) {
  const meta = [
    profile.age && `${profile.age}yo`,
    profile.sex,
    profile.location,
    profile.ecog_score !== null && profile.ecog_score !== undefined && `ECOG ${profile.ecog_score}`,
  ].filter(Boolean).join(' · ')

  return (
    <div className="bg-white rounded-2xl border-l-4 border-l-slate-800 border border-slate-100 shadow-sm p-4">
      <div className="text-base font-bold text-slate-900">{profile.diagnosis} {profile.stage || ''}</div>
      <div className="text-xs text-slate-400 mt-0.5 mb-3">{meta}</div>

      {profile.biomarkers?.length > 0 && (
        <div className="mb-2">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mb-1">Biomarkers</div>
          {profile.biomarkers.map(b => <Pill key={b} text={b} color="blue" />)}
        </div>
      )}
      {profile.prior_treatments?.length > 0 && (
        <div className="mb-2">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mb-1">Prior Treatments</div>
          {profile.prior_treatments.map(t => <Pill key={t} text={t} color="orange" />)}
        </div>
      )}
      {profile.comorbidities?.length > 0 && (
        <div>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mb-1">Comorbidities</div>
          {profile.comorbidities.map(c => <Pill key={c} text={c} color="gray" />)}
        </div>
      )}
      {profile.missing_info?.length > 0 && (
        <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-800">
          <strong>Confirm with doctor:</strong> {profile.missing_info.join('; ')}
        </div>
      )}
    </div>
  )
}
