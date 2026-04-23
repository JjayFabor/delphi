import Link from 'next/link'
import Image from 'next/image'
import { Github } from 'lucide-react'
import ThemeToggle from './ThemeToggle'
import Search from './Search'
import MobileMenu from './MobileMenu'

export default function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-sm">
      <div className="mx-auto max-w-7xl flex items-center justify-between h-14 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold text-text-primary tracking-tight text-sm">
          <Image src="/logo-icon.svg" alt="Delphi" width={24} height={24} />
          <span>delphi</span>
        </Link>

        {/* Desktop nav */}
        <nav aria-label="Main" className="hidden md:flex items-center gap-6 text-sm text-text-muted">
          <Link href="/docs" className="hover:text-text-primary transition-colors">Docs</Link>
          <Link href="/api-reference" className="hover:text-text-primary transition-colors">API Reference</Link>
          <a
            href="https://github.com/JjayFabor/delphi"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-text-primary transition-colors flex items-center gap-1.5"
          >
            <Github size={14} />
            GitHub
          </a>
        </nav>

        <div className="flex items-center gap-1 sm:gap-2">
          <Search />
          <ThemeToggle />
          <Link
            href="/docs/introduction"
            className="hidden sm:inline-flex px-3 sm:px-4 py-1.5 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors"
          >
            Get Started
          </Link>
          <MobileMenu />
        </div>
      </div>
    </header>
  )
}
