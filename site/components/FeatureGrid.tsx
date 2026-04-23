'use client'
import { useRef } from 'react'
import { Database, Pencil, Plug, Bot, Clock, Wrench } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

const features: { icon: LucideIcon; title: string; desc: string }[] = [
  { icon: Database, title: 'Persistent Memory',  desc: 'Remembers facts, preferences, and past context across every session.' },
  { icon: Pencil,   title: 'Teachable Skills',   desc: 'Teach new workflows just by chatting — no config files, no restarts.' },
  { icon: Plug,     title: 'MCP Connectors',     desc: 'Self-installing integrations: GitHub, HubSpot, Slack, and more.' },
  { icon: Bot,      title: 'Sub-agents',         desc: 'Spawn focused specialists with their own workspaces and tool sets.' },
  { icon: Clock,    title: 'Scheduler',           desc: 'Schedule recurring tasks — reports, reminders, status checks.' },
  { icon: Wrench,   title: 'Self-Improving',     desc: 'Reads and edits its own source code, syntax-checks, and restarts.' },
]

function FeatureCard({ icon: Icon, title, desc }: { icon: LucideIcon; title: string; desc: string }) {
  const ref = useRef<HTMLDivElement>(null)

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const card = ref.current
    if (!card) return
    const { left, top, width, height } = card.getBoundingClientRect()
    const x = (e.clientX - left) / width - 0.5
    const y = (e.clientY - top) / height - 0.5
    card.style.transform = `perspective(700px) rotateX(${(-y * 9).toFixed(2)}deg) rotateY(${(x * 9).toFixed(2)}deg) scale(1.025)`
  }

  const onLeave = () => {
    const card = ref.current
    if (card) card.style.transform = 'perspective(700px) rotateX(0deg) rotateY(0deg) scale(1)'
  }

  return (
    <div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      className="feature-card rounded-xl border border-border bg-surface p-6"
      style={{ transition: 'transform 0.22s ease, box-shadow 0.22s ease', willChange: 'transform' }}
    >
      <div className="w-9 h-9 rounded-lg bg-accent/10 flex items-center justify-center mb-4">
        <Icon size={18} className="text-accent" />
      </div>
      <h3 className="font-semibold text-text-primary mb-2 text-sm">{title}</h3>
      <p className="text-sm text-text-muted leading-relaxed">{desc}</p>
    </div>
  )
}

export default function FeatureGrid() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {features.map((f, i) => (
        <div key={f.title} data-reveal data-delay={`${(i % 3) * 100}`}>
          <FeatureCard icon={f.icon} title={f.title} desc={f.desc} />
        </div>
      ))}
    </div>
  )
}
