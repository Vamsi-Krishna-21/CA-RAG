import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register as registerApi } from '../services/authApi'
import { useAuth } from '../context/AuthContext.jsx'
import AuthLayout from '../components/common/AuthLayout.jsx'

export default function Register() {
  const [name, setName] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setLoading(true)
    try {
      const data = await registerApi(name, email, password, username.trim())
      login(data.access_token, data.user)
      navigate('/')
    } catch (err) {
      setError(
        err.response
          ? err.response.data?.detail || 'Registration failed.'
          : "Can't reach the server. Check that the backend is running, then try again.",
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      footer={<>Already have an account? <Link to="/login">Sign in</Link></>}
    >
      <form onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="name">Name</label>
          <input id="name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" autoFocus required />
        </div>
        <div className="field">
          <label htmlFor="username">Username (optional)</label>
          <input id="username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
        </div>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" required />
          <span className="field-hint">At least 8 characters.</span>
        </div>
        <div className="field">
          <label htmlFor="confirm">Confirm password</label>
          <input id="confirm" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" required />
        </div>
        {error && <p className="error-text" role="alert">{error}</p>}
        <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
          {loading ? 'Creating account…' : 'Create account'}
        </button>
      </form>
    </AuthLayout>
  )
}
