import { Info, AlertTriangle, AlertOctagon } from 'lucide-react'

interface CalloutProps {
  type: 'note' | 'warning' | 'danger'
  children: React.ReactNode
}

const variants = {
  note:    { border: 'border-blue-500',  bg: 'bg-blue-500/10',  Icon: Info,          text: 'text-blue-400' },
  warning: { border: 'border-amber-500', bg: 'bg-amber-500/10', Icon: AlertTriangle, text: 'text-amber-400' },
  danger:  { border: 'border-red-500',   bg: 'bg-red-500/10',   Icon: AlertOctagon,  text: 'text-red-400' },
}

const labels: Record<CalloutProps['type'], string> = {
  note: 'Note',
  warning: 'Warning',
  danger: 'Danger',
}

export default function Callout({ type, children }: CalloutProps) {
  const { border, bg, Icon, text } = variants[type]
  return (
    <div
      role="note"
      aria-label={labels[type]}
      className={`flex gap-3 rounded-r-lg border-l-4 ${border} ${bg} px-4 py-3 my-4`}
    >
      <Icon size={16} aria-hidden="true" className={`${text} flex-shrink-0 mt-0.5`} />
      <div className="text-sm text-text-primary leading-relaxed">{children}</div>
    </div>
  )
}
