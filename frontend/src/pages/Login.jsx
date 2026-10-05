import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login as loginApi } from '../services/authApi'
import { useAuth } from '../context/AuthContext.jsx'
import AuthLayout from '../components/common/AuthLayout.jsx'

export default function Login() {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await loginApi(identifier, password)
      login(data.access_token, data.user)
      navigate('/')
    } catch (err) {
      setError(
        err.response
          ? err.response.data?.detail || 'Login failed.'
          : "Can't reach the server. Check that the backend is running, then try again.",
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Sign in"
      footer={<>Don't have an account? <Link to="/register">Create account</Link></>}
    >
      <form onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="identifier">Email or username</label>
          <input id="identifier" value={identifier} onChange={(e) => setIdentifier(e.target.value)} autoComplete="username" autoFocus required />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </div>
        {error && <p className="error-text" role="alert">{error}</p>}
        <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="auth-aside"><Link to="/forgot-password">Forgot password?</Link></p>
      </form>
    </AuthLayout>
  )
}
