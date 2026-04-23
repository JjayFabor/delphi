'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Menu, X } from 'lucide-react'
import type { NavSection } from '@/lib/nav'

interface SidebarProps {
  nav: NavSection[]
  basePath: '/docs' | '/api-reference'
}

function NavLinks({
  nav,
  basePath,
  pathname,
  onNavigate,
}: {
  nav: NavSection[]
  basePath: string
  pathname: string
  onNavigate?: () => void
}) {
  return (
    <>
      {nav.map(section => (
        <div key={section.title} className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-text-muted mb-3 px-3">
            {section.title}
          </p>
          <ul className="space-y-0.5">
            {section.items.map(item => {
              const href = `${basePath}/${item.slug}`
              const active = pathname === href
              return (
                <li key={item.slug}>
                  <Link
                    href={href}
                    onClick={onNavigate}
                    className={`block text-sm px-3 py-1.5 rounded-md transition-colors ${
                      active
                        ? 'bg-accent/10 text-accent font-medium'
                        : 'text-text-muted hover:text-text-primary hover:bg-surface'
                    }`}
                  >
                    {item.title}
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </>
  )
}

export default function Sidebar({ nav, basePath }: SidebarProps) {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  useEffect(() => { setOpen(false) }, [pathname])
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [open])

  return (
    <>
      {/* Mobile trigger — visible below lg */}
      <div className="lg:hidden mb-4">
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 text-sm text-text-muted hover:text-text-primary border border-border rounded-lg px-3 py-2 transition-colors w-full"
        >
          <Menu size={15} />
          <span>Browse navigation</span>
        </button>

        {open && (
          <>
            <div
              className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
              onClick={() => setOpen(false)}
            />
            <div className="fixed left-0 top-0 h-full w-72 z-50 bg-background border-r border-border overflow-y-auto p-6 shadow-2xl">
              <button
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 text-sm text-text-muted hover:text-text-primary mb-6 transition-colors"
              >
                <X size={16} />
                Close
              </button>
              <NavLinks nav={nav} basePath={basePath} pathname={pathname} onNavigate={() => setOpen(false)} />
            </div>
          </>
        )}
      </div>

      {/* Desktop sidebar — visible at lg+ */}
      <nav aria-label="Sidebar" className="w-60 flex-shrink-0 hidden lg:block">
        <NavLinks nav={nav} basePath={basePath} pathname={pathname} />
      </nav>
    </>
  )
}
