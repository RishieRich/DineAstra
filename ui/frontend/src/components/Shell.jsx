import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/overview', label: 'Overview' },
  { to: '/banquets', label: 'Banquets' },
  { to: '/proof', label: 'Proof' },
  { to: '/ask', label: 'Ask' },
  { to: '/brain', label: 'Brain' },
  { to: '/connections', label: 'Connections' },
]

/**
 * The frame every signed-in screen sits in: burgundy masthead, ruled nav,
 * paper content well. The "Sample data" chip is part of the frame, so it
 * cannot go missing from a screen.
 */
function Shell({ children, user, onSignOut }) {
  return (
    <div className="flex min-h-full flex-col bg-paper">
      <header className="bg-burgundy">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-sm px-md py-md">
          <div className="flex items-baseline gap-md">
            <span className="font-serif text-2xl text-gold">Darpan</span>
            <span className="rounded-sm border border-gold px-sm py-xs text-xs tracking-[0.14em] text-gold-soft">
              Sample data
            </span>
          </div>
          <div className="flex items-center gap-md">
            {user ? (
              <span className="text-sm text-gold-soft">
                {user.name} <span className="text-gold">&middot;</span> {user.role}
              </span>
            ) : null}
            {onSignOut ? (
              <button
                type="button"
                onClick={onSignOut}
                className="rounded-sm border border-gold px-md py-xs text-sm text-gold-soft"
              >
                Sign out
              </button>
            ) : null}
          </div>
        </div>

        <nav aria-label="Primary" className="border-t border-gold">
          <ul className="mx-auto flex w-full max-w-6xl gap-lg overflow-x-auto overflow-y-hidden px-md">
            {NAV_ITEMS.map((item) => (
              <li key={item.to} className="shrink-0">
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    `-mb-px inline-block border-b-2 py-sm text-sm ${
                      isActive
                        ? 'border-gold text-gold'
                        : 'border-transparent text-gold-soft'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-md py-xl">{children}</main>

      <footer className="border-t border-line">
        <div className="mx-auto w-full max-w-6xl px-md py-md text-xs text-muted">
          Darpan runs entirely on generated sample data. No property system is
          connected.
        </div>
      </footer>
    </div>
  )
}

export default Shell
