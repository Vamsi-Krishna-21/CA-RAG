import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

/*
  Frontend route protection is only for navigation/UX -- it decides what
  the user is shown. It is NOT a security boundary: the FastAPI backend
  independently verifies the JWT on every protected endpoint regardless
  of what happens here.
*/
export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) return <div className="page">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}
