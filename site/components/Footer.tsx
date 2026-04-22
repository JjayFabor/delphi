import Link from 'next/link'

export default function Footer() {
  return (
    <footer className="border-t border-border mt-24">
      <div className="mx-auto max-w-7xl px-6 py-12 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div>
          <p className="font-semibold text-text-primary tracking-tight text-sm">claudhaus</p>
          <p className="text-xs text-text-muted mt-1">Personal AI. Self-hosted.</p>
        </div>
        <nav className="flex flex-wrap items-center gap-6 text-sm text-text-muted">
          <Link href="/docs" className="hover:text-text-primary transition-colors">Docs</Link>
          <Link href="/api-reference" className="hover:text-text-primary transition-colors">API Reference</Link>
          <a
            href="https://github.com/JjayFabor/claudhaus"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-text-primary transition-colors"
          >
            GitHub
          </a>
          <a
            href="https://github.com/JjayFabor/claudhaus/blob/main/LICENSE"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-text-primary transition-colors"
          >
            License
          </a>
        </nav>
      </div>
      <div className="border-t border-border">
        <p className="text-center text-xs text-text-muted py-4">
          Independent open-source project. Not affiliated with Anthropic.
        </p>
      </div>
    </footer>
  )
}
