'use client'
import { useEffect, useState, useCallback, useRef } from 'react'
import { Search as SearchIcon } from 'lucide-react'

interface SearchResult {
  url: string
  title: string
  excerpt: string
}

declare global {
  interface Window {
    pagefind?: {
      search: (q: string) => Promise<{
        results: Array<{ data: () => Promise<{ url: string; excerpt: string; meta: { title: string } }> }>
      }>
    }
  }
}

export default function Search() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  // Keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen(o => !o)
      }
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // Focus input on open
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50)
    else { setQuery(''); setResults([]) }
  }, [open])

  // Lazy-load Pagefind script
  useEffect(() => {
    if (open && !window.pagefind) {
      const script = document.createElement('script')
      script.src = '/pagefind/pagefind.js'
      script.type = 'module'
      document.head.appendChild(script)
    }
  }, [open])

  const runSearch = useCallback(async (q: string) => {
    if (!q.trim() || !window.pagefind) { setResults([]); return }
    try {
      const res = await window.pagefind.search(q)
      const data = await Promise.all(res.results.slice(0, 8).map(r => r.data()))
      setResults(data.map(d => ({ url: d.url, title: d.meta.title, excerpt: d.excerpt })))
    } catch {
      setResults([])
    }
  }, [])

  useEffect(() => { runSearch(query) }, [query, runSearch])

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border text-text-muted text-sm hover:border-accent transition-colors"
      >
        <SearchIcon size={13} />
        <span>Search</span>
        <kbd className="ml-1 text-xs bg-surface px-1.5 py-0.5 rounded border border-border">⌘K</kbd>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-background/80 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-xl bg-surface border border-border rounded-xl shadow-2xl overflow-hidden mx-4"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
              <SearchIcon size={16} className="text-text-muted flex-shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search documentation..."
                className="flex-1 bg-transparent text-text-primary placeholder-text-muted outline-none text-sm"
              />
              <kbd className="text-xs text-text-muted bg-background px-1.5 py-0.5 rounded border border-border">
                Esc
              </kbd>
            </div>

            {results.length > 0 && (
              <ul className="divide-y divide-border max-h-80 overflow-y-auto">
                {results.map(r => (
                  <li key={r.url}>
                    <a
                      href={r.url}
                      className="block px-4 py-3 hover:bg-background transition-colors"
                      onClick={() => setOpen(false)}
                    >
                      <p className="text-sm font-medium text-text-primary">{r.title}</p>
                      <p
                        className="text-xs text-text-muted mt-0.5 line-clamp-2"
                        dangerouslySetInnerHTML={{ __html: r.excerpt }}
                      />
                    </a>
                  </li>
                ))}
              </ul>
            )}

            {query && results.length === 0 && (
              <p className="px-4 py-6 text-sm text-text-muted text-center">
                No results for &quot;{query}&quot;
              </p>
            )}
          </div>
        </div>
      )}
    </>
  )
}
