import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { auth } from '../api'
import { setUnauthorizedHandler } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null)) // session expired mid-use -> back to login
    auth.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (data) => setUser(await auth.login(data)), [])
  const register = useCallback(async (data) => setUser(await auth.register(data)), [])
  const logout = useCallback(async () => {
    try { await auth.logout() } finally { setUser(null) }
  }, [])
  const updateProfile = useCallback(async (data) => setUser(await auth.update(data)), [])

  const value = useMemo(() => ({ user, loading, login, register, logout, updateProfile }), [user, loading, login, register, logout, updateProfile])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
