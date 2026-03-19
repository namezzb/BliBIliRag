import { useState } from 'react'
import { useAppStore } from '@/stores/appStore'

export default function SettingsPage() {
  const theme = useAppStore((state) => state.theme)
  const setTheme = useAppStore((state) => state.setTheme)
  const [apiUrl, setApiUrl] = useState(localStorage.getItem('apiUrl') || 'http://localhost:8000')
  const [saved, setSaved] = useState(false)

  const handleSaveSettings = () => {
    localStorage.setItem('apiUrl', apiUrl)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">设置</h2>

      {/* Success message */}
      {saved && (
        <div className="p-4 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200 rounded-lg">
          设置已保存
        </div>
      )}

      {/* Theme settings */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">外观</h3>

        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">主题</label>
          <div className="flex gap-4">
            <button
              onClick={() => setTheme('light')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                theme === 'light'
                  ? 'bg-primary text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
              }`}
            >
              ☀️ 浅色
            </button>
            <button
              onClick={() => setTheme('dark')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                theme === 'dark'
                  ? 'bg-primary text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
              }`}
            >
              🌙 深色
            </button>
          </div>
        </div>
      </div>

      {/* API settings */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">API 配置</h3>

        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">API 地址</label>
          <input
            type="text"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="http://localhost:8000"
          />
          <p className="text-xs text-gray-500 dark:text-gray-400">
            后端 API 服务器地址，默认为 http://localhost:8000
          </p>
        </div>

        <button
          onClick={handleSaveSettings}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          保存设置
        </button>
      </div>

      {/* About */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">关于</h3>

        <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <p>
            <strong>应用名称:</strong> B站收藏夹智能管理系统
          </p>
          <p>
            <strong>版本:</strong> 0.1.0
          </p>
          <p>
            <strong>技术栈:</strong> React + TypeScript + Tailwind CSS
          </p>
          <p>
            <strong>后端:</strong> FastAPI + LangChain + ChromaDB
          </p>
        </div>
      </div>

      {/* Data management */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">数据管理</h3>

        <button
          onClick={() => {
            if (confirm('确定要清空所有本地数据吗？')) {
              localStorage.clear()
              alert('本地数据已清空')
            }
          }}
          className="px-4 py-2 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg hover:bg-red-200 dark:hover:bg-red-800 transition-colors"
        >
          清空本地数据
        </button>
      </div>
    </div>
  )
}
