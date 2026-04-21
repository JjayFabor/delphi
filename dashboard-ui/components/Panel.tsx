import type { ReactNode } from 'react'

interface Props {
  title: string
  count?: number | string
  children: ReactNode
  full?: boolean
}

export default function Panel({ title, count, children, full }: Props) {
  return (
    <div className={`bg-card border border-border rounded-xl overflow-hidden${full ? ' col-span-full' : ''}`}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <span className="text-[11px] font-semibold tracking-widest uppercase text-muted">{title}</span>
        {count !== undefined && (
          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full text-primary"
                style={{ background: 'var(--color-primary-dim)' }}>
            {count}
          </span>
        )}
      </div>
      <div className="max-h-80 overflow-y-auto">
        {children}
      </div>
    </div>
  )
}
