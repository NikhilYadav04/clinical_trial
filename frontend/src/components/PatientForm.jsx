import { useState, useEffect } from 'react'
import { getExamples } from '../api'

const DEFAULTS = {
  age: '', sex: 'Female', ecog: 1,
  diagnosis: '', stage: '', biomarkers: '',
  prior_treatments: '', current_medications: '', comorbidities: '',
  labs: [],
  location: '', max_travel: 100, travel_unit: 'miles', phases: [],
}

const ECOG_OPTIONS = [
  { value: 0, label: '0 — Fully active' },
  { value: 1, label: '1 — Restricted, ambulatory' },
  { value: 2, label: '2 — Self-care only' },
  { value: 3, label: '3 — Limited self-care' },
  { value: 4, label: '4 — Completely disabled' },
]

const PHASE_OPTIONS = ['Phase 1', 'Phase 2', 'Phase 3', 'Phase 4']

const DIAGNOSIS_CATEGORIES = [
  { label: 'Lung',   chips: ['NSCLC', 'SCLC', 'Mesothelioma'] },
  { label: 'Breast', chips: ['HER2+ Breast Cancer', 'Triple-Negative Breast Cancer', 'ER+ Breast Cancer'] },
  { label: 'Neuro',  chips: ['Glioblastoma (GBM)', 'Glioma', 'Brain Metastases'] },
  { label: 'GI',     chips: ['Colorectal Cancer', 'Pancreatic Cancer', 'Hepatocellular Carcinoma', 'Gastric Cancer'] },
  { label: 'Blood',  chips: ['Multiple Myeloma', 'AML', 'CLL', 'Diffuse Large B-Cell Lymphoma'] },
  { label: 'Other',  chips: ['Ovarian Cancer', 'Prostate Cancer', 'Renal Cell Carcinoma', 'ALS', 'Melanoma'] },
]

const STAGE_CATEGORIES = [
  { label: 'Stage',     chips: ['Stage I', 'Stage II', 'Stage III', 'Stage IV'] },
  { label: 'Status',    chips: ['Newly Diagnosed', 'Relapsed', 'Refractory', 'Metastatic'] },
  { label: 'Qualifier', chips: ['Locally Advanced', 'Unresectable', 'De novo Metastatic'] },
]

const BIOMARKER_CATEGORIES = [
  { label: 'Lung',      chips: ['EGFR exon 19 del', 'EGFR L858R', 'ALK fusion', 'ROS1 fusion', 'KRAS G12C'] },
  { label: 'Breast',    chips: ['HER2 3+ (IHC)', 'BRCA1 mutation', 'BRCA2 mutation', 'ER positive', 'PR positive'] },
  { label: 'Immune',    chips: ['PD-L1 >1%', 'PD-L1 >50%', 'MSI-H', 'TMB high', 'dMMR'] },
  { label: 'Pan-cancer',chips: ['BRAF V600E', 'TP53 mutation', 'PIK3CA mutation', 'FGFR amplification'] },
]

const TREATMENT_CATEGORIES = [
  { label: 'Chemo',    chips: ['Carboplatin', 'Paclitaxel', 'Cisplatin', 'Pemetrexed', 'Gemcitabine', 'Docetaxel'] },
  { label: 'Immuno',   chips: ['Pembrolizumab', 'Nivolumab', 'Atezolizumab', 'Durvalumab', 'Ipilimumab'] },
  { label: 'Targeted', chips: ['Osimertinib', 'Trastuzumab', 'Bevacizumab', 'Erlotinib', 'Olaparib'] },
  { label: 'Other',    chips: ['Radiation', 'Surgery', 'Stem Cell Transplant', 'CAR-T'] },
]

const LAB_CATEGORIES = [
  { label: 'Kidney', items: [{ name: 'Creatinine', unit: 'mg/dL' }, { name: 'eGFR', unit: 'mL/min' }] },
  { label: 'Liver',  items: [{ name: 'ALT', unit: 'U/L' }, { name: 'AST', unit: 'U/L' }, { name: 'Bilirubin', unit: 'mg/dL' }, { name: 'Albumin', unit: 'g/dL' }] },
  { label: 'Blood',  items: [{ name: 'Hemoglobin', unit: 'g/dL' }, { name: 'WBC', unit: 'K/uL' }, { name: 'Platelets', unit: 'K/uL' }, { name: 'ANC', unit: 'K/uL' }] },
  { label: 'Markers',items: [{ name: 'LDH', unit: 'U/L' }, { name: 'CEA', unit: 'ng/mL' }, { name: 'CA-125', unit: 'U/mL' }, { name: 'PSA', unit: 'ng/mL' }] },
]

const SECTION_COLORS = {
  indigo:  { accent: '#1a4f7a', iconBg: '#eef3f8' },
  blue:    { accent: '#1a4f7a', iconBg: '#eef3f8' },
  amber:   { accent: '#7d4e00', iconBg: '#fdf6e8' },
  emerald: { accent: '#1a6b3c', iconBg: '#eef6f0' },
  violet:  { accent: '#5b2d8e', iconBg: '#f3eef8' },
}

function SectionCard({ color, icon, title, subtitle, children }) {
  const c = SECTION_COLORS[color] || SECTION_COLORS.indigo
  return (
    <div className="section-card" style={{ borderLeft: `3px solid ${c.accent}` }}>
      <div className="section-header">
        <div className="section-icon" style={{ background: c.iconBg, color: c.accent }}>{icon}</div>
        <div>
          <div className="section-title-text">{title}</div>
          {subtitle && <div className="section-subtitle">{subtitle}</div>}
        </div>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <div>
      {label && <label className="label">{label}</label>}
      {children}
      {hint && <p className="hint">{hint}</p>}
    </div>
  )
}

function CategorizedChips({ categories, color, onAdd }) {
  return (
    <div className="mt-2 space-y-1.5 border-t border-[#f0ece6] pt-2.5">
      {categories.map(cat => (
        <div key={cat.label} className="flex items-start gap-2">
          <span className="text-[9px] font-bold text-[#9b9b9b] uppercase tracking-widest w-14 flex-shrink-0 mt-1.5 text-right">{cat.label}</span>
          <div className="flex flex-wrap gap-1">
            {cat.chips.map(chip => (
              <button key={chip} type="button" onClick={() => onAdd(chip)} className={`chip chip-${color}`}>
                + {chip}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function PhaseToggle({ selected, onChange }) {
  const toggle = p => onChange(selected.includes(p) ? selected.filter(x => x !== p) : [...selected, p])
  return (
    <div className="flex gap-2 flex-wrap items-center">
      {PHASE_OPTIONS.map(p => (
        <button key={p} type="button" onClick={() => toggle(p)}
          style={{ borderRadius: 0 }}
          className={`px-3 py-1.5 text-xs font-semibold border transition-all ${
            selected.includes(p)
              ? 'bg-[#5b2d8e] text-white border-[#5b2d8e]'
              : 'bg-white text-[#6b6b6b] border-[#dedad4] hover:border-[#5b2d8e] hover:text-[#5b2d8e]'
          }`}>
          {p}
        </button>
      ))}
      {selected.length === 0 && <span className="text-[11px] text-[#9b9b9b]">any phase accepted</span>}
    </div>
  )
}

function LabRow({ lab, index, onChange, onRemove }) {
  return (
    <div className="flex gap-2 items-center">
      <input className="input input-emerald flex-1 text-xs" placeholder="Lab name" value={lab.name} onChange={e => onChange(index, 'name', e.target.value)} />
      <input className="input input-emerald w-20 text-xs" placeholder="Value" value={lab.value} onChange={e => onChange(index, 'value', e.target.value)} />
      <input className="input input-emerald w-20 text-xs" placeholder="Unit" value={lab.unit} onChange={e => onChange(index, 'unit', e.target.value)} />
      <button type="button" onClick={() => onRemove(index)} className="text-[#c0bbb4] hover:text-[#8b1a1a] text-lg leading-none">×</button>
    </div>
  )
}

function LabValuesSection({ labs, onChange }) {
  const addLab = (name = '', unit = '') => onChange([...labs, { name, value: '', unit }])
  const updateLab = (i, key, val) => { const next = [...labs]; next[i] = { ...next[i], [key]: val }; onChange(next) }
  const removeLab = i => onChange(labs.filter((_, idx) => idx !== i))

  return (
    <SectionCard color="emerald" icon="🧪" title="Lab Values" subtitle="Add any recent results — helps evaluate eligibility criteria">
      {labs.length > 0 && (
        <div className="space-y-2">
          <div className="grid grid-cols-[1fr_80px_80px_24px] gap-2">
            <span className="label">Lab name</span><span className="label">Value</span><span className="label">Unit</span><span />
          </div>
          {labs.map((lab, i) => <LabRow key={i} lab={lab} index={i} onChange={updateLab} onRemove={removeLab} />)}
        </div>
      )}
      <button type="button" onClick={() => addLab()}
              className="flex items-center gap-1.5 text-xs font-semibold text-[#1a6b3c] hover:text-[#0f5730] transition-colors">
        <span className="w-5 h-5 bg-[#eef6f0] border border-[#b8dfc5] flex items-center justify-center text-base leading-none">+</span>
        Add lab value
      </button>
      <div className="border-t border-[#f0ece6] pt-2.5 space-y-1.5">
        {LAB_CATEGORIES.map(cat => (
          <div key={cat.label} className="flex items-start gap-2">
            <span className="text-[9px] font-bold text-[#9b9b9b] uppercase tracking-widest w-14 flex-shrink-0 mt-1.5 text-right">{cat.label}</span>
            <div className="flex flex-wrap gap-1">
              {cat.items.map(l => (
                <button key={l.name} type="button" onClick={() => addLab(l.name, l.unit)} className="chip chip-emerald">+ {l.name}</button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  )
}

function appendToField(current, addition) {
  const val = current?.trim()
  if (!val) return addition
  if (val.toLowerCase().includes(addition.toLowerCase())) return val
  return val + ', ' + addition
}

export default function PatientForm({ onSubmit, loading, savedPatients = [], onSavePatient, onDeletePatient }) {
  const [form,          setForm]          = useState(DEFAULTS)
  const [examples,      setExamples]      = useState([])
  const [showSaveInput, setShowSaveInput] = useState(false)
  const [saveLabel,     setSaveLabel]     = useState('')
  const [savingPatient, setSavingPatient] = useState(false)

  useEffect(() => {
    getExamples().then(d => setExamples(d.examples || [])).catch(() => {})
  }, [])

  const set    = key => e => setForm(f => ({ ...f, [key]: e.target.value }))
  const setVal = (key, val) => setForm(f => ({ ...f, [key]: val }))
  const append = key => chip => setForm(f => ({ ...f, [key]: appendToField(f[key], chip) }))

  const loadExample = ex => setForm({ ...DEFAULTS, ...ex.fields, labs: ex.fields.labs || [] })

  const loadPatient = (patientId) => {
    const p = savedPatients.find(p => p.patient_id === patientId)
    if (p) setForm({ ...DEFAULTS, ...p.form_data, labs: p.form_data.labs || [] })
  }

  const handleSavePatient = async () => {
    if (!saveLabel.trim()) return
    setSavingPatient(true)
    try {
      await onSavePatient(saveLabel.trim(), { ...form, age: Number(form.age), ecog: Number(form.ecog) })
      setSaveLabel('')
      setShowSaveInput(false)
    } finally {
      setSavingPatient(false)
    }
  }

  const handleSubmit = e => {
    e.preventDefault()
    onSubmit({ ...form, age: Number(form.age), ecog: Number(form.ecog) })
  }

  const canSubmit = !loading && String(form.diagnosis).trim().length > 1 && form.age

  return (
    <form onSubmit={handleSubmit} className="space-y-4 pb-4">

      {/* ── Saved patients bar ── */}
      <div className="p-3 border border-[#e8e4de] bg-[#f9f8f5] space-y-2">
        <div className="flex items-center justify-between">
          <span className="data-label">Patient Records</span>
          {!showSaveInput && (
            <button type="button" onClick={() => { setShowSaveInput(true); setSaveLabel(form.diagnosis ? `${form.diagnosis}` : '') }}
                    className="text-[10px] text-[#1a4f7a] hover:underline font-medium">
              + Save current
            </button>
          )}
        </div>

        {savedPatients.length > 0 && (
          <div className="flex gap-1.5 items-center">
            <select
              defaultValue=""
              onChange={e => { if (e.target.value) loadPatient(e.target.value) }}
              className="input text-xs flex-1"
              style={{ borderRadius: 0, padding: '4px 8px' }}
            >
              <option value="">Load saved patient…</option>
              {savedPatients.map(p => (
                <option key={p.patient_id} value={p.patient_id}>{p.label}</option>
              ))}
            </select>
          </div>
        )}

        {showSaveInput && (
          <div className="flex gap-1.5 items-center">
            <input
              autoFocus
              className="input text-xs flex-1"
              style={{ borderRadius: 0, padding: '4px 8px' }}
              placeholder="Label e.g. Jane — NSCLC Stage IIIB"
              value={saveLabel}
              onChange={e => setSaveLabel(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleSavePatient() } if (e.key === 'Escape') setShowSaveInput(false) }}
            />
            <button type="button" onClick={handleSavePatient} disabled={!saveLabel.trim() || savingPatient}
                    className="text-[11px] px-2 py-1 border font-medium transition-colors disabled:opacity-40"
                    style={{ borderRadius: 0, borderColor: '#1a4f7a', color: '#1a4f7a', background: '#eef3f8' }}>
              {savingPatient ? '…' : 'Save'}
            </button>
            <button type="button" onClick={() => setShowSaveInput(false)}
                    className="text-[11px] px-2 py-1 border border-[#dedad4] text-[#9b9b9b] hover:text-[#1a1a1a] transition-colors"
                    style={{ borderRadius: 0 }}>
              ✕
            </button>
          </div>
        )}

        {savedPatients.length === 0 && !showSaveInput && (
          <p className="text-[11px] text-[#c0bbb4]">No saved patients yet. Fill the form and save.</p>
        )}
      </div>

      {/* Examples */}
      {examples.length > 0 && (
        <div>
          <p className="label mb-2">Load Example Patient</p>
          <div className="grid grid-cols-2 gap-1.5">
            {examples.map(ex => (
              <button key={ex.label} type="button" onClick={() => loadExample(ex)}
                className="px-3 py-2 text-xs font-medium bg-[#f9f8f5] text-[#6b6b6b] text-left
                           border border-[#e8e4de] hover:bg-[#1a1a1a] hover:text-white hover:border-[#1a1a1a] transition-all"
                style={{ borderRadius: 0 }}>
                {ex.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Demographics */}
      <SectionCard color="indigo" icon="👤" title="Patient Demographics" subtitle="Basic patient information">
        <div className="grid grid-cols-3 gap-2">
          <Field label="Age *">
            <input className="input input-indigo" type="number" min="1" max="120" placeholder="e.g. 58"
              value={form.age} onChange={set('age')} required />
          </Field>
          <Field label="Sex">
            <select className="input input-indigo" value={form.sex} onChange={set('sex')}>
              <option>Female</option><option>Male</option><option>Other</option>
            </select>
          </Field>
          <Field label="ECOG">
            <select className="input input-indigo" value={form.ecog} onChange={e => setVal('ecog', Number(e.target.value))}>
              {ECOG_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>
        </div>
      </SectionCard>

      {/* Diagnosis */}
      <SectionCard color="blue" icon="🩺" title="Diagnosis" subtitle="Primary condition, stage, and biomarkers">
        <Field label="Primary Condition *">
          <input className="input input-blue" placeholder="e.g. Non-Small Cell Lung Cancer (NSCLC)"
            value={form.diagnosis} onChange={set('diagnosis')} required />
          <CategorizedChips categories={DIAGNOSIS_CATEGORIES} color="blue" onAdd={chip => setVal('diagnosis', chip)} />
        </Field>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Stage / Grade">
            <input className="input input-blue" placeholder="e.g. Stage IIIB" value={form.stage} onChange={set('stage')} />
            <CategorizedChips categories={STAGE_CATEGORIES} color="blue" onAdd={chip => setVal('stage', chip)} />
          </Field>
          <Field label="Biomarkers & Mutations" hint="Separate multiple with commas">
            <input className="input input-blue" placeholder="e.g. EGFR exon 19 del, PD-L1 40%"
              value={form.biomarkers} onChange={set('biomarkers')} />
            <CategorizedChips categories={BIOMARKER_CATEGORIES} color="blue" onAdd={append('biomarkers')} />
          </Field>
        </div>
      </SectionCard>

      {/* Treatment History */}
      <SectionCard color="amber" icon="💊" title="Treatment History" subtitle="Prior therapies, current drugs, and comorbidities">
        <Field label="Prior Treatments" hint="Include drug names, cycles, and when completed">
          <textarea className="input input-amber resize-none" rows={2}
            placeholder="e.g. Carboplatin + Paclitaxel (6 cycles, completed 6 months ago)"
            value={form.prior_treatments} onChange={set('prior_treatments')} />
          <CategorizedChips categories={TREATMENT_CATEGORIES} color="amber" onAdd={append('prior_treatments')} />
        </Field>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Current Medications">
            <input className="input input-amber" placeholder="e.g. Amlodipine 5mg"
              value={form.current_medications} onChange={set('current_medications')} />
          </Field>
          <Field label="Comorbidities">
            <input className="input input-amber" placeholder="e.g. Hypertension, T2 Diabetes"
              value={form.comorbidities} onChange={set('comorbidities')} />
          </Field>
        </div>
      </SectionCard>

      {/* Labs */}
      <LabValuesSection labs={form.labs} onChange={labs => setVal('labs', labs)} />

      {/* Location */}
      <SectionCard color="violet" icon="📍" title="Location & Preferences" subtitle="Used to find nearby sites and filter trial phases">
        <Field label="Location" hint="City and state/country">
          <input className="input input-violet" placeholder="e.g. Boston, MA  or  Mumbai, Maharashtra, India"
            value={form.location} onChange={set('location')} />
        </Field>
        <div className="grid grid-cols-3 gap-2 items-end">
          <div className="col-span-2">
            <label className="label">
              Max Travel — <span className="font-bold normal-case tracking-normal" style={{ color: '#5b2d8e' }}>{form.max_travel} {form.travel_unit}</span>
            </label>
            <input type="range" min="0" max={form.travel_unit === 'km' ? 1000 : 500} step="25"
              value={form.max_travel} onChange={e => setVal('max_travel', Number(e.target.value))}
              className="w-full mt-1" style={{ accentColor: '#5b2d8e' }} />
            <div className="flex justify-between text-[10px] text-[#c0bbb4] mt-0.5">
              <span>0</span><span>{form.travel_unit === 'km' ? '1000 km' : '500 mi'}</span>
            </div>
          </div>
          <Field label="Unit">
            <select className="input input-violet" value={form.travel_unit} onChange={set('travel_unit')}>
              <option value="miles">Miles</option>
              <option value="km">Kilometres</option>
            </select>
          </Field>
        </div>
        <Field label="Preferred Trial Phases" hint="Leave blank to include all phases">
          <PhaseToggle selected={form.phases} onChange={v => setVal('phases', v)} />
        </Field>
      </SectionCard>

      {/* Submit */}
      <div className="pt-3 sticky bottom-0 bg-white pb-1">
        <button type="submit" disabled={!canSubmit} className="btn-primary">
          {loading
            ? <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Running pipeline...
              </span>
            : '🔍  Find Matching Trials'
          }
        </button>
      </div>
    </form>
  )
}
