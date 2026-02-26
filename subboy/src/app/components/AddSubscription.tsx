import { useState } from 'react'
import { ArrowLeft, Save } from 'lucide-react'
import type { CategoryApi } from '@/app/api'
import { getSubscriptionColor } from './SubscriptionCard'

const SUBSCRIPTION_COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', '#ef4444'] as const

const CATEGORY_OPTIONS = [
  'Streaming',
  'Productivity',
  'Cloud Storage',
  'Music',
  'Gaming',
  'News',
  'Other',
]

type Props = {
  categories: CategoryApi[]
  onBack: () => void
  onSubmit: (data: {
    name: string
    price: number
    period: 'monthly' | 'yearly'
    next_payment: string
    category_id: number | null
    categoryName?: string
    color: string
  }) => Promise<void>
}

export function AddSubscription({ categories, onBack, onSubmit }: Props) {
  const [name, setName] = useState('')
  const [price, setPrice] = useState('')
  const [period, setPeriod] = useState<'monthly' | 'yearly'>('monthly')
  const [nextPayment, setNextPayment] = useState('')
  const [categoryName, setCategoryName] = useState('')
  const [colorIndex, setColorIndex] = useState(0)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const categoryId = categoryName ? categories.find((c) => c.name === categoryName)?.id ?? null : null
  const categoryNameForSubmit = categoryName?.trim() || undefined

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    const p = parseFloat(price)
    if (!name.trim()) {
      setError('Введите название сервиса')
      return
    }
    if (Number.isNaN(p) || p < 0) {
      setError('Введите корректную цену')
      return
    }
    if (!nextPayment) {
      setError('Укажите дату следующего списания')
      return
    }
    setSaving(true)
    try {
      await onSubmit({
        name: name.trim(),
        price: p,
        period,
        next_payment: nextPayment,
        category_id: categoryId,
        categoryName: categoryNameForSubmit,
        color: SUBSCRIPTION_COLORS[colorIndex],
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <header className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm p-4 border-b border-border flex items-center justify-between">
        <button type="button" onClick={onBack} className="p-2 -ml-2 hover:bg-secondary/60 rounded-lg transition-colors">
          <ArrowLeft className="w-5 h-5 text-foreground" />
        </button>
        <span className="text-foreground font-medium">New Subscription</span>
        <button
          type="submit"
          form="add-sub-form"
          disabled={saving}
          className="p-2 -mr-2 hover:bg-secondary/60 rounded-lg transition-colors disabled:opacity-50"
        >
          <Save className="w-5 h-5 text-foreground" />
        </button>
      </header>

      <form id="add-sub-form" onSubmit={handleSubmit} className="p-4 space-y-4">
        {error && <p className="text-sm text-destructive">{error}</p>}

        <div>
          <label className="text-xs text-muted-foreground mb-2 block">Service Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Netflix, Spotify"
            className="w-full bg-secondary/40 border border-border rounded-lg px-4 py-3 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-colors"
          />
        </div>

        <div>
          <label className="text-xs text-muted-foreground mb-2 block">Price</label>
          <div className="relative">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground">₽</span>
            <input
              type="number"
              step="0.01"
              min="0"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="0.00"
              className="w-full bg-secondary/40 border border-border rounded-lg pl-8 pr-4 py-3 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-colors"
            />
          </div>
        </div>

        <div>
          <label className="text-xs text-muted-foreground mb-2 block">Billing Cycle</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setPeriod('monthly')}
              className={`py-3 rounded-lg border transition-colors ${
                period === 'monthly'
                  ? 'bg-foreground text-background border-foreground'
                  : 'bg-secondary/40 text-foreground border-border hover:bg-secondary/60'
              }`}
            >
              Monthly
            </button>
            <button
              type="button"
              onClick={() => setPeriod('yearly')}
              className={`py-3 rounded-lg border transition-colors ${
                period === 'yearly'
                  ? 'bg-foreground text-background border-foreground'
                  : 'bg-secondary/40 text-foreground border-border hover:bg-secondary/60'
              }`}
            >
              Yearly
            </button>
          </div>
        </div>

        <div>
          <label className="text-xs text-muted-foreground mb-2 block">Next Billing Date</label>
          <input
            type="date"
            value={nextPayment}
            onChange={(e) => setNextPayment(e.target.value)}
            className="w-full bg-secondary/40 border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-colors"
          />
        </div>

        <div>
          <label className="text-xs text-muted-foreground mb-2 block">Category</label>
          <select
            value={categoryName}
            onChange={(e) => setCategoryName(e.target.value)}
            className="w-full bg-secondary/40 border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-colors"
          >
            <option value="">—</option>
            {categories.map((c) => (
              <option key={c.id} value={c.name}>
                {c.name}
              </option>
            ))}
            {CATEGORY_OPTIONS.filter((o) => !categories.some((c) => c.name === o)).map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs text-muted-foreground mb-2 block">Color</label>
          <div className="flex gap-3">
            {SUBSCRIPTION_COLORS.map((c, i) => (
              <button
                key={c}
                type="button"
                onClick={() => setColorIndex(i)}
                className={`w-10 h-10 rounded-lg transition-transform ${
                  colorIndex === i ? 'scale-110 ring-2 ring-ring ring-offset-2 ring-offset-background' : ''
                }`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full bg-foreground text-background py-3 rounded-lg mt-6 hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {saving ? 'Сохранение…' : 'Add Subscription'}
        </button>
      </form>
    </>
  )
}
