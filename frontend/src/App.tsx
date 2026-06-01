import { Navigate, NavLink, Route, Routes } from 'react-router-dom'
import { GeneratePage } from './pages/GeneratePage'
import { ApplicationsPage } from './pages/ApplicationsPage'

export function App() {
  return (
    <div className="app-shell">
      <header className="top-nav">
        <span className="wordmark">Job Application Tailor</span>
        <nav className="nav-links">
          <NavLink to="/generate" className={navClass}>
            Сгенерировать
          </NavLink>
          <NavLink to="/applications" className={navClass}>
            Заявки
          </NavLink>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<Navigate to="/generate" replace />} />
        <Route path="/generate" element={<GeneratePage />} />
        <Route path="/applications" element={<ApplicationsPage />} />
        <Route path="*" element={<Navigate to="/generate" replace />} />
      </Routes>
    </div>
  )
}

function navClass({ isActive }: { isActive: boolean }): string {
  return isActive ? 'nav-link is-active' : 'nav-link'
}
