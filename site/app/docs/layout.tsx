import { docsNav } from '@/lib/nav'
import Sidebar from '@/components/Sidebar'

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-7xl px-6 py-12">
      <div className="flex gap-12">
        <Sidebar nav={docsNav} basePath="/docs" />
        <div className="flex-1 min-w-0 flex gap-12">
          {children}
        </div>
      </div>
    </div>
  )
}
