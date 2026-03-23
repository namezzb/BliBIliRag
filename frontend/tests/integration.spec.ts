import { expect, test } from '@playwright/test'

const API_URL = process.env.PLAYWRIGHT_API_URL || 'http://localhost:8000'

test.describe('BiliBiliRag Real Integration', () => {
  test.beforeEach(async ({ page }) => {
    const health = await page.request.get(`${API_URL}/api/health`)
    expect(health.ok()).toBeTruthy()
  })

  test('should render shell and navigate between core pages', async ({ page, baseURL }) => {
    await page.goto('/')

    await expect(page.getByTestId('app-header')).toBeVisible()
    await expect(page.getByTestId('app-sidebar')).toBeVisible()

    await page.getByTestId('nav-search').click()
    await expect(page).toHaveURL(`${baseURL}/search`)

    await page.getByTestId('nav-chat').click()
    await expect(page).toHaveURL(`${baseURL}/chat`)

    await page.getByTestId('nav-tasks').click()
    await expect(page).toHaveURL(`${baseURL}/tasks`)

    await page.getByTestId('nav-settings').click()
    await expect(page).toHaveURL(`${baseURL}/settings`)

    await page.getByTestId('nav-videos').click()
    await expect(page).toHaveURL(`${baseURL}/`)
  })

  test('should toggle theme and sidebar', async ({ page }) => {
    await page.goto('/')

    const appRoot = page.getByTestId('app-root')
    const initialClass = await appRoot.getAttribute('class')

    await page.getByTestId('theme-toggle').click()
    const newClass = await appRoot.getAttribute('class')
    expect(initialClass).not.toEqual(newClass)

    const sidebar = page.getByTestId('app-sidebar')
    const initialSidebarClass = await sidebar.getAttribute('class')
    await page.getByTestId('sidebar-toggle').click()
    await page.waitForTimeout(250)
    const newSidebarClass = await sidebar.getAttribute('class')

    expect(initialSidebarClass).not.toEqual(newSidebarClass)
  })

  test('videos page should call api and render stable state', async ({ page }) => {
    await page.goto('/')

    const videosResp = await page.request.get(`${API_URL}/api/videos?skip=0&limit=20`)
    expect(videosResp.status()).toBeLessThan(500)

    await expect(page.getByTestId('videos-page')).toBeVisible()
    await expect(page.getByTestId('videos-import-btn')).toBeVisible()
  })

  test('search page should submit query request and keep ui stable', async ({ page }) => {
    await page.goto('/search')
    await page.getByTestId('search-input').fill('RAG 检索策略')

    const [request] = await Promise.all([
      page.waitForRequest(
        (req) => req.url().includes('/api/v1/search') && req.method() === 'POST',
        { timeout: 15000 }
      ),
      page.getByTestId('search-submit').click(),
    ])

    expect(request.postData()).toContain('RAG')
    await expect(page.getByTestId('search-page')).toBeVisible()
    await expect(page.getByTestId('search-results')).toBeVisible()
  })

  test('chat page should submit chat request and keep ui stable', async ({ page }) => {
    await page.goto('/chat')
    await page.getByTestId('chat-input').fill('请总结当前知识库的能力')

    const [request] = await Promise.all([
      page.waitForRequest(
        (req) => req.url().includes('/api/v1/chat') && req.method() === 'POST',
        { timeout: 15000 }
      ),
      page.getByTestId('chat-send').click(),
    ])

    expect(request.postData()).toContain('知识库')
    await expect(page.getByTestId('chat-page')).toBeVisible()
    await expect(page.getByTestId('chat-messages')).toBeVisible()
  })

  test('tasks page should render filter and refresh controls', async ({ page }) => {
    await page.goto('/tasks')

    const tasksResp = await page.request.get(`${API_URL}/api/v1/tasks?skip=0&limit=20`)
    expect(tasksResp.status()).toBeLessThan(500)

    await expect(page.getByTestId('tasks-page')).toBeVisible()
    await expect(page.getByTestId('tasks-refresh')).toBeVisible()
    await expect(page.getByTestId('tasks-filter-all')).toBeVisible()
  })

  test('should remain usable on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/')

    await expect(page.getByTestId('app-header')).toBeVisible()
    await page.getByTestId('sidebar-toggle').click()
    await expect(page.getByTestId('app-sidebar')).toBeVisible()
  })
})
