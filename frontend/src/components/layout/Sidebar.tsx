import { Link, useLocation } from 'react-router-dom'
import { useAppStore } from '@/stores/appStore'

export default function Sidebar() {
  const location = useLocation()
  const sidebarOpen = useAppStore((state) => state.sidebarOpen)

  const navItems = [
    { path: '/', label: '视频库', icon: '🧰', testId: 'nav-videos' },
    { path: '/search', label: '智能搜索', icon: '🛰', testId: 'nav-search' },
    { path: '/chat', label: '对话助手', icon: '🤖', testId: 'nav-chat' },
    { path: '/tasks', label: '任务队列', icon: '📡', testId: 'nav-tasks' },
    { path: '/settings', label: '系统设置', icon: '⚙', testId: 'nav-settings' },
  ]

  return (
    <aside
      data-testid="app-sidebar"
      className={`relative z-20 h-full shrink-0 border-r transition-all duration-300 ${
        sidebarOpen ? 'w-72' : 'w-[88px]'
      }`}
      style={{
        backgroundColor: 'var(--surface)',
        borderColor: 'var(--line)',
      }}
    >
      <div className="h-full flex flex-col">
        <div className="px-4 py-5 border-b" style={{ borderColor: 'var(--line)' }}>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl flex items-center justify-center text-white font-bold"
              style={{ background: 'linear-gradient(140deg, #0b88d1, #16a8f5)' }}
            >
              BR
            </div>
            {sidebarOpen && (
              <div className="min-w-0">
                <p className="text-sm font-semibold tracking-wide" style={{ color: 'var(--text-main)' }}>
                  BiliBiliRag
                </p>
                <p className="text-xs truncate" style={{ color: 'var(--text-subtle)' }}>
                  Video Intelligence Console
                </p>
              </div>
            )}
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-2">
          {navItems.map((item) => {
            const active = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={item.testId}
                className={`group flex items-center gap-3 rounded-xl px-3 py-3 transition-all duration-200 ${
                  active ? 'shadow-panel' : ''
                }`}
                style={
                  active
                    ? {
                        background: 'linear-gradient(120deg, #0b88d1, #16a8f5)',
                        color: '#fff',
                      }
                    : { color: 'var(--text-main)' }
                }
              >
                <span className="text-lg leading-none shrink-0">{item.icon}</span>
                {sidebarOpen && <span className="text-sm font-medium truncate">{item.label}</span>}
              </Link>
            )
          })}
        </nav>

        <div className="px-4 py-4 border-t" style={{ borderColor: 'var(--line)' }}>
          <div className="panel-muted px-3 py-2 text-xs font-medium" style={{ color: 'var(--text-subtle)' }}>
            v0.1.0 · Dashboard Mode
          </div>
        </div>
      </div>
    </aside>
  )
}
