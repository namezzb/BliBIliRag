import { useAppStore } from '@/stores/appStore'

export default function Header() {
  const theme = useAppStore((state) => state.theme)
  const setTheme = useAppStore((state) => state.setTheme)
  const setSidebarOpen = useAppStore((state) => state.setSidebarOpen)
  const sidebarOpen = useAppStore((state) => state.sidebarOpen)

  return (
    <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-between">
      {/* Left side */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          title="Toggle sidebar"
        >
          ☰
        </button>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">B站收藏夹智能管理系统</h1>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          title="Toggle theme"
        >
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
        <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-white font-bold">
          U
        </div>
      </div>
    </header>
  )
}
