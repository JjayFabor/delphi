'use client'
import useSWR from 'swr'
import Panel from './Panel'

interface ActivityRow { chat_id: number; role: string; content: string; created_at: string }

const fetcher = (url: string) => fetch(url).then(r => r.json())

export default function ActivityFeed() {
  const { data: rows = [] } = useSWR<ActivityRow[]>('/api/activity', fetcher, { refreshInterval: 30000 })

  return (
    <Panel title="Recent Activity" count="last 15">
      {rows.length === 0 ? (
        <p className="text-center text-sm text-muted py-8">No activity yet.</p>
      ) : rows.map((row, i) => (
        <div key={i} className="flex items-start gap-3 px-4 py-3 border-b border-border last:border-0 hover:bg-[rgba(123,110,246,.04)] transition-colors">
          <span className={`flex-shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded mt-0.5 ${
            row.role === 'user'
              ? 'bg-[rgba(123,110,246,.2)] text-primary'
              : 'bg-[rgba(6,214,160,.15)] text-secondary'
          }`}>
            {row.role.slice(0, 4).toUpperCase()}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-sm truncate">{row.content}</p>
            <p className="text-[11px] text-muted font-mono mt-0.5">
              chat {row.chat_id} · {row.created_at}
            </p>
          </div>
        </div>
      ))}
    </Panel>
  )
}
