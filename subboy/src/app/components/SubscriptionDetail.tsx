import { CreditCard, Calendar, Tag, DollarSign, Bell, Trash2, ArrowLeft } from 'lucide-react'
import { getSubscriptionColor } from './SubscriptionCard'

type SubWithCategory = {
  id: number
  name: string
  price: string
  period: string
  next_payment: string
  created_at: string
  category_id: number | null
  categoryName?: string
}

type Props = {
  subscription: SubWithCategory
  colorIndex?: number
  onBack: () => void
  onDelete: () => void
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`
}

export function SubscriptionDetail({ subscription, colorIndex = 0, onBack, onDelete }: Props) {
  const color = getSubscriptionColor(colorIndex)
  const price = Number(subscription.price).toFixed(2)
  const yearlyTotal = subscription.period === 'yearly' ? Number(subscription.price) : Number(subscription.price) * 12

  return (
    <>
      <header className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm p-4 border-b border-border flex items-center justify-between">
        <button type="button" onClick={onBack} className="p-2 -ml-2 hover:bg-secondary/60 rounded-lg transition-colors">
          <ArrowLeft className="w-5 h-5 text-foreground" />
        </button>
        <span className="text-foreground font-medium">Details</span>
        <button
          type="button"
          onClick={onDelete}
          className="p-2 -mr-2 hover:bg-destructive/20 rounded-lg transition-colors"
        >
          <Trash2 className="w-5 h-5 text-destructive" />
        </button>
      </header>

      <div className="p-4 space-y-6">
        <div className="text-center py-6">
          <div
            className="w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ backgroundColor: color + '20', color }}
          >
            <CreditCard className="w-10 h-10" />
          </div>
          <h1 className="text-2xl text-foreground font-medium mb-2">{subscription.name}</h1>
          {subscription.categoryName && (
            <p className="text-sm text-muted-foreground">{subscription.categoryName}</p>
          )}
        </div>

        <div className="bg-secondary/40 border border-border rounded-lg p-6 text-center">
          <p className="text-xs text-muted-foreground mb-2">Current Plan</p>
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
              <p className="text-xs text-muted-foreground">Next billing</p>
              <p className="text-foreground mt-0.5">{formatDate(subscription.next_payment)}</p>
            </div>
          </div>
          {subscription.categoryName && (
            <div className="bg-secondary/40 border border-border rounded-lg p-4 flex items-center gap-3">
              <Tag className="w-5 h-5 text-muted-foreground shrink-0" />
              <div className="flex-1">
                <p className="text-xs text-muted-foreground">Category</p>
                <p className="text-foreground mt-0.5">{subscription.categoryName}</p>
              </div>
            </div>
          )}
          <div className="bg-secondary/40 border border-border rounded-lg p-4 flex items-center gap-3">
            <DollarSign className="w-5 h-5 text-muted-foreground shrink-0" />
            <div className="flex-1">
              <p className="text-xs text-muted-foreground">Start date</p>
              <p className="text-foreground mt-0.5">{formatDate(subscription.created_at)}</p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
