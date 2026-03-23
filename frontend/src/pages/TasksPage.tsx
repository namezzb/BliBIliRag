import { useEffect, useState } from 'react'
import { apiClient, Task } from '@/services/api'
import { useAppStore } from '@/stores/appStore'

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)

  const setAppTasks = useAppStore((state) => state.setTasks)

  useEffect(() => {
    void loadTasks()
    const interval = setInterval(() => {
      void loadTasks()
    }, 3000)

    return () => clearInterval(interval)
  }, [statusFilter])

  const loadTasks = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiClient.getTasks(statusFilter, 0, 50)
      setTasks(data.tasks)
      setAppTasks(data.tasks)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async (taskId: string) => {
    if (!confirm('确定要取消这个任务吗？')) return

    try {
      await apiClient.cancelTask(taskId)
      await loadTasks()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel task')
    }
  }

  const statusOptions = [
    { value: undefined, label: '全部', testId: 'tasks-filter-all' },
    { value: 'pending', label: '待处理', testId: 'tasks-filter-pending' },
    { value: 'running', label: '运行中', testId: 'tasks-filter-running' },
    { value: 'completed', label: '已完成', testId: 'tasks-filter-completed' },
    { value: 'failed', label: '失败', testId: 'tasks-filter-failed' },
  ]

  return (
    <div data-testid="tasks-page" className="space-y-6 animate-fade-in">
      <section className="panel p-5 sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-3xl font-bold" style={{ color: 'var(--text-main)' }}>
              任务队列监控
            </h2>
            <p className="mt-2 text-sm" style={{ color: 'var(--text-subtle)' }}>
              实时观察导入、索引和处理任务状态。
            </p>
          </div>
          <button data-testid="tasks-refresh" onClick={() => void loadTasks()} className="btn-primary">
            刷新
          </button>
        </div>
      </section>

      <section className="panel p-4">
        <div className="flex flex-wrap gap-2">
          {statusOptions.map((option) => (
            <button
              key={String(option.value)}
              data-testid={option.testId}
              onClick={() => setStatusFilter(option.value)}
              className={statusFilter === option.value ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
            >
              {option.label}
            </button>
          ))}
        </div>
      </section>

      {error && (
        <section className="panel p-4 text-sm" style={{ color: '#a92929', borderColor: '#f5bcbc', background: '#fff1f1' }}>
          {error}
        </section>
      )}

      <section className="panel overflow-hidden">
        {loading ? (
          <div className="p-8 text-sm" style={{ color: 'var(--text-subtle)' }}>
            正在同步任务队列...
          </div>
        ) : tasks.length === 0 ? (
          <div className="p-10 text-center">
            <p className="text-lg font-semibold" style={{ color: 'var(--text-main)' }}>
              暂无任务
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px]">
              <thead>
                <tr style={{ background: 'var(--surface-muted)' }}>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase">任务ID</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase">类型</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase">状态</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase">进度</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase">创建时间</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase">操作</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.task_id} className="border-t" style={{ borderColor: 'var(--line)' }}>
                    <td className="px-4 py-3 text-xs font-mono" style={{ color: 'var(--text-subtle)' }}>
                      {task.task_id.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-main)' }}>
                      {task.task_type}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={
                          task.status === 'completed'
                            ? 'badge-success'
                            : task.status === 'running'
                              ? 'badge-primary'
                              : task.status === 'failed'
                                ? 'badge-danger'
                                : 'badge-warning'
                        }
                      >
                        {task.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-subtle)' }}>
                      {task.progress}%
                    </td>
                    <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-subtle)' }}>
                      {new Date(task.created_at * 1000).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {task.status === 'pending' || task.status === 'running' ? (
                        <button onClick={() => void handleCancel(task.task_id)} className="btn-danger btn-sm">
                          取消
                        </button>
                      ) : (
                        <span style={{ color: 'var(--text-subtle)' }}>-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
