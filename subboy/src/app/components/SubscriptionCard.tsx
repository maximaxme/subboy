import { CreditCard, ChevronRight } from 'lucide-react'

const SUBSCRIPTION_COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', '#ef4444'] as const

function getColor(index: number): string {
  return SUBSCRIPTION_COLORS[index % SUBSCRIPTION_COLORS.length]
}

type Props = {
  name: string
  price: string
  period: 'monthly' | 'yearly'
  nextBilling: string
  categoryName?: string
  colorIndex?: number
  onClick: () => void
}

export function SubscriptionCard({
  name,
  price,
  period,
  nextBilling,
  categoryName,
  colorIndex = 0,
  onClick,
}: Props) {
  const color = getColor(colorIndex)
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left bg-secondary/40 hover:bg-secondary/60 border border-border rounded-lg p-4 transition-colors group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
            style={{ backgroundColor: color + '20', color }}
          >
            <CreditCard className="w-5 h-5" />
          </div>
          <div>
            <p className="text-foreground font-medium">{name}</p>
            {categoryName && (
              <p className="text-xs text-muted-foreground mt-0.5">{categoryName}</p>
            )}
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground shrink-0" />
      </div>
      <div className="flex items-center justify-between">
        <span className="text-foreground">
          {price} ₽
          <span className="text-xs text-muted-foreground ml-1">/{period === 'monthly' ? 'мес' : 'год'}</span>
        </span>
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
          {nextBilling}
        </span>
      </div>
    </button>
  )
}

export { getColor as getSubscriptionColor }
