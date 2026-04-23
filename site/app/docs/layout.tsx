import { docsNav } from '@/lib/nav'
import Sidebar from '@/components/Sidebar'

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-8 sm:py-12">
      <div className="flex flex-col lg:flex-row gap-6 lg:gap-12">
        <Sidebar nav={docsNav} basePath="/docs" />
        <div className="flex-1 min-w-0 flex flex-col lg:flex-row gap-12">
          {children}
        </div>
      </div>
    </div>
  )
}
