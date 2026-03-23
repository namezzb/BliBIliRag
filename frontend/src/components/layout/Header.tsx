import { useAppStore } from '@/stores/appStore'

export default function Header() {
  const theme = useAppStore((state) => state.theme)
  const setTheme = useAppStore((state) => state.setTheme)
  const setSidebarOpen = useAppStore((state) => state.setSidebarOpen)
  const sidebarOpen = useAppStore((state) => state.sidebarOpen)

  return (
    <header
      data-testid="app-header"
      className="border-b px-4 py-3 sm:px-6"
      style={{
        backgroundColor: 'var(--surface)',
        borderColor: 'var(--line)',
      }}
    >
      <div className="mx-auto flex w-full max-w-[1600px] items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            data-testid="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="btn-secondary btn-sm"
            aria-label="Toggle sidebar"
          >
            ☰
          </button>

          <div>
            <p className="text-sm font-semibold" style={{ color: 'var(--text-main)' }}>
              B站收藏夹智能管理系统
            </p>
            <p className="text-xs" style={{ color: 'var(--text-subtle)' }}>
              Realtime Indexing · Retrieval · Conversation
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <span className="hidden sm:inline-flex badge-primary">联调环境</span>
          <button
            data-testid="theme-toggle"
            onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            className="btn-secondary btn-sm"
            aria-label="Toggle theme"
            title="Toggle theme"
          >
            {theme === 'light' ? '夜间' : '日间'}
          </button>
          <div className="h-9 w-9 rounded-full flex items-center justify-center text-white font-semibold"
            style={{ background: 'linear-gradient(120deg, #0b88d1, #16a8f5)' }}
          >
            U
          </div>
        </div>
      </div>
    </header>
  )
}
