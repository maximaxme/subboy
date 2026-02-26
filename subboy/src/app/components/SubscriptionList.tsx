import { SubscriptionCard } from './SubscriptionCard'
import type { SubscriptionApi } from '@/app/api'
import type { CategoryApi } from '@/app/api'

type SubWithCategory = SubscriptionApi & { categoryName?: string }

type Props = {
  subscriptions: SubWithCategory[]
  categories: CategoryApi[]
  onSelect: (sub: SubWithCategory) => void
}

function formatNextBilling(dateStr: string): string {
  const d = new Date(dateStr)
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`
}

export function SubscriptionList({ subscriptions, categories, onSelect }: Props) {
  const getCategoryName = (id: number | null) =>
    id ? categories.find((c) => c.id === id)?.name : undefined

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">All Services</span>
        <span className="text-xs text-muted-foreground">{subscriptions.length}</span>
      </div>
      <div className="space-y-2">
        {subscriptions.map((sub, i) => (
          <SubscriptionCard
            key={sub.id}
            name={sub.name}
            price={Number(sub.price).toFixed(2)}
            period={sub.period === 'yearly' ? 'yearly' : 'monthly'}
            nextBilling={formatNextBilling(sub.next_payment)}
            categoryName={getCategoryName(sub.category_id)}
            colorIndex={i}
            onClick={() => onSelect({ ...sub, categoryName: getCategoryName(sub.category_id) })}
          />
        ))}
      </div>
    </div>
  )
}
