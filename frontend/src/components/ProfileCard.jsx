function Tag({ text, variant = 'default' }) {
  const cls = {
    default: 'bg-[#f5f4f0] text-[#4a4a4a] border-[#dedad4]',
    blue:    'bg-[#eef3f8] text-[#1a4f7a] border-[#c5d6e8]',
    orange:  'bg-[#fdf6e8] text-[#7d4e00] border-[#e8d5a0]',
  }[variant]
  return (
    <span className={`inline-block px-2 py-0.5 border text-[11px] font-medium mr-1 mb-1 ${cls}`}>
      {text}
    </span>
  )
}

function DataRow({ label, value }) {
  if (!value && value !== 0) return null
  return (
    <div className="flex gap-4 py-1.5 border-b last:border-0" style={{ borderColor: '#dde8f0' }}>
      <span className="text-[10px] font-semibold uppercase tracking-widest w-24 flex-shrink-0 mt-0.5"
            style={{ color: '#6b8fa8' }}>
        {label}
      </span>
      <span className="text-xs" style={{ color: '#1a1a1a' }}>{value}</span>
    </div>
  )
}

export default function ProfileCard({ profile }) {
  const meta = [
    profile.age  && `${profile.age} yo`,
    profile.sex,
    profile.ecog_score !== null && profile.ecog_score !== undefined && `ECOG ${profile.ecog_score}`,
  ].filter(Boolean).join(' · ')

  return (
    <div className="overflow-hidden" style={{ border: '1px solid #c5d6e8' }}>
      {/* Header — blue-tinted to signal "patient data" */}
      <div className="pl-4 pr-4 py-3 border-b" style={{
        borderLeft: '3px solid #1a4f7a',
        borderBottom: '1px solid #c5d6e8',
        background: '#eef3f8',
      }}>
        <div className="text-sm font-semibold" style={{ color: '#1a1a1a' }}>
          {profile.diagnosis}
          {profile.stage && <span className="font-normal" style={{ color: '#4a6b85' }}> · {profile.stage}</span>}
        </div>
        <div className="font-mono text-[11px] mt-0.5" style={{ color: '#6b8fa8' }}>{meta}</div>
      </div>

      <div className="px-4 py-3 space-y-3" style={{ background: '#f8fafd' }}>
        <div>
          <DataRow label="Location"   value={profile.location} />
          <DataRow label="Max Travel" value={profile.max_travel_miles ? `${profile.max_travel_miles} miles` : null} />
        </div>

        {profile.biomarkers?.length > 0 && (
          <div>
            <div className="data-label mb-1.5" style={{ color: '#6b8fa8' }}>Biomarkers</div>
            <div>{profile.biomarkers.map(b => <Tag key={b} text={b} variant="blue" />)}</div>
          </div>
        )}
        {profile.prior_treatments?.length > 0 && (
          <div>
            <div className="data-label mb-1.5" style={{ color: '#6b8fa8' }}>Prior Treatments</div>
            <div>{profile.prior_treatments.map(t => <Tag key={t} text={t} variant="orange" />)}</div>
          </div>
        )}
        {profile.comorbidities?.length > 0 && (
          <div>
            <div className="data-label mb-1.5" style={{ color: '#6b8fa8' }}>Comorbidities</div>
            <div>{profile.comorbidities.map(c => <Tag key={c} text={c} />)}</div>
          </div>
        )}
        {profile.lab_values && Object.keys(profile.lab_values).length > 0 && (
          <div>
            <div className="data-label mb-1.5" style={{ color: '#6b8fa8' }}>Lab Values</div>
            {Object.entries(profile.lab_values).map(([k, v]) => (
              <DataRow key={k} label={k} value={String(v)} />
            ))}
          </div>
        )}
        {profile.missing_info?.length > 0 && (
          <div className="px-3 py-2" style={{ border: '1px solid #e8d5a0', background: '#fdf6e8' }}>
            <div className="text-[10px] font-semibold uppercase tracking-widest mb-1"
                 style={{ color: '#7d4e00' }}>
              Confirm with physician
            </div>
            {profile.missing_info.map((m, i) => (
              <p key={i} className="text-xs" style={{ color: '#7d4e00' }}>• {m}</p>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
