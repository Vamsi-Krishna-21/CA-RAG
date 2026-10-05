import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { resetPassword } from '../services/authApi'
import AuthLayout from '../components/common/AuthLayout.jsx'

export default function ResetPassword() {
  const { token } = useParams()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  // After a successful reset, send the user to the sign-in page.
  useEffect(() => {
    if (!message) return undefined
    const timer = setTimeout(() => navigate('/login'), 2000)
    return () => clearTimeout(timer)
  }, [message, navigate])

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setLoading(true)
    try {
      const data = await resetPassword(token, password)
      setMessage(data.detail || 'Password reset successful')
    } catch (err) {
      setError(
        err.response
          ? err.response.data?.detail || 'Password reset failed.'
          : "Can't reach the server. Check that the backend is running, then try again.",
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Choose a new password" footer={<Link to="/login">Back to sign in</Link>}>
      <form onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="new-password">New password</label>
          <input id="new-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" autoFocus required />
          <span className="field-hint">At least 8 characters.</span>
        </div>
        <div className="field">
          <label htmlFor="confirm-password">Confirm new password</label>
          <input id="confirm-password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" required />
        </div>
        {error && <p className="error-text" role="alert">{error}</p>}
        {message && <p className="success-text" role="status">{message} Redirecting to sign in…</p>}
        <button className="btn btn-primary btn-block" type="submit" disabled={loading || !!message}>
          {loading ? 'Saving…' : 'Reset password'}
        </button>
      </form>
    </AuthLayout>
  )
}
