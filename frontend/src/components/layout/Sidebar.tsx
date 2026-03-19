import { Link, useLocation } from 'react-router-dom'
import { useAppStore } from '@/stores/appStore'

export default function Sidebar() {
  const location = useLocation()
  const sidebarOpen = useAppStore((state) => state.sidebarOpen)

  const isActive = (path: string) => location.pathname === path

  const navItems = [
    { path: '/', label: '视频库', icon: '📹' },
    { path: '/search', label: '搜索', icon: '🔍' },
    { path: '/chat', label: '对话', icon: '💬' },
    { path: '/tasks', label: '任务', icon: '⚙️' },
    { path: '/settings', label: '设置', icon: '⚙️' },
  ]

  return (
    <aside
      className={`${
        sidebarOpen ? 'w-64' : 'w-20'
      } bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-all duration-300 flex flex-col`}
    >
      {/* Logo */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="text-2xl font-bold text-primary">B</div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-colors ${
              isActive(item.path)
                ? 'bg-primary text-white'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          >
            <span className="text-xl">{item.icon}</span>
            {sidebarOpen && <span className="text-sm font-medium">{item.label}</span>}
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="text-xs text-gray-500 dark:text-gray-400 text-center">v0.1.0</div>
      </div>
    </aside>
  )
}
