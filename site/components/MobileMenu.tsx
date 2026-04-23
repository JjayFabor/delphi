'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Menu, X, Github } from 'lucide-react'

export default function MobileMenu() {
  const [open, setOpen] = useState(false)
  const pathname = usePathname()

  // Close on route change
  useEffect(() => { setOpen(false) }, [pathname])

  // Prevent body scroll when open
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [open])

  return (
    <div className="md:hidden">
      <button
        onClick={() => setOpen(!open)}
        aria-label={open ? 'Close menu' : 'Open menu'}
        aria-expanded={open}
        className="p-2 rounded-md text-text-muted hover:text-text-primary hover:bg-surface transition-colors"
      >
        {open ? <X size={20} /> : <Menu size={20} />}
      </button>

      {open && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 top-14 z-40 bg-black/40 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          {/* Drawer */}
          <div className="fixed left-0 right-0 top-14 z-50 bg-background border-b border-border shadow-xl px-6 py-6 flex flex-col gap-4">
            <Link href="/docs" className="text-sm font-medium text-text-primary hover:text-accent transition-colors py-2 border-b border-border">
              Docs
            </Link>
            <Link href="/api-reference" className="text-sm font-medium text-text-primary hover:text-accent transition-colors py-2 border-b border-border">
              API Reference
            </Link>
            <a
              href="https://github.com/JjayFabor/delphi"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-text-primary hover:text-accent transition-colors py-2 border-b border-border flex items-center gap-2"
            >
              <Github size={15} />
              GitHub
            </a>
            <Link
              href="/docs/introduction"
              className="mt-2 text-center px-4 py-2.5 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors"
            >
              Get Started
            </Link>
          </div>
        </>
      )}
    </div>
  )
}
