import type { Metadata } from 'next'
import './globals.css'
import { Zap } from 'lucide-react'

export const metadata: Metadata = {
  title: 'claudhaus',
  description: 'Personal AI command center dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="sticky top-0 z-50 flex items-center justify-between px-6 h-14 bg-surface border-b border-border">
          <div className="flex items-center gap-2 font-bold text-sm tracking-tight">
            <Zap size={16} className="text-primary" />
            claudhaus
          </div>
          <div className="flex items-center gap-5 text-xs text-muted">
            <span className="flex items-center gap-1.5 text-secondary font-medium">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-secondary shadow-[0_0_6px_var(--color-secondary)] animate-pulse" />
              online
            </span>
          </div>
        </header>
        <main className="max-w-[1200px] mx-auto px-6 py-8 pb-16">
          {children}
        </main>
      </body>
    </html>
  )
}
