import { useState } from 'react'
import { login, register } from '../api'

export default function AuthPage({ onAuth }) {
  const [tab,      setTab]      = useState('login')   // 'login' | 'register'
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [name,     setName]     = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = tab === 'login'
        ? await login(email, password)
        : await register(email, password, name)
      onAuth(res.user, res.token)
    } catch (err) {
      setError(err.message || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: '#f7f6f2' }}>
      <div className="w-full max-w-sm">

        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="font-serif text-3xl font-bold text-[#1a1a1a] leading-none">TrialMatch</h1>
          <div className="w-8 h-px bg-[#1a4f7a] mx-auto mt-2 mb-3" />
          <p className="text-[11px] text-[#9b9b9b] uppercase tracking-widest">
            Clinical Trial Matching · LangGraph Multi-Agent
          </p>
        </div>

        {/* Card */}
        <div className="bg-white border border-[#e8e4de]" style={{ borderTop: '2px solid #1a4f7a' }}>

          {/* Tab switcher */}
          <div className="flex border-b border-[#e8e4de]">
            {[['login', 'Sign In'], ['register', 'Create Account']].map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => { setTab(key); setError('') }}
                className="flex-1 py-3 text-[11px] font-semibold uppercase tracking-widest transition-colors"
                style={{
                  color:      tab === key ? '#1a4f7a' : '#9b9b9b',
                  background: tab === key ? '#f3f7fc' : 'white',
                  borderBottom: tab === key ? '2px solid #1a4f7a' : '2px solid transparent',
                  marginBottom: -1,
                }}
              >
                {label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-4">

            {tab === 'register' && (
              <div>
                <label className="label">Full Name</label>
                <input
                  className="input"
                  type="text"
                  placeholder="Dr. Jane Smith"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  required
                  autoComplete="name"
                />
              </div>
            )}

            <div>
              <label className="label">Email</label>
              <input
                className="input"
                type="email"
                placeholder="you@hospital.org"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            <div>
              <label className="label">Password</label>
              <input
                className="input"
                type="password"
                placeholder={tab === 'register' ? 'At least 6 characters' : '••••••••'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
              />
            </div>

            {error && (
              <div className="px-3 py-2 text-xs border"
                   style={{ background: '#fff5f5', border: '1px solid #c97b7b', color: '#8b1a1a' }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary">
              {loading
                ? <span className="flex items-center justify-center gap-2">
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    {tab === 'login' ? 'Signing in…' : 'Creating account…'}
                  </span>
                : tab === 'login' ? 'Sign In' : 'Create Account'
              }
            </button>

            <p className="text-center text-[11px] text-[#9b9b9b]">
              {tab === 'login' ? "Don't have an account? " : 'Already have an account? '}
              <button type="button" onClick={() => { setTab(tab === 'login' ? 'register' : 'login'); setError('') }}
                      className="text-[#1a4f7a] hover:underline font-medium">
                {tab === 'login' ? 'Create one' : 'Sign in'}
              </button>
            </p>
          </form>
        </div>

        <p className="text-center text-[10px] text-[#c0bbb4] mt-6">
          For research and informational purposes only
        </p>
      </div>
    </div>
  )
}
