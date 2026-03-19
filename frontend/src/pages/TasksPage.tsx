import { useState, useEffect } from 'react'
import { apiClient, Task } from '@/services/api'
import { useAppStore } from '@/stores/appStore'

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)

  const appTasks = useAppStore((state) => state.tasks)
  const setAppTasks = useAppStore((state) => state.setTasks)

  useEffect(() => {
    loadTasks()
    const interval = setInterval(loadTasks, 2000)
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-200'
      case 'running':
        return 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-200'
      case 'completed':
        return 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200'
      case 'failed':
        return 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200'
      case 'cancelled':
        return 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200'
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">任务管理</h2>
        <button
          onClick={loadTasks}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          刷新
        </button>
      </div>

      {/* Status filter */}
      <div className="flex gap-2">
        <button
          onClick={() => setStatusFilter(undefined)}
          className={`px-3 py-1 text-sm rounded ${
            statusFilter === undefined
              ? 'bg-primary text-white'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
          }`}
        >
          全部
        </button>
        {['pending', 'running', 'completed', 'failed'].map((status) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            className={`px-3 py-1 text-sm rounded ${
              statusFilter === status
                ? 'bg-primary text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      {/* Error message */}
      {error && (
        <div className="p-4 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg">
          {error}
        </div>
      )}

      {/* Tasks table */}
      {loading ? (
        <div className="text-center py-12">加载中...</div>
      ) : tasks.length === 0 ? (
        <div className="text-center py-12 text-gray-500">暂无任务</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="px-4 py-2 text-left text-sm font-semibold text-gray-900 dark:text-white">
                  任务ID
                </th>
                <th className="px-4 py-2 text-left text-sm font-semibold text-gray-900 dark:text-white">
                  类型
                </th>
                <th className="px-4 py-2 text-left text-sm font-semibold text-gray-900 dark:text-white">
                  状态
                </th>
                <th className="px-4 py-2 text-left text-sm font-semibold text-gray-900 dark:text-white">
                  进度
                </th>
                <th className="px-4 py-2 text-left text-sm font-semibold text-gray-900 dark:text-white">
                  创建时间
                </th>
                <th className="px-4 py-2 text-left text-sm font-semibold text-gray-900 dark:text-white">
                  操作
                </th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr
                  key={task.task_id}
                  className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  <td className="px-4 py-2 text-sm text-gray-900 dark:text-white font-mono">
                    {task.task_id.slice(0, 8)}...
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-900 dark:text-white">{task.task_type}</td>
                  <td className="px-4 py-2 text-sm">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(task.status)}`}>
                      {task.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-900 dark:text-white">
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all"
                          style={{ width: `${task.progress}%` }}
                        />
                      </div>
                      <span className="text-xs">{task.progress}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">
                    {new Date(task.created_at * 1000).toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {task.status === 'pending' || task.status === 'running' ? (
                      <button
                        onClick={() => handleCancel(task.task_id)}
                        className="px-2 py-1 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded hover:bg-red-200 dark:hover:bg-red-800 transition-colors"
                      >
                        取消
                      </button>
                    ) : (
                      <span className="text-xs text-gray-500">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
