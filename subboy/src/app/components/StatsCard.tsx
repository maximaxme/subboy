import type { ReactNode } from 'react'

type Props = {
  label: string
  value: string
  icon?: ReactNode
  trend?: 'up' | 'down'
  trendLabel?: string
  className?: string
}

export function StatsCard({ label, value, icon, trend, trendLabel, className = '' }: Props) {
  return (
    <div className={`bg-secondary/40 border border-border rounded-lg p-4 ${className}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-muted-foreground">{label}</span>
        {icon && <span className="text-muted-foreground w-4 h-4">{icon}</span>}
      </div>
      <p className="text-2xl text-foreground">{value}</p>
      {trend && trendLabel && (
        <div className={`flex items-center gap-1 mt-1 text-xs ${trend === 'up' ? 'text-green-500' : 'text-red-500'}`}>
          {trend === 'up' ? (
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" /></svg>
          ) : (
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" /></svg>
          )}
          <span>{trendLabel}</span>
        </div>
      )}
    </div>
  )
}
