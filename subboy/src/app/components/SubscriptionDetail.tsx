import { useState } from 'react'
import { CreditCard, Calendar, Tag, DollarSign, Trash2, ArrowLeft, Edit2, Check, X, Play, Pause } from 'lucide-react'
import { getSubscriptionColor } from './SubscriptionCard'
import type { CategoryApi } from '@/app/api'

type SubWithCategory = {
  id: number
  name: string
  price: string
  period: string
  next_payment: string
  created_at: string
  category_id: number | null
  categoryName?: string
  is_active: boolean
}

type Props = {
  subscription: SubWithCategory
  categories: CategoryApi[]
  colorIndex?: number
  onBack: () => void
  onDelete: () => void
  onToggle: () => Promise<void>
  onUpdate: (data: { name: string; price: number; period: string; next_payment: string; category_id: number | null }) => Promise<void>
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`
}

export function SubscriptionDetail({ subscription, categories, colorIndex = 0, onBack, onDelete, onToggle, onUpdate }: Props) {
  const color = getSubscriptionColor(colorIndex)
  const price = Number(subscription.price).toFixed(2)
  const yearlyTotal = subscription.period === 'yearly' ? Number(subscription.price) : Number(subscription.price) * 12

  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [toggling, setToggling] = useState(false)
  const [editName, setEditName] = useState(subscription.name)
  const [editPrice, setEditPrice] = useState(String(Number(subscription.price)))
  const [editPeriod, setEditPeriod] = useState<'monthly' | 'yearly'>(
    subscription.period === 'yearly' ? 'yearly' : 'monthly'
  )
  const [editDate, setEditDate] = useState(subscription.next_payment.slice(0, 10))
  const [editCategoryId, setEditCategoryId] = useState<number | null>(subscription.category_id)
  const [editError, setEditError] = useState('')

  const startEditing = () => {
    setEditName(subscription.name)
    setEditPrice(String(Number(subscription.price)))
    setEditPeriod(subscription.period === 'yearly' ? 'yearly' : 'monthly')
    setEditDate(subscription.next_payment.slice(0, 10))
    setEditCategoryId(subscription.category_id)
    setEditError('')
    setEditing(true)
  }

  const handleSave = async () => {
    const p = parseFloat(editPrice)
    if (!editName.trim()) { setEditError('Введите название'); return }
    if (Number.isNaN(p) || p < 0) { setEditError('Укажите корректную цену'); return }
    if (!editDate) { setEditError('Укажите дату'); return }
    setSaving(true)
    try {
      await onUpdate({
        name: editName.trim(),
        price: p,
        period: editPeriod,
        next_payment: editDate,
        category_id: editCategoryId,
      })
      setEditing(false)
    } catch (e) {
      setEditError(e instanceof Error ? e.message : 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async () => {
    setToggling(true)
    try {
      await onToggle()
    } finally {
      setToggling(false)
    }
  }

  return (
    <>
      <header className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm p-4 border-b border-border flex items-center justify-between">
        <button type="button" onClick={onBack} className="p-2 -ml-2 hover:bg-secondary/60 rounded-lg transition-colors">
          <ArrowLeft className="w-5 h-5 text-foreground" />
        </button>
        <span className="text-foreground font-medium">{editing ? 'Редактирование' : 'Подписка'}</span>
        <div className="flex items-center gap-1">
          {editing ? (
            <>
              <button type="button" onClick={() => setEditing(false)} className="p-2 hover:bg-secondary/60 rounded-lg transition-colors">
                <X className="w-5 h-5 text-muted-foreground" />
              </button>
              <button type="button" onClick={handleSave} disabled={saving} className="p-2 hover:bg-secondary/60 rounded-lg transition-colors disabled:opacity-50">
                <Check className="w-5 h-5 text-foreground" />
              </button>
            </>
          ) : (
            <>
              <button type="button" onClick={startEditing} className="p-2 hover:bg-secondary/60 rounded-lg transition-colors">
                <Edit2 className="w-4 h-4 text-foreground" />
              </button>
              <button type="button" onClick={onDelete} className="p-2 hover:bg-destructive/20 rounded-lg transition-colors">
                <Trash2 className="w-5 h-5 text-destructive" />
              </button>
            </>
          )}
        </div>
      </header>

      <div className="p-4 space-y-6">
        {editing ? (
          <div className="space-y-4">
            {editError && <p className="text-sm text-destructive">{editError}</p>}
            <div>
              <label className="text-xs text-muted-foreground mb-2 block">Название</label>
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-full bg-secondary/40 border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-2 block">Цена (₽)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={editPrice}
                onChange={(e) => setEditPrice(e.target.value)}
                className="w-full bg-secondary/40 border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-2 block">Период</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setEditPeriod('monthly')}
                  className={`py-3 rounded-lg border transition-colors ${
                    editPeriod === 'monthly'
                      ? 'bg-foreground text-background border-foreground'
                      : 'bg-secondary/40 text-foreground border-border hover:bg-secondary/60'
                  }`}
                >
                  Месяц
                </button>
                <button
                  type="button"
                  onClick={() => setEditPeriod('yearly')}
                  className={`py-3 rounded-lg border transition-colors ${
                    editPeriod === 'yearly'
                      ? 'bg-foreground text-background border-foreground'
                      : 'bg-secondary/40 text-foreground border-border hover:bg-secondary/60'
                  }`}
                >
                  Год
                </button>
              </div>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-2 block">Следующее списание</label>
              <input
                type="date"
                value={editDate}
                onChange={(e) => setEditDate(e.target.value)}
                className="w-full bg-secondary/40 border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-2 block">Категория</label>
              <select
                value={editCategoryId ?? ''}
                onChange={(e) => setEditCategoryId(e.target.value ? Number(e.target.value) : null)}
                className="w-full bg-secondary/40 border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">—</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="w-full bg-foreground text-background py-3 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {saving ? 'Сохранение…' : 'Сохранить'}
            </button>
          </div>
        ) : (
          <>
            <div className="text-center py-6">
              <div
                className={`w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-4 ${!subscription.is_active ? 'opacity-50' : ''}`}
                style={{ backgroundColor: color + '20', color }}
              >
                <CreditCard className="w-10 h-10" />
              </div>
              <h1 className="text-2xl text-foreground font-medium mb-2">{subscription.name}</h1>
              {subscription.categoryName && (
                <p className="text-sm text-muted-foreground">{subscription.categoryName}</p>
              )}
              {!subscription.is_active && (
                <span className="inline-block mt-2 text-xs font-medium px-2 py-1 rounded bg-secondary text-muted-foreground uppercase tracking-wide">
                  На паузе
                </span>
              )}
            </div>

            <div className="bg-secondary/40 border border-border rounded-lg p-6 text-center">
              <p className="text-xs text-muted-foreground mb-2">Тариф</p>
              <p className="text-4xl text-foreground mb-1">{price} ₽</p>
              <p className="text-sm text-muted-foreground">
                в {subscription.period === 'yearly' ? 'год' : 'месяц'}
              </p>
              <div className="border-t border-border mt-4 pt-4">
                <p className="text-xs text-muted-foreground">В год</p>
                <p className="text-foreground mt-1">{yearlyTotal.toFixed(2)} ₽</p>
              </div>
            </div>

            <div className="space-y-3">
              <div className="bg-secondary/40 border border-border rounded-lg p-4 flex items-center gap-3">
                <Calendar className="w-5 h-5 text-muted-foreground shrink-0" />
                <div className="flex-1">
                  <p className="text-xs text-muted-foreground">Следующее списание</p>
                  <p className="text-foreground mt-0.5">{formatDate(subscription.next_payment)}</p>
                </div>
              </div>
              {subscription.categoryName && (
                <div className="bg-secondary/40 border border-border rounded-lg p-4 flex items-center gap-3">
                  <Tag className="w-5 h-5 text-muted-foreground shrink-0" />
                  <div className="flex-1">
                    <p className="text-xs text-muted-foreground">Категория</p>
                    <p className="text-foreground mt-0.5">{subscription.categoryName}</p>
                  </div>
                </div>
              )}
              <div className="bg-secondary/40 border border-border rounded-lg p-4 flex items-center gap-3">
                <DollarSign className="w-5 h-5 text-muted-foreground shrink-0" />
                <div className="flex-1">
                  <p className="text-xs text-muted-foreground">Добавлена</p>
                  <p className="text-foreground mt-0.5">{formatDate(subscription.created_at)}</p>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={handleToggle}
              disabled={toggling}
              className={`w-full flex items-center justify-center gap-2 py-3 rounded-lg border transition-colors disabled:opacity-50 ${
                subscription.is_active
                  ? 'border-border text-muted-foreground hover:bg-secondary/60'
                  : 'border-border text-foreground hover:bg-secondary/60'
              }`}
            >
              {subscription.is_active ? (
                <><Pause className="w-4 h-4" /> Приостановить</>
              ) : (
                <><Play className="w-4 h-4" /> Возобновить</>
              )}
            </button>
          </>
        )}
      </div>
    </>
  )
}
