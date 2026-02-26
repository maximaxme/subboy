import { useState, useEffect, useCallback } from 'react'
import { Menu, Plus, DollarSign } from 'lucide-react'
import { StatsCard } from '@/app/components/StatsCard'
import { SubscriptionList } from '@/app/components/SubscriptionList'
import { SubscriptionDetail } from '@/app/components/SubscriptionDetail'
import { AddSubscription } from '@/app/components/AddSubscription'
import * as api from '@/app/api'
import type { SubscriptionApi } from '@/app/api'
import type { CategoryApi } from '@/app/api'

type SubWithCategory = SubscriptionApi & { categoryName?: string }
type Screen = 'login' | 'home' | 'detail' | 'add'

function getToken(): string | null {
  return localStorage.getItem('subboy_token')
}

function setToken(token: string) {
  localStorage.setItem('subboy_token', token)
}

function clearToken() {
  localStorage.removeItem('subboy_token')
}

export default function App() {
  const [token, setTokenState] = useState<string | null>(() => getToken())
  const [screen, setScreen] = useState<Screen>(token ? 'home' : 'login')
  const [subscriptions, setSubscriptions] = useState<SubscriptionApi[]>([])
  const [categories, setCategories] = useState<CategoryApi[]>([])
  const [report, setReport] = useState<api.ReportSummaryApi | null>(null)
  const [selectedSub, setSelectedSub] = useState<SubWithCategory | null>(null)
  const [loading, setLoading] = useState(true)
  const [loginError, setLoginError] = useState('')
  const [devUserId, setDevUserId] = useState('')

  const loadData = useCallback(async () => {
    if (!getToken()) return
    setLoading(true)
    try {
      const [subs, cats, sum] = await Promise.all([
        api.subscriptions.list(),
        api.categories.list(),
        api.reports.summary(),
      ])
      setSubscriptions(subs)
      setCategories(cats)
      setReport(sum)
    } catch {
      setTokenState(null)
      clearToken()
      setScreen('login')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (token) loadData()
  }, [token, loadData])

  useEffect(() => {
    const onLogout = () => {
      setTokenState(null)
      setScreen('login')
    }
    window.addEventListener('auth:logout', onLogout)
    return () => window.removeEventListener('auth:logout', onLogout)
  }, [])

  const handleDevLogin = async () => {
    const id = parseInt(devUserId, 10)
    if (Number.isNaN(id)) {
      setLoginError('Введите Telegram user id (число)')
      return
    }
    setLoginError('')
    try {
      const { access_token } = await api.auth.devLogin(id)
      setToken(access_token)
      setTokenState(access_token)
      setScreen('home')
    } catch (e) {
      setLoginError(e instanceof Error ? e.message : 'Ошибка входа')
    }
  }

  const handleLogout = () => {
    clearToken()
    setTokenState(null)
    setScreen('login')
  }

  const handleSelectSub = (sub: SubWithCategory) => {
    setSelectedSub(sub)
    setScreen('detail')
  }

  const handleDeleteSub = async () => {
    if (!selectedSub) return
    try {
      await api.subscriptions.delete(selectedSub.id)
      setSubscriptions((prev) => prev.filter((s) => s.id !== selectedSub.id))
      setSelectedSub(null)
      setScreen('home')
      await loadData()
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Ошибка удаления')
    }
  }

  const handleAddSubmit = async (data: {
    name: string
    price: number
    period: 'monthly' | 'yearly'
    next_payment: string
    category_id: number | null
    categoryName?: string
    color: string
  }) => {
    let categoryId = data.category_id
    if (categoryId == null && data.categoryName?.trim()) {
      const created = await api.categories.create(data.categoryName.trim())
      categoryId = created.id
    }
    await api.subscriptions.create({
      name: data.name,
      price: data.price,
      period: data.period,
      next_payment: data.next_payment,
      category_id: categoryId ?? undefined,
    })
    setScreen('home')
    await loadData()
  }

  if (screen === 'login') {
    const isLocalhost = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(window.location.origin)
    return (
      <div className="dark min-h-screen bg-background">
        <div className="max-w-md mx-auto bg-background min-h-screen border-x border-border p-4 flex flex-col items-center justify-center">
          <h1 className="text-2xl text-foreground font-medium mb-2">Subboy</h1>
          <p className="text-muted-foreground text-center mb-6">
            Учёт подписок — те же данные, что и в боте
          </p>
          <p className="text-sm text-muted-foreground text-center mb-4">
            {isLocalhost
              ? 'На localhost: введите Telegram user id (узнать в @userinfobot) и нажмите «Войти».'
              : 'Войдите через кнопку «Login with Telegram» (нужен HTTPS) или по user id.'}
          </p>
          <input
            type="number"
            value={devUserId}
            onChange={(e) => setDevUserId(e.target.value)}
            placeholder="Telegram user id"
            className="w-full max-w-xs bg-secondary/40 border border-border rounded-lg px-4 py-3 text-foreground placeholder:text-muted-foreground mb-3"
          />
          <button
            type="button"
            onClick={handleDevLogin}
            className="w-full max-w-xs bg-foreground text-background py-3 rounded-lg hover:opacity-90 transition-opacity"
          >
            Войти по id
          </button>
          {loginError && <p className="text-destructive text-sm mt-2">{loginError}</p>}
        </div>
      </div>
    )
  }

  if (screen === 'add') {
    return (
      <div className="dark min-h-screen bg-background">
        <div className="max-w-md mx-auto bg-background min-h-screen border-x border-border">
          <AddSubscription
            categories={categories}
            onBack={() => setScreen('home')}
            onSubmit={handleAddSubmit}
          />
        </div>
      </div>
    )
  }

  if (screen === 'detail' && selectedSub) {
    const colorIndex = subscriptions.findIndex((s) => s.id === selectedSub.id)
    return (
      <div className="dark min-h-screen bg-background">
        <div className="max-w-md mx-auto bg-background min-h-screen border-x border-border">
          <SubscriptionDetail
            subscription={selectedSub}
            colorIndex={colorIndex >= 0 ? colorIndex : 0}
            onBack={() => { setSelectedSub(null); setScreen('home') }}
            onDelete={handleDeleteSub}
          />
        </div>
      </div>
    )
  }

  if (loading && subscriptions.length === 0) {
    return (
      <div className="dark min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">Загрузка…</p>
      </div>
    )
  }

  const monthlyTotal = report?.total_monthly ?? 0
  const yearlyTotal = monthlyTotal * 12

  return (
    <div className="dark min-h-screen bg-background">
      <div className="max-w-md mx-auto bg-background min-h-screen border-x border-border">
        <header className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm p-4 border-b border-border flex items-center justify-between">
          <button
            type="button"
            className="p-2 -ml-2 hover:bg-secondary/60 rounded-lg transition-colors"
            aria-label="Menu"
          >
            <Menu className="w-5 h-5 text-foreground" />
          </button>
          <span className="text-foreground font-medium">Subscriptions</span>
          <button
            type="button"
            onClick={() => setScreen('add')}
            className="p-2 -mr-2 hover:bg-secondary/60 rounded-lg transition-colors"
            aria-label="Add"
          >
            <Plus className="w-5 h-5 text-foreground" />
          </button>
        </header>

        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <StatsCard
              label="В месяц"
              value={`${monthlyTotal.toFixed(2)} ₽`}
              icon={<DollarSign className="w-4 h-4" />}
            />
            <StatsCard label="В год" value={`${yearlyTotal.toFixed(2)} ₽`} />
            <StatsCard
              label="Active Services"
              value={String(subscriptions.length)}
              icon={<DollarSign className="w-4 h-4" />}
              className="col-span-2"
            />
          </div>
        </div>

        <SubscriptionList
          subscriptions={subscriptions.map((s) => ({
            ...s,
            categoryName: s.category_id ? categories.find((c) => c.id === s.category_id)?.name : undefined,
          }))}
          categories={categories}
          onSelect={handleSelectSub}
        />

        <div className="p-4 border-t border-border">
          <button
            type="button"
            onClick={handleLogout}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Выйти
          </button>
        </div>
      </div>
    </div>
  )
}
