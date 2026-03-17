import { useState, useEffect } from 'react'
import { getApiKey, setApiKey, clearApiKey } from '../api'

export function useAuth() {
  const [authenticated, setAuthenticated] = useState(false)
  const [checking, setChecking] = useState(true)

  const verify = async (key?: string) => {
    const apiKey = key ?? getApiKey()
    if (!apiKey) {
      setAuthenticated(false)
      setChecking(false)
      return false
    }
    try {
      const res = await fetch('/api/health', {
        headers: { 'X-API-Key': apiKey },
      })
      if (res.ok) {
        setApiKey(apiKey)
        setAuthenticated(true)
        setChecking(false)
        return true
      }
      clearApiKey()
      setAuthenticated(false)
      setChecking(false)
      return false
    } catch {
      setAuthenticated(false)
      setChecking(false)
      return false
    }
  }

  const logout = () => {
    clearApiKey()
    setAuthenticated(false)
  }

  useEffect(() => {
    verify()
  }, [])

  return { authenticated, checking, verify, logout }
}

interface LoginGateProps {
  authenticated: boolean
  checking: boolean
  verify: (key?: string) => Promise<boolean>
  children: React.ReactNode
}

export default function LoginGate({ authenticated, checking, verify, children }: LoginGateProps) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (checking) {
    return (
      <div className="h-screen flex items-center justify-center bg-bg">
        <p className="text-text-muted text-sm">Loading...</p>
      </div>
    )
  }

  if (authenticated) return <>{children}</>

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    const ok = await verify(password)
    if (!ok) setError('Invalid password')
    setSubmitting(false)
  }

  return (
    <div className="h-screen flex items-center justify-center bg-bg">
      <form onSubmit={handleSubmit} className="bg-card border border-border rounded-lg p-8 w-80 space-y-4">
        <h1 className="text-lg font-semibold text-text text-center">CE Orchestrator</h1>
        <p className="text-xs text-text-muted text-center">Enter password to continue</p>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          autoFocus
          className="w-full px-3 py-2 rounded-md border border-border bg-bg text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {error && <p className="text-xs text-red-500 text-center">{error}</p>}
        <button
          type="submit"
          disabled={submitting || !password}
          className="w-full py-2 rounded-md bg-primary text-white text-sm font-medium hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? 'Checking...' : 'Sign In'}
        </button>
      </form>
    </div>
  )
}
