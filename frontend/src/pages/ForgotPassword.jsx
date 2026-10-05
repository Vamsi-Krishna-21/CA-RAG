import { useState } from 'react'
import { Link } from 'react-router-dom'
import { forgotPassword } from '../services/authApi'
import AuthLayout from '../components/common/AuthLayout.jsx'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    setLoading(true)
    try {
      const data = await forgotPassword(email)
      setMessage(data.detail || 'If that email is registered, a reset link has been sent')
    } catch (err) {
      setError(
        err.response
          ? err.response.data?.detail || 'Could not send reset link.'
          : "Can't reach the server. Check that the backend is running, then try again.",
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Reset your password"
      subtitle="Enter your email and we'll send you a link to choose a new password."
      footer={<Link to="/login">Back to sign in</Link>}
    >
      <form onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" autoFocus required />
        </div>
        {error && <p className="error-text" role="alert">{error}</p>}
        {message && <p className="success-text" role="status">{message}</p>}
        <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
          {loading ? 'Sending…' : 'Send reset link'}
        </button>
      </form>
    </AuthLayout>
  )
}
