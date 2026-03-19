import axios, { AxiosInstance } from 'axios'

export interface Video {
  bvid: string
  title: string
  description?: string
  owner_name?: string
  duration?: number
  pubdate?: number
  tags: string[]
  view_count?: number
  like_count?: number
}

export interface SearchResult {
  bvid: string
  title: string
  content: string
  relevance_score: number
  source: string
}

export interface ChatSource {
  bvid: string
  title: string
  relevance: number
}

export interface Task {
  task_id: string
  task_type: string
  status: string
  progress: number
  total: number
  completed: number
  error?: string
  created_at: number
  updated_at: number
  result?: Record<string, any>
}

class ApiClient {
  private client: AxiosInstance

  constructor(baseURL: string = import.meta.env.VITE_API_URL || 'http://localhost:8000') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  // Video APIs
  async getVideos(skip: number = 0, limit: number = 20): Promise<{ videos: Video[]; total: number }> {
    const response = await this.client.get('/api/videos', {
      params: { skip, limit },
    })
    return response.data
  }

  async getVideo(bvid: string): Promise<Video> {
    const response = await this.client.get(`/api/videos/${bvid}`)
    return response.data
  }

  async deleteVideo(bvid: string): Promise<void> {
    await this.client.delete(`/api/videos/${bvid}`)
  }

  async importVideos(favoriteId: string): Promise<Task> {
    const response = await this.client.post('/api/v1/tasks', {
      task_type: 'import_videos',
      metadata: { favorite_id: favoriteId },
    })
    return response.data
  }

  // Search APIs
  async search(
    query: string,
    topK: number = 5,
    routingStrategy: string = 'hybrid'
  ): Promise<{ results: SearchResult[]; total_results: number }> {
    const response = await this.client.post('/api/v1/search', {
      query,
      top_k: topK,
      routing_strategy: routingStrategy,
    })
    return response.data
  }

  // Chat APIs
  async chat(
    query: string,
    conversationId: string = 'default',
    useSelfRag: boolean = true
  ): Promise<{ answer: string; sources: ChatSource[] }> {
    const response = await this.client.post('/api/v1/chat', {
      query,
      conversation_id: conversationId,
      use_self_rag: useSelfRag,
    })
    return response.data
  }

  // Task APIs
  async getTasks(status?: string, skip: number = 0, limit: number = 20): Promise<{ tasks: Task[]; total: number }> {
    const response = await this.client.get('/api/v1/tasks', {
      params: { status, skip, limit },
    })
    return response.data
  }

  async getTask(taskId: string): Promise<Task> {
    const response = await this.client.get(`/api/v1/tasks/${taskId}`)
    return response.data
  }

  async updateTask(taskId: string, updates: Partial<Task>): Promise<Task> {
    const response = await this.client.patch(`/api/v1/tasks/${taskId}`, updates)
    return response.data
  }

  async cancelTask(taskId: string): Promise<void> {
    await this.client.delete(`/api/v1/tasks/${taskId}`)
  }

  async getTaskStats(): Promise<Record<string, number>> {
    const response = await this.client.get('/api/v1/tasks/stats/overview')
    return response.data
  }
}

export const apiClient = new ApiClient()
