import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const LINKS = [
  ['/', 'Dashboard'],
  ['/subjects', 'Subjects'],
  ['/tasks', 'Tasks'],
  ['/exams', 'Exams'],
  ['/sessions', 'Study'],
  ['/planner', 'Planner'],
]

export default function Layout() {
  const { user, logout } = useAuth()
  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>
      <header className="topbar">
        <div className="topbar-inner">
          <span className="brand">📚 StudyOS</span>
          <nav aria-label="Main">
            {LINKS.map(([to, label]) => (
              <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => (isActive ? 'active' : '')}>
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="user-menu">
            <NavLink to="/settings" className="user-name">{user.name}</NavLink>
            <button className="btn btn-small" onClick={logout}>Log out</button>
          </div>
        </div>
      </header>
      <main id="main" className="container">
        <Outlet />
      </main>
    </>
  )
}
