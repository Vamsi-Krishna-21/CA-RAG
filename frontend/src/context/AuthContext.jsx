import { createContext, useContext, useEffect, useState } from 'react'
import { getMe } from '../services/authApi'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('carag_token')
    if (!token) {
      setLoading(false)
      return
    }
    getMe()
      .then((u) => setUser(u))
      .catch(() => {
        localStorage.removeItem('carag_token')
      })
      .finally(() => setLoading(false))
  }, [])

  const login = (token, userData) => {
    localStorage.setItem('carag_token', token)
    setUser(userData)
  }

  const logout = () => {
    localStorage.removeItem('carag_token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
