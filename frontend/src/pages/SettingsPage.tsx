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
    setTimeout(() => setSaved(false), 1600)
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <section className="panel p-5 sm:p-6">
        <h2 className="text-3xl font-bold" style={{ color: 'var(--text-main)' }}>
          系统设置
        </h2>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-subtle)' }}>
          配置主题与联调地址，管理本地缓存状态。
        </p>
      </section>

      {saved && (
        <section className="panel p-4 text-sm" style={{ color: '#0f7b48', borderColor: '#bde9cf', background: '#ecfbf2' }}>
          设置已保存
        </section>
      )}

      <section className="panel p-5 sm:p-6 space-y-4">
        <h3 className="text-lg font-semibold" style={{ color: 'var(--text-main)' }}>
          外观
        </h3>
        <div className="flex gap-2">
          <button
            onClick={() => setTheme('light')}
            className={theme === 'light' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
          >
            浅色模式
          </button>
          <button
            onClick={() => setTheme('dark')}
            className={theme === 'dark' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
          >
            深色模式
          </button>
        </div>
      </section>

      <section className="panel p-5 sm:p-6 space-y-4">
        <h3 className="text-lg font-semibold" style={{ color: 'var(--text-main)' }}>
          API 配置
        </h3>
        <input
          type="text"
          value={apiUrl}
          onChange={(e) => setApiUrl(e.target.value)}
          className="input-base"
          placeholder="http://localhost:8000"
        />
        <p className="text-xs" style={{ color: 'var(--text-subtle)' }}>
          仅用于本地开发联调显示，不会覆盖 `VITE_API_URL` 环境变量。
        </p>
        <button onClick={handleSaveSettings} className="btn-primary">
          保存设置
        </button>
      </section>

      <section className="panel p-5 sm:p-6 space-y-3">
        <h3 className="text-lg font-semibold" style={{ color: 'var(--text-main)' }}>
          关于
        </h3>
        <div className="grid gap-2 text-sm" style={{ color: 'var(--text-subtle)' }}>
          <p>应用名称：B站收藏夹智能管理系统</p>
          <p>版本：0.1.0</p>
          <p>技术栈：React + TypeScript + Tailwind CSS</p>
          <p>后端：FastAPI + LangChain + ChromaDB</p>
        </div>
      </section>

      <section className="panel p-5 sm:p-6">
        <h3 className="text-lg font-semibold" style={{ color: 'var(--text-main)' }}>
          数据管理
        </h3>
        <p className="mt-2 text-xs" style={{ color: 'var(--text-subtle)' }}>
          清空后将移除本地缓存与会话偏好。
        </p>
        <button
          onClick={() => {
            if (confirm('确定要清空所有本地数据吗？')) {
              localStorage.clear()
              alert('本地数据已清空')
            }
          }}
          className="btn-danger mt-4"
        >
          清空本地数据
        </button>
      </section>
    </div>
  )
}
