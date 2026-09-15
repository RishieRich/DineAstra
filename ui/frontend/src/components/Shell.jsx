import { NavLink, useLocation } from 'react-router-dom'
import BrandMark from './BrandMark'

const NAV_GROUPS = [
  {
    label: 'Main',
    items: [
      { to: '/overview', label: 'Command centre', icon: '⌂' },
      { to: '/ask', label: 'Ask DineAstra', icon: '✦' },
      { to: '/data', label: 'Data Studio', icon: '↥', badge: 'NEW' },
    ],
  },
  {
    label: 'Operations',
    items: [
      { to: '/banquets', label: 'Events & banquets', icon: '◇' },
      { to: '/proof', label: 'Daily proof', icon: '✓' },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { to: '/brain', label: 'Operating brain', icon: '◎' },
      { to: '/connections', label: 'Connections', icon: '⌁' },
    ],
  },
]

const TITLES = {
  '/overview': 'Command centre',
  '/ask': 'Ask DineAstra',
  '/data': 'Data Studio',
  '/banquets': 'Events & banquets',
  '/proof': 'Daily proof',
  '/brain': 'Operating brain',
  '/connections': 'Connections',
}

function Shell({ children, user, onSignOut }) {
  const location = useLocation()
  const section = location.pathname.startsWith('/banquets/')
    ? 'Event detail'
    : TITLES[location.pathname] || 'Workspace'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <BrandMark inverse />
          <div><p>DineAstra</p><small>by ARQ One AI Labs</small></div>
        </div>

        <div className="workspace-card">
          <p>Client workspace</p>
          <strong>Astra House Group</strong>
          <small>Restaurant & hospitality operations</small>
        </div>

        <nav aria-label="Primary">
          {NAV_GROUPS.map((group) => (
            <div className="nav-group" key={group.label}>
              <p>{group.label}</p>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => `nav-link ${isActive ? 'nav-link--active' : ''}`}
                >
                  <span className="nav-icon" aria-hidden="true">{item.icon}</span>
                  <span>{item.label}</span>
                  {item.badge ? <em>{item.badge}</em> : null}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-foot">
          <p><i /> Sample workspace</p>
          <small>Customer data stays local in this prototype.</small>
        </div>
      </aside>

      <div className="app-column">
        <header className="topbar">
          <div className="crumbs"><span>Astra House Group</span><b>/</b><strong>{section}</strong></div>
          <div className="topbar-actions">
            <span className="date-chip">16 Sep 2026</span>
            <span className="sample-chip"><i /> Sample + uploads</span>
            <span className="user-chip" title={`${user.name} · ${user.role}`}>{user.name?.charAt(0) || 'A'}</span>
            <button type="button" className="signout-button" onClick={onSignOut}>Sign out</button>
          </div>
        </header>

        <main className="app-main">{children}</main>

        <footer className="app-footer">
          <span>Workspace: <strong>Astra House Group</strong></span>
          <span>Product: <strong>DineAstra by ARQ One AI Labs</strong></span>
          <span className="secure-note"><i /> Securely connected</span>
        </footer>
      </div>
    </div>
  )
}

export default Shell
