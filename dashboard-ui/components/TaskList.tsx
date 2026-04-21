'use client'
import useSWR from 'swr'
import Panel from './Panel'

interface TaskRow { id: number; chat_id: number; task_prompt: string; schedule_str: string; enabled: boolean }

const fetcher = (url: string) => fetch(url).then(r => r.json())

export default function TaskList() {
  const { data: tasks = [] } = useSWR<TaskRow[]>('/api/tasks', fetcher, { refreshInterval: 30000 })

  return (
    <Panel title="Scheduled Tasks" count={tasks.length}>
      {tasks.length === 0 ? (
        <p className="text-center text-sm text-muted py-8">No scheduled tasks.</p>
      ) : tasks.map(t => (
        <div key={t.id} className="flex items-center gap-3 px-4 py-3 border-b border-border last:border-0 hover:bg-[rgba(123,110,246,.04)] transition-colors">
          <span className="font-mono text-[11px] text-muted w-7 flex-shrink-0">#{t.id}</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm truncate">{t.task_prompt}</p>
            <p className="text-[11px] font-mono text-muted mt-0.5">{t.schedule_str}</p>
          </div>
          <span className={`flex-shrink-0 w-2 h-2 rounded-full ${
            t.enabled
              ? 'bg-secondary shadow-[0_0_5px_var(--color-secondary)]'
              : 'bg-muted'
          }`} />
        </div>
      ))}
    </Panel>
  )
}
