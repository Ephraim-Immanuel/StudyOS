import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { Loading } from './components/ui'
import { useAuth } from './context/AuthContext'
import Dashboard from './pages/Dashboard'
import Exams from './pages/Exams'
import { Login, Register } from './pages/AuthPages'
import Planner from './pages/Planner'
import Sessions from './pages/Sessions'
import Settings from './pages/Settings'
import SubjectDetail from './pages/SubjectDetail'
import Subjects from './pages/Subjects'
import Tasks from './pages/Tasks'

function Protected({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <Loading label="Starting StudyOS…" />
  return user ? children : <Navigate to="/login" replace />
}

function GuestOnly({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <Loading label="Starting StudyOS…" />
  return user ? <Navigate to="/" replace /> : children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
      <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/subjects" element={<Subjects />} />
        <Route path="/subjects/:id" element={<SubjectDetail />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/exams" element={<Exams />} />
        <Route path="/sessions" element={<Sessions />} />
        <Route path="/planner" element={<Planner />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
