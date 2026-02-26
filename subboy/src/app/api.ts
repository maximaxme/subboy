const API_BASE = import.meta.env.VITE_API_BASE || ''

function getToken(): string | null {
  return localStorage.getItem('subboy_token')
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken()
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${API_BASE}/api${path}`, { ...options, headers })
  if (res.status === 401) {
    localStorage.removeItem('subboy_token')
    window.dispatchEvent(new Event('auth:logout'))
    throw new Error('Нужно войти')
  }
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText))
  return res.json()
}

export type SubscriptionApi = {
  id: number
  user_id: number
  category_id: number | null
  name: string
  price: string
  period: string
  next_payment: string
  created_at: string
}

export type CategoryApi = { id: number; user_id: number; name: string }

export type ReportSummaryApi = { total_monthly: number; by_category: Record<string, number> }

export const subscriptions = {
  list: () => api<SubscriptionApi[]>('/subscriptions'),
  create: (body: { name: string; price: number; period: string; category_id?: number; next_payment: string }) =>
    api<SubscriptionApi>('/subscriptions', { method: 'POST', body: JSON.stringify(body) }),
  delete: (id: number) => api<{ ok: boolean }>(`/subscriptions/${id}`, { method: 'DELETE' }),
}

export const categories = {
  list: () => api<CategoryApi[]>('/categories'),
  create: (name: string) =>
    api<CategoryApi>('/categories', { method: 'POST', body: JSON.stringify({ name }) }),
}

export const reports = {
  summary: () => api<ReportSummaryApi>('/reports/summary'),
}

export const auth = {
  devLogin: (userId: number) =>
    api<{ access_token: string; user_id: number }>('/auth/dev-login', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId }),
    }),
}
