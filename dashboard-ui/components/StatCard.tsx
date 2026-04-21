import type { ReactNode } from 'react'

interface Props {
  label: string
  value: string | number
  icon: ReactNode
  unit?: string
}

export default function StatCard({ label, value, icon, unit }: Props) {
  return (
    <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-2 hover:border-primary hover:shadow-[0_0_0_1px_rgba(123,110,246,.10)] transition-all duration-150">
      <div className="w-8 h-8 rounded-lg flex items-center justify-center text-primary"
           style={{ background: 'var(--color-primary-dim)' }}>
        {icon}
      </div>
      <div className="flex items-end gap-1 leading-none">
        <span className="text-3xl font-bold tracking-tight">{value}</span>
        {unit && <span className="text-sm font-medium text-muted mb-0.5">{unit}</span>}
      </div>
      <div className="text-xs font-medium text-muted">{label}</div>
    </div>
  )
}
