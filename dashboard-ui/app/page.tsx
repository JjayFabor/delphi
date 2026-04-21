import { Users, Clock, Pencil, Database, Plug, BookOpen, Moon } from 'lucide-react'
import StatCard from '@/components/StatCard'
import Panel from '@/components/Panel'
import ActivityFeed from '@/components/ActivityFeed'
import TaskList from '@/components/TaskList'
import { getSessionStats } from '@/lib/db'
import { getMemoryStats, getSkillCount, getConnectorCount, getSkills, getConnectors } from '@/lib/files'

export const dynamic = 'force-dynamic'
export const revalidate = 0

export default function DashboardPage() {
  const { session_count, task_count } = getSessionStats()
  const { memory_kb, dreams_count, daily_notes } = getMemoryStats()
  const skill_count = getSkillCount()
  const connector_count = getConnectorCount()
  const skills = getSkills()
  const connectors = getConnectors()

  return (
    <div className="space-y-6">
      {/* Stat cards */}
      <div>
        <p className="text-[11px] font-semibold tracking-widest uppercase text-muted mb-3">Overview</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          <StatCard label="Active sessions"   value={session_count}  icon={<Users size={15} />} />
          <StatCard label="Scheduled tasks"   value={task_count}     icon={<Clock size={15} />} />
          <StatCard label="Skills"            value={skill_count}    icon={<Pencil size={15} />} />
          <StatCard label="Memory"            value={memory_kb}      icon={<Database size={15} />} unit="kb" />
          <StatCard label="Connectors"        value={connector_count} icon={<Plug size={15} />} />
          <StatCard label="Daily notes"       value={daily_notes}    icon={<BookOpen size={15} />} />
          <StatCard label="Dreams"            value={dreams_count}   icon={<Moon size={15} />} />
        </div>
      </div>

      {/* Activity + Tasks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <ActivityFeed />
        <TaskList />
      </div>

      {/* Skills + Connectors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Panel title="Skills" count={skills.length}>
          {skills.length === 0 ? (
            <p className="text-center text-sm text-muted py-8">No skills saved yet.</p>
          ) : skills.map(s => (
            <div key={s.name} className="flex items-center gap-3 px-4 py-2.5 border-b border-border last:border-0 hover:bg-[rgba(123,110,246,.04)] transition-colors">
              <span className="font-mono text-xs text-primary flex-shrink-0 w-36 truncate">{s.name}</span>
              <span className="text-xs text-muted truncate">{s.preview}</span>
            </div>
          ))}
        </Panel>

        <Panel title="Connectors" count={`${connectors.filter(c => c.installed).length} / ${connectors.length}`}>
          {connectors.map(c => (
            <div key={c.name} className="flex items-center gap-3 px-4 py-2.5 border-b border-border last:border-0 hover:bg-[rgba(123,110,246,.04)] transition-colors">
              <span className={`font-semibold text-sm capitalize flex-shrink-0 w-28 ${c.installed ? 'text-txt' : 'text-muted'}`}>
                {c.name}
              </span>
              <span className="text-xs text-muted flex-1 truncate">{c.description}</span>
              <span className={`flex-shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded ${
                c.installed
                  ? 'bg-[rgba(6,214,160,.15)] text-secondary'
                  : 'bg-[rgba(90,90,122,.12)] text-muted'
              }`}>
                {c.installed ? 'ON' : 'OFF'}
              </span>
            </div>
          ))}
        </Panel>
      </div>
    </div>
  )
}
